package main

import (
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"slices"
	"strings"
)

// config is read from the environment; every variable is in .env.example.
type config struct {
	transport      string
	httpAddr       string
	authToken      string
	searchProvider string
	fixtureDir     string // empty: the embedded corpus
	cacheDir       string
	sports         []string
	logLevel       slog.Level
}

const minTokenLength = 32

// Values that are planned but not built yet, and the phase that adds them.
var planned = map[string]string{
	"SEARCH_PROVIDER=exa":    "Phase 1",
	"SEARCH_PROVIDER=tavily": "Phase 1",
	"ENABLED_SPORTS=f1":      "Phase 2",
	"ENABLED_SPORTS=cricket": "Phase 2",
}

func loadConfig(getenv func(string) string) (config, error) {
	c := config{
		transport:      or(getenv("MCP_TRANSPORT"), "stdio"),
		httpAddr:       or(getenv("MCP_HTTP_ADDR"), ":8081"),
		authToken:      getenv("MCP_AUTH_TOKEN"),
		searchProvider: or(getenv("SEARCH_PROVIDER"), "fixture"),
		fixtureDir:     getenv("SEARCH_FIXTURE_DIR"),
		cacheDir:       getenv("CACHE_DIR"),
	}
	if err := oneOf("MCP_TRANSPORT", c.transport, "stdio", "http"); err != nil {
		return c, err
	}
	// compose generates the token into a volume; MCP_AUTH_TOKEN wins if set.
	if path := getenv("MCP_AUTH_TOKEN_FILE"); c.authToken == "" && path != "" {
		b, err := os.ReadFile(path)
		if err != nil {
			return c, fmt.Errorf("MCP_AUTH_TOKEN_FILE: %w", err)
		}
		c.authToken = strings.TrimSpace(string(b))
	}
	if c.transport == "http" && len(c.authToken) < minTokenLength {
		return c, fmt.Errorf("MCP_TRANSPORT=http needs MCP_AUTH_TOKEN of at least %d characters, such as the output of: openssl rand -hex 32", minTokenLength)
	}
	if err := oneOf("SEARCH_PROVIDER", c.searchProvider, "fixture"); err != nil {
		return c, err
	}
	for _, s := range strings.Split(or(getenv("ENABLED_SPORTS"), "football"), ",") {
		s = strings.TrimSpace(s)
		if err := oneOf("ENABLED_SPORTS", s, "football"); err != nil {
			return c, err
		}
		c.sports = append(c.sports, s)
	}
	if c.cacheDir == "" {
		dir, err := os.UserCacheDir()
		if err != nil {
			return c, fmt.Errorf("CACHE_DIR is unset and there is no user cache directory: %w", err)
		}
		c.cacheDir = filepath.Join(dir, "matchday-muse", "mcp-server")
	}
	if err := c.logLevel.UnmarshalText([]byte(or(getenv("LOG_LEVEL"), "info"))); err != nil {
		return c, fmt.Errorf("LOG_LEVEL: %w", err)
	}
	return c, nil
}

func oneOf(name, value string, valid ...string) error {
	if slices.Contains(valid, value) {
		return nil
	}
	if phase, ok := planned[name+"="+value]; ok {
		return fmt.Errorf("%s=%s arrives in %s; for now use %s", name, value, phase, strings.Join(valid, " or "))
	}
	return fmt.Errorf("%s=%q is not valid; use %s", name, value, strings.Join(valid, " or "))
}

func or(s, fallback string) string {
	if s == "" {
		return fallback
	}
	return s
}
