# TODO

Work that is planned but deliberately not scheduled into a phase yet. When an item is picked up, move it into the roadmap in [docs/design.md](docs/design.md#build-roadmap) and delete it here. Undecided design choices live under [Open questions](docs/design.md#agent-instructions-and-open-questions) instead.

## Parked

### Measure pick quality

**Why it matters:** choosing the week's most dramatic or funny match is the product's core decision, and nothing currently scores it. The current evals check that the passage is grounded, accurate and on-style, not that it is about the right match.

**What is already in place:** the golden set is built from whole frozen weeks, each with a reference match, so this can be added without re-recording any data.

**The work:**

- [ ] For each golden week, label every match you would accept as the week's pick (usually 1 to 3), each tagged `drama` or `comedy`, with a one-line reason.
- [ ] Add Inspect scorers:
  - **Pick hit rate:** the share of weeks where `pick_match`'s choice is on the acceptable list. Proposed target ≥ 0.8.
  - **Angle agreement:** the pick's `angle` matches the label for that match. Track only.
  - **Signals-only baseline:** the hit rate of simply taking the match with the highest drama-signal total. The LLM pick must beat it, or the LLM step is not earning its cost.
- [ ] Set a human ceiling for the target. Ask another football fan to pick their match of the week for the same golden weeks, without seeing your lists, and count how often their pick is on your list. Set the hit-rate target at or below that agreement rate: if you agree 9 weeks in 10, 0.8 is fair; if only 6 in 10, widen the lists or lower the target.
- [ ] Publish two comparisons in the README: LLM pick vs the signals-only baseline, and `pick_match` with vs without the `search_coverage` tool.
- [ ] Add the pick hit-rate target to the next phase gate.

**Unblocks:** tuning the drama-signal weights (roadmap Phase 4), which needs a pick score to tune against.

### Decide what "week" means for far-from-UK users

**Found while building the mocks:** a calendar week in the user's timezone can split a league's matchweek. In Melbourne (UTC+11 in October), the week of Mon 12 Oct 2026 contains 9 EPL matches from two different matchweeks: the tail of one (the three Sunday 11 Oct games, which kick off from midnight Monday local time, and the Monday-night game) and the Saturday 17 Oct games of the next. The Sunday 18 Oct games fall into the following week. The same week in London time is one clean set of 10 matches.

- [ ] Decide between: calendar weeks in the user's timezone (current design, simple but splits matchweeks); calendar weeks in the league's home timezone; or the league's own matchweek or round, where the source provides one.
- [ ] Whatever is chosen, show it in the range label so the user can see why a match is in or out.
