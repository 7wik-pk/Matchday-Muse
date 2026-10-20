// Command record fetches a date range from ESPN through the football adapter
// and saves every response under testdata/espn/, trimmed to the fields the
// adapter reads. It also writes the week's match reports, headline and
// one-line description only, as a corpus for the fixture search provider.
//
//	go run ./cmd/record -league eng.1 -from 2026-10-12 -days 7
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/search"
	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/sports/espn"
)

func main() {
	league := flag.String("league", "eng.1", "ESPN league code")
	fromDay := flag.String("from", "", "first day, YYYY-MM-DD, London time")
	days := flag.Int("days", 7, "number of days")
	out := flag.String("out", "testdata", "testdata directory")
	flag.Parse()

	london, err := time.LoadLocation("Europe/London")
	if err != nil {
		log.Fatal(err)
	}
	start, err := time.ParseInLocation("2006-01-02", *fromDay, london)
	if err != nil {
		log.Fatalf("-from: %v", err)
	}
	end := start.AddDate(0, 0, *days)

	a := espn.New(espn.Options{
		Transport: &espn.RecordingTransport{Dir: filepath.Join(*out, "espn"), Base: http.DefaultTransport},
		MinGap:    500 * time.Millisecond,
	})
	ctx := context.Background()
	matches, err := a.FindMatches(ctx, *league, start, end)
	if err != nil {
		log.Fatal(err)
	}
	var corpus []search.Result
	for _, m := range matches {
		t, err := a.MatchEvents(ctx, *league, m.ID)
		if err != nil {
			log.Fatal(err)
		}
		fmt.Printf("%s  %-40s %3d events\n", m.ID, m.FinalResult, len(t.Events))
		if len(t.Sources) > 1 && t.Match.Summary != "" {
			report := t.Sources[1]
			corpus = append(corpus, search.Result{
				Title: report.Title, URL: report.URL, PublishedAt: report.PublishedAt, Content: t.Match.Summary,
			})
		}
	}
	data, err := json.MarshalIndent(corpus, "", "  ")
	if err != nil {
		log.Fatal(err)
	}
	name := filepath.Join(*out, "search", fmt.Sprintf("espn-reports-%s-%s.json", *league, start.Format("20060102")))
	if err := os.MkdirAll(filepath.Dir(name), 0o755); err != nil {
		log.Fatal(err)
	}
	if err := os.WriteFile(name, append(data, '\n'), 0o644); err != nil {
		log.Fatal(err)
	}
	fmt.Printf("%d matches; search corpus %s\n", len(matches), name)
}
