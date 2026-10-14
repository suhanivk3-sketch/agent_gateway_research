#!/usr/bin/env python3
"""Draws the 10 "number 10" A4 kids' worksheets (banner + instruction box + scene + card strip).

Re-uses the drawing helpers from make_worksheets.py. Units are mm (viewBox 0 0 210 297).
Usage: make_worksheets_10.py OUT_DIR   -> OUT_DIR/png, OUT_DIR/svg and number-10-worksheets.pdf
"""
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_worksheets import (INK, OW, FONT, C, E, R, P, poly, line, blob, stroke_shape, one_glyph, txt, number,  # noqa: E402
                             star, cloud, sun, flower, leaf, stem_flower, bee, butterfly, duck, balloon, string,
                             rainbow, tufts, lilypad, f, render)

SX, SY, SW, SH = 12, 74, 186, 158          # main scene frame
RAINBOW = ["#ff4d6d", "#ff9f1c", "#ffd60a", "#3fbf4a", "#2f9bff", "#b66dff"]
SKIN = "#ffd2a8"
_FONT = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf", 100)


def fit(text, max_w, max_size):
    return min(max_size, max_w / (_FONT.getlength(text) / 100.0))


def width_of(text, size):
    return _FONT.getlength(text) / 100.0 * size


# ---------- shared bits ----------
def heart(cx, cy, s, fill="#ff6b9d"):
    d = (f"M{f(cx)},{f(cy + s * .9)} C{f(cx - 1.7 * s)},{f(cy - .1 * s)} {f(cx - .9 * s)},{f(cy - 1.2 * s)} {f(cx)},{f(cy - .35 * s)} "
         f"C{f(cx + .9 * s)},{f(cy - 1.2 * s)} {f(cx + 1.7 * s)},{f(cy - .1 * s)} {f(cx)},{f(cy + .9 * s)}Z")
    return P(d, fill, INK, 1.2)


def confetti(pts):
    g = ""
    for i, (x, y) in enumerate(pts):
        col = RAINBOW[i % 6]
        g += (f'<rect x="{f(x - 1.6)}" y="{f(y - .8)}" width="3.2" height="1.6" rx=".5" fill="{col}" stroke="{INK}" '
              f'stroke-width=".6" transform="rotate({(i * 47) % 180} {f(x)} {f(y)})"/>')
    return g


def zero(cx, cy, rx, ry, w, fill, ow=1.5, dash=None):
    d = (f"M{f(cx)},{f(cy - ry)} A{f(rx)},{f(ry)} 0 1 0 {f(cx)},{f(cy + ry)} "
         f"A{f(rx)},{f(ry)} 0 1 0 {f(cx)},{f(cy - ry)}")
    return stroke_shape(d, w, fill, ow, dash)


def arrow(x, y, rot, sc=0.8, col="#2ecc40"):
    return (f'<g transform="translate({f(x)},{f(y)}) rotate({rot}) scale({sc})">'
            + P("M-9,-3 H3 V-7 L13,0 L3,7 V3 H-9z", col, INK, 1.4) + "</g>")


def rainbow_text(s, cx, cy, size, stroke_w=2.4):
    cols, out, k = RAINBOW, "", 0
    for ch in s:
        if ch == " ":
            out += "\u00a0"
        else:
            out += f'<tspan fill="{cols[k % 6]}">{ch}</tspan>'
            k += 1
    return (f'<text x="{f(cx)}" y="{f(cy)}" font-family="{FONT}" font-weight="800" font-size="{f(size)}" '
            f'text-anchor="middle" dominant-baseline="central" stroke="{INK}" stroke-width="{stroke_w}" '
            f'stroke-linejoin="round" paint-order="stroke" xml:space="preserve">{out}</text>')


def hand(cx, top_y, s, fill="#fff", flip=False, dots=True, sw=1.6):
    """Open hand, 5 fingers, with a small dot above each finger."""
    xs = [cx - 18 * s + i * 9.4 * s for i in range(4)]
    hs = [26, 33, 36, 32]
    items = [("r", cx - 18 * s, top_y, 36 * s, 34 * s, 12 * s)]
    for x, h in zip(xs, hs):
        items.append(("r", x, top_y - h * s, 8.4 * s, h * s + 12 * s, 4.2 * s))
    items += [("c", cx + 21 * s, top_y + 18 * s, 7.4 * s), ("c", cx + 28 * s, top_y + 7 * s, 5.8 * s)]
    g = blob(items, fill, sw)
    if dots:
        for x, h in zip(xs, hs):
            g += C(x + 4.2 * s, top_y - h * s - 6 * s, 2.3 * s, "#ff4d6d", 1.0)
        g += C(cx + 29 * s, top_y - 4 * s, 2.3 * s, "#ff4d6d", 1.0)
    if flip:
        g = f'<g transform="translate({f(2 * cx)},0) scale(-1,1)">{g}</g>'
    return g


