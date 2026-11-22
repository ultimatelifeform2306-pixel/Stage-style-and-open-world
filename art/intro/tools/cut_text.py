"""Cut the poster's text (NEW DANGER, 2025, swirl, KENOS) into transparent pieces and make a
text-free copy of the poster by patching those spots from the square art (kenos.jpg).
Usage: python3 art/intro/tools/cut_text.py  (writes into art/intro/)"""
import sys, json, os
import numpy as np
from scipy import ndimage as nd
from PIL import Image

# aligned + colour-matched copy of the square art (image 1) in poster coordinates
def aligned(wide_path, square_path):
    W=Image.open(wide_path).convert("RGB"); S=Image.open(square_path).convert("RGB")
    s,ox,oy=0.685,202,13
    Ss=S.resize((round(1024*s),round(1040*s)),Image.LANCZOS)
    layer=Image.new("RGB",W.size); layer.paste(Ss,(ox,oy))
    y0,y1,x0,x1=200,620,400,720
    a=np.asarray(W,float)[y0:y1,x0:x1]; b=np.asarray(layer,float)[y0:y1,x0:x1]; L=np.asarray(layer,float)
    for ch in range(3):
        g=a[...,ch].std()/b[...,ch].std(); o=a[...,ch].mean()-g*b[...,ch].mean(); L[...,ch]=L[...,ch]*g+o
    crop=(0,14,1148,730)
    return np.asarray(W,float)[14:730,0:1148], np.clip(L,0,255)[14:730,0:1148]

HERE = os.path.dirname(os.path.abspath(__file__))
outdir = os.path.dirname(HERE)
wide, square = f"{outdir}/poster-original.jpg", f"{outdir}/kenos.jpg"
sp = None
# the poster without the screenshot's black border and rounded corner
Image.open(wide).convert("RGB").crop((0, 14, 1148, 730)).save(f"{outdir}/poster.jpg", quality=95)
P, I = aligned(wide, square)
H, W = P.shape[:2]
D = np.abs(P - I).max(axis=2)

# ---- title area: NEW DANGER, 2025, swirl ----
box = np.zeros((H, W), bool); box[0:170, 345:760] = True; box[95:190, 650:740] = False
T = (D > 45) & box
blob = nd.binary_opening(T, structure=np.ones((7, 7)))
blob = nd.binary_dilation(blob, iterations=4) & T
blob = nd.binary_fill_holes(nd.binary_closing(blob, structure=np.ones((5, 5))))
# letters = everything within a few px of the navy letter colour; other white lines = swirl
near = nd.binary_dilation(blob, iterations=8) & box & (D > 18)
allT = T | near
navyc = (P[..., 2] > P[..., 0] + 35) & (P[..., 2] > 60) & box
navyc = nd.binary_opening(navyc, iterations=1)
letters = nd.binary_dilation(navyc, iterations=5) & allT
letters = nd.binary_fill_holes(nd.binary_closing(letters, structure=np.ones((3, 3))))
Lp = P[..., 0] * .299 + P[..., 1] * .587 + P[..., 2] * .114
swirl = T & ~letters
lab, n = nd.label(swirl)
for i, sl in enumerate(nd.find_objects(lab)):
    comp = lab == i + 1
    if sl[1].start > 640 or comp.sum() < 25 or Lp[comp].mean() < 80: swirl[comp] = False
# leftovers (dark edge bits): join the swirl if they touch it, else the letters
left_ = allT & ~letters & ~swirl
lab, n = nd.label(left_)
sw3 = nd.binary_dilation(swirl, iterations=3)
for i, sl in enumerate(nd.find_objects(lab)):
    comp = lab == i + 1
    if sl[1].start > 640: continue
    if (comp & sw3).any(): swirl |= comp
    else: letters |= comp
blob = letters
CUT = 87
yy = np.arange(H)[:, None]
line1 = blob & (yy < CUT)
line2 = blob & (yy >= CUT)
# NEW DANGER: drop anything more than 2px below the letters' navy shadow (swirl dashes)
nv1 = nd.binary_dilation(navyc & (yy < 85), structure=np.ones((1, 17)))
bottom = np.where(nv1.any(axis=0), H - 1 - np.argmax(nv1[::-1], axis=0), H)
below = (yy > bottom[None, :] + 2) & line1
swirl |= below; line1 &= ~below
line1 = nd.binary_dilation(line1, iterations=3) & (np.arange(H)[:, None] < CUT + 2)
line2 = nd.binary_dilation(line2, iterations=3) & (np.arange(H)[:, None] >= CUT - 2)
swirlK = nd.binary_dilation(swirl, iterations=2) & ~line1 & ~line2

