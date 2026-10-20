// Package mcpserver embeds the default corpus for the fixture search
// provider, so the server needs no files beside its binary.
package mcpserver

import "embed"

//go:embed testdata/search/*.json
var SearchCorpus embed.FS