def pointing_hand(x, y, s):
    """Pointing hand whose fingertip is at (x, y)."""
    return (f'<g transform="translate({f(x)},{f(y)}) scale({f(s)})">'
            + blob([("r", -3.2, 0, 6.4, 20, 3.2), ("e", 0, 17, 10, 8.5), ("e", -8, 14, 3.6, 5.5)], SKIN, 1.0)
            + "</g>")


def fish(cx, cy, s, col):
    g = poly([(cx - 0.8 * s, cy), (cx - 1.8 * s, cy - 0.7 * s), (cx - 1.8 * s, cy + 0.7 * s)], col, 1.0)
    g += E(cx, cy, 1.05 * s, 0.7 * s, col, 1.0)
    g += P(f"M{f(cx - 0.1 * s)},{f(cy - 0.62 * s)} q{f(0.4 * s)},{f(-0.5 * s)} {f(0.8 * s)},{f(-0.1 * s)}", col, INK, 0.9)
    g += C(cx + 0.55 * s, cy - 0.15 * s, 0.2 * s, "#fff", 0.7) + C(cx + 0.6 * s, cy - 0.15 * s, 0.09 * s, INK, 0)
    return g


def crayon(col):
    return ('<g transform="rotate(-35)">'
            + poly([(-4, -10), (4, -10), (0, -17)], col, 1.0)
            + R(-4, -10, 8, 26, 1.2, col, 1.0) + R(-4, -3, 8, 9, 0, "#fff", 0.9) + "</g>")


# ---------- the page frame ----------
CARD_W = {1: 64, 2: 62, 3: 44, 6: 26}
CARD_GAP = {1: 0, 2: 10, 3: 14, 6: 4}


def card_centres(n):
    w, gap = CARD_W[n], CARD_GAP[n]
    total = n * w + (n - 1) * gap
    x0 = 105 - total / 2
    return [x0 + i * (w + gap) + w / 2 for i in range(n)]


def sheet(title, instr, scene_bg, scene, label, cards, extra=""):
    g = ""
    # sky and soft clouds
    g += cloud(28, 52, 4.2) + cloud(184, 54, 4.2) + cloud(152, 8, 4.5) + cloud(58, 6, 4)
    # wooden banner
    g += R(48, 8, 114, 34, 6, "#d9a066", 2.0)
    g += R(52, 12, 106, 26, 4, "#e8b97a", 1.0)
    for y in (19, 25, 31):
        g += P(f"M55,{y} q20,-2 40,0 t40,0 t17,0", "none", "#c58a4f", 0.7)
    for x, y in ((53, 13), (157, 13), (53, 37), (157, 37)):
        g += C(x, y, 1.1, "#8a5426", 0.5)
    g += rainbow_text(title, 105, 25.5, fit(title, 96, 9.5))
    g += sun(23, 24, 9) + butterfly(188, 25, 1.25, 14, "#ff7eb6", "#ffc2dd")
    # instruction box
    g += R(34, 48, 142, 19, 9.5, "#f3e8ff", 1.6, "#b66dff")
    g += txt(instr, 105, 57.8, fit(instr, 130, 6.0), "#3b2a6b", None, weight=800)
    # scene frame
    g += f'<clipPath id="sc"><rect x="{SX}" y="{SY}" width="{SW}" height="{SH}" rx="9"/></clipPath>'
    g += R(SX, SY, SW, SH, 9, scene_bg, 0)
    g += '<g clip-path="url(#sc)">' + scene + "</g>"
    g += R(SX, SY, SW, SH, 9, "none", 2.6)
    # bottom strip
    g += R(12, 238, 186, 52, 8, "#fff8dc", 1.2, "#e0a030", 'stroke-dasharray="3 2.2"')
    lw = width_of(label, 4.4) + 9
    g += R(20, 233, lw, 9, 4.5, "#ffd60a", 1.1) + txt(label, 20 + lw / 2, 237.7, 4.4, INK, None, weight=800)
    n = len(cards)
    for cx, icon in zip(card_centres(n), cards):
        g += R(cx - CARD_W[n] / 2, 248, CARD_W[n], 36, 4.5, "#fff", 1.3)
        g += f'<g transform="translate({f(cx)},266)">{icon}</g>'
    g += extra
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">'
            '<rect width="210" height="297" fill="#bfe6ff"/>' + g + "</svg>")


