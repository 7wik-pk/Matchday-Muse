package main

import (
	"context"
	"crypto/subtle"
	"errors"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"os"
	"time"

	"github.com/go-resty/resty/v2"
	"github.com/modelcontextprotocol/go-sdk/auth"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// httpHandler serves MCP at /mcp behind the shared bearer token, and an
// unauthenticated /healthz. Sessions are stateless: no tool calls back to
// the client, and any instance can answer any request.
func httpHandler(srv *mcp.Server, token string, log *slog.Logger) http.Handler {
	mcpHandler := mcp.NewStreamableHTTPHandler(
		func(*http.Request) *mcp.Server { return srv },
		&mcp.StreamableHTTPOptions{Stateless: true, Logger: log},
	)
	verify := func(_ context.Context, got string, _ *http.Request) (*auth.TokenInfo, error) {
		if subtle.ConstantTimeCompare([]byte(got), []byte(token)) != 1 {
			return nil, auth.ErrInvalidToken
		}
		return &auth.TokenInfo{}, nil
	}
	requireToken := auth.RequireBearerToken(verify, &auth.RequireBearerTokenOptions{AllowMissingExpiration: true})

	mux := http.NewServeMux()
	mux.Handle("/mcp", requireToken(mcpHandler))
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		fmt.Fprintln(w, "ok")
	})
	return mux
}

func serveHTTP(ctx context.Context, cfg config, srv *mcp.Server, log *slog.Logger) error {
	hs := &http.Server{
		Addr:              cfg.httpAddr,
		Handler:           httpHandler(srv, cfg.authToken, log),
		ReadHeaderTimeout: 10 * time.Second,
		BaseContext:       func(net.Listener) context.Context { return ctx },
	}
	errc := make(chan error, 1)
	go func() { errc <- hs.ListenAndServe() }()
	log.Info("listening", "addr", cfg.httpAddr, "path", "/mcp")
	select {
	case err := <-errc:
		return err
	case <-ctx.Done():
	}
	shutdown, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := hs.Shutdown(shutdown); err != nil && !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}

// healthcheck exits non-zero unless the local HTTP server answers /healthz.
func healthcheck() error {
	_, port, err := net.SplitHostPort(or(os.Getenv("MCP_HTTP_ADDR"), ":8081"))
	if err != nil {
		return err
	}
	resp, err := resty.New().SetTimeout(3 * time.Second).R().Get("http://127.0.0.1:" + port + "/healthz")
	if err != nil {
		return err
	}
	if resp.StatusCode() != http.StatusOK {
		return fmt.Errorf("healthz returned HTTP %d", resp.StatusCode())
	}
	return nil
}
