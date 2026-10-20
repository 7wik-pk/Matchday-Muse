// Package espn is the football adapter over ESPN's unofficial site API. The
// API is undocumented, so every response is cached and requests are spaced
// out.
package espn

import (
	"cmp"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"maps"
	"net/http"
	"net/url"
	"regexp"
	"slices"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/go-resty/resty/v2"

	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/cache"
	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/sports"
)

const (
	DefaultBaseURL = "https://site.api.espn.com/apis/site/v2/sports/soccer"
	UserAgent      = "matchday-muse/0.1 (+https://github.com/7wik-pk/Matchday-Muse)"

	// MaxRange bounds find_matches: a calendar month plus a daylight-saving hour.
	MaxRange = 32 * 24 * time.Hour

	// ESPN gives kickoff times only.
	matchLength = 2 * time.Hour

	recentTTL   = 15 * time.Minute
	finishedTTL = 7 * 24 * time.Hour
)

var leagues = map[string]string{
	"eng.1": "Premier League",
}

// Options configures an Adapter. Zero values select the defaults.
type Options struct {
	BaseURL   string
	Transport http.RoundTripper // nil uses resty's default; the recorder wraps it
	Cache     *cache.Cache      // nil disables caching
	MinGap    time.Duration
	Logger    *slog.Logger
	Now       func() time.Time
}

// Adapter implements sports.Adapter for football.
type Adapter struct {
	base   string
	http   *resty.Client
	cache  *cache.Cache
	minGap time.Duration
	log    *slog.Logger
	now    func() time.Time

	mu   sync.Mutex
	last time.Time
}

func New(o Options) *Adapter {
	a := &Adapter{base: o.BaseURL, cache: o.Cache, minGap: o.MinGap, log: o.Logger, now: o.Now}
	if a.base == "" {
		a.base = DefaultBaseURL
	}
	if a.log == nil {
		a.log = slog.New(slog.DiscardHandler)
	}
	if a.now == nil {
		a.now = time.Now
	}
	a.http = resty.New().
		SetBaseURL(a.base).
		SetTimeout(15*time.Second).
		SetHeader("User-Agent", UserAgent).
		SetHeader("Accept", "application/json").
		SetResponseBodyLimit(16 << 20).
		// Network errors are retried by default; server errors are too.
		SetRetryCount(2).
		AddRetryCondition(func(r *resty.Response, err error) bool {
			return err == nil && r.StatusCode() >= http.StatusInternalServerError
		}).
		OnBeforeRequest(func(_ *resty.Client, r *resty.Request) error {
			return a.wait(r.Context())
		}).
		OnAfterResponse(func(_ *resty.Client, r *resty.Response) error {
			a.log.Debug("espn fetch", "url", r.Request.URL, "status", r.StatusCode(),
				"bytes", len(r.Body()), "ms", r.Time().Milliseconds())
			return nil
		})
	if o.Transport != nil {
		a.http.SetTransport(o.Transport)
	}
	return a
}

func (a *Adapter) Sport() string { return "football" }

func (a *Adapter) Competitions() []sports.Competition {
	out := make([]sports.Competition, 0, len(leagues))
	for code, name := range leagues {
		out = append(out, sports.Competition{
			Sport: "football", League: code, Name: name, Source: "ESPN", Coverage: sports.FullEvents,
		})
	}
	slices.SortFunc(out, func(x, y sports.Competition) int { return strings.Compare(x.League, y.League) })
	return out
}