# ---------- scenes ----------
def sc1():
    g = rainbow(105, 224, 88, 5.0)
    g += P("M0,214 Q105,188 210,214 V240 H0Z", "#7bd77a", 1.6)
    g += tufts([30, 180], 226)
    ax, ay, H, w = 70, 94, 96, 26
    d1 = f"M{f(ax - 0.2 * H)},{f(ay + 0.19 * H)} L{ax},{ay} L{ax},{ay + H}"
    g += stroke_shape(d1, w, "#fff7d6", 1.5, 7.5)
    g += C(ax - 0.2 * H, ay + 0.19 * H, 4.4, "#2ecc40", 1.4) + arrow(ax - 0.2 * H - 10, ay + 0.19 * H + 14, -40)
    g += zero(138, 146, 22, 48, w, "#fff7d6", 1.5, 7.5)
    g += C(138, 98, 4.4, "#2ecc40", 1.4) + arrow(150, 98, 180, 0.7)
    g += butterfly(24, 92, 1.1, -12) + butterfly(188, 94, 1.0, 14, "#ff4d6d", "#ffd60a") + butterfly(94, 214, 0.8, 6, "#4cc9f0", "#b66dff")
    g += flower(30, 224, 4.5, "#ff4d6d") + flower(48, 220, 3.5, "#ffd60a") + flower(176, 224, 4.5, "#b66dff") + flower(192, 218, 3.5, "#ff9f1c")
    return g


def sc2():
    g = P("M0,212 Q105,190 210,212 V240 H0Z", "#7bd77a", 1.6) + tufts([30, 110, 185], 226)
    w = 30
    ax, ay, H = 76, 98, 84
    d1 = f"M{f(ax - 0.2 * H)},{f(ay + 0.19 * H)} L{ax},{ay} L{ax},{ay + H}"
    g += P(d1, "none", INK, w + 6) + P(d1, "none", "#fff", w)
    cx, cy, rx, ry = 134, 140, 23, 42
    d0 = (f"M{cx},{cy - ry} A{rx},{ry} 0 1 0 {cx},{cy + ry} A{rx},{ry} 0 1 0 {cx},{cy - ry}")
    g += P(d0, "none", INK, w + 6) + P(d0, "none", "#fff", w)
    g += balloon(24, 112, 18, 23, "#ff4d6d") + string(24, 125, 24, 148, 3)
    g += balloon(186, 118, 18, 23, "#4cc9f0") + string(186, 131, 186, 156, -3)
    g += star(26, 170, 7) + star(184, 176, 7, "#ff9f1c") + star(105, 88, 6, "#ff9f1c") + star(40, 90, 5) + star(172, 92, 5)
    g += heart(104, 206, 6) + heart(32, 202, 5, "#b66dff") + heart(180, 204, 5, "#ff9ec7")
    g += confetti([(60, 86), (150, 86), (22, 140), (190, 150), (105, 216), (70, 214)])
    g += flower(60, 224, 4.5, "#ff4d6d") + flower(150, 224, 4.5, "#ffd60a")
    return g


def sc3():
    g = ""
    g += hand(50, 148, 1.45, "#fff", flip=False) + hand(160, 148, 1.45, "#fff", flip=True)
    g += star(104, 100, 8) + star(104, 182, 6, "#ff9f1c") + star(22, 90, 5, "#ff9f1c") + star(190, 214, 6)
    g += confetti([(30, 84), (80, 80), (125, 82), (180, 84), (104, 140), (22, 210), (86, 216), (126, 216), (180, 118), (22, 130), (186, 160)])
    return g


