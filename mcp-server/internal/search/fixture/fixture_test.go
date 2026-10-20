package fixture

import (
	"context"
	"os"
	"testing"
	"testing/fstest"
	"time"

	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/search"
)

func corpus(t *testing.T) *Provider {
	t.Helper()
	p, err := New(os.DirFS("../../../testdata/search"))
	if err != nil {
		t.Fatal(err)
	}
	return p
}

func urls(rs []search.Result) []string {
	out := []string{}
	for _, r := range rs {
		out = append(out, r.URL)
	}
	return out
}

func TestSearch(t *testing.T) {
	const brentford = "https://www.espn.com/soccer/report/_/gameId/401879262"
	tests := []struct {
		name  string
		query search.Query
		want  []string
	}{
		{
			name:  "best match first",
			query: search.Query{Text: "Isak winner nine-man Brentford", MaxResults: 5},
			want:  []string{brentford},
		},
		{
			name:  "capped at max results",
			query: search.Query{Text: "Premier League win", MaxResults: 2},
		},
		{
			name: "published after excludes older pages",
			query: search.Query{
				Text: "Isak Brentford", MaxResults: 5,
				PublishedAfter: time.Date(2026, 10, 18, 0, 0, 0, 0, time.UTC),
			},
			want: []string{},
		},
		{
			name:  "no overlap, no results",
			query: search.Query{Text: "cricket ashes", MaxResults: 5},
			want:  []string{},
		},
	}
	p := corpus(t)
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := p.Search(context.Background(), tt.query)
			if err != nil {
				t.Fatal(err)
			}
			if len(got) > tt.query.MaxResults {
				t.Fatalf("%d results, max %d", len(got), tt.query.MaxResults)
			}
			if tt.want == nil {
				return
			}
			g := urls(got)
			if len(tt.want) == 0 && len(g) != 0 {
				t.Fatalf("got %v, want none", g)
			}
			for i, w := range tt.want {
				if i >= len(g) || g[i] != w {
					t.Fatalf("got %v, want %v first", g, tt.want)
				}
			}
		})
	}
}

func TestRejectsBadCorpus(t *testing.T) {
	for name, fsys := range map[string]fstest.MapFS{
		"empty":    {},
		"not JSON": {"a.json": {Data: []byte("{")}},
		"bad date": {"a.json": {Data: []byte(`[{"title":"t","url":"u","content":"c","published_at":"yesterday"}]`)}},
	} {
		if _, err := New(fsys); err == nil {
			t.Errorf("%s: New succeeded", name)
		}
	}
}
