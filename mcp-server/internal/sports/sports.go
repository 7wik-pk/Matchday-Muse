// Package sports defines the normalised match data every sport adapter
// returns, and the interface the adapters implement. The JSON tags here are
// the MCP tool contract: cmd/schemagen exports them to contracts/mcp/.
package sports

import (
	"context"
	"time"
)

// Coverage says how much event-level detail a source has for a match.
type Coverage string

const (
	FullEvents Coverage = "full_events"
	RoundStats Coverage = "round_stats"
	ScoresOnly Coverage = "scores_only"
)

// Competition is one league an adapter serves.
type Competition struct {
	Sport    string   `json:"sport" jsonschema:"Sport id to pass to find_matches, such as football"`
	League   string   `json:"league" jsonschema:"League code to pass to find_matches, such as eng.1"`
	Name     string   `json:"name" jsonschema:"Display name, such as Premier League"`
	Source   string   `json:"source" jsonschema:"Where the data comes from"`
	Coverage Coverage `json:"coverage" jsonschema:"Detail available per match: full_events, round_stats or scores_only"`
}

// Participant is a team (or, in individual sports, an athlete) in a match.
type Participant struct {
	Name         string `json:"name" jsonschema:"Full display name, such as Brentford"`
	ShortName    string `json:"short_name" jsonschema:"Short display name, such as Spurs"`
	Abbreviation string `json:"abbreviation" jsonschema:"Three-letter code, such as BRE"`
	Role         string `json:"role" jsonschema:"home or away; empty where a sport has neither"`
	Score        string `json:"score" jsonschema:"Final or current score, as the source writes it"`
	Winner       bool   `json:"winner" jsonschema:"True for the winner of a completed match; false for both sides in a draw"`
}

// Match is one fixture, as find_matches lists it.
type Match struct {
	ID           string        `json:"id" jsonschema:"Source match id, passed to get_match_events"`
	Sport        string        `json:"sport"`
	League       string        `json:"league"`
	Title        string        `json:"title" jsonschema:"Home v away, such as Brentford v Liverpool"`
	FinalResult  string        `json:"final_result" jsonschema:"Canonical result line, such as Brentford 1–2 Liverpool; empty until the match is completed"`
	Participants []Participant `json:"participants"`
	Kickoff      string        `json:"kickoff" jsonschema:"Scheduled start, RFC 3339 UTC"`
	EndEstimate  string        `json:"end_estimate" jsonschema:"Estimated finish, RFC 3339 UTC: the source gives start times only"`
	Status       string        `json:"status" jsonschema:"scheduled, in_progress, completed or other (postponed, abandoned)"`
	Venue        string        `json:"venue"`
	Summary      string        `json:"summary" jsonschema:"One-line recap from the source; may be empty"`
}

// Event is one entry in a match timeline, normalised across sports.
type Event struct {
	Clock       string   `json:"clock" jsonschema:"Match clock as the sport writes it: 67', 45+8', Lap 42, Over 18.4"`
	Type        string   `json:"type" jsonschema:"Normalised type. Football: kickoff, half_time, second_half, full_time, goal, penalty_goal, own_goal, penalty_miss, yellow_card, red_card, sub, var, shot_on_target, shot_off_target, shot_blocked, woodwork, foul, handball, corner, offside, injury, other"`
	Team        string   `json:"team,omitempty" jsonschema:"The team the event belongs to, when the source says"`
	Actors      []string `json:"actors" jsonschema:"People involved, main actor first: the scorer then the assister; the player coming on then the one going off"`
	Description string   `json:"description" jsonschema:"The source's own wording"`
	ScoreAfter  string   `json:"score_after,omitempty" jsonschema:"Home-away score after a goal or at a break, such as 1-2"`
	SourceRef   string   `json:"source_ref" jsonschema:"Provenance for grounding checks: source, match id and play id"`
}

// TeamStats are the per-team totals a source reports for a match.
type TeamStats struct {
	Team          string  `json:"team"`
	PossessionPct float64 `json:"possession_pct"`
	Shots         int     `json:"shots"`
	ShotsOnTarget int     `json:"shots_on_target"`
	Corners       int     `json:"corners"`
	Fouls         int     `json:"fouls"`
	YellowCards   int     `json:"yellow_cards"`
	RedCards      int     `json:"red_cards"`
	Saves         int     `json:"saves"`
}

// Source is a page a fact can be cited to.
type Source struct {
	Title       string `json:"title"`
	URL         string `json:"url"`
	Publisher   string `json:"publisher"`
	PublishedAt string `json:"published_at,omitempty" jsonschema:"RFC 3339 UTC, when known"`
}

// Timeline is everything get_match_events returns for one match.
type Timeline struct {
	Match     Match       `json:"match"`
	Coverage  Coverage    `json:"coverage"`
	Events    []Event     `json:"events" jsonschema:"In match order; empty when coverage is scores_only"`
	TeamStats []TeamStats `json:"team_stats" jsonschema:"Home first; empty when the source has none"`
	Sources   []Source    `json:"sources" jsonschema:"Pages to cite: the match page, and the match report when there is one"`
}

// Adapter serves one sport from one source.
type Adapter interface {
	Sport() string
	Competitions() []Competition
	// FindMatches returns the completed matches kicking off in [from, to).
	FindMatches(ctx context.Context, league string, from, to time.Time) ([]Match, error)
	MatchEvents(ctx context.Context, league, matchID string) (Timeline, error)
}