def sc4():
    g = P("M0,0 H210 V240 H0Z", "#c8efb0", 0)
    g += E(105, 154, 92, 74, "#5ec4f2", 2.2)
    g += E(105, 154, 80, 62, "#7cd3f7", 0)
    for y, x0 in ((100, 62), (205, 70)):
        g += P(f"M{x0},{y} q5,-3 10,0 t10,0 t10,0", "none", "#bfeaff", 1.4)
    spots = [(40, 114), (84, 104), (130, 108), (170, 118), (60, 150), (108, 154), (152, 150), (42, 188), (92, 192), (146, 190)]
    cols = ["#ffd60a"] * 10
    for x, y in spots:
        g += duck(x, y, 7.2)
    g += lilypad(27, 90, 11, "#ff9ec7") + lilypad(180, 92, 11, "#fff") + lilypad(26, 222, 11, "#fff") + lilypad(182, 220, 11, "#ff9ec7")
    g += stem_flower(100, 212, 232, 4, "#ff4d6d") if False else ""
    g += flower(104, 224, 4.5, "#ffd60a") + flower(60, 80, 4, "#ff4d6d") + flower(150, 80, 4, "#b66dff")
    return g


def sc5():
    g = P("M0,200 Q105,176 210,204 V240 H0Z", "#7bd77a", 1.6)
    g += cloud(40, 82, 6) + cloud(168, 214, 6) + cloud(60, 224, 5)
    nums = [4, 10, 8, 10, 2, 6, 10, 1, 3, 9, 5, 7]
    cols = ["#ff4d6d", "#ffd60a", "#2f9bff", "#3fbf4a", "#ff9f1c", "#b66dff"]
    for i, n in enumerate(nums):
        r, c = divmod(i, 4)
        cx, cy = 35 + c * 46.5, 99 + r * 52
        col = cols[(i * 5 + r) % 6]
        g += string(cx, cy + 20, cx + 1, cy + 29, 2)
        g += balloon(cx, cy, 31, 38, col, 1.5)
        g += number(str(n), cx, cy - 1, 15, ["#fff", "#fff"])
    return g


def sc6():
    g = ""
    import random
    rnd = random.Random(4)
    for _ in range(26):
        x, y = rnd.uniform(18, 192), rnd.uniform(80, 226)
        if (x - 105) ** 2 / 78 ** 2 + (y - 160) ** 2 / 78 ** 2 < 1 or (x - 38) ** 2 + (y - 100) ** 2 < 24 ** 2:
            continue
        g += star(x, y, rnd.uniform(1.8, 3.2), "#fff7b0", 0.5)
    g += C(36, 102, 15, "#fff3b0", 1.6)
    g += C(31, 99, 1.6, INK, 0) + C(41, 99, 1.6, INK, 0)
    g += P("M30,106 Q36,111 42,106", "none", INK, 1.2) + C(27, 104, 2.4, "#ffab91", 0) + C(45, 104, 2.4, "#ffab91", 0)
    g += star(176, 98, 3.4, "#fff7b0", 0.6)
    cx, cy, Ro, Ri = 105, 162, 64, 27
    for i in range(10):
        a = math.radians(-90 + i * 36)
        rr = Ro if i % 2 == 0 else Ri
        x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
        g += C(x, y, 6.8, "#ffd60a", 1.4) + txt(str(i + 1), x, y + 0.3, 7.2 if i < 9 else 6.2, INK, None, weight=800)
    return g