func (a *Adapter) FindMatches(ctx context.Context, league string, from, to time.Time) ([]sports.Match, error) {
	if err := checkLeague(league); err != nil {
		return nil, err
	}
	if !to.After(from) {
		return nil, errors.New("to must be after from")
	}
	if to.Sub(from) > MaxRange {
		return nil, fmt.Errorf("range is longer than %d days", int(MaxRange.Hours()/24))
	}
	// The scoreboard takes one day per request, and its days need not be UTC
	// days, so fetch a day either side and filter on kickoff time.
	first := from.UTC().Truncate(24*time.Hour).AddDate(0, 0, -1)
	last := to.UTC().Truncate(24*time.Hour).AddDate(0, 0, 1)
	seen := map[string]bool{}
	var matches []sports.Match
	for day := first; !day.After(last); day = day.AddDate(0, 0, 1) {
		var sb scoreboard
		ttl := recentTTL
		if a.now().Sub(day) > 3*24*time.Hour {
			ttl = finishedTTL
		}
		q := url.Values{"dates": {day.Format("20060102")}}
		if err := a.getJSON(ctx, "/"+league+"/scoreboard", q, &sb, func() time.Duration { return ttl }); err != nil {
			return nil, err
		}
		for _, ev := range sb.Events {
			m, kickoff, ok := matchFrom(league, ev.ID, ev.Date, ev.Status, ev.Competitions)
			if !ok || seen[m.ID] || m.Status != "completed" || kickoff.Before(from) || !kickoff.Before(to) {
				continue
			}
			seen[m.ID] = true
			matches = append(matches, m)
		}
	}
	slices.SortFunc(matches, func(x, y sports.Match) int {
		return cmp.Or(strings.Compare(x.Kickoff, y.Kickoff), strings.Compare(x.ID, y.ID))
	})
	if matches == nil {
		matches = []sports.Match{}
	}
	return matches, nil
}

func (a *Adapter) MatchEvents(ctx context.Context, league, matchID string) (sports.Timeline, error) {
	if err := checkLeague(league); err != nil {
		return sports.Timeline{}, err
	}
	if _, err := strconv.ParseUint(matchID, 10, 64); err != nil {
		return sports.Timeline{}, fmt.Errorf("match_id %q is not an ESPN match id", matchID)
	}
	var s summary
	q := url.Values{"event": {matchID}}
	err := a.getJSON(ctx, "/"+league+"/summary", q, &s, func() time.Duration {
		if c := s.Header.Competitions; len(c) > 0 && c[0].Status != nil && c[0].Status.Type.Completed {
			return finishedTTL
		}
		return recentTTL
	})
	if err != nil {
		return sports.Timeline{}, err
	}
	m, _, ok := matchFrom(league, s.Header.ID, "", status{}, s.Header.Competitions)
	if !ok {
		return sports.Timeline{}, fmt.Errorf("ESPN has no match %s in %s", matchID, league)
	}
	if s.Article != nil {
		m.Summary = oneLine(s.Article.Description)
	}
	if m.Venue == "" {
		m.Venue = s.GameInfo.Venue.FullName
	}
	t := sports.Timeline{
		Match:     m,
		Coverage:  sports.ScoresOnly,
		Events:    timeline(matchID, s),
		TeamStats: teamStats(m, s.Boxscore.Teams),
		Sources: []sports.Source{{
			Title:     m.Title + ": match events",
			URL:       "https://www.espn.com/soccer/match/_/gameId/" + matchID,
			Publisher: "ESPN",
		}},
	}
	if len(t.Events) > 0 {
		t.Coverage = sports.FullEvents
	}
	if s.Article != nil && strings.TrimSpace(s.Article.Headline) != "" {
		t.Sources = append(t.Sources, sports.Source{
			Title:       strings.TrimSpace(s.Article.Headline),
			URL:         "https://www.espn.com/soccer/report/_/gameId/" + matchID,
			Publisher:   "ESPN",
			PublishedAt: rfc3339(s.Article.Published),
		})
	}
	return t, nil
}

func checkLeague(league string) error {
	if _, ok := leagues[league]; !ok {
		return fmt.Errorf("unknown football league %q; supported: %s", league, strings.Join(slices.Sorted(maps.Keys(leagues)), ", "))
	}
	return nil
}

// getJSON fetches path from the cache or from ESPN, decodes it into v, and
// caches a fresh response for the TTL that ttl returns once v is decoded.
func (a *Adapter) getJSON(ctx context.Context, path string, q url.Values, v any, ttl func() time.Duration) error {
	u := a.base + path + "?" + q.Encode()
	if a.cache != nil {
		if body, ok := a.cache.Get(u); ok {
			return json.Unmarshal(body, v)
		}
	}
	body, err := a.fetch(ctx, path, q)
	if err != nil {
		return err
	}
	if err := json.Unmarshal(body, v); err != nil {
		return fmt.Errorf("ESPN %s: decoding: %w", path, err)
	}
	if a.cache != nil {
		if err := a.cache.Put(u, body, ttl()); err != nil {
			a.log.Warn("cache write failed", "url", u, "err", err)
		}
	}
	return nil
}

