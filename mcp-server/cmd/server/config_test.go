package main

import (
	"log/slog"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"
)

func env(vars map[string]string) func(string) string {
	return func(k string) string { return vars[k] }
}

func TestDefaults(t *testing.T) {
	c, err := loadConfig(env(map[string]string{"CACHE_DIR": "/tmp/c"}))
	if err != nil {
		t.Fatal(err)
	}
	if c.searchProvider != "fixture" || c.fixtureDir != "" || !slices.Equal(c.sports, []string{"football"}) || c.logLevel != slog.LevelInfo {
		t.Fatalf("%+v", c)
	}
}

func TestHTTP(t *testing.T) {
	c, err := loadConfig(env(map[string]string{"CACHE_DIR": "/tmp/c", "MCP_TRANSPORT": "http", "MCP_AUTH_TOKEN": strings.Repeat("a", 32)}))
	if err != nil {
		t.Fatal(err)
	}
	if c.transport != "http" || c.httpAddr != ":8081" {
		t.Fatalf("%+v", c)
	}
}

func TestTokenFile(t *testing.T) {
	path := filepath.Join(t.TempDir(), "token")
	if err := os.WriteFile(path, []byte(strings.Repeat("f", 64)+"\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	tests := map[string]struct {
		token string
		want  string
	}{
		"from the file":     {"", strings.Repeat("f", 64)},
		"the variable wins": {strings.Repeat("a", 32), strings.Repeat("a", 32)},
	}
	for name, tt := range tests {
		c, err := loadConfig(env(map[string]string{"CACHE_DIR": "/tmp/c", "MCP_TRANSPORT": "http", "MCP_AUTH_TOKEN": tt.token, "MCP_AUTH_TOKEN_FILE": path}))
		if err != nil {
			t.Fatalf("%s: %v", name, err)
		}
		if c.authToken != tt.want {
			t.Errorf("%s: got token %q, want %q", name, c.authToken, tt.want)
		}
	}
}

func TestRejects(t *testing.T) {
	tests := map[string]struct {
		vars map[string]string
		want string
	}{
		"http without token":    {map[string]string{"MCP_TRANSPORT": "http"}, "needs MCP_AUTH_TOKEN"},
		"http with short token": {map[string]string{"MCP_TRANSPORT": "http", "MCP_AUTH_TOKEN": "secret"}, "at least 32"},
		"missing token file":    {map[string]string{"MCP_TRANSPORT": "http", "MCP_AUTH_TOKEN_FILE": "/nonexistent/token"}, "MCP_AUTH_TOKEN_FILE"},
		"unknown transport":     {map[string]string{"MCP_TRANSPORT": "grpc"}, "not valid"},
		"exa":                   {map[string]string{"SEARCH_PROVIDER": "exa"}, "arrives in Phase 1"},
		"unknown search":        {map[string]string{"SEARCH_PROVIDER": "bing"}, "not valid"},
		"f1":                    {map[string]string{"ENABLED_SPORTS": "football,f1"}, "arrives in Phase 2"},
		"log level":             {map[string]string{"LOG_LEVEL": "loud"}, "LOG_LEVEL"},
	}
	for name, tt := range tests {
		tt.vars["CACHE_DIR"] = "/tmp/c"
		if _, err := loadConfig(env(tt.vars)); err == nil || !strings.Contains(err.Error(), tt.want) {
			t.Errorf("%s: got %v, want %q", name, err, tt.want)
		}
	}
}