def sc7():
    g = P("M0,0 H210 V240 H0Z", "#7fd3f0", 0)
    g += P("M0,226 Q105,214 210,226 V240 H0Z", "#f0d9a0", 1.4)
    # big 10 in a rainbow circle
    cx, cy, r = 52, 152, 31
    g += C(cx, cy, r + 5, INK, 0)
    for i, c in enumerate(RAINBOW):
        g += C(cx, cy, r + 4 - i * 1.6, c, 0)
    g += C(cx, cy, r - 6, "#fff", 1.6)
    g += number("10", cx, cy, 24, ["#ff9f1c", "#2f9bff"])
    g += C(cx + r + 6, cy, 3.4, "#2ecc40", 1.2)
    boxes = [80, 132, 184]
    fish_cols = ["#ff9f1c", "#ff6b9d", "#ffd60a", "#b66dff", "#3fbf4a"]
    groups = [4, 10, 7]
    for by, n in zip(boxes, groups):
        g += R(94, by, 98, 44, 7, "#e9f9ff", 1.8) + C(94, by + 22, 3.4, "#2ecc40", 1.2)
        rows = [n] if n <= 5 else [5, n - 5]
        for ri, cnt in enumerate(rows):
            ys = by + 22 if len(rows) == 1 else by + 12 + ri * 20
            span = 18
            x0 = 143 - (cnt - 1) * span / 2
            for k in range(cnt):
                g += fish(x0 + k * span, ys, 4.6, fish_cols[(k + ri * 2 + by) % 5])
    # coral, seaweed, bubbles
    g += P("M18,232 q-4,-14 2,-22 q-6,-8 0,-16", "none", INK, 5) + P("M18,232 q-4,-14 2,-22 q-6,-8 0,-16", "none", "#ff6b6b", 3)
    g += P("M36,232 q4,-12 -2,-20", "none", INK, 5) + P("M36,232 q4,-12 -2,-20", "none", "#ff9ec7", 3)
    g += P("M80,232 q-6,-12 0,-22 q6,-8 0,-14", "none", INK, 5) + P("M80,232 q-6,-12 0,-22 q6,-8 0,-14", "none", "#3fbf4a", 3)
    for x, y, rr in [(24, 92, 5), (42, 108, 3.4), (74, 96, 4), (30, 200, 4), (64, 206, 3.4), (190, 232, 3)]:
        g += C(x, y, rr, "#e6f7ff", 1.0) + C(x - rr * .3, y - rr * .3, rr * .2, "#fff", 0)
    return g


def sc8():
    g = P("M0,200 Q105,184 210,204 V240 H0Z", "#7bd77a", 1.6) + tufts([28, 182], 224)
    g += R(22, 88, 62, 82, 7, "#fff", 2.0) + R(126, 88, 62, 82, 7, "#fff", 2.0)
    g += P("M53,98 V160", "none", "#555", 3.2, 'stroke-dasharray="0 6.5"') + C(53, 98, 3.8, "#2ecc40", 1.3)
    g += P("M157,100 a21,21 0 1 0 0.1,0", "none", "#555", 3.2, 'stroke-dasharray="0 6.5"') + C(157, 100, 3.8, "#2ecc40", 1.3)
    g += P("M105,110 V150 M85,130 H125", "none", INK, 12) + P("M105,110 V150 M85,130 H125", "none", "#ff9f1c", 8.5)
    g += number("10", 105, 196, 34, ["#ff9f1c", "#2f9bff"])
    g += bee(40, 84, 0.9, -8) + bee(172, 80, 0.9, 10) + bee(96, 82, 0.8, 4)
    g += stem_flower(22, 192, 232, 5, "#ff4d6d", 2) + stem_flower(188, 190, 232, 5, "#b66dff", -2)
    g += stem_flower(46, 205, 234, 4, "#ffd60a", 2) + stem_flower(164, 204, 234, 4, "#4cc9f0", -2)
    return g


def sc9():
    g = rainbow(105, 232, 90, 5.5)
    g += P("M0,222 Q105,208 210,222 V240 H0Z", "#7bd77a", 1.6)
    g += cloud(26, 222, 8) + cloud(184, 222, 8) + cloud(40, 88, 6) + cloud(176, 90, 6)
    pts = [(34 + i * 34.5, 128 + 9 * math.sin(i * 1.4)) for i in range(5)]
    pts += [(34 + (4 - i) * 34.5, 186 + 9 * math.sin(i * 1.4 + 1)) for i in range(5)]
    path = "M" + " L".join(f"{f(x)},{f(y)}" for x, y in pts[:5]) + " Q198,157 " + " L".join(f"{f(x)},{f(y)}" for x, y in pts[5:])
    g += P(path, "none", "#fff", 2.2, 'stroke-dasharray="1 3.5"')
    for i, (x, y) in enumerate(pts):
        g += C(x, y, 10, "#fff", 1.9, INK)
    g += star(105, 94, 6) + star(150, 100, 4, "#ff9f1c") + star(60, 100, 4, "#ff9f1c")
    return g