func (a *Adapter) fetch(ctx context.Context, path string, q url.Values) ([]byte, error) {
	resp, err := a.http.R().SetContext(ctx).SetQueryParamsFromValues(q).Get(path)
	if err != nil {
		return nil, fmt.Errorf("ESPN request failed: %w", err)
	}
	if resp.StatusCode() != http.StatusOK {
		return nil, fmt.Errorf("ESPN returned HTTP %d for %s", resp.StatusCode(), resp.Request.URL)
	}
	return resp.Body(), nil
}

// wait spaces network requests at least minGap apart.
func (a *Adapter) wait(ctx context.Context) error {
	a.mu.Lock()
	defer a.mu.Unlock()
	if d := a.minGap - time.Since(a.last); d > 0 {
		select {
		case <-time.After(d):
		case <-ctx.Done():
			return ctx.Err()
		}
	}
	a.last = time.Now()
	return nil
}

// matchFrom normalises a scoreboard event or a summary header. The
// competition's own date and status win over the event's when present.
func matchFrom(league, id, date string, st status, comps []competition) (sports.Match, time.Time, bool) {
	if id == "" || len(comps) == 0 {
		return sports.Match{}, time.Time{}, false
	}
	c := comps[0]
	if c.Date != "" {
		date = c.Date
	}
	if c.Status != nil {
		st = *c.Status
	}
	kickoff, err := parseTime(date)
	if err != nil {
		return sports.Match{}, time.Time{}, false
	}
	m := sports.Match{
		ID:          id,
		Sport:       "football",
		League:      league,
		Kickoff:     kickoff.Format(time.RFC3339),
		EndEstimate: kickoff.Add(matchLength).Format(time.RFC3339),
		Status:      statusName(st),
		Venue:       c.Venue.FullName,
	}
	var home, away *sports.Participant
	for _, comp := range c.Competitors {
		p := sports.Participant{
			Name:         comp.Team.DisplayName,
			ShortName:    comp.Team.ShortDisplayName,
			Abbreviation: comp.Team.Abbreviation,
			Role:         comp.HomeAway,
			Score:        comp.Score,
			Winner:       comp.Winner,
		}
		m.Participants = append(m.Participants, p)
	}
	slices.SortStableFunc(m.Participants, func(x, y sports.Participant) int {
		return cmp.Compare(roleOrder[x.Role], roleOrder[y.Role])
	})
	for i := range m.Participants {
		switch m.Participants[i].Role {
		case "home":
			home = &m.Participants[i]
		case "away":
			away = &m.Participants[i]
		}
	}
	if home == nil || away == nil {
		return sports.Match{}, time.Time{}, false
	}
	m.Title = home.Name + " v " + away.Name
	if m.Status == "completed" {
		m.FinalResult = fmt.Sprintf("%s %s–%s %s", home.Name, home.Score, away.Score, away.Name)
	}
	for _, h := range c.Headlines {
		if s := oneLine(h.Description); s != "" {
			m.Summary = s
			break
		}
	}
	return m, kickoff, true
}

var roleOrder = map[string]int{"home": 0, "away": 1}

func statusName(st status) string {
	switch {
	case st.Type.Completed:
		return "completed"
	case st.Type.State == "in":
		return "in_progress"
	case st.Type.State == "pre":
		return "scheduled"
	default:
		return "other"
	}
}

var eventTypes = map[string]string{
	"kickoff":              "kickoff",
	"halftime":             "half_time",
	"start-2nd-half":       "second_half",
	"end-regular-time":     "full_time",
	"penalty---scored":     "penalty_goal",
	"own-goal":             "own_goal",
	"penalty---missed":     "penalty_miss",
	"penalty---saved":      "penalty_miss",
	"yellow-card":          "yellow_card",
	"red-card":             "red_card",
	"substitution":         "sub",
	"deleted-after-review": "var",
	"shot-on-target":       "shot_on_target",
	"shot-off-target":      "shot_off_target",
	"shot-blocked":         "shot_blocked",
	"shot-hit-woodwork":    "woodwork",
	"foul":                 "foul",
	"handball":             "handball",
	"corner-awarded":       "corner",
	"offside":              "offside",
	"retired":              "injury",
}

