package tools

import (
	"context"
	"encoding/json"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/google/jsonschema-go/jsonschema"
	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/search/fixture"
	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/sports"
	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/sports/espn"
)

// connect serves the tools over an in-memory transport, backed by the ESPN
// recordings and the fixture corpus, and returns a client session.
func connect(t *testing.T) *mcp.ClientSession {
	t.Helper()
	srv := httptest.NewServer(espn.ReplayHandler(os.DirFS("../../testdata/espn")))
	t.Cleanup(srv.Close)
	corpus, err := fixture.New(os.DirFS("../../testdata/search"))
	if err != nil {
		t.Fatal(err)
	}
	now := time.Date(2026, 10, 20, 9, 0, 0, 0, time.UTC)
	s := NewServer(Deps{
		Sports: map[string]sports.Adapter{"football": espn.New(espn.Options{BaseURL: srv.URL, Now: func() time.Time { return now }})},
		Search: corpus,
	}, Version)
	st, ct := mcp.NewInMemoryTransports()
	ctx := context.Background()
	if _, err := s.Connect(ctx, st, nil); err != nil {
		t.Fatal(err)
	}
	cs, err := mcp.NewClient(&mcp.Implementation{Name: "test", Version: Version}, nil).Connect(ctx, ct, nil)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { cs.Close() })
	return cs
}

// call runs a tool that must succeed, checks its output against the schema
// exported to contracts/mcp/, and decodes it into out.
func call(t *testing.T, cs *mcp.ClientSession, tool string, args map[string]any, out any) {
	t.Helper()
	res, err := cs.CallTool(context.Background(), &mcp.CallToolParams{Name: tool, Arguments: args})
	if err != nil {
		t.Fatal(err)
	}
	if res.IsError {
		t.Fatalf("%s failed: %s", tool, text(res))
	}
	data, err := json.Marshal(res.StructuredContent)
	if err != nil {
		t.Fatal(err)
	}
	var instance any
	if err := json.Unmarshal(data, &instance); err != nil {
		t.Fatal(err)
	}
	if err := exportedOutputSchema(t, tool).Validate(instance); err != nil {
		t.Fatalf("%s output does not match contracts/mcp/%s.json: %v", tool, tool, err)
	}
	if err := json.Unmarshal(data, out); err != nil {
		t.Fatal(err)
	}
}

func exportedOutputSchema(t *testing.T, tool string) *jsonschema.Resolved {
	t.Helper()
	data, err := os.ReadFile(filepath.Join("../../../contracts/mcp", tool+".json"))
	if err != nil {
		t.Fatal(err)
	}
	var file struct {
		OutputSchema *jsonschema.Schema `json:"outputSchema"`
	}
	if err := json.Unmarshal(data, &file); err != nil {
		t.Fatal(err)
	}
	r, err := file.OutputSchema.Resolve(nil)
	if err != nil {
		t.Fatal(err)
	}
	return r
}

func text(res *mcp.CallToolResult) string {
	var parts []string
	for _, c := range res.Content {
		if tc, ok := c.(*mcp.TextContent); ok {
			parts = append(parts, tc.Text)
		}
	}
	return strings.Join(parts, " ")
}

var week = map[string]any{"sport": "football", "league": "eng.1", "from": "2026-10-11T23:00:00Z", "to": "2026-10-18T23:00:00Z"}

func TestTools(t *testing.T) {
	cs := connect(t)

	var comps ListCompetitionsOutput
	call(t, cs, "list_competitions", nil, &comps)
	if len(comps.Competitions) != 1 || comps.Competitions[0].League != "eng.1" {
		t.Fatalf("competitions %+v", comps.Competitions)
	}

	var found FindMatchesOutput
	call(t, cs, "find_matches", week, &found)
	if len(found.Matches) != 10 {
		t.Fatalf("%d matches", len(found.Matches))
	}

	var tl sports.Timeline
	call(t, cs, "get_match_events", map[string]any{"sport": "football", "league": "eng.1", "match_id": "401879262"}, &tl)
	if tl.Match.FinalResult != "Brentford 1–2 Liverpool" || len(tl.Events) == 0 {
		t.Fatalf("timeline %q, %d events", tl.Match.FinalResult, len(tl.Events))
	}

	var hits SearchCoverageOutput
	call(t, cs, "search_coverage", map[string]any{"query": "Isak winner nine-man Brentford"}, &hits)
	if hits.Provider != "fixture" || len(hits.Results) == 0 || !strings.Contains(hits.Results[0].Title, "Isak") {
		t.Fatalf("search %+v", hits)
	}
	// max_results defaults to 5.
	call(t, cs, "search_coverage", map[string]any{"query": "Premier League win"}, &hits)
	if len(hits.Results) != 5 {
		t.Fatalf("%d results by default", len(hits.Results))
	}
}

func TestToolErrors(t *testing.T) {
	cs := connect(t)
	with := func(base map[string]any, k string, v any) map[string]any {
		m := map[string]any{}
		for key, val := range base {
			m[key] = val
		}
		m[k] = v
		return m
	}
	tests := []struct {
		name, tool string
		args       map[string]any
		want       string
	}{
		{"sport not enabled", "find_matches", with(week, "sport", "f1"), "not enabled; enabled: football"},
		{"bad time", "find_matches", with(week, "from", "last Saturday"), "RFC 3339"},
		{"unknown league", "find_matches", with(week, "league", "esp.1"), "supported: eng.1"},
		{"missing argument", "find_matches", map[string]any{"sport": "football"}, "required"},
		{"bad match id", "get_match_events", map[string]any{"sport": "football", "league": "eng.1", "match_id": "abc"}, "not an ESPN match id"},
		{"short query", "search_coverage", map[string]any{"query": "a"}, "minLength"},
		{"too many results", "search_coverage", map[string]any{"query": "Isak", "max_results": 50}, "maximum"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			res, err := cs.CallTool(context.Background(), &mcp.CallToolParams{Name: tt.tool, Arguments: tt.args})
			if err != nil {
				t.Fatal(err)
			}
			if !res.IsError || !strings.Contains(text(res), tt.want) {
				t.Fatalf("IsError %v, %q; want %q", res.IsError, text(res), tt.want)
			}
		})
	}
}

func TestTruncate(t *testing.T) {
	long := strings.Repeat("word ", 100)
	got := truncate(long, 50)
	if len([]rune(got)) > 52 || !strings.HasSuffix(got, "…") {
		t.Fatalf("%q", got)
	}
	if truncate("short", 50) != "short" {
		t.Fatal("short text changed")
	}
}
