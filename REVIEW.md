the backend was built recently and ideally could use some manual review:

The backend is built, and the UI now talks to it by default. Choosing a range really fetches that period's Premier League matches from ESPN through the MCP server, scores their drama, picks one, gathers coverage and builds the fact sheet. Only the LLM calls are stubbed. make test passes in full, with 33 new backend tests, and nothing is committed.

What you'll see
- The pipeline: the panel shows the real stages, for example "5 completed matches" and "Picked Tottenham Hotspur v Coventry City · drama".
- The poem is a stand-in. Its first line says "No LLM yet: the mock writer lines up the facts instead", and each stanza is one key moment's fact. The lines still link to their facts.
- The checks: all seven guardrail chips show as skipped.
- Retelling works, reusing the same fact sheet. To see the old scripted runs, add ?mock=success.

I checked this in a headless browser on the running stack. For the week of 12 Oct it picks Brentford 1–2 Liverpool, the same match your scripted mock shows.

What's in it
- New pipeline contracts in contracts/pipeline/: MatchPick, MomentPick, FactDraft, Poem and GroundingVerdict are what the LLM calls will return, and make test checks they stay inside what every provider accepts. The fact sheet is assembled by the backend, so the final score, the names and the sources always come from match data, never from the model.
- backend/: FastAPI on Python 3.14 managed with uv. A swappable LLM interface with the mock behind it, so the real model calls slot in without touching the stages. It reaches the MCP server over HTTP in compose, or launches it over stdio outside Docker.
- Tests: they drive the socket the way the UI does and check every message against the WebSocket contracts. Several also compare the backend with your scripted runs, so the two can't drift apart. One test runs the real Go server. ruff and strict mypy are clean.
- Compose: a backend service on port 8000 that reloads on code changes. The frontend's dev server forwards the socket to it.

Changes to existing files
- The scripted runs now say "Premier League" instead of "English Premier League", matching what the server reports.
- The coverage search now keeps only reports that name both teams. Before, it kept other Coventry and Liverpool reports.
- Design doc: two checklist items ticked (contracts and backend), plus the new models and settings.

Things to know
- Install uv with sudo pacman -S uv, because make test now needs it. I used a private copy for this session.
- The stack is still running. I started the backend and restarted the frontend with podman compose up -d; the MCP server container was already up, maybe from your own make dev. Open http://localhost:4200, or run make down to stop it.
- screens/ isn't mine. It appeared untracked in the repo and I haven't touched it.

Next is the real LLM stages through LiteLLM with your key from the settings drawer, which is when actual rhyming poems appear. Shall I start on that?