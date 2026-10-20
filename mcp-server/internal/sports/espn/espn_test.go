package espn

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"reflect"
	"slices"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/cache"
	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/sports"
)

// The recordings cover Mon 12 to Sun 18 Oct 2026, London time.
var (
	weekStart = time.Date(2026, 10, 11, 23, 0, 0, 0, time.UTC)
	weekEnd   = time.Date(2026, 10, 18, 23, 0, 0, 0, time.UTC)
	now       = time.Date(2026, 10, 20, 9, 0, 0, 0, time.UTC)
)

func replay(t *testing.T, c *cache.Cache) (*Adapter, *httptest.Server) {
	t.Helper()
	srv := httptest.NewServer(ReplayHandler(os.DirFS("../../../testdata/espn")))
	t.Cleanup(srv.Close)
	return New(Options{BaseURL: srv.URL, Cache: c, Now: func() time.Time { return now }}), srv
}

func TestFindMatches(t *testing.T) {
	a, _ := replay(t, nil)
	tests := []struct {
		name     string
		from, to time.Time
		want     []string
	}{
		{"the week, by kickoff then id", weekStart, weekEnd, []string{
			"Coventry City 4–1 Newcastle United",
			"Everton 0–2 Chelsea",
			"Fulham 1–0 Hull City",
			"Manchester City 3–2 Ipswich Town",
			"Brentford 1–2 Liverpool",
			"Newcastle United 0–1 Aston Villa",
			"Leeds United 1–1 Manchester United",
			"Brighton & Hove Albion 5–0 Crystal Palace",
			"AFC Bournemouth 2–0 Sunderland",
			"Nottingham Forest 0–1 Arsenal",
		}},
		{"kickoff in [from, to)", time.Date(2026, 10, 17, 11, 30, 0, 0, time.UTC), time.Date(2026, 10, 17, 14, 0, 0, 0, time.UTC), []string{
			"Everton 0–2 Chelsea",
		}},
		{"a day without matches", time.Date(2026, 10, 13, 23, 0, 0, 0, time.UTC), time.Date(2026, 10, 14, 23, 0, 0, 0, time.UTC), []string{}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			matches, err := a.FindMatches(context.Background(), "eng.1", tt.from, tt.to)
			if err != nil {
				t.Fatal(err)
			}
			got := []string{}
			for _, m := range matches {
				got = append(got, m.FinalResult)
			}
			if !slices.Equal(got, tt.want) {
				t.Fatalf("got %q\nwant %q", got, tt.want)
			}
		})
	}
}

func TestMatchFields(t *testing.T) {
	a, _ := replay(t, nil)
	matches, err := a.FindMatches(context.Background(), "eng.1", weekStart, weekEnd)
	if err != nil {
		t.Fatal(err)
	}
	i := slices.IndexFunc(matches, func(m sports.Match) bool { return m.ID == "401879262" })
	if i < 0 {
		t.Fatal("Brentford v Liverpool missing")
	}
	m := matches[i]
	want := sports.Match{
		ID: "401879262", Sport: "football", League: "eng.1",
		Title: "Brentford v Liverpool", FinalResult: "Brentford 1–2 Liverpool",
		Kickoff: "2026-10-17T14:00:00Z", EndEstimate: "2026-10-17T16:00:00Z",
		Status: "completed", Venue: "Gtech Community Stadium",
	}
	got := m
	got.Participants, got.Summary = nil, ""
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("got %+v", got)
	}
	if p := m.Participants; len(p) != 2 || p[0].Role != "home" || p[0].Name != "Brentford" || p[1].Abbreviation != "LIV" || !p[1].Winner || p[0].Winner {
		t.Fatalf("participants %+v", p)
	}
	if !strings.Contains(m.Summary, "Isak") || strings.Contains(m.Summary, "\n") {
		t.Fatalf("summary %q", m.Summary)
	}
}

func TestMatchEvents(t *testing.T) {
	a, _ := replay(t, nil)
	tl, err := a.MatchEvents(context.Background(), "eng.1", "401879262")
	if err != nil {
		t.Fatal(err)
	}
	if tl.Coverage != sports.FullEvents || tl.Match.FinalResult != "Brentford 1–2 Liverpool" {
		t.Fatalf("coverage %s, result %q", tl.Coverage, tl.Match.FinalResult)
	}
	var goals, reds, vars []string
	for _, e := range tl.Events {
		switch e.Type {
		case "goal":
			goals = append(goals, e.Clock+" "+e.Actors[0]+" "+e.ScoreAfter)
		case "red_card":
			reds = append(reds, e.Clock+" "+e.Actors[0]+" "+e.Team)
		case "var":
			vars = append(vars, e.Clock)
		}
	}
	wantGoals := []string{"44' Keane Lewis-Potter 1-0", "62' Víctor Muñoz 1-1", "70' Alexander Isak 1-2"}
	wantReds := []string{"45+8' Yehor Yarmoliuk Brentford", "90+2' Vitaly Janelt Brentford"}
	if !slices.Equal(goals, wantGoals) || !slices.Equal(reds, wantReds) {
		t.Fatalf("goals %q\nreds %q", goals, reds)
	}
	// The penalty overturned on review, and the red card upgraded on review.
	if !slices.Equal(vars, []string{"41'", "45+5'"}) {
		t.Fatalf("var %q", vars)
	}
	if len(tl.TeamStats) != 2 || tl.TeamStats[1].Team != "Liverpool" || tl.TeamStats[1].PossessionPct != 59.9 || tl.TeamStats[1].Shots != 21 || tl.TeamStats[0].RedCards != 2 {
		t.Fatalf("stats %+v", tl.TeamStats)
	}
	wantSources := []string{
		"https://www.espn.com/soccer/match/_/gameId/401879262",
		"https://www.espn.com/soccer/report/_/gameId/401879262",
	}
	var gotSources []string
	for _, s := range tl.Sources {
		gotSources = append(gotSources, s.URL)
	}
	if !slices.Equal(gotSources, wantSources) || tl.Sources[1].PublishedAt != "2026-10-17T16:07:00Z" {
		t.Fatalf("sources %+v", tl.Sources)
	}
}