// Stoppages for treatment carry no story, so they are dropped.
var droppedTypes = map[string]bool{"start-delay": true, "end-delay": true}

func eventType(p play) string {
	slug := p.Type.Type
	if t, ok := eventTypes[slug]; ok {
		return t
	}
	switch {
	case strings.HasPrefix(slug, "var"):
		return "var"
	case slug == "goal" || strings.HasPrefix(slug, "goal---"):
		return "goal" // goal---header, goal---volley, goal---free-kick
	}
	return "other"
}

// scoreLine finds "Brentford 1, Liverpool 0." in a goal or break description.
// ESPN names the home side first.
var scoreLine = regexp.MustCompile(`([A-Z][^.,!]*?) (\d+), ([A-Z][^.,!]*?) (\d+)\.`)

var scoreTypes = map[string]bool{
	"goal": true, "penalty_goal": true, "own_goal": true, "half_time": true, "full_time": true,
}

// timeline prefers the full commentary, which includes shots, VAR reviews and
// fouls, and falls back to the key events.
func timeline(matchID string, s summary) []sports.Event {
	type item struct {
		text string
		p    play
	}
	var items []item
	for _, c := range s.Commentary {
		if c.Play != nil {
			items = append(items, item{cmp.Or(c.Text, c.Play.Text), *c.Play})
		}
	}
	if len(items) == 0 {
		for _, p := range s.KeyEvents {
			items = append(items, item{p.Text, p})
		}
	}
	events := []sports.Event{}
	for _, it := range items {
		if droppedTypes[it.p.Type.Type] {
			continue
		}
		e := sports.Event{
			Clock:       clock(it.p.Clock.DisplayValue),
			Type:        eventType(it.p),
			Actors:      []string{},
			Description: strings.TrimSpace(it.text),
			SourceRef:   fmt.Sprintf("espn:%s:play:%s", matchID, it.p.ID),
		}
		if it.p.Team != nil {
			e.Team = it.p.Team.DisplayName
		}
		for _, part := range it.p.Participants {
			if n := part.Athlete.DisplayName; n != "" {
				e.Actors = append(e.Actors, n)
			}
		}
		if scoreTypes[e.Type] {
			if m := scoreLine.FindStringSubmatch(e.Description); m != nil {
				e.ScoreAfter = m[2] + "-" + m[4]
			}
		}
		events = append(events, e)
	}
	return events
}

// clock turns ESPN's "45'+8'" into "45+8'", and the empty kickoff clock into "0'".
func clock(v string) string {
	if v == "" {
		return "0'"
	}
	return strings.Replace(v, "'+", "+", 1)
}

func teamStats(m sports.Match, teams []boxTeam) []sports.TeamStats {
	out := []sports.TeamStats{}
	for _, p := range m.Participants {
		for _, t := range teams {
			if t.Team.DisplayName != p.Name {
				continue
			}
			ts := sports.TeamStats{Team: p.Name}
			for _, st := range t.Statistics {
				f, err := strconv.ParseFloat(st.DisplayValue, 64)
				if err != nil {
					continue
				}
				switch st.Name {
				case "possessionPct":
					ts.PossessionPct = f
				case "totalShots":
					ts.Shots = int(f)
				case "shotsOnTarget":
					ts.ShotsOnTarget = int(f)
				case "wonCorners":
					ts.Corners = int(f)
				case "foulsCommitted":
					ts.Fouls = int(f)
				case "yellowCards":
					ts.YellowCards = int(f)
				case "redCards":
					ts.RedCards = int(f)
				case "saves":
					ts.Saves = int(f)
				}
			}
			out = append(out, ts)
		}
	}
	return out
}

func parseTime(s string) (time.Time, error) {
	for _, layout := range []string{time.RFC3339, "2006-01-02T15:04Z07:00"} {
		if t, err := time.Parse(layout, s); err == nil {
			return t.UTC(), nil
		}
	}
	return time.Time{}, fmt.Errorf("bad time %q", s)
}

func rfc3339(s string) string {
	t, err := parseTime(s)
	if err != nil {
		return ""
	}
	return t.Format(time.RFC3339)
}

func oneLine(s string) string {
	s = strings.TrimSpace(s)
	if i := strings.IndexByte(s, '\n'); i >= 0 {
		s = strings.TrimSpace(s[:i])
	}
	return s
}
