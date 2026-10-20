package espn

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"net/http"
	"net/url"
	"os"
	"path"
	"path/filepath"
	"strings"
)

// RecordedName is the testdata file for an ESPN request:
// {league}/scoreboard-{YYYYMMDD}.json or {league}/summary-{match id}.json.
func RecordedName(u *url.URL) (string, bool) {
	dir, endpoint := path.Split(strings.TrimSuffix(u.Path, "/"))
	league := path.Base(dir)
	var arg string
	switch endpoint {
	case "scoreboard":
		arg = u.Query().Get("dates")
	case "summary":
		arg = u.Query().Get("event")
	}
	if arg == "" || !fs.ValidPath(league) || strings.ContainsAny(arg, `/\.`) {
		return "", false
	}
	return league + "/" + endpoint + "-" + arg + ".json", true
}

// RecordingTransport saves every successful ESPN response under Dir,
// trimmed to the fields the adapter reads, and hands the trimmed body on.
type RecordingTransport struct {
	Dir  string
	Base http.RoundTripper
}

func (t *RecordingTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	resp, err := t.Base.RoundTrip(req)
	if err != nil || resp.StatusCode != http.StatusOK {
		return resp, err
	}
	defer resp.Body.Close()
	name, ok := RecordedName(req.URL)
	if !ok {
		return nil, fmt.Errorf("record: no testdata name for %s", req.URL)
	}
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	var v any = &summary{}
	if strings.Contains(name, "/scoreboard-") {
		v = &scoreboard{}
	}
	if err := json.Unmarshal(body, v); err != nil {
		return nil, fmt.Errorf("record %s: %w", name, err)
	}
	if body, err = json.Marshal(v); err != nil {
		return nil, err
	}
	file := filepath.Join(t.Dir, filepath.FromSlash(name))
	if err := os.MkdirAll(filepath.Dir(file), 0o755); err != nil {
		return nil, err
	}
	if err := os.WriteFile(file, append(body, '\n'), 0o644); err != nil {
		return nil, err
	}
	resp.Body = io.NopCloser(bytes.NewReader(body))
	resp.ContentLength = int64(len(body))
	return resp, nil
}

// ReplayHandler serves recorded responses, standing in for ESPN in tests.
// A request with no recording gets a 404, so a test cannot quietly pass on
// data nobody recorded.
func ReplayHandler(recordings fs.FS) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		name, ok := RecordedName(r.URL)
		if !ok {
			http.Error(w, "no recording name", http.StatusBadRequest)
			return
		}
		body, err := fs.ReadFile(recordings, name)
		if err != nil {
			http.Error(w, "not recorded: "+name, http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.Write(body)
	})
}
