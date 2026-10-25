"""Render a 16-bit style screen of 'La route des flamboyants' (fan-art homage).

Draws at 320x224 (SNES/Genesis resolution) with a fixed palette and
ordered dithering, then upscales 4x with nearest-neighbour.
"""
import math
import random

from PIL import Image, ImageDraw, ImageFont

W, H = 320, 224
SCALE = 4
HORIZON = 112
VP = (160, HORIZON)
rng = random.Random(7)

P = {
    "sky0": (40, 48, 120), "sky1": (88, 80, 168), "sky2": (176, 104, 160),
    "sky3": (240, 136, 112), "sky4": (248, 184, 104), "sky5": (252, 224, 152),
    "sun": (255, 244, 200),
    "hill_far": (152, 96, 120), "hill_near": (112, 80, 88),
    "grass0": (216, 176, 80), "grass1": (184, 144, 56), "grass2": (144, 112, 40),
    "grass3": (96, 80, 32),
    "road0": (200, 96, 56), "road1": (176, 80, 48), "road2": (136, 56, 40),
    "road3": (224, 128, 80),
    "trunk0": (96, 56, 40), "trunk1": (64, 36, 32), "trunk2": (136, 88, 56),
    "fl0": (248, 72, 40), "fl1": (216, 40, 32), "fl2": (152, 24, 32),
    "fl3": (255, 152, 64), "leaf0": (56, 120, 48), "leaf1": (32, 80, 40),
    "thatch0": (200, 160, 88), "thatch1": (152, 112, 56), "mud": (168, 104, 64),
    "mud1": (120, 72, 48), "black": (16, 12, 16), "white": (248, 240, 224),
    "skin": (72, 40, 32),
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


# Sky and sun
dither_band(0, HORIZON, [P["sky0"], P["sky1"], P["sky2"], P["sky3"], P["sky4"], P["sky5"]])
d.ellipse((196, 58, 244, 106), fill=P["sun"])
for y in (70, 80, 88, 94, 99):  # retro sun stripes
    d.line((190, y, 250, y), fill=P["sky4"] if y > 85 else P["sky3"])
# Pixel clouds
for cx, cy, w in ((40, 30, 46), (120, 18, 30), (270, 40, 38), (90, 60, 26)):
    for k in range(4):
        d.ellipse((cx + k * w // 5, cy - 4 + (k % 2) * 2, cx + k * w // 5 + w // 2, cy + 4), fill=P["sky2"] if cy < 40 else P["sky4"])
    d.line((cx + 2, cy + 4, cx + w, cy + 4), fill=P["sky1"] if cy < 40 else P["sky3"])

# Distant hills
for x in range(W):
    h1 = 10 + 5 * math.sin(x * 0.03) + 3 * math.sin(x * 0.11 + 1)
    d.line((x, HORIZON - int(h1), x, HORIZON), fill=P["hill_far"])
for x in range(W):
    h2 = 4 + 3 * math.sin(x * 0.05 + 2) + 2 * math.sin(x * 0.17)
    d.line((x, HORIZON - int(h2), x, HORIZON), fill=P["hill_near"])


def baobab(x, base, s, col):
    d.rectangle((x - 2 * s, base - 9 * s, x + 2 * s, base), fill=col)
    for dx, dy in ((-5, -12), (-2, -14), (2, -13), (5, -11)):
        d.line((x, base - 8 * s, x + dx * s, base + dy * s), fill=col, width=max(1, s))
        d.line((x + dx * s, base + dy * s, x + dx * s + s, base + dy * s - 2 * s), fill=col)


baobab(34, HORIZON - 4, 1, P["hill_near"])
baobab(282, HORIZON - 2, 1, P["hill_near"])

# Savanna ground
dither_band(HORIZON, H, [P["grass1"], P["grass0"], P["grass1"], P["grass2"]])
for _ in range(900):  # grass tufts, denser/larger near the bottom
    y = rng.randint(HORIZON + 2, H - 1)
    x = rng.randint(0, W - 1)
    tall = 1 + (y - HORIZON) // 30
    c = rng.choice((P["grass2"], P["grass3"], P["grass0"]))
    d.line((x, y, x + rng.choice((-1, 0, 1)), y - tall), fill=c)

# Road in perspective
road_half_bottom = 92
for y in range(HORIZON, H):
    t = (y - HORIZON) / (H - HORIZON)
    hw = 2 + t * road_half_bottom
    x0, x1 = int(VP[0] - hw), int(VP[0] + hw)
    z = 1 / max(t, 0.02)
    band = int(z * 3) % 2  # stripes that compress toward the horizon
    for x in range(max(0, x0), min(W, x1 + 1)):
        edge = x - x0 < 1 + t * 4 or x1 - x < 1 + t * 4
        if edge:
            c = P["road2"]
        else:
            u = (x - VP[0]) / hw
            rut = abs(abs(u) - 0.45) < 0.06
            c = P["road2"] if rut else (P["road1"] if band else P["road0"])
            if not rut and BAYER[y % 4][x % 4] > 13 and t > 0.3:
                c = P["road3"]
        px[x, y] = c


def project(side, z):
    """Screen position and scale of a roadside point at depth z (1 = bottom)."""
    t = 1 / z
    y = HORIZON + t * (H - HORIZON)
    hw = 2 + t * road_half_bottom
    x = VP[0] + side * (hw + 14 * t + 6)
    return x, y, t


def hut(x, base, s):
    w, h = int(10 * s), int(8 * s)
    d.rectangle((x - w // 2, base - h, x + w // 2, base), fill=P["mud"])
    d.rectangle((x - w // 2, base - h, x - w // 2 + max(1, w // 5), base), fill=P["mud1"])
    d.rectangle((x - max(1, w // 8), base - h // 2, x + max(1, w // 8), base), fill=P["black"])
    d.polygon([(x - w // 2 - 3 * s, base - h + 1), (x, base - h - 9 * s), (x + w // 2 + 3 * s, base - h + 1)], fill=P["thatch0"])
    d.line((x, base - h - 9 * s, x + w // 2 + 3 * s, base - h + 1), fill=P["thatch1"])
    for k in range(1, 4):
        yy = base - h - 9 * s + k * (9 * s) // 4
        d.line((x - k * w // 6, yy, x + k * w // 6, yy), fill=P["thatch1"])


hut(250, 128, 1)
hut(270, 131, 1.3)
hut(58, 130, 1.2)


def flamboyant(x, base, s):
    """Delonix regia: short trunk, forked limbs, a wide flat umbrella of red blossom."""
    th = 22 * s
    tw = max(1, int(3 * s))
    d.rectangle((x - tw // 2, base - th, x + tw // 2, base), fill=P["trunk0"])
    d.line((x + tw // 2, base - th, x + tw // 2, base), fill=P["trunk1"])
    d.line((x - tw // 2, base - th, x - tw // 2, base), fill=P["trunk2"])
    top = base - th
    limbs = [(-22, -12), (-10, -18), (4, -19), (18, -13), (26, -8)]
    for lx, ly in limbs:
        d.line((x, top + 2 * s, x + lx * s, top + ly * s), fill=P["trunk0"], width=max(1, int(2 * s)))
    cw, ch = 40 * s, 14 * s
    cy = top - 14 * s
    # canopy: layered blobs (shadow -> body -> highlight), leaves peeking through
    blobs = [(rng.uniform(-1, 1), rng.uniform(-0.6, 0.5)) for _ in range(int(26 + 30 * s))]
    for layer, col, off, r in (("shadow", P["fl2"], 2, 1.0), ("leaf", P["leaf1"], 1, 0.7),
                               ("body", P["fl1"], 0, 0.9), ("main", P["fl0"], -1, 0.75),
                               ("hi", P["fl3"], -2, 0.35)):
        for i, (bx, by) in enumerate(blobs):
            if layer == "leaf" and i % 3:
                continue
            if layer == "hi" and (by > 0 or i % 2):
                continue
            rad = max(1, int((5 + (i * 7) % 4) * s * r))
            cx = x + bx * (cw - rad)
            cyy = cy + by * ch + off * s
            d.ellipse((cx - rad * 1.4, cyy - rad, cx + rad * 1.4, cyy + rad), fill=col)
    # scattered blossom speckles
    for _ in range(int(60 * s)):
        sx = x + rng.uniform(-cw, cw)
        sy = cy + rng.uniform(-ch * 0.8, ch * 0.8)
        if px[int(max(0, min(W - 1, sx))), int(max(0, min(H - 1, sy)))] in (P["fl0"], P["fl1"]):
            px[int(sx), int(sy)] = rng.choice((P["fl3"], P["fl2"], P["leaf0"]))
    # fallen petals underneath
    for _ in range(int(40 * s)):
        fx = int(x + rng.uniform(-cw, cw))
        fy = int(base + rng.uniform(-2 * s, 6 * s))
        if 0 <= fx < W and 0 <= fy < H:
            px[fx, fy] = rng.choice((P["fl0"], P["fl1"]))


# Avenue of trees, far to near so near trees overlap far ones
trees = []
for z in (9.0, 6.0, 4.2, 3.0, 2.2, 1.6, 1.15):
    for side in (-1, 1):
        trees.append((z * (1.08 if side > 0 else 1.0), side))
for z, side in sorted(trees, reverse=True):
    x, y, t = project(side, z)
    flamboyant(x, y, t * 1.25)

# Petals drifting on the road
for _ in range(220):
    t = rng.random() ** 0.6
    y = int(HORIZON + 3 + t * (H - HORIZON - 4))
    hw = 2 + t * road_half_bottom
    x = int(VP[0] + rng.uniform(-hw, hw))
    px[x, y] = rng.choice((P["fl0"], P["fl1"], P["fl3"]))
    if t > 0.6 and x + 1 < W:
        px[x + 1, y] = P["fl1"]


def little_hero(x, base):
    """Tiny original sprite of a small village boy running down the road."""
    sprite = [
        "...KKK...",
        "..KKKKK..",
        "..KKWKK..",
        "..KKKKK..",
        "...KKK...",
        ".K.KKK.K.",
        "K..KKK..K",
        "...KKK...",
        "...SSS...",
        "...K.K...",
        "..K...K..",
        ".K.....K.",
    ]
    cmap = {"K": P["skin"], "W": P["white"], "S": P["black"]}
    for j, row in enumerate(sprite):
        for i, ch in enumerate(row):
            if ch in cmap:
                px[x + i, base - len(sprite) + j] = cmap[ch]
    d.line((x + 1, base + 1, x + 7, base + 1), fill=P["road2"])  # shadow


little_hero(150, 196)

# Stage title card, Super Famicom style
font = ImageFont.load_default()
title = "LA ROUTE DES FLAMBOYANTS"
tw = d.textlength(title, font=font)
bx0, bx1 = int(160 - tw / 2 - 10), int(160 + tw / 2 + 10)
d.rectangle((bx0, 6, bx1, 22), fill=P["black"])
d.rectangle((bx0 + 1, 7, bx1 - 1, 21), outline=P["fl3"])
d.text((160 - tw / 2 + 1, 9), title, font=font, fill=P["fl2"])
d.text((160 - tw / 2, 8), title, font=font, fill=P["sky5"])
d.text((8, H - 14), "STAGE 2", font=font, fill=P["black"])
d.text((7, H - 15), "STAGE 2", font=font, fill=P["white"])

# Snap every pixel to the palette so the frame stays strictly 16-bit-ish
pal = list(P.values())
for y in range(H):
    for x in range(W):
        c = px[x, y]
        if c not in P.values():
            px[x, y] = min(pal, key=lambda q: sum((a - b) ** 2 for a, b in zip(q, c)))

out = img.resize((W * SCALE, H * SCALE), Image.NEAREST)
out.save(__file__.replace(".py", ".png"))
print("colors:", len(set(img.getdata())))
