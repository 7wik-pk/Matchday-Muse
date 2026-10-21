"""Draws the Matchday Muse logo and writes every file made from it.

The mark: a chip whose die is marked out as a football pitch (AI, about
football), between typographic quotation marks, “ top left and ” bottom right
(something said). The quotes share the chip's character: rounded-square heads
with its corner ratio, and tails that end flat at its line weight. The chip is
sized so its nearest ink sits GAP from each quote pair.

    python3 docs/brand/make_logo.py          # from the repo root; then make brand-png

Writes:
    docs/brand/logo.svg                   the mark, accent green
    docs/brand/app-icon.svg               macOS-style tile for the portfolio: green on dark grey
    frontend/public/favicon.svg           the mark, green for light and dark tabs
    frontend/src/app/brand/logo.html      the header's inline SVG (currentColor)
"""

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SIZE, MARGIN, GAP = 40, 2.0, 1.6  # canvas, outer margin, quotes-to-chip spacing
QUOTE_SCALE = 0.85

# Line weights, in canvas units; they never scale.
OUTLINE, PIN, FINE = 2.2, 1.6, 1.2

# A closing quote mark at full size: head side and corner, tail widths and drop.
W, RC = 5.2, 1.0
ROOT_W, TIP_W = 2.9, OUTLINE
DROP, FILLET = 4.0, 0.8
H = W + DROP
SPACING = 6.4  # between the two marks of a pair

# The chip's proportions at half-width 7, scaled with it.
BASE_HALF, BASE_PIN_LEN, BASE_RX = 7.0, 3.0, 2.1


def closing_mark() -> str:
    """The 9-shaped mark with its top-left at the origin: one outline from the
    head's right side straight on into the tail (no seam), a flat end, and a
    filleted inner corner."""
    out_end = W - 2.0
    in_end = out_end - TIP_W
    root = W - ROOT_W
    return (
        f"M{RC} 0H{W - RC}A{RC} {RC} 0 0 1 {W} {RC}"
        f"V{W}C{W} {W + 2.4} {W - 0.8} {H - 0.4} {out_end} {H}"
        f"H{in_end:.2f}"
        f"C{in_end + 1.2:.2f} {H - 1.1:.2f} {root:.2f} {W + 2.2:.2f} {root:.2f} {W + FILLET:.2f}"
        f"Q{root:.2f} {W} {root - FILLET:.2f} {W}"
        f"H{RC}A{RC} {RC} 0 0 1 0 {W - RC}V{RC}A{RC} {RC} 0 0 1 {RC} 0Z"
    )


def quotes(f: float) -> str:
    """Both pairs at scale f, anchored in their corners."""
    mark = closing_mark()
    w, h, s = W * f, H * f, SPACING * f

    def at(x: float, y: float, opening: bool) -> str:
        turn = f' transform="rotate(180 {W / 2} {H / 2})"' if opening else ""
        return f'<g transform="translate({x:.2f} {y:.2f}) scale({f})"><path{turn} d="{mark}"/></g>'

    cx, cy = SIZE - MARGIN - w - s, SIZE - MARGIN - h
    return (
        f'<g class="logo-quotes">{at(MARGIN, MARGIN, True)}{at(MARGIN + s, MARGIN, True)}'
        f"{at(cx, cy, False)}{at(cx + s, cy, False)}</g>"
    )


def chip_geometry(half: float) -> dict[str, float]:
    k = half / BASE_HALF
    return {"rx": BASE_RX * k, "pin_off": 0.5 * half, "pin_len": BASE_PIN_LEN * k}


def ink_points(half: float, n: int = 60) -> list[tuple[float, float]]:
    """Points on the outer edge of the chip's top-left ink: body corner, edges, pins."""
    g = chip_geometry(half)
    pts = []
    outer = half + OUTLINE / 2
    r = g["rx"] + OUTLINE / 2
    c = 20 - outer + r
    for i in range(n + 1):
        a = math.radians(180 + 90 * i / n)
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
        t = 20 - outer + r + (2 * outer - 2 * r) * i / n
        pts += [(t, 20 - outer), (20 - outer, t)]
    for o in (-g["pin_off"], 0, g["pin_off"]):
        for j in range(n + 1):
            along = 20 - half - g["pin_len"] * j / n
            pts += [(20 + o - PIN / 2, along), (20 + o + PIN / 2, along), (along, 20 + o - PIN / 2), (along, 20 + o + PIN / 2)]
            a = math.radians(360 * j / n)
            tip = 20 - half - g["pin_len"]
            pts += [(20 + o + PIN / 2 * math.cos(a), tip + PIN / 2 * math.sin(a)), (tip + PIN / 2 * math.cos(a), 20 + o + PIN / 2 * math.sin(a))]
    return pts


