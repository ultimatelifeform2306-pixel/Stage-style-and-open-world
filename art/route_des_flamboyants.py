"""Render a 16-bit style screen of 'La route des flamboyants' (fan-art homage).

Side-on shot like the film: a row of flame trees whose red crowns merge into
one ceiling of blossom over a clear blue sky, with slender dark trunks forking
into fans of branches and a villager walking past with spear and shield.
Drawn at 320x224 (Mega Drive resolution) with a fixed palette and ordered
dithering, then upscaled 4x with nearest-neighbour.
"""
import math
import random

from PIL import Image, ImageDraw

W, H = 320, 224
SCALE = 4
GROUND = 211
rng = random.Random(11)

P = {
    "sky0": (24, 72, 184), "sky1": (40, 104, 216), "sky2": (72, 144, 232),
    "sky3": (120, 184, 240), "sky4": (176, 216, 244), "sky5": (216, 236, 248),
    "red0": (112, 8, 16), "red1": (160, 16, 20), "red2": (204, 24, 24),
    "red3": (232, 48, 32), "red4": (248, 96, 64), "red5": (255, 160, 120),
    "bark0": (44, 38, 40), "bark1": (60, 52, 52), "bark2": (112, 102, 100),
    "haze0": (120, 136, 152), "haze1": (88, 96, 104), "haze2": (152, 168, 176),
    "dirt0": (56, 40, 36), "dirt1": (88, 64, 52), "dirt2": (40, 28, 28),
    "skin0": (56, 32, 28), "skin1": (88, 52, 40), "cloth": (176, 32, 32),
    "hide0": (208, 168, 112), "hide1": (160, 120, 80), "spear": (136, 124, 112),
}

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

img = Image.new("RGB", (W, H))
px = img.load()
d = ImageDraw.Draw(img)


def dither_band(y0, y1, colors):
    """Vertical gradient through `colors`, ordered-dithered between steps."""
    n = len(colors) - 1
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1) * n
        i = min(int(t), n - 1)
        f = t - i
        for x in range(W):
            px[x, y] = colors[i + 1] if f * 16 > BAYER[y % 4][x % 4] + 0.5 else colors[i]


def limb(p0, p1, p2, w0, w1, col, hi=None):
    """Tapered branch along a quadratic bezier p0 -> p2 bending through p1."""
    steps = int(math.dist(p0, p2)) + 2
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        r = (w0 + (w1 - w0) * t) / 2
        d.ellipse((x - r, y - r, x + r, y + r), fill=col)
        if hi and r >= 1.5:
            px[int(x - r + 0.5), int(y)] = hi


# Sky: deep blue overhead fading to pale haze at the horizon
dither_band(0, 100, [P["sky0"], P["sky1"]])
dither_band(100, GROUND, [P["sky1"], P["sky2"], P["sky3"], P["sky4"], P["sky5"]])

# Hazy distant bush line on the horizon
for x in range(W):
    h = 3 + 2 * math.sin(x * 0.09) + 2 * math.sin(x * 0.23 + 2)
    d.line((x, GROUND - int(h), x, GROUND), fill=P["haze2"])
for _ in range(26):
    x = rng.randint(0, W)
    w, h = rng.randint(4, 14), rng.randint(3, 9)
    d.ellipse((x - w, GROUND - h, x + w, GROUND + 2), fill=rng.choice((P["haze0"], P["haze1"])))
for x in (36, 104, 152, 258, 300):  # little far-off trees
    d.line((x, GROUND - 4, x, GROUND - 12), fill=P["haze1"])
    d.ellipse((x - 5, GROUND - 17, x + 5, GROUND - 10), fill=P["haze0"])

# Ground strip
d.rectangle((0, GROUND, W, H), fill=P["dirt0"])
d.line((0, GROUND, W, GROUND), fill=P["dirt1"])
for _ in range(500):
    x, y = rng.randrange(W), rng.randint(GROUND + 1, H - 1)
    px[x, y] = rng.choice((P["dirt1"], P["dirt2"], P["dirt2"]))

# Trees: slender dark trunks that fork into a fan of upswept limbs
TREES = [(6, 150), (21, 158), (86, 160), (123, 150), (210, 156), (229, 146), (294, 158)]
twig_tips = []
for tx, fork in TREES:
    lean = rng.uniform(-3, 3)
    top = (tx + lean, fork)
    limb((tx, GROUND + 1), (tx, (GROUND + fork) / 2), top, 5, 4, P["bark0"], P["bark2"])
    d.polygon([(tx - 4, GROUND + 1), (tx + 4, GROUND + 1), (tx + 2, GROUND - 5), (tx - 2, GROUND - 5)], fill=P["bark0"])
    for ang in rng.sample((-50, -28, -8, 14, 34, 52), 4):
        ang += rng.uniform(-6, 6)
        a = math.radians(ang)
        length = rng.uniform(50, 66)
        end = (top[0] + math.sin(a) * length, top[1] - math.cos(a) * length)
        mid = (top[0] + math.sin(a) * length * 0.3, top[1] - length * 0.55)
        limb(top, mid, end, 3, 1, P["bark1"], P["bark2"])
        twig_tips.append(end)
        # one side twig off each limb
        for _ in range(1):
            s = rng.uniform(0.45, 0.8)
            bx = top[0] + (end[0] - top[0]) * s
            by = top[1] + (end[1] - top[1]) * s
            a2 = a + rng.choice((-1, 1)) * rng.uniform(0.3, 0.7)
            l2 = rng.uniform(10, 20)
            limb((bx, by), (bx + math.sin(a2) * l2 * 0.5, by - l2 * 0.6),
                 (bx + math.sin(a2) * l2, by - math.cos(a2) * l2), 1, 1, P["bark1"])


