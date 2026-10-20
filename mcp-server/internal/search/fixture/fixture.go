// Package fixture is the offline search provider for tests, evals and local
// runs. It ranks a fixed corpus of results by keyword overlap with the query,
// so any query an LLM writes gets a deterministic answer with no network.
package fixture

import (
	"cmp"
	"context"
	"encoding/json"
	"fmt"
	"io/fs"
	"slices"
	"strings"
	"time"
	"unicode"

	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/search"
)

type Provider struct {
	docs []doc
}

type doc struct {
	search.Result
	published time.Time
	title     map[string]bool
	content   map[string]bool
}

// New loads every *.json file in corpus; each holds an array of results.
func New(corpus fs.FS) (*Provider, error) {
	names, err := fs.Glob(corpus, "*.json")
	if err != nil {
		return nil, err
	}
	if len(names) == 0 {
		return nil, fmt.Errorf("fixture search: no *.json corpus files")
	}
	p := &Provider{}
	for _, name := range names {
		data, err := fs.ReadFile(corpus, name)
		if err != nil {
			return nil, err
		}
		var results []search.Result
		if err := json.Unmarshal(data, &results); err != nil {
			return nil, fmt.Errorf("fixture search: %s: %w", name, err)
		}
		for _, r := range results {
			d := doc{Result: r, title: terms(r.Title), content: terms(r.Content)}
			if r.PublishedAt != "" {
				if d.published, err = time.Parse(time.RFC3339, r.PublishedAt); err != nil {
					return nil, fmt.Errorf("fixture search: %s: %s: %w", name, r.URL, err)
				}
			}
			p.docs = append(p.docs, d)
		}
	}
	return p, nil
}

func (p *Provider) Name() string { return "fixture" }

// Search scores each result 3 per query term in its title and 1 per term in
// its content, and returns the best, newest first on ties.
func (p *Provider) Search(_ context.Context, q search.Query) ([]search.Result, error) {
	query := terms(q.Text)
	type hit struct {
		d     *doc
		score int
	}
	var hits []hit
	for i := range p.docs {
		d := &p.docs[i]
		if !q.PublishedAfter.IsZero() && !d.published.After(q.PublishedAfter) {
			continue
		}
		score := 0
		for t := range query {
			if d.title[t] {
				score += 3
			}
			if d.content[t] {
				score++
			}
		}
		if score > 0 {
			hits = append(hits, hit{d, score})
		}
	}
	slices.SortFunc(hits, func(x, y hit) int {
		return cmp.Or(
			cmp.Compare(y.score, x.score),
			y.d.published.Compare(x.d.published),
			strings.Compare(x.d.URL, y.d.URL),
		)
	})
	out := []search.Result{}
	for _, h := range hits[:min(len(hits), q.MaxResults)] {
		out = append(out, h.d.Result)
	}
	return out, nil
}

var stopwords = map[string]bool{
	"a": true, "an": true, "and": true, "as": true, "at": true, "by": true, "for": true,
	"from": true, "in": true, "is": true, "of": true, "on": true, "or": true, "the": true,
	"to": true, "v": true, "vs": true, "was": true, "with": true,
}

func terms(s string) map[string]bool {
	out := map[string]bool{}
	for _, w := range strings.FieldsFunc(strings.ToLower(s), func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	}) {
		if !stopwords[w] {
			out[w] = true
		}
	}
	return out
}
