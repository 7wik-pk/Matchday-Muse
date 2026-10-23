#!/usr/bin/env bash
# Deploys, or redeploys, the production stack (compose.prod.yaml) on the
# server: pulls the current branch, rebuilds the images, restarts what
# changed, and waits until the site answers. Needs ALLOWED_ORIGINS in .env;
# no make. Run it from anywhere: ~/ws/Matchday-Muse/deploy.sh
set -euo pipefail

say() { printf '\n==> %s\n' "$*"; }
warn() { printf 'deploy: note: %s\n' "$*" >&2; }
die() {
	printf 'deploy: %s\n' "$*" >&2
	exit 1
}

# A value from .env, read without running the file.
setting() { sed -n "s/^$1=//p" .env 2>/dev/null | tail -1; }

# All in a function, which bash reads in full before running: the pull below
# may replace this file.
main() {
	cd "$(dirname "$0")"
	local engine port before after
	if command -v podman >/dev/null; then engine=podman; else engine=docker; fi
	local compose=("$engine" compose -f compose.prod.yaml)

	[ -n "$(setting ALLOWED_ORIGINS)" ] ||
		die "set ALLOWED_ORIGINS in .env to the site's address, such as ALLOWED_ORIGINS=https://matchday-muse.example.com"
	port=$(setting APP_PORT)
	port=${port:-8080}

	if ! git diff --quiet HEAD; then
		git status --short
		die "the tracked files above have local changes; commit, stash or discard them, then deploy again"
	fi

	say "Pulling"
	before=$(git rev-parse --short HEAD)
	git pull --ff-only
	after=$(git rev-parse --short HEAD)
	if [ "$before" = "$after" ]; then echo "Already at $after"; else git log --oneline "$before..$after"; fi

	say "Building and starting"
	"${compose[@]}" up -d --build --remove-orphans

	say "Waiting for http://127.0.0.1:$port/healthz"
	local ok=false
	for _ in $(seq 60); do
		if curl -fsS -o /dev/null "http://127.0.0.1:$port/healthz" 2>/dev/null; then
			ok=true
			break
		fi
		sleep 2
	done
	"${compose[@]}" ps
	if ! $ok; then
		"${compose[@]}" logs --tail 40 backend
		die "the backend did not answer within 2 minutes; logs above"
	fi

	# The images the previous deploy ran, now untagged.
	"$engine" image prune -f >/dev/null

	if [ -n "$("$engine" ps -q --filter label=com.docker.compose.project=matchday-muse)" ]; then
		warn "the development stack is running too; stop it with: $engine compose down"
	fi
	if [ "$engine" = podman ] && ! systemctl --user is-enabled -q podman-restart.service 2>/dev/null; then
		warn "the stack will not come back after a reboot until you run, once:"
		warn "  systemctl --user enable podman-restart.service && sudo loginctl enable-linger $USER"
	fi
	say "Deployed $after on http://127.0.0.1:$port"
}

main "$@"
