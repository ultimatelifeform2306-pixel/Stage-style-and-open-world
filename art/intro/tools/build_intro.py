"""Build intro.html (one self-contained file) from intro.src.html and the pictures in art/intro/.
Usage: python3 art/intro/tools/build_intro.py"""
import base64, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
art = os.path.dirname(HERE)
src, out = f"{HERE}/intro.src.html", os.path.join(art, "..", "..", "intro.html")
def uri(name, mime):
    return f"data:{mime};base64," + base64.b64encode(open(f"{art}/{name}", "rb").read()).decode()
s = open(src).read()
geom = json.load(open(f"{art}/sprites.json"))
geom["letters"] = {"cuts": geom["letters"]["cuts"]}
rep = {
    "__CLEAN__": uri("kenos-wide.jpg", "image/jpeg"),
    "__POSTER__": uri("poster.jpg", "image/jpeg"),
    "__T_NEWDANGER__": uri("t-newdanger.png", "image/png"),
    "__T_2025__": uri("t-2025.png", "image/png"),
    "__T_SWIRL__": uri("t-swirl.png", "image/png"),
    "__T_KENOS__": uri("t-kenos.png", "image/png"),
    "__GEOM__": json.dumps(geom),
}
for k, v in rep.items():
    assert k in s, k
    s = s.replace(k, v)
open(out, "w").write(s)
print(len(s) // 1024, "KB")
