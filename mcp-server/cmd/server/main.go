// Command server is the Matchday Muse MCP server: sports data and web search
// for the pipeline, over stdio or Streamable HTTP. It never calls an LLM.
//
// "server healthcheck" probes a running HTTP server, for container
// healthchecks in images without a shell.
package main

import (
	"context"
	"fmt"
	"io/fs"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	mcpserver "github.com/7wik-pk/Matchday-Muse/mcp-server"
	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/cache"
	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/search/fixture"
	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/sports"
	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/sports/espn"
	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/tools"
)

func main() {
	run := run
	if len(os.Args) > 1 && os.Args[1] == "healthcheck" {
		run = healthcheck
	}
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "mcp-server:", err)
		os.Exit(1)
	}
}

func run() error {
	cfg, err := loadConfig(os.Getenv)
	if err != nil {
		return err
	}
	// Over stdio, stdout carries the protocol, so logs always go to stderr.
	log := slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: cfg.logLevel}))

	c, err := cache.New(cfg.cacheDir)
	if err != nil {
		return err
	}
	adapters := map[string]sports.Adapter{}
	for _, sport := range cfg.sports {
		switch sport {
		case "football":
			adapters[sport] = espn.New(espn.Options{Cache: c, MinGap: 250 * time.Millisecond, Logger: log})
		}
	}

	var corpus fs.FS = os.DirFS(cfg.fixtureDir)
	if cfg.fixtureDir == "" {
		if corpus, err = fs.Sub(mcpserver.SearchCorpus, "testdata/search"); err != nil {
			return err
		}
	}
	provider, err := fixture.New(corpus)
	if err != nil {
		return err
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	srv := tools.NewServer(tools.Deps{Sports: adapters, Search: provider}, tools.Version)
	log.Info("serving", "transport", cfg.transport, "sports", cfg.sports, "search", provider.Name(), "cache", cfg.cacheDir)
	if cfg.transport == "http" {
		return serveHTTP(ctx, cfg, srv, log)
	}
	return srv.Run(ctx, &mcp.StdioTransport{})
}
