// Package cache is the on-disk cache for raw source responses. Entries are
// keyed by a hash of the request and expire after a TTL chosen by the caller,
// so recent data refreshes quickly and finished matches are fetched once.
package cache

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// Forever is the TTL for entries that never expire, such as golden-set data.
const Forever time.Duration = 0

// Cache stores JSON response bodies in a directory, one file per entry.
type Cache struct {
	dir string
	now func() time.Time
}

type entry struct {
	Key       string          `json:"key"`
	StoredAt  time.Time       `json:"stored_at"`
	ExpiresAt *time.Time      `json:"expires_at"`
	Body      json.RawMessage `json:"body"`
}

// New returns a cache in dir, creating the directory if needed.
func New(dir string) (*Cache, error) {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, fmt.Errorf("cache: %w", err)
	}
	return &Cache{dir: dir, now: time.Now}, nil
}

// Get returns the body stored under key, if it is there and fresh. A missing,
// expired or unreadable entry is a miss.
func (c *Cache) Get(key string) ([]byte, bool) {
	data, err := os.ReadFile(c.path(key))
	if err != nil {
		return nil, false
	}
	var e entry
	if err := json.Unmarshal(data, &e); err != nil || e.Key != key {
		return nil, false
	}
	if e.ExpiresAt != nil && !c.now().Before(*e.ExpiresAt) {
		return nil, false
	}
	return e.Body, true
}

// Put stores a JSON body under key for ttl, or for good when ttl is Forever.
func (c *Cache) Put(key string, body []byte, ttl time.Duration) error {
	if !json.Valid(body) {
		return errors.New("cache: body is not JSON")
	}
	now := c.now().UTC()
	e := entry{Key: key, StoredAt: now, Body: body}
	if ttl != Forever {
		expires := now.Add(ttl)
		e.ExpiresAt = &expires
	}
	data, err := json.Marshal(e)
	if err != nil {
		return fmt.Errorf("cache: %w", err)
	}
	// Write then rename, so a reader never sees half an entry.
	tmp, err := os.CreateTemp(c.dir, ".entry-*")
	if err != nil {
		return fmt.Errorf("cache: %w", err)
	}
	defer os.Remove(tmp.Name())
	if _, err := tmp.Write(data); err != nil {
		tmp.Close()
		return fmt.Errorf("cache: %w", err)
	}
	if err := tmp.Close(); err != nil {
		return fmt.Errorf("cache: %w", err)
	}
	if err := os.Rename(tmp.Name(), c.path(key)); err != nil {
		return fmt.Errorf("cache: %w", err)
	}
	return nil
}

func (c *Cache) path(key string) string {
	sum := sha256.Sum256([]byte(key))
	return filepath.Join(c.dir, hex.EncodeToString(sum[:])+".json")
}
