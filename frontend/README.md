# Matchday Muse frontend

Angular 22: standalone components, signals, zoneless. See the Angular frontend section of [docs/design.md](../docs/design.md#angular-frontend).

```sh
make dev              # from the repo root: the stack in docker compose; ng serve on http://localhost:4200
cd frontend && npx ng serve   # or on the host, without Docker
make test-frontend    # Vitest + jsdom, offline
```

Until the backend exists, `src/environments/environment.ts` has `wsUrl: null`, so the app replays the scripted runs in `contracts/ws/examples/`. `?mock=<script>` opens one and plays it; `?speed=<n>` replays n times faster, the poem reveal included (0 for instant). Whatever style you pick, the mock answers with that style's take from `contracts/ws/examples/takes.json`.

`src/app/contracts/contracts.ts` is generated from `contracts/` by `make gen`. Do not edit it.
