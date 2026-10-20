# Matchday Muse frontend

Angular 22: standalone components, signals, zoneless. See the Angular frontend section of [docs/design.md](../docs/design.md#angular-frontend).

```sh
make dev              # from the repo root: the stack in docker compose; ng serve on http://localhost:4200
cd frontend && npx ng serve   # or on the host, without Docker
make test-frontend    # Vitest + jsdom, offline
```

The app talks to the backend on `/ws`, which `ng serve` proxies to `BACKEND_URL` (default `http://localhost:8000`; see `proxy.conf.mjs`). `?mock=<script>` replays one of the scripted runs in `contracts/ws/examples/` instead, with no backend; `?speed=<n>` replays n times faster, the poem reveal included (0 for instant). Whatever style you pick, the mock answers with that style's take from `contracts/ws/examples/takes.json`.

`src/app/contracts/contracts.ts` is generated from `contracts/` by `make gen`. Do not edit it.