def sc10():
    g = P("M0,226 Q105,214 210,228 V240 H0Z", "#7bd77a", 1.6)
    tip = (141, 170)
    for r in range(2):
        for c in range(5):
            pass
    pos = [(34 + c * 35.5, 96 + r * 40) for r in range(2) for c in range(5)]
    for x, y in pos:
        g += P(f"M{f(x)},{f(y + 17)} Q{f(x + (tip[0] - x) * .15)},{f(y + (tip[1] - y) * .7)} {tip[0]},{tip[1]}", "none", INK, 0.8)
    for x, y in pos:
        g += balloon(x, y, 28, 34, "#fff", 1.6)
    # elephant
    bc = "#9db8d6"
    g += blob([("c", 80, 202, 17), ("c", 130, 202, 17)], bc, 1.5)
    g += C(80, 202, 11, "#ffc2dd", 0) + C(130, 202, 11, "#ffc2dd", 0)
    g += blob([("e", 105, 250, 40, 34)], bc, 1.5)
    tr = f"M112,222 C128,230 140,214 {tip[0]},{tip[1] + 6}"
    g += P(tr, "none", INK, 12.5) + P(tr, "none", bc, 9.5)
    g += blob([("c", 105, 210, 24)], bc, 1.5)
    g += C(97, 204, 2.4, INK, 0) + C(113, 204, 2.4, INK, 0) + P("M99,216 q6,4 12,0", "none", INK, 1.1)
    g += C(94, 212, 3.2, "#ffab91", 0) + C(116, 212, 3.2, "#ffab91", 0)
    g += star(26, 172, 7) + star(184, 196, 7, "#ff9f1c") + star(40, 214, 5, "#ff9f1c") + star(188, 168, 5)
    g += confetti([(24, 150), (186, 150), (40, 190), (170, 214), (60, 168), (150, 220)])
    return g


# ---------- cards (icons in local coords, centre 0,0) ----------
def ico_trace(kind):
    if kind == "1":
        g = P("M-8,-6 L0,-14 L0,14", "none", "#555", 2.6, 'stroke-dasharray="0 4.4"') + C(-8, -6, 2.4, "#2ecc40", 0.8)
        return g + pointing_hand(-8, -6, 0.9).replace('translate(-8.00,-6.00)', 'translate(-8.00,-6.00)')
    g = P("M0,-13 a9,13 0 1 0 0.1,0", "none", "#555", 2.6, 'stroke-dasharray="0 4.4"') + C(0, -13, 2.4, "#2ecc40", 0.8)
    return g + pointing_hand(0, -13, 0.9)


def ico_crayon(col):
    return crayon(col)


def ico_five():
    return hand(-11, 3, 0.36, "#fff", dots=False, sw=0.9) + txt("5", 17, 0.5, 18, "#ff4d6d", INK, 2.0)


def ico_ten():
    return hand(-24, 3, 0.26, "#fff", dots=False, sw=0.8) + hand(-6, 3, 0.26, "#fff", True, False, 0.8) + txt("10", 18, 0.5, 14, "#2f9bff", INK, 2.0)


def ico_num(n, col="#ff9f1c"):
    return number(str(n), 0, 0, 16, [col, col])


def ico_badge():
    return C(0, 0, 15, "#ff4d6d", 1.5) + number("10", 0, 0, 13, ["#fff", "#fff"])


def ico_dot(n):
    return C(0, 0, 11, "#ffd60a", 1.5) + txt(str(n), 0, 0.4, 12, INK, None, weight=800)


def ico_match():
    g = number("10", -16, 0, 11, ["#ff9f1c", "#2f9bff"])
    g += P("M-6,0 H6", "none", INK, 1.0, 'stroke-dasharray="1.5 1.5"')
    g += R(8, -10, 17, 20, 3, "#e9f9ff", 1.0)
    g += fish(17, -5, 2.4, "#ff9f1c") + fish(17, 1, 2.4, "#ff6b9d") + fish(17, 7, 2.4, "#ffd60a")
    return g


def ico_line():
    return P("M0,-13 V13", "none", INK, 7) + P("M0,-13 V13", "none", "#ff4d6d", 4.4)


def ico_circle():
    return C(0, 0, 11, "none", 6.4, INK) + C(0, 0, 11, "none", 3.8, "#2f9bff")


def ico_finger():
    return pointing_hand(0, -14, 1.2) + C(0, 15, 0.1, "#fff", 0)