def canopy_bottom(x):
    return 116 + 7 * math.sin(x * 0.045 + 0.6) + 4 * math.sin(x * 0.12 + 2) + 3 * math.sin(x * 0.31)


def canopy_top(x):
    return 4 + 9 * math.sin(x * 0.035 + 1.3) + 5 * math.sin(x * 0.11)


def blossom_clump(cx, cy, rx, ry):
    """One tuft of flowers: dark underside, red body, sunlit crown, scalloped edge."""
    d.ellipse((cx - rx, cy - ry + 2, cx + rx, cy + ry + 2), fill=P["red0"])
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=P["red1"])
    for k in range(7):  # ragged petal outline
        a = k / 7 * math.tau + rng.uniform(0, 0.6)
        ex, ey = cx + math.cos(a) * rx, cy + math.sin(a) * ry
        r = rng.uniform(2, 4)
        d.ellipse((ex - r, ey - r, ex + r, ey + r), fill=P["red1"] if math.sin(a) > 0 else P["red2"])
    d.ellipse((cx - rx * 0.8, cy - ry * 0.9, cx + rx * 0.6, cy + ry * 0.4), fill=P["red2"])
    d.ellipse((cx - rx * 0.6, cy - ry * 0.85, cx + rx * 0.3, cy - ry * 0.05), fill=P["red3"])
    for _ in range(int(rx * ry / 10)):  # individual blossoms catching the light
        sx = int(cx + rng.uniform(-rx * 0.7, rx * 0.5))
        sy = int(cy + rng.uniform(-ry * 0.9, ry * 0.2))
        if 0 <= sx < W and 0 <= sy < H:
            px[sx, sy] = rng.choice((P["red4"], P["red4"], P["red5"], P["red3"]))


# Fill the ceiling of blossom; lower clumps drawn last so they sit in front
clumps = []
for row, gy in enumerate(range(-6, 140, 11)):
    for gx in range(-14, W + 16, 17):
        x = gx + rng.uniform(-5, 5) + (row % 2) * 8
        y = gy + rng.uniform(-3, 3)
        if canopy_top(x) + 4 <= y <= canopy_bottom(x) - 8:
            clumps.append((x, y, rng.uniform(13, 20), rng.uniform(8, 11)))
for tx, ty in twig_tips:  # tufts at the ends of the limbs so branches feed into blossom
    if ty < canopy_bottom(tx) + 6:
        clumps.append((tx, ty - 3, rng.uniform(8, 12), rng.uniform(5, 7)))
for c in sorted(clumps, key=lambda c: c[1]):
    blossom_clump(*c)

# Break up the clump shapes with petal-sized flecks so it reads as blossom, not bubbles
reds = {P["red1"], P["red2"], P["red3"]}
for y in range(H):
    for x in range(W):
        if px[x, y] in reds and rng.random() < 0.12:
            px[x, y] = rng.choice((P["red0"], P["red1"], P["red3"], P["red4"]))



def villager(x, base):
    """Original sprite: a hunter walking left, spear forward, hide shield on his back."""
    k, k1 = P["skin0"], P["skin1"]
    d.ellipse((x + 4, base - 42, x + 17, base - 12), fill=P["hide1"])          # shield
    d.ellipse((x + 5, base - 41, x + 15, base - 14), fill=P["hide0"])
    d.line((x + 10, base - 39, x + 10, base - 16), fill=P["hide1"])
    d.line((x + 1, base - 22, x + 7, base - 1), fill=k, width=3)              # back leg
    d.line((x + 7, base - 1, x + 10, base - 1), fill=k)
    d.line((x - 1, base - 22, x - 8, base - 2), fill=k, width=3)              # front leg
    d.line((x - 8, base - 1, x - 11, base - 1), fill=k)
    d.polygon([(x - 4, base - 38), (x + 4, base - 38), (x + 3, base - 22), (x - 3, base - 22)], fill=k)
    d.line((x - 4, base - 37, x - 3, base - 24), fill=k1)                     # rim light
    d.rectangle((x - 4, base - 24, x + 4, base - 19), fill=P["cloth"])        # loincloth
    d.polygon([(x - 2, base - 19), (x + 2, base - 19), (x - 1, base - 14)], fill=P["cloth"])
    d.ellipse((x - 4, base - 47, x + 3, base - 39), fill=k)                   # head
    px[x - 4, base - 43] = k1
    d.line((x - 2, base - 36, x - 9, base - 29), fill=k, width=2)             # arm
    d.line((x - 34, base - 31, x + 9, base - 26), fill=P["spear"])            # spear
    d.polygon([(x - 38, base - 31), (x - 33, base - 33), (x - 32, base - 30)], fill=P["haze2"])
    d.line((x - 7, base, x + 9, base), fill=P["dirt2"])                       # shadow


villager(74, GROUND + 6)

# Snap every pixel to the palette so the frame stays strictly 16-bit-ish
pal = list(P.values())
palset = set(pal)
for y in range(H):
    for x in range(W):
        c = px[x, y]
        if c not in palset:
            px[x, y] = min(pal, key=lambda q: sum((a - b) ** 2 for a, b in zip(q, c)))

out = img.resize((W * SCALE, H * SCALE), Image.NEAREST)
out.save(__file__.replace(".py", ".png"))