// Every recorded match: the timeline's goals add up to the final score, and
// the last score line matches it.
func TestTimelinesAgreeWithScores(t *testing.T) {
	a, _ := replay(t, nil)
	matches, err := a.FindMatches(context.Background(), "eng.1", weekStart, weekEnd)
	if err != nil {
		t.Fatal(err)
	}
	for _, m := range matches {
		t.Run(m.Title, func(t *testing.T) {
			tl, err := a.MatchEvents(context.Background(), "eng.1", m.ID)
			if err != nil {
				t.Fatal(err)
			}
			home, _ := strconv.Atoi(m.Participants[0].Score)
			away, _ := strconv.Atoi(m.Participants[1].Score)
			goals, last := 0, ""
			for _, e := range tl.Events {
				if e.Type == "" || e.Clock == "" || e.SourceRef == "" {
					t.Fatalf("incomplete event %+v", e)
				}
				switch e.Type {
				case "goal", "penalty_goal", "own_goal":
					goals++
					if e.ScoreAfter == "" {
						t.Errorf("no score after %q", e.Description)
					}
				}
				if e.ScoreAfter != "" {
					last = e.ScoreAfter
				}
			}
			if goals != home+away || last != strconv.Itoa(home)+"-"+strconv.Itoa(away) {
				t.Fatalf("%d goals, last score %q; final %d-%d", goals, last, home, away)
			}
		})
	}
}

func TestErrors(t *testing.T) {
	a, _ := replay(t, nil)
	ctx := context.Background()
	if _, err := a.FindMatches(ctx, "esp.1", weekStart, weekEnd); err == nil || !strings.Contains(err.Error(), "supported: eng.1") {
		t.Errorf("unknown league: %v", err)
	}
	if _, err := a.FindMatches(ctx, "eng.1", weekEnd, weekStart); err == nil {
		t.Error("reversed range accepted")
	}
	if _, err := a.FindMatches(ctx, "eng.1", weekStart, weekStart.Add(MaxRange+time.Hour)); err == nil {
		t.Error("long range accepted")
	}
	if _, err := a.FindMatches(ctx, "eng.1", weekStart.AddDate(0, 0, 14), weekEnd.AddDate(0, 0, 14)); err == nil || !strings.Contains(err.Error(), "404") {
		t.Errorf("unrecorded day: %v", err)
	}
	if _, err := a.MatchEvents(ctx, "eng.1", "401879262&x=1"); err == nil {
		t.Error("bad match id accepted")
	}
}

func TestServesFromCache(t *testing.T) {
	c, err := cache.New(filepath.Join(t.TempDir(), "cache"))
	if err != nil {
		t.Fatal(err)
	}
	a, srv := replay(t, c)
	ctx := context.Background()
	first, err := a.FindMatches(ctx, "eng.1", weekStart, weekEnd)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := a.MatchEvents(ctx, "eng.1", "401879262"); err != nil {
		t.Fatal(err)
	}
	srv.Close()
	again, err := a.FindMatches(ctx, "eng.1", weekStart, weekEnd)
	if err != nil || len(again) != len(first) {
		t.Fatalf("after the server closed: %d matches, %v", len(again), err)
	}
	if _, err := a.MatchEvents(ctx, "eng.1", "401879262"); err != nil {
		t.Fatalf("after the server closed: %v", err)
	}
}

func TestRetriesServerErrors(t *testing.T) {
	replayer := ReplayHandler(os.DirFS("../../../testdata/espn"))
	failures := 1
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if failures > 0 {
			failures--
			http.Error(w, "busy", http.StatusServiceUnavailable)
			return
		}
		replayer.ServeHTTP(w, r)
	}))
	t.Cleanup(srv.Close)
	a := New(Options{BaseURL: srv.URL, Now: func() time.Time { return now }})
	if _, err := a.MatchEvents(context.Background(), "eng.1", "401879262"); err != nil {
		t.Fatalf("after one 503: %v", err)
	}
}
