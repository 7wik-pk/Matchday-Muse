# Matchday Muse frontend

Angular 22: standalone components, signals, zoneless. See the Angular frontend section of [docs/design.md](../docs/design.md#angular-frontend).

```sh
make dev              # from the repo root: the stack in docker compose; ng serve on http://localhost:4200
cd frontend && npx ng serve   # or on the host, without Docker
make test-frontend    # Vitest + jsdom, offline
```

The app talks to the backend on `/ws`, which `ng serve` proxies to `BACKEND_URL` (default `http://localhost:8000`; see `proxy.conf.mjs`). `?mock=<script>` replays one of the scripted runs in `contracts/ws/examples/` instead, with no backend; `?speed=<n>` replays n times faster, the poem reveal included (0 for instant). Whatever style you pick, the mock answers with that style's take from `contracts/ws/examples/takes.json`.

The production build (`environment.ts`, `samplesWithoutKey: true`) does the same for visitors without an LLM key, without `?mock`: `RoutingSocket` (`src/app/socket/routing-socket.ts`) keeps the real socket for the session and sends each run with the user's key to the backend, and each run without one to the sample replay (the `success` and `retell` scripts, in the requested style). The controls stay on the sample week, greyed out, and the result card says the poem was written in advance. The choice is per run, so adding or removing a key needs no reload. `ng serve` uses `environment.development.ts`, where runs without a key go to the backend and its `LLM_API_KEY`.

`src/app/contracts/contracts.ts` is generated from `contracts/` by `make gen`. Do not edit it.