def ico_marker():
    return ('<g transform="rotate(30)">' + R(-4.5, -14, 9, 22, 2, "#4cc9f0", 1.0) + R(-4.5, -14, 9, 7, 2, "#2f9bff", 1.0)
            + poly([(-4.5, 8), (4.5, 8), (0, 13)], "#ff4d6d", 1.0) + "</g>" + C(-6, 14, 3, "#ff4d6d", 0.8))


def ico_sticker():
    return C(0, 0, 12, "#ffd60a", 1.4) + star(0, 0, 6.5, "#ff6b9d", 1.0) + P("M7,11 q5,-1 5,-6 q-5,0 -5,6z", "#fff", INK, 0.9)


# ---------- pages ----------
def page_cards():
    cr = ["#ff4d6d", "#2f9bff", "#ffd60a", "#3fbf4a", "#ff9f1c"]
    p2 = [ico_crayon(c) for c in cr + ["#ff7eb6"]]
    p10 = [ico_crayon(c) for c in cr + ["#b66dff"]]
    arrows = "".join(arrow(x, 266, 0, 0.9, "#ff9f1c") for x in (card_centres(3)[0] + 29, card_centres(3)[1] + 29))
    pages = [
        ("Trace the Number 10!", "Trace the 1 and the 0 with your finger.", "#e8f6ff", sc1, "Trace like this:",
         [ico_trace("1"), ico_trace("0")], ""),
        ("Color the Number 10!", "Color the big 10 with your favorite colors.", "#e8f6ff", sc2, "Use these:", p2, ""),
        ("10 Fingers!", "Count your fingers. Color each finger.", "#fff7e0", sc3, "Count with me:", [ico_five(), ico_ten()], ""),
        ("Duck Pond Count!", "Count the ducks. Circle the number 10.", "#c8efb0", sc4, "Find the right number:",
         [ico_num(8, "#ff4d6d"), ico_num(10, "#ff9f1c"), ico_num(12, "#3fbf4a")], ""),
        ("Number 10 Hunt!", "Find and circle every 10.", "#d8f0ff", sc5, "Look for this:", [ico_badge()], ""),
        ("Connect the Dots!", "Draw a line from 1 to 10.", "#1d2b64", sc6, "Follow the numbers:",
         [ico_dot(1), ico_dot(2), ico_dot(3)], arrows),
        ("Match the Number!", "Draw a line from 10 to the group of 10 fish.", "#7fd3f0", sc7, "Draw a line like this:", [ico_match()], ""),
        ("A Stick and a Ball!", "Draw a line. Draw a circle. Make 10!", "#d8f0ff", sc8, "Draw these:", [ico_line(), ico_circle()], ""),
        ("Dab 10 Dots!", "Press a finger in each circle. Count to 10.", "#d8f0ff", sc9, "Use one:",
         [ico_finger(), ico_marker(), ico_sticker()], ""),
        ("10 Balloons!", "Count the balloons. Color each one.", "#e8f6ff", sc10, "Color them:", p10, ""),
    ]
    names = ["01-trace-the-number-10", "02-color-the-number-10", "03-10-fingers", "04-duck-pond-count",
             "05-number-10-hunt", "06-connect-the-dots", "07-match-the-number", "08-a-stick-and-a-ball",
             "09-dab-10-dots", "10-10-balloons"]
    return list(zip(names, pages))


def build(item, out):
    name, (title, instr, bg, scene, label, cards, extra) = item
    svg = os.path.join(out, "svg", name + ".svg")
    with open(svg, "w") as fh:
        fh.write(sheet(title, instr, bg, scene(), label, cards, extra))
    png = os.path.join(out, "png", name + ".png")
    render(svg, png)
    return name


if __name__ == "__main__":
    out = sys.argv[1]
    only = set(sys.argv[2:])
    os.makedirs(os.path.join(out, "svg"), exist_ok=True)
    os.makedirs(os.path.join(out, "png"), exist_ok=True)
    items = [it for it in page_cards() if not only or it[0][:2] in only]
    with ThreadPoolExecutor(max_workers=5) as ex:
        for n in ex.map(lambda it: build(it, out), items):
            print("done", n, flush=True)
    if not only:
        fs = sorted(os.listdir(os.path.join(out, "png")))
        ims = [Image.open(os.path.join(out, "png", x)).convert("RGB") for x in fs]
        ims[0].save(os.path.join(out, "number-10-worksheets.pdf"), save_all=True, append_images=ims[1:], resolution=300.0)
        print("pdf written")
