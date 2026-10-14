#!/usr/bin/env python3
"""Draws the 10 "number 11" A4 kids' worksheets as SVG, then renders PNGs.

Units are millimetres (viewBox 0 0 210 297). PNGs are 2480x3508 (A4 at 300 dpi).
Page 1 is the existing ../worksheet/worksheet.svg and is copied as-is.

Usage: make_worksheets.py OUT_DIR   (renders all pages in parallel)
"""
import math
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
INK = "#111"
OW = 1.4  # outline width
FONT = "Inter, 'DejaVu Sans', sans-serif"
PAL = ["#ff4d6d", "#ff9f1c", "#ffd60a", "#6fd65a", "#4cc9f0", "#b66dff"]


# ---------- basic pieces ----------
def f(x):
    return f"{x:.2f}"


def P(d, fill="none", stroke=INK, sw=OW, extra=""):
    return (f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{f(sw)}" '
            f'stroke-linecap="round" stroke-linejoin="round" {extra}/>')


def C(cx, cy, r, fill="#fff", sw=OW, stroke=INK, extra=""):
    return (f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{f(sw)}" {extra}/>')


def E(cx, cy, rx, ry, fill="#fff", sw=OW, rot=0, stroke=INK):
    t = f' transform="rotate({rot} {f(cx)} {f(cy)})"' if rot else ""
    return (f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{f(sw)}"{t}/>')


def R(x, y, w, h, rx=0, fill="#fff", sw=OW, stroke=INK, extra=""):
    return (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{f(sw)}" {extra}/>')


def poly(pts, fill="#fff", sw=OW):
    p = " ".join(f"{f(x)},{f(y)}" for x, y in pts)
    return (f'<polygon points="{p}" fill="{fill}" stroke="{INK}" stroke-width="{f(sw)}" '
            f'stroke-linejoin="round"/>')


def line(x0, y0, x1, y1, sw=0.9, stroke=INK):
    return (f'<line x1="{f(x0)}" y1="{f(y0)}" x2="{f(x1)}" y2="{f(y1)}" stroke="{stroke}" '
            f'stroke-width="{f(sw)}" stroke-linecap="round"/>')


def blob(items, fill, sw=OW):
    """Several overlapping shapes drawn as ONE outlined silhouette."""
    def one(it, fl, stroke_w, stroke):
        k = it[0]
        s = f'fill="{fl}" stroke="{stroke}" stroke-width="{f(stroke_w)}" stroke-linejoin="round"'
        if k == "c":
            return f'<circle cx="{f(it[1])}" cy="{f(it[2])}" r="{f(it[3])}" {s}/>'
        if k == "e":
            return f'<ellipse cx="{f(it[1])}" cy="{f(it[2])}" rx="{f(it[3])}" ry="{f(it[4])}" {s}/>'
        return (f'<rect x="{f(it[1])}" y="{f(it[2])}" width="{f(it[3])}" height="{f(it[4])}" '
                f'rx="{f(it[5])}" {s}/>')
    back = "".join(one(i, INK, 2 * sw, INK) for i in items)
    front = "".join(one(i, fill, 0, "none") for i in items)
    return back + front


def stroke_shape(d, w, fill, ow=1.5, dash=None):
    """A thick rounded stroke with an outline (used for the number 1)."""
    s = P(d, "none", INK, w + 2 * ow) + P(d, "none", fill, w)
    if dash:
        s += P(d, "none", "#555", 3, f'stroke-dasharray="0 {dash}"')
    return s


# ---------- numbers ----------
def one_glyph(ax, ay, H, w, fill, ow=1.5):
    """Number 1: apex (ax, ay) of the centre line, height H, stroke width w."""
    d = f"M{f(ax - 0.2 * H)},{f(ay + 0.19 * H)} L{f(ax)},{f(ay)} L{f(ax)},{f(ay + H)}"
    return stroke_shape(d, w, fill, ow)


def txt(s, x, y, size, fill=INK, stroke=None, sw=2.8, weight=800):
    st = (f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" paint-order="stroke"'
          if stroke else "")
    return (f'<text x="{f(x)}" y="{f(y)}" font-family="{FONT}" font-weight="{weight}" '
            f'font-size="{f(size)}" text-anchor="middle" dominant-baseline="central" '
            f'fill="{fill}"{st}>{s}</text>')


def number(s, cx, cy, h, fills=None):
    """Bubbly number string of cap-height h centred on (cx, cy)."""
    fills = fills or ["#ff9f1c", "#4cc9f0"]
    w = 0.2 * h
    H = h - w
    adv = []
    for ch in s:
        adv.append(0.2 * H + w if ch == "1" else 0.78 * h)
    gap = 0.16 * h
    total = sum(adv) + gap * (len(s) - 1)
    x = cx - total / 2
    out = []
    for i, ch in enumerate(s):
        a = adv[i]
        col = fills[i % len(fills)]
        if ch == "1":
            out.append(one_glyph(x + 0.2 * H + w / 2, cy - h / 2 + w / 2, H, w, col, ow=h * 0.04 + 0.5))
        else:
            out.append(txt(ch, x + a / 2, cy + h * 0.04, h * 1.38, col, INK, 2.2 + h * 0.03))
        x += a + gap
    return "".join(out)


# ---------- scenery ----------
def star(cx, cy, r, fill="#ffd60a", sw=OW):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.48
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return poly(pts, fill, sw)


def cloud(cx, cy, s, fill="#fff"):
    items = [("c", cx - 0.9 * s, cy + 0.1 * s, 0.6 * s), ("c", cx - 0.1 * s, cy - 0.25 * s, 0.8 * s),
             ("c", cx + 0.85 * s, cy + 0.05 * s, 0.62 * s), ("r", cx - 1.3 * s, cy + 0.1 * s, 2.6 * s, 0.6 * s, 0.3 * s)]
    return blob(items, fill)


def sun(cx, cy, r):
    s = ""
    for i in range(12):
        a = i * math.pi / 6
        x0, y0 = cx + 1.25 * r * math.cos(a), cy + 1.25 * r * math.sin(a)
        x1, y1 = cx + 1.7 * r * math.cos(a), cy + 1.7 * r * math.sin(a)
        s += line(x0, y0, x1, y1, 2.4 + 0.0, INK)
        s += line(x0, y0, x1, y1, 1.0, "#ffd60a")
    s += C(cx, cy, r, "#ffd60a", 1.6)
    s += C(cx - 0.35 * r, cy - 0.15 * r, 0.1 * r, INK, 0) + C(cx + 0.35 * r, cy - 0.15 * r, 0.1 * r, INK, 0)
    s += P(f"M{f(cx - 0.4 * r)},{f(cy + 0.2 * r)} Q{f(cx)},{f(cy + 0.6 * r)} {f(cx + 0.4 * r)},{f(cy + 0.2 * r)}", "none", INK, 1.0)
    s += C(cx - 0.6 * r, cy + 0.2 * r, 0.14 * r, "#ffab91", 0) + C(cx + 0.6 * r, cy + 0.2 * r, 0.14 * r, "#ffab91", 0)
    return s


def flower(cx, cy, s, col, cc="#ffd60a"):
    out = ""
    for i in range(6):
        a = i * math.pi / 3
        out += C(cx + s * math.cos(a), cy + s * math.sin(a), 0.78 * s, col, 1.1)
    return out + C(cx, cy, 0.62 * s, cc, 1.1)


def leaf(x, y, rot=0, L=10, fill="#6fd65a"):
    return (f'<g transform="translate({f(x)},{f(y)}) rotate({rot})">'
            + P(f"M0,0 q{f(L * .55)},{f(-L * .6)} {f(L)},{f(-L * .08)} q{f(-L * .6)},{f(L * .55)} {f(-L)},{f(L * .08)}z",
                fill, "#111", 1.0) + "</g>")


def stem_flower(x, y_top, y_bot, s, col, lean=0):
    d = f"M{f(x)},{f(y_bot)} Q{f(x + lean)},{f((y_top + y_bot) / 2)} {f(x)},{f(y_top)}"
    out = P(d, "none", INK, 3.6) + P(d, "none", "#3fbf4a", 1.6)
    out += leaf(x, y_top + (y_bot - y_top) * 0.62, -20, s * 2.2) + leaf(x, y_top + (y_bot - y_top) * 0.78, 200, s * 2.2)
    return out + flower(x, y_top, s, col)


def bee(cx, cy, s=1.0, rot=0):
    g = f'<g transform="translate({f(cx)},{f(cy)}) rotate({rot}) scale({f(s)})">'
    g += E(-3, -8, 5, 7, "#d6f1ff", 1.0, -25) + E(4, -8, 5, 7, "#d6f1ff", 1.0, 25)
    g += E(0, 0, 11, 8, "#ffd60a", 1.3)
    g += P("M-3,-7.5 q-2,7.5 0,15", "none", INK, 2.2) + P("M3,-7.7 q-2,7.7 0,15.4", "none", INK, 2.2)
    g += C(8.5, -1.5, 1.4, INK, 0) + P("M-11,0 l-3,0", "none", INK, 1.5)
    g += P("M6,-7 q2,-4 5,-5", "none", INK, 1.0) + "</g>"
    return g


def butterfly(cx, cy, s=1.0, rot=0, c1="#b66dff", c2="#ff9f1c"):
    g = f'<g transform="translate({f(cx)},{f(cy)}) rotate({rot}) scale({f(s)})">'
    g += E(-9, -6, 9, 11, c1, 1.3, -25) + E(9, -6, 9, 11, c1, 1.3, 25)
    g += E(-7, 9, 6.5, 8, c2, 1.3, 20) + E(7, 9, 6.5, 8, c2, 1.3, -20)
    g += C(-9, -7, 2.6, "#fff", 0) + C(9, -7, 2.6, "#fff", 0)
    g += E(0, 1, 2.2, 11, INK, 0)
    g += P("M-1,-9 q-4,-7 -7,-7", "none", INK, 1.0) + P("M1,-9 q4,-7 7,-7", "none", INK, 1.0)
    return g + "</g>"


def duck(cx, cy, s):
    g = blob([("e", cx, cy + 0.2 * s, 1.0 * s, 0.7 * s), ("c", cx + 0.6 * s, cy - 0.55 * s, 0.52 * s)], "#ffd60a", 1.1)
    g += P(f"M{f(cx - 0.95 * s)},{f(cy + 0.05 * s)} l{f(-0.4 * s)},{f(-0.35 * s)} l{f(0.1 * s)},{f(0.6 * s)}z", "#ffd60a", INK, 1.0)
    g += E(cx + 1.12 * s, cy - 0.5 * s, 0.3 * s, 0.16 * s, "#ff9f1c", 0.9)
    g += C(cx + 0.7 * s, cy - 0.7 * s, 0.09 * s, INK, 0)
    g += P(f"M{f(cx - 0.4 * s)},{f(cy + 0.15 * s)} q{f(0.4 * s)},{f(0.5 * s)} {f(0.85 * s)},{f(-0.1 * s)}", "#ffe66d", INK, 0.9)
    return g


def balloon(cx, cy, w, h, fill="#fff", sw=OW, shine=True):
    x0, x1 = cx - w / 2, cx + w / 2
    top, bot = cy - h / 2, cy + h / 2
    d = (f"M{f(cx)},{f(bot)} C{f(cx - w * .62)},{f(cy + h * .22)} {f(x0 - w * .12)},{f(top)} {f(cx)},{f(top)} "
         f"C{f(x1 + w * .12)},{f(top)} {f(cx + w * .62)},{f(cy + h * .22)} {f(cx)},{f(bot)}Z")
    g = P(d, fill, INK, sw)
    g += poly([(cx, bot - 0.6), (cx - w * .09, bot + w * .1), (cx + w * .09, bot + w * .1)], fill, 1.0)
    if shine:
        g += P(f"M{f(cx - w * .27)},{f(cy - h * .12)} q{f(w * .03)},{f(-h * .2)} {f(w * .2)},{f(-h * .27)}", "none", "#fff", 1.4,
               'opacity=".85"') if fill != "#fff" else ""
    return g


def string(x0, y0, x1, y1, wig=4):
    dy = y1 - y0
    d = (f"M{f(x0)},{f(y0)} C{f(x0 + wig)},{f(y0 + dy * .3)} {f(x1 - wig)},{f(y0 + dy * .6)} "
         f"{f((x0 + x1) / 2)},{f(y0 + dy * .72)} S{f(x1 + wig * .5)},{f(y1 - 4)} {f(x1)},{f(y1)}")
    return P(d, "none", INK, 0.8)


def rainbow(cx, cy, r, bw=3.4, cols=None):
    cols = cols or ["#ff4d6d", "#ff9f1c", "#ffd60a", "#6fd65a", "#4cc9f0", "#b66dff"]
    n = len(cols)
    g = ""
    d = lambda rr: f"M{f(cx - rr)},{f(cy)} A{f(rr)},{f(rr)} 0 0 1 {f(cx + rr)},{f(cy)}"
    g += (f'<path d="{d(r - bw * (n - 1) / 2)}" fill="none" stroke="{INK}" stroke-width="{f(bw * n + 2.4)}"/>')
    for i, c in enumerate(cols):
        g += (f'<path d="{d(r - i * bw)}" fill="none" stroke="{c}" stroke-width="{f(bw)}"/>')
    return g


def grass_hill(path, fill="#7bd77a"):
    return P(path, fill, INK, 1.6)


def tufts(xs, y, fill="#3fbf4a"):
    g = ""
    for x in xs:
        g += P(f"M{x - 3},{y} l2,-7 l1.2,5 l1.8,-8 l1.4,8 l1.6,-5 l1.6,7", "none", "#2e9e3a", 1.3)
    return g


def lilypad(cx, cy, r, flower_col=None):
    a1, a2 = -0.5, 0.5
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1) * 0.6
    d = f"M{f(cx)},{f(cy)} L{f(cx + r * 1.0)},{f(cy - r * .22)} A{f(r)},{f(r * .6)} 0 1 1 {f(cx + r * 1.0)},{f(cy + r * .22)}Z"
    g = P(d, "#6fd65a", INK, 1.2)
    if flower_col:
        g += flower(cx - r * .2, cy - r * .1, r * .28, flower_col)
    return g


def cattail(x, y_top, y_bot):
    d = f"M{f(x)},{f(y_bot)} Q{f(x + 2)},{f((y_top + y_bot) / 2)} {f(x)},{f(y_top)}"
    return P(d, "none", INK, 3.0) + P(d, "none", "#3fbf4a", 1.2) + R(x - 2.6, y_top - 12, 5.2, 14, 2.6, "#a0693e", 1.1)


# ---------- page wrapper ----------
def page(body, bg="#fff"):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">'
            f'<rect width="210" height="297" fill="{bg}"/>' + body + "</svg>")


# ---------- the pages ----------
def page2():
    """Huge outlined 11 to colour in."""
    g = ""
    g += cloud(36, 18, 8) + cloud(176, 18, 8) + star(105, 18, 11, "#fff")
    g += balloon(36, 172, 26, 34) + string(36, 189, 36, 214, 3)
    g += star(125, 160, 10, "#fff") + star(200, 98, 7, "#fff") + star(14, 100, 7, "#fff")
    g += balloon(124, 204, 24, 31) + string(124, 220, 124, 236, 3)
    g += balloon(50, 270, 22, 28) + balloon(105, 272, 22, 28) + balloon(160, 270, 22, 28)
    g += cloud(28, 244, 6) + cloud(182, 244, 6)
    H, w = 150, 34
    for ax in (80, 170):
        d = f"M{f(ax - 0.2 * H)},{f(60 + 0.19 * H)} L{f(ax)},60 L{f(ax)},{f(60 + H)}"
        g += P(d, "none", INK, w + 6) + P(d, "none", "#fff", w)
    return page(g)


def page3():
    """Count the apples: exactly 11."""
    g = ""
    g += sun(172, 30, 14)
    # trunk
    g += P("M92,140 L96,215 L114,215 L118,140Z", "#b5763a", INK, 1.6)
    g += P("M100,160 q3,10 0,18", "none", "#8a5426", 1.2) + P("M110,185 q-3,8 0,16", "none", "#8a5426", 1.2)
    # canopy
    can = [("c", 105, 105, 40), ("c", 68, 118, 31), ("c", 142, 118, 31), ("c", 85, 82, 30), ("c", 125, 82, 30),
           ("c", 50, 100, 22), ("c", 160, 100, 22)]
    g += blob(can, "#5ccf5f", 1.6)
    g += grass_hill("M0,218 Q105,184 210,218 V297 H0Z")
    g += tufts([20, 48, 160, 190], 232) + tufts([75, 140], 285)
    for x, y in [(70, 105), (105, 74), (140, 105), (85, 137), (125, 137), (105, 113), (52, 128), (158, 128)]:
        g += apple(x, y, 7.4)
    for x, y in [(55, 248), (105, 266), (155, 248)]:
        g += apple(x, y, 8.2)
    g += stem_flower(22, 262, 292, 4, "#ff4d6d") + stem_flower(190, 268, 294, 4, "#b66dff")
    # big 11 in a circle at the top
    g += C(36, 34, 24, "#fff7d6", 2.2) + number("11", 36, 34, 25)
    return page(g)


def apple(cx, cy, r):
    g = blob([("c", cx - 0.3 * r, cy + 0.08 * r, 0.76 * r), ("c", cx + 0.3 * r, cy + 0.08 * r, 0.76 * r)], "#ff3b4f", 1.2)
    g += P(f"M{f(cx)},{f(cy - 0.7 * r)} q{f(0.05 * r)},{f(-0.5 * r)} {f(0.25 * r)},{f(-0.75 * r)}", "none", "#6b3f1d", 1.3)
    g += leaf(cx + 0.1 * r, cy - 0.85 * r, -25, r * 0.9)
    g += P(f"M{f(cx - 0.62 * r)},{f(cy - 0.1 * r)} q{f(0.02 * r)},{f(-0.35 * r)} {f(0.3 * r)},{f(-0.4 * r)}", "none", "#fff", 1.1, 'opacity=".85"')
    return g


def page4():
    """Find and circle the number 11."""
    nums = [3, 7, 11, 5, 11, 2, 9, 11, 4, 8, 6, 1]
    cols = ["#ff4d6d", "#ffd60a", "#4cc9f0", "#6fd65a", "#ff9f1c", "#b66dff"]
    g = ""
    for i, n in enumerate(nums):
        r, c = divmod(i, 3)
        cx, cy = 38 + c * 67 + (r % 2) * 0, 42 + r * 68
        col = cols[(i * 5 + r) % 6]
        g += string(cx, cy + 24, cx + 2, cy + 36, 2)
        g += balloon(cx, cy, 40, 48, col, 1.6)
        g += number(str(n), cx, cy - 1, 20, ["#fff", "#fff"])
    return page(g)


def page5():
    """Dot-to-dot 1..11 making a fish."""
    pts = [(28, 160), (58, 122), (105, 108), (146, 132), (180, 108), (166, 160),
           (180, 212), (146, 188), (110, 214), (70, 203), (40, 188)]
    g = ""
    # waves top and bottom
    for y in (14, 24):
        g += P("M0," + str(y) + " " + " ".join(f"q6,-6 12,0 t12,0" for _ in range(1)) + " t12,0" * 16, "none", "#4cc9f0", 2.0)
    for y in (276, 286):
        g += P("M0," + str(y) + " q6,-6 12,0" + " t12,0" * 17, "none", "#4cc9f0", 2.0)
    # bubbles
    for x, y, r in [(18, 50, 6), (30, 76, 4), (14, 104, 7), (190, 52, 7), (182, 80, 4), (196, 104, 5),
                    (22, 232, 6), (14, 250, 4), (188, 238, 6), (196, 256, 4), (95, 58, 5), (116, 70, 3.5), (84, 78, 3)]:
        g += C(x, y, r, "#e6f7ff", 1.2) + C(x - r * .3, y - r * .3, r * .22, "#fff", 0)
    # seaweed & starfish
    g += P("M40,277 q-6,-10 0,-18 q6,-8 0,-16", "none", INK, 5) + P("M40,277 q-6,-10 0,-18 q6,-8 0,-16", "none", "#3fbf4a", 3)
    g += P("M170,277 q6,-10 0,-18 q-6,-8 0,-16", "none", INK, 5) + P("M170,277 q6,-10 0,-18 q-6,-8 0,-16", "none", "#3fbf4a", 3)
    g += star(105, 262, 11, "#ff9f1c")
    # hint of the fish: eye (inside the shape only)
    g += C(62, 148, 5.5, "#fff", 1.3) + C(63.5, 148, 2.4, INK, 0)
    for i, (x, y) in enumerate(pts, 1):
        g += C(x, y, 7.2, "#ffd60a", 1.5) + txt(str(i), x, y + 0.4, 8.4 if i < 10 else 7.2, INK, None, weight=800)
    return page(g)


def page6():
    """Match the number to the right group."""
    g = ""
    g += cattail(12, 200, 292) + cattail(20, 222, 294)
    g += lilypad(35, 262, 14, "#ff9ec7") + lilypad(170, 276, 12, "#fff") + lilypad(40, 40, 12, "#ff9ec7")
    g += E(40, 50, 0.1, 0.1, "none", 0)
    # big 11 in a circle
    g += C(45, 148, 34, "#fff7d6", 2.4) + number("11", 45, 148, 40)
    g += C(79, 148, 3.3, "#2ecc40", 1.2)
    boxes = [24, 108, 192]
    for by in boxes:
        g += R(98, by, 100, 72, 8, "#e6f7ff", 1.8)
        g += P(f"M106,{by + 66} q6,-4 12,0 t12,0 t12,0 t12,0", "none", "#bfe6f7", 1.4)
        g += C(98, by + 36, 3.3, "#2ecc40", 1.2)

    def ducks(by, spots):
        return "".join(duck(98 + x, by + y, 5.6) for x, y in spots)
    g += ducks(24, [(25, 38), (50, 38), (75, 38)])
    g += ducks(108, [(17, 17), (40, 17), (63, 17), (86, 17), (17, 38), (40, 38), (63, 38), (86, 38),
                     (28, 59), (51, 59), (74, 59)])
    g += ducks(192, [(25, 26), (50, 26), (75, 26), (25, 52), (50, 52), (75, 52)])
    return page(g)


def page7():
    """Dab 11 dots."""
    g = ""
    g += rainbow(182, 190, 22, 3.0) + cloud(160, 192, 5) + cloud(204, 194, 4.5)
    g += rainbow(32, 262, 22, 3.0) + cloud(14, 264, 5) + cloud(52, 267, 5)
    g += cloud(28, 70, 9) + cloud(170, 60, 8)
    g += star(190, 120, 6) + star(20, 150, 6) + star(190, 250, 6)
    pts = [(105 + 50 * math.sin(i * 0.9), 76 + i * 20.5) for i in range(11)]
    # soft guide line
    guide = "M" + " L".join(f"{f(x)},{f(y)}" for x, y in pts)
    g += P(guide, "none", "#ddd", 1.2, 'stroke-dasharray="1 3"')
    for i, (x, y) in enumerate(pts):
        g += C(x, y, 8.6, "#fff", 1.7, PAL[i % 6])
        g += C(x, y, 8.6, "none", 0.7)
    g += number("11", 105, 34, 34)
    return page(g)


def page8():
    """Colour 11 balloons (outline only) with a bear."""
    hand = (105, 207)
    pos = [(99, 58), (141, 58), (183, 58),
           (36, 112), (78, 112), (120, 112), (162, 112),
           (57, 166), (99, 166), (141, 166), (183, 166)]
    pos[0], pos[1], pos[2] = (84, 58), (128, 58), (172, 58)
    g = ""
    for x, y in pos:
        g += P(f"M{x},{y + 27} Q{f(x + (hand[0] - x) * 0.15)},{f(y + (hand[1] - y) * 0.7)} {hand[0]},{hand[1]}", "none", INK, 0.8)
    for x, y in pos:
        g += balloon(x, y, 36, 46, "#fff", 1.6)
    g += number("11", 30, 28, 30)
    # bear
    br, dk = "#c98a54", "#a8693a"
    g += blob([("e", 105, 285, 34, 34)], br, 1.6)
    g += E(105, 285, 20, 24, "#f3d3a8", 1.0)
    for sx, dx in ((-1, -1), (1, 1)):
        d = f"M{105 + sx * 26},{272} Q{105 + sx * 44},{235} {105 + sx * 9},{208}"
        g += P(d, "none", INK, 13.5) + P(d, "none", br, 10.5)
    g += blob([("c", 105, 244, 24), ("c", 84, 224, 9), ("c", 126, 224, 9)], br, 1.6)
    g += C(84, 224, 4.6, "#f3d3a8", 1.0) + C(126, 224, 4.6, "#f3d3a8", 1.0)
    g += E(105, 252, 11, 8.5, "#f3d3a8", 1.1) + E(105, 247.5, 3.6, 2.6, INK, 0)
    g += C(95, 238, 2.4, INK, 0) + C(115, 238, 2.4, INK, 0)
    g += P("M105,250 v3 M99,254 q6,5 12,0", "none", INK, 1.1)
    g += C(88, 247, 3.4, "#ffab91", 0) + C(122, 247, 3.4, "#ffab91", 0)
    g += C(97, 208, 6.6, br, 1.4) + C(113, 208, 6.6, br, 1.4)
    return page(g)


def page9():
    """Make 11 with two sticks."""
    g = ""
    for x in (30, 138):
        g += R(x, 48, 42, 124, 8, "#fff", 2.0)
        g += R(x + 6, 56, 30, 108, 5, "none", 1.0, "#bbb", 'stroke-dasharray="2 3"')
    # plus sign
    g += P("M105,92 V128 M87,110 H123", "none", INK, 17) + P("M105,92 V128 M87,110 H123", "none", "#ff9f1c", 13)
    # arrow down
    g += poly([(98, 184), (112, 184), (112, 204), (122, 204), (105, 222), (88, 204), (98, 204)], "#2ecc40", 1.6)
    g += number("11", 105, 258, 52)
    # bees and flowers
    g += bee(32, 24, 1.0, -10) + bee(180, 30, 1.0, 8) + bee(176, 196, 0.9, -8) + bee(32, 200, 0.9, 10)
    g += stem_flower(16, 238, 297, 5.5, "#ff4d6d", 3) + stem_flower(194, 244, 297, 5.5, "#b66dff", -3)
    g += stem_flower(42, 268, 297, 4.5, "#ffd60a", 2) + stem_flower(168, 274, 297, 4.5, "#4cc9f0", -2)
    return page(g)


def page10():
    """Hidden 11 in the garden."""
    g = ""
    g += sun(34, 34, 14) + cloud(110, 32, 10) + cloud(176, 62, 9)
    # back hills
    g += P("M0,150 Q60,118 130,150 Q175,168 210,150 V297 H0Z", "#a8e6a0", 1.6)
    # tree (trunk + canopy)
    g += '<g transform="translate(-14,0)">'
    g += P("M148,128 L152,215 L186,215 L190,128Z", "#b5763a", INK, 1.6)
    g += one_glyph(164, 148, 42, 8, "#8a5426", 0.7) + one_glyph(180, 148, 42, 8, "#8a5426", 0.7)
    can = [("c", 168, 90, 32), ("c", 140, 108, 24), ("c", 196, 108, 24), ("c", 148, 76, 22), ("c", 190, 74, 22)]
    g += blob(can, "#4fc95a", 1.6)
    for x, y in [(150, 100), (178, 78), (192, 108), (140, 82)]:
        g += apple(x, y, 5.6)
    g += "</g>"
    # fence with the other hidden 11
    g += R(0, 160, 140, 6, 2, "#c88f52", 1.4) + R(0, 190, 140, 6, 2, "#c88f52", 1.4)
    for i in range(8):
        x = 4 + i * 17
        g += poly([(x, 160), (x + 7, 150), (x + 14, 160), (x + 14, 214), (x, 214)], "#e8b878", 1.4)
    g += one_glyph(58, 168, 40, 8.5, "#c98c4c", 0.7) + one_glyph(76, 168, 40, 8.5, "#c98c4c", 0.7)
    # front hill + flowers
    g += P("M0,222 Q90,196 210,226 V297 H0Z", "#7bd77a", 1.6)
    g += tufts([14, 70, 130, 196], 240)
    g += stem_flower(30, 244, 290, 9, "#ff4d6d", 3) + stem_flower(72, 252, 295, 8, "#ffd60a", -3)
    g += stem_flower(118, 242, 292, 9, "#b66dff", 3) + stem_flower(160, 256, 296, 8, "#ff9f1c", -3)
    g += stem_flower(196, 246, 292, 8, "#4cc9f0", -3)
    g += butterfly(98, 78, 1.5, -12) + butterfly(24, 120, 1.0, 14, "#ff4d6d", "#ffd60a")
    g += bee(70, 120, 1.0, -8)
    return page(g)


PAGES = [
    ("01-trace-the-number-11", None),
    ("02-color-the-big-number-11", page2),
    ("03-count-and-circle-11-apples", page3),
    ("04-find-and-circle-the-number-11", page4),
    ("05-dot-to-dot-1-to-11", page5),
    ("06-match-the-number-to-the-group", page6),
    ("07-dab-11-dots", page7),
    ("08-color-11-balloons", page8),
    ("09-make-11-with-two-sticks", page9),
    ("10-hidden-11-in-the-garden", page10),
]

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def render(svg_path, png_path):
    html = svg_path[:-4] + ".html"
    with open(html, "w") as fh:
        fh.write('<html><body style="margin:0"><img src="file://%s" '
                 'style="width:2480px;height:3508px;display:block"></body></html>' % os.path.abspath(svg_path))
    prof = svg_path[:-4] + ".profile"
    subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                    f"--user-data-dir={prof}", f"--screenshot={os.path.abspath(png_path)}",
                    "--window-size=2480,3800", "file://" + os.path.abspath(html)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=180)
    from PIL import Image
    im = Image.open(png_path)
    im.crop((0, 0, 2480, 3508)).save(png_path, optimize=True)
    os.remove(html)
    shutil.rmtree(prof, ignore_errors=True)


def build(name, fn, out):
    svg = os.path.join(out, name + ".svg")
    if fn is None:
        shutil.copy(os.path.join(HERE, "..", "worksheet", "worksheet.svg"), svg)
    else:
        with open(svg, "w") as fh:
            fh.write(fn())
    render(svg, os.path.join(out, name + ".png"))
    return name


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    only = set(sys.argv[2:])
    todo = [(n, fn) for n, fn in PAGES if not only or n[:2] in only]
    with ThreadPoolExecutor(max_workers=5) as ex:
        for n in ex.map(lambda a: build(a[0], a[1], out), todo):
            print("done", n, flush=True)
