package cache

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func newTestCache(t *testing.T) (*Cache, *time.Time) {
	t.Helper()
	c, err := New(filepath.Join(t.TempDir(), "cache"))
	if err != nil {
		t.Fatal(err)
	}
	now := time.Date(2026, 10, 20, 9, 0, 0, 0, time.UTC)
	c.now = func() time.Time { return now }
	return c, &now
}

func TestGetPut(t *testing.T) {
	c, now := newTestCache(t)
	if _, ok := c.Get("k"); ok {
		t.Fatal("empty cache hit")
	}
	if err := c.Put("k", []byte(`{"a":1}`), 15*time.Minute); err != nil {
		t.Fatal(err)
	}
	if body, ok := c.Get("k"); !ok || string(body) != `{"a":1}` {
		t.Fatalf("Get = %q, %v", body, ok)
	}
	*now = now.Add(15 * time.Minute)
	if _, ok := c.Get("k"); ok {
		t.Fatal("expired entry hit")
	}
}

func TestForever(t *testing.T) {
	c, now := newTestCache(t)
	if err := c.Put("k", []byte(`[]`), Forever); err != nil {
		t.Fatal(err)
	}
	*now = now.AddDate(10, 0, 0)
	if _, ok := c.Get("k"); !ok {
		t.Fatal("pinned entry expired")
	}
}

func TestRejectsNonJSON(t *testing.T) {
	c, _ := newTestCache(t)
	if err := c.Put("k", []byte("<html>"), time.Hour); err == nil {
		t.Fatal("Put accepted a non-JSON body")
	}
}

func TestCorruptEntryIsAMiss(t *testing.T) {
	c, _ := newTestCache(t)
	if err := os.WriteFile(c.path("k"), []byte("{not json"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, ok := c.Get("k"); ok {
		t.Fatal("corrupt entry hit")
	}
}