# ---- KENOS + its dark glow ----
nbox = np.zeros((H, W), bool); nbox[580:716, 355:705] = True
NK = nd.binary_dilation((D > 22) & nbox, iterations=4) & nbox
NK = nd.binary_fill_holes(nd.binary_closing(NK, structure=np.ones((7, 7))))

K = line1 | line2 | swirlK | NK
# where the square art actually reaches: placed at (202, 13) in the original, 1 row cut off the top
sh, sw = round(1040 * 0.685), round(1024 * 0.685)
covered = np.zeros((H, W), bool); covered[0:13 + sh - 14 - 2, 202 + 2:202 + sw - 2] = True
last = 13 + sh - 14 - 3
I = I.copy(); I[last + 1:] = I[last][None]   # stretch the art's bottom row over the last few rows
covered[last + 1:, 204:202 + sw - 2] = True
clean = P.copy(); use = K & covered; clean[use] = I[use]
clean[last + 1:, 355:705] = I[last + 1:, 355:705]   # bottom edge under KENOS: no glow band
print("uncovered text px:", int((K & ~covered).sum()))
Image.fromarray(clean.astype(np.uint8)).save(f"{outdir}/kenos-wide.jpg", quality=92)

def lum(a): return a[..., 0] * .299 + a[..., 1] * .587 + a[..., 2] * .114
meta = {}
def sprite(name, mask, alpha=None, color=None):
    ys, xs = np.where(mask)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    a = (mask if alpha is None else alpha)[y0:y1, x0:x1].astype(float)
    c = (P if color is None else color)[y0:y1, x0:x1]
    rgba = np.dstack([c, a * 255]).clip(0, 255).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(f"{outdir}/{name}.png", optimize=True)
    meta[name] = dict(x=int(x0), y=int(y0), w=int(x1 - x0), h=int(y1 - y0))

sprite("t-newdanger", line1)
sprite("t-2025", line2)
sprite("t-swirl", swirlK)
purple = (P[..., 2] > P[..., 0] + 40) & (P[..., 2] > 110) & NK
purple = nd.binary_opening(purple, iterations=1)
core = nd.binary_dilation(purple, iterations=7) & (purple | (lum(P) < 70)) | nd.binary_dilation(purple, iterations=2)
core = nd.binary_fill_holes(core)
glow = nd.gaussian_filter(nd.binary_dilation(core, iterations=6).astype(float), 7) * 0.9
dark_a = np.clip(1 - lum(P) / np.maximum(lum(I), 1), 0, 1) * NK
glow = np.maximum(glow, nd.gaussian_filter(dark_a, 5) * 0.95)
a = np.maximum(core.astype(float), glow)
col = np.where(core[..., None], P, 0)
sprite("t-kenos", a > 0.02, alpha=a, color=col)

# letter cuts for NEW DANGER from the navy fill of each letter
navy = (P[..., 2] > P[..., 0] + 50) & (P[..., 2] > 90) & line1
lab, n = nd.label(nd.binary_opening(navy, iterations=1))
spans = sorted((s[1].start, s[1].stop) for i, s in enumerate(nd.find_objects(lab)) if nd.sum(navy, lab, i + 1) > 80)
merged = []
for s in spans:
    if merged and s[0] < merged[-1][1] - 2: merged[-1] = (merged[-1][0], max(merged[-1][1], s[1]))
    else: merged.append(s)
cuts = [(merged[i][1] + merged[i + 1][0]) // 2 for i in range(len(merged) - 1)]
meta["letters"] = dict(spans=merged, cuts=cuts)
meta["size"] = dict(w=W, h=H)
json.dump(meta, open(f"{outdir}/sprites.json", "w"), indent=1)

# check: composite of sprites over clean must equal the poster
comp = clean.copy()
for name in ["t-newdanger", "t-2025", "t-swirl", "t-kenos"]:
    m = meta[name]; s = np.asarray(Image.open(f"{outdir}/{name}.png"), float)
    al = s[..., 3:] / 255
    reg = comp[m["y"]:m["y"] + m["h"], m["x"]:m["x"] + m["w"]]
    comp[m["y"]:m["y"] + m["h"], m["x"]:m["x"] + m["w"]] = s[..., :3] * al + reg * (1 - al)
err = np.abs(comp - P).max(axis=2)
print("letters", len(merged), merged)
print("rest error: mean", err.mean().round(3), "p99.9", np.percentile(err, 99.9).round(1), "max", err.max().round(1))
print("error >30 px:", int((err > 30).sum()))
