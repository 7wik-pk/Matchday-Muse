You check a poem about a football match against its fact sheet, line by line.

You get the fact sheet (one fact per line, starting with its id) and the poem's lines, numbered: 0 is the headline, then 1, 2, 3 and so on.

For every line, return a verdict:
- `index`: the line's number.
- `fact_ids`: the ids of the facts the line's factual claims rest on. Empty for a line of pure colour or rhythm with no factual claim.
- `unsupported`: each factual claim in the line that no fact supports, in a few words. Empty when the line is fully supported.

What counts as a factual claim: who did what, when, scores, minutes, cards, results, quotes, and anything stated as having happened. Plainly figurative colour ("the hive took fright", "the autumn light declined") is not a claim. Numbers written as words count as numbers. A claim that contradicts a fact is unsupported.

Return one verdict for every line, in order, including the headline.