def chip_half(f: float) -> float:
    """The largest chip whose ink stays GAP from the quotes and inside the margin."""
    box = (MARGIN, MARGIN, MARGIN + (SPACING + W) * f, MARGIN + H * f)

    def clearance(half: float) -> float:
        return min(
            math.hypot(max(box[0] - x, 0, x - box[2]), max(box[1] - y, 0, y - box[3])) for x, y in ink_points(half)
        )

    lo, hi = 2.0, (SIZE / 2 - MARGIN - PIN / 2) / (1 + BASE_PIN_LEN / BASE_HALF)
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if clearance(mid) >= GAP else (lo, mid)
    return lo


def chip(half: float) -> str:
    g = chip_geometry(half)
    o, length = g["pin_off"], g["pin_len"]
    pins = "".join(
        f"M{20 + d:.2f} {20 - half:.2f}v{-length:.2f}M{20 + d:.2f} {20 + half:.2f}v{length:.2f}"
        f"M{20 - half:.2f} {20 + d:.2f}h{-length:.2f}M{20 + half:.2f} {20 + d:.2f}h{length:.2f}"
        for d in (-o, 0, o)
    )
    i, cr = half * 0.657, half * 0.30
    return (
        f'<g class="logo-chip" fill="none" stroke-linecap="round" stroke-linejoin="round">'
        f'<rect x="{20 - half:.2f}" y="{20 - half:.2f}" width="{2 * half:.2f}" height="{2 * half:.2f}" rx="{g["rx"]:.2f}" stroke-width="{OUTLINE}"/>'
        f'<path d="{pins}" stroke-width="{PIN}"/>'
        f'<rect x="{20 - i:.2f}" y="{20 - i:.2f}" width="{2 * i:.2f}" height="{2 * i:.2f}" rx="{0.1 * half:.2f}" stroke-width="{FINE}"/>'
        f'<path d="M{20 - i:.2f} 20h{2 * i:.2f}" stroke-width="{FINE}"/>'
        f'<circle cx="20" cy="20" r="{cr:.2f}" stroke-width="{FINE}"/></g>'
    )


def mark_body(colour: str = "currentColor") -> str:
    half = chip_half(QUOTE_SCALE)
    return f'<g fill="{colour}">{quotes(QUOTE_SCALE)}</g><g stroke="{colour}">{chip(half)}</g>'


def svg(inner: str, view: str = f"0 0 {SIZE} {SIZE}", extra: str = "") -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}"{extra}>{inner}</svg>\n'


def squircle(size: float, n: float = 5.0, steps: int = 240) -> str:
    """A macOS-style continuous-corner tile: the superellipse |x|^n + |y|^n = 1."""
    r = size / 2
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        c, s = math.cos(t), math.sin(t)
        pts.append((r + r * math.copysign(abs(c) ** (2 / n), c), r + r * math.copysign(abs(s) ** (2 / n), s)))
    return "M" + "L".join(f"{x:.2f} {y:.2f}" for x, y in pts) + "Z"


# The portfolio tile: a vertical dark-grey gradient, as on the portfolio's other
# macOS-style icons, with the mark large in the green.
TILE_TOP, TILE_BOTTOM, TILE_RIM = "#3a3a3c", "#1c1c1e", "rgba(255,255,255,0.08)"
TILE_MARK = "#46ab76"  # the app's dark-mode green (#52b883), 5% darker
TILE_PAD = 0.085  # of the tile, each side: the mark fills about 83% of it


def app_icon(background: tuple[str, str], foreground: str, rim: str) -> str:
    """The mark on a 1024 tile, like the portfolio's other project icons."""
    size = 1024
    pad = TILE_PAD * size
    scale = (size - 2 * pad) / SIZE
    return svg(
        f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{background[0]}"/><stop offset="1" stop-color="{background[1]}"/></linearGradient></defs>'
        f'<path d="{squircle(size)}" fill="url(#bg)"/>'
        f'<path d="{squircle(size)}" fill="none" stroke="{rim}" stroke-width="4"/>'
        f'<g transform="translate({pad} {pad}) scale({scale:.3f})">{mark_body(foreground)}</g>',
        view=f"0 0 {size} {size}",
    )


def main() -> None:
    brand = ROOT / "docs" / "brand"
    (brand / "logo.svg").write_text(svg(mark_body("#1d6b45")))
    (brand / "app-icon.svg").write_text(app_icon((TILE_TOP, TILE_BOTTOM), TILE_MARK, TILE_RIM))
    themed = (
        "<style>svg{color:#1d6b45}@media (prefers-color-scheme:dark){svg{color:#52b883}}</style>" + mark_body()
    )
    (ROOT / "frontend" / "public" / "favicon.svg").write_text(svg(themed))
    header = ROOT / "frontend" / "src" / "app" / "brand"
    header.mkdir(parents=True, exist_ok=True)
    (header / "logo.html").write_text(
        "<!-- GENERATED by docs/brand/make_logo.py; do not edit. -->\n"
        + svg(mark_body(), extra=' class="logo" aria-hidden="true" focusable="false"').replace(' xmlns="http://www.w3.org/2000/svg"', "")
    )
    print(f"chip half-width {chip_half(QUOTE_SCALE):.2f}; wrote logo, app icons, favicon and header template")


if __name__ == "__main__":
    main()
