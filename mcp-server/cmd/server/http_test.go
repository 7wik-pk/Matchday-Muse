package main

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"testing/fstest"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/search/fixture"
	"github.com/7wik-pk/Matchday-Muse/mcp-server/internal/tools"
)

const testToken = "0123456789abcdef0123456789abcdef"

type bearer struct{ token string }

func (b bearer) RoundTrip(r *http.Request) (*http.Response, error) {
	r = r.Clone(r.Context())
	r.Header.Set("Authorization", "Bearer "+b.token)
	return http.DefaultTransport.RoundTrip(r)
}

func serve(t *testing.T) *httptest.Server {
	t.Helper()
	corpus, err := fixture.New(fstest.MapFS{"a.json": {Data: []byte(`[{"title":"Isak wins it","url":"https://example.com/a","content":"Late winner"}]`)}})
	if err != nil {
		t.Fatal(err)
	}
	srv := tools.NewServer(tools.Deps{Search: corpus}, tools.Version)
	ts := httptest.NewServer(httpHandler(srv, testToken, nil))
	t.Cleanup(ts.Close)
	return ts
}

func TestHTTPWithToken(t *testing.T) {
	ts := serve(t)
	transport := &mcp.StreamableClientTransport{
		Endpoint:   ts.URL + "/mcp",
		HTTPClient: &http.Client{Transport: bearer{testToken}},
	}
	ctx := context.Background()
	cs, err := mcp.NewClient(&mcp.Implementation{Name: "test", Version: "0"}, nil).Connect(ctx, transport, nil)
	if err != nil {
		t.Fatal(err)
	}
	defer cs.Close()
	res, err := cs.CallTool(ctx, &mcp.CallToolParams{Name: "search_coverage", Arguments: map[string]any{"query": "Isak winner"}})
	if err != nil || res.IsError {
		t.Fatalf("call: %v %+v", err, res)
	}
}

func TestHTTPRejectsBadTokens(t *testing.T) {
	ts := serve(t)
	for name, header := range map[string]string{
		"no token":    "",
		"wrong token": "Bearer " + strings.Repeat("x", len(testToken)),
	} {
		req, _ := http.NewRequest(http.MethodPost, ts.URL+"/mcp", strings.NewReader(`{}`))
		if header != "" {
			req.Header.Set("Authorization", header)
		}
		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatal(err)
		}
		resp.Body.Close()
		if resp.StatusCode != http.StatusUnauthorized {
			t.Errorf("%s: HTTP %d, want 401", name, resp.StatusCode)
		}
	}
}

func TestHealthz(t *testing.T) {
	ts := serve(t)
	resp, err := http.Get(ts.URL + "/healthz")
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("HTTP %d", resp.StatusCode)
	}
}
