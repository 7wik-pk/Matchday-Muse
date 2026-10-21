"""The output checks. Each returns a Check: its status, a one-line detail for
the result card's chip, and, when it fails, the problems to send back to the
writer for the repair attempt.

Guardrails protect truth and safety; craft (metre, rhyme, where the result
lands) is left to evals. The only craft rules enforced here are the word caps
and the line counts of fixed forms.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from app.contracts.pipeline.fact_sheet import FactSheet
from app.contracts.pipeline.grounding_verdict import GroundingVerdict
from app.contracts.pipeline.poem import Poem
from app.guardrails.vocab import GENERIC, STOCK_FIGURES, TEAM_ALIASES

type CheckId = Literal["score", "names", "quotes", "overlap", "form", "grounding", "moderation"]
type Status = Literal["pass", "fail", "skipped"]

MAX_HEADLINE_WORDS = 10
MIN_LINES, MAX_LINES = 8, 30
MAX_WORDS = 300
MAX_QUOTES, MAX_QUOTE_WORDS = 1, 25
MAX_SHARED_SPAN = 10  # words in a row shared with any source
MAX_CONTAINMENT = 0.05  # share of the poem's 8-grams found in a source
NGRAM = 8
MAX_SCORE_NUMBER = 15  # larger pairs are minutes, years or formations, not scores


@dataclass
class Check:
    id: CheckId
    status: Status
    detail: str | None
    problems: list[str] = field(default_factory=list)


@dataclass
class Material:
    """What the checks compare the poem with."""

    sheet: FactSheet
    style: str
    venue: str | None
    scores: Sequence[str]  # every home-away score the match passed through, such as "1-0"
    coverage: Sequence[str]  # the text of the coverage the fact sheet drew on


def poem_lines(poem: Poem) -> list[str]:
    return [line for stanza in poem.stanzas for line in stanza.lines]


_WORD = re.compile(r"[\w'’]+")


def words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


# Score


_N = r"(?:\d{1,2}|nil|nought|zero|one|two|three|four|five|six|seven|eight|nine|ten)"
_NUMBERS = {"nil": 0, "nought": 0, "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
_NUMBERS |= {"seven": 7, "eight": 8, "nine": 9, "ten": 10}
_SCORE_PATTERNS = [
    # 1–2, one–nil, 2-1; not 4-4-2, a minute like 45+2, or a word like nine-man
    re.compile(rf"(?<![\w+'’–-])({_N})\s*[-–—]\s*({_N})(?![\w'’+–-])", re.IGNORECASE),
    re.compile(rf"\b({_N})\s+goals?\s+to\s+({_N})\b", re.IGNORECASE),
    re.compile(r"(?<![\w+])(\d{1,2})\s+to\s+(\d{1,2})(?!\w)"),
]
_ONE_TWO = re.compile(r"\ban?\s+(?:quick\s+|slick\s+|neat\s+)?one[-–]two\b", re.IGNORECASE)  # the passing move


def number(token: str) -> int:
    return int(token) if token.isdigit() else _NUMBERS[token.lower()]


def scores_in(text: str) -> list[tuple[int, int]]:
    text = _ONE_TWO.sub(" ", text)
    found = []
    for pattern in _SCORE_PATTERNS:
        for m in pattern.finditer(text):
            a, b = number(m[1]), number(m[2])
            if max(a, b) <= MAX_SCORE_NUMBER:
                found.append((a, b))
    return found


def check_score(poem: Poem, m: Material) -> Check:
    """Every score in the poem must be one the match passed through. Order is
    ignored ("two–one to Liverpool" is fine for Brentford 1–2 Liverpool); the
    grounding judge checks who led."""
    allowed = {(0, 0)}
    for s in m.scores:
        h, _, a = s.partition("-")
        if h.isdigit() and a.isdigit():
            allowed.add(tuple(sorted((int(h), int(a)))))  # type: ignore[arg-type]
    stated = [s for line in [poem.headline, *poem_lines(poem)] for s in scores_in(line)]
    wrong = sorted({s for s in stated if tuple(sorted(s)) not in allowed})
    if wrong:
        shown = ", ".join(f"{a}–{b}" for a, b in wrong)
        return Check(
            "score",
            "fail",
            f"Score not in the match: {shown}",
            [f"The score {a}–{b} never happened; the final result was {m.sheet.final_result}." for a, b in wrong],
        )
    if not stated:
        return Check("score", "pass", "No score stated in figures")
    return Check("score", "pass", "Every score matches the match data")


# Names


_TOKEN = re.compile(r"[^\W\d_][\w'’\-]*")
_SENTENCE_START = re.compile(r"(?:^|[.!?:;—–\"“”(])\s*$")


def _base(token: str) -> str:
    for suffix in ("'s", "’s", "'", "’"):
        token = token.removesuffix(suffix)
    return token


def allowed_names(m: Material) -> set[str]:
    phrases: list[str] = [*GENERIC, *STOCK_FIGURES.get(m.style, set()), m.sheet.competition]
    phrases += [m.venue or ""]
    for team in m.sheet.teams_or_participants:
        phrases += [team, *TEAM_ALIASES.get(team, set())]
    for p in m.sheet.roster:
        phrases += [p.canonical, *p.variants]
    # Names the facts themselves use, such as a referee or manager from coverage.
    phrases += [t for f in m.sheet.facts for t in _TOKEN.findall(f.text) if t[0].isupper()]
    allowed: set[str] = set()
    for phrase in phrases:
        for token in _TOKEN.findall(phrase):
            token = _base(token).casefold()
            allowed |= {token, *token.split("-")}
    return allowed


def _is_allowed(token: str, allowed: set[str]) -> bool:
    t = _base(token).casefold()
    candidates = {t, t.removesuffix("s"), f"{t}s"}  # Bee and Bees
    return bool(candidates & allowed) or all(part in allowed for part in t.split("-") if part)


def check_names(poem: Poem, m: Material) -> Check:
    """Capitalised words in mid-line must be people in the roster or the
    facts, the teams and their nicknames, the venue, or the form's stock
    figures. Line and sentence starts are skipped, and so is the headline,
    which is in title case. (A deterministic stand-in for named-entity
    recognition: see the design doc's future scope.)"""
    allowed = allowed_names(m)
    unknown: dict[str, int] = {}
    for n, line in enumerate(poem_lines(poem), start=1):
        for match in _TOKEN.finditer(line):
            token = match.group()
            if not token[0].isupper() or _SENTENCE_START.search(line[: match.start()]):
                continue
            if not _is_allowed(token, allowed):
                unknown.setdefault(_base(token), n)
    if unknown:
        return Check(
            "names",
            "fail",
            f"Not in the match: {', '.join(unknown)}",
            [
                f"Line {n}: {name} is not anyone or anything in this match; use only the roster's people."
                for name, n in unknown.items()
            ],
        )
    people = {p.canonical for p in m.sheet.roster if _mentions(poem, p.canonical, p.variants)}
    return Check("names", "pass", f"{len(people)} people named, all in the match roster")


def _mentions(poem: Poem, canonical: str, variants: Iterable[str]) -> bool:
    text = " ".join(poem_lines(poem)).casefold()
    return any(name.casefold() in text for name in [canonical, *variants])


# Quotes


_QUOTE = re.compile(r"[“\"]([^”\"]+)[”\"]")


def _squash(text: str) -> str:
    return " ".join(words(text))


def check_quotes(poem: Poem, m: Material) -> Check:
    """Quoted words must appear word for word in a quote fact."""
    text = " ".join([poem.headline, *poem_lines(poem)])
    quotes = [q.strip() for q in _QUOTE.findall(text) if q.strip()]
    if not quotes:
        return Check("quotes", "pass", "No quotes used")
    sources = [_squash(f.text) for f in m.sheet.facts if f.kind == "quote"]
    problems = [
        f'"{q}" is not a quote from the fact sheet; quote only a quote fact word for word, or do not quote.'
        for q in quotes
        if not any(_squash(q) in s for s in sources)
    ]
    long = [q for q in quotes if len(words(q)) > MAX_QUOTE_WORDS]
    problems += [f'"{q[:40]}…" is longer than {MAX_QUOTE_WORDS} words.' for q in long]
    if len(quotes) > MAX_QUOTES:
        problems.append(f"Use at most {MAX_QUOTES} quote; the poem has {len(quotes)}.")
    if problems:
        return Check("quotes", "fail", problems[0], problems)
    return Check("quotes", "pass", "1 quote, from the fact sheet")


# Originality


def longest_shared_span(a: Sequence[str], b: Sequence[str]) -> int:
    best, row = 0, [0] * (len(b) + 1)
    for x in a:
        prev_diag = 0
        for j, y in enumerate(b, start=1):
            current = row[j]
            row[j] = prev_diag + 1 if x == y else 0
            best = max(best, row[j])
            prev_diag = current
    return best


def ngrams(tokens: Sequence[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def check_overlap(poem: Poem, m: Material) -> Check:
    """The poem may not copy the coverage: no shared run longer than
    MAX_SHARED_SPAN words, and at most MAX_CONTAINMENT of its 8-grams found in
    a source. Verified quotes are left out of the comparison."""
    text = _QUOTE.sub(" ", " ".join(poem_lines(poem)))
    tokens = words(text)
    if not m.coverage or not tokens:
        return Check("overlap", "pass", "No coverage to compare with")
    span = max(longest_shared_span(tokens, words(src)) for src in m.coverage)
    grams = ngrams(tokens, NGRAM)
    source_grams = set().union(*(ngrams(words(src), NGRAM) for src in m.coverage))
    containment = len(grams & source_grams) / len(grams) if grams else 0.0
    detail = f"Longest span shared with a source: {span} words; {NGRAM}-gram overlap {containment:.1%}"
    problems = []
    if span > MAX_SHARED_SPAN:
        problems.append(f"{span} words in a row are copied from a source; say it in your own words.")
    if containment > MAX_CONTAINMENT:
        problems.append(f"{containment:.0%} of the poem's phrases are copied from a source; say it in your own words.")
    return Check("overlap", "fail" if problems else "pass", detail, problems)


# Length and form


# Fixed forms: total lines, or lines per stanza (design doc: Guardrails).
FORM_LINES = {"sonnet": 14, "villanelle": 19}
STANZA_LINES = {"limericks": 5, "clerihews": 4}


def check_form(poem: Poem, m: Material) -> Check:
    lines = poem_lines(poem)
    n_words = sum(len(words(line)) for line in lines)
    head_words = len(words(poem.headline))
    problems = []
    if head_words > MAX_HEADLINE_WORDS:
        problems.append(f"The headline has {head_words} words; use at most {MAX_HEADLINE_WORDS}.")
    if not MIN_LINES <= len(lines) <= MAX_LINES:
        problems.append(f"The poem has {len(lines)} lines; write {MIN_LINES} to {MAX_LINES}.")
    if n_words > MAX_WORDS:
        problems.append(f"The poem has {n_words} words; use at most {MAX_WORDS}.")
    if (want := FORM_LINES.get(m.style)) and len(lines) != want:
        problems.append(f"A {m.style} has exactly {want} lines; this one has {len(lines)}.")
    if (per := STANZA_LINES.get(m.style)) and any(len(s.lines) != per for s in poem.stanzas):
        counts = ", ".join(str(len(s.lines)) for s in poem.stanzas)
        problems.append(f"Each stanza of {m.style} has {per} lines; these have {counts}.")
    detail = f"{len(poem.stanzas)} stanzas, {len(lines)} lines; {n_words} words"
    return Check("form", "fail" if problems else "pass", problems[0] if problems else detail, problems)


# Grounding


def check_grounding(poem: Poem, verdict: GroundingVerdict) -> Check:
    """Every factual claim must rest on a fact: the judge lists each line's
    unsupported claims. A line the judge skipped counts as unchecked."""
    lines = [poem.headline, *poem_lines(poem)]
    by_index = {v.index: v for v in verdict.lines}
    problems = []
    for i, line in enumerate(lines):
        v = by_index.get(i)
        if v is None:
            problems.append(f'Line {i} ("{line}") was not checked; make every line checkable against the facts.')
            continue
        where = "The headline" if i == 0 else f"Line {i}"
        problems += [f'{where}: "{claim}" is not supported by the fact sheet.' for claim in v.unsupported]
    if problems:
        return Check("grounding", "fail", problems[0], problems)
    claims = sum(1 for v in verdict.lines if v.fact_ids)
    return Check("grounding", "pass", f"{claims} lines with factual claims, all supported")


def deterministic(poem: Poem, m: Material) -> list[Check]:
    return [
        check_score(poem, m),
        check_names(poem, m),
        check_quotes(poem, m),
        check_overlap(poem, m),
        check_form(poem, m),
    ]
