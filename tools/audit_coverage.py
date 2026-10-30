"""Authoritative coverage audit using ast (handles BOTH quote styles and
implicit concatenation), instead of the regex that silently skipped
single-quoted values and produced a false '0 left in English'.
"""
import ast, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import WIDGETS
FILES = [
    ("swapper_layout_data", "SWAPPER_LAYOUT_DATA"),
    ("common_layout_data", "COMMON_LAYOUT_DATA"),
    ("settings_layout_data", "SETTINGS_LAYOUT_DATA"),
    ("face_editor_layout_data", "FACE_EDITOR_LAYOUT_DATA"),
    ("denoiser_layout_data", "DENOISER_LAYOUT_DATA"),
]


def has_cjk(s):
    return any("一" <= c <= "鿿" for c in s)


def walk(mod, var, use_orig):
    name = mod + (".py.orig" if use_orig else ".py")
    src = WIDGETS / name
    if not src.is_file():
        src = WIDGETS / (mod + ".py")
    tree = ast.parse(src.read_text(encoding="utf-8"))
    node = None
    for n in ast.walk(tree):
        tg = n.targets if isinstance(n, ast.Assign) else (
            [n.target] if isinstance(n, ast.AnnAssign) else [])
        for t in tg:
            if isinstance(t, ast.Name) and t.id == var and isinstance(n.value, ast.Dict):
                node = n.value
    out = []
    if node is None:
        return out
    for gk, gv in zip(node.keys, node.values):
        if not isinstance(gv, ast.Dict):
            continue
        for wk, wv in zip(gv.keys, gv.values):
            if not isinstance(wv, ast.Dict):
                continue
            wname = wk.value if isinstance(wk, ast.Constant) else "?"
            spec = {}
            for sk, sv in zip(wv.keys, wv.values):
                key = sk.value if isinstance(sk, ast.Constant) else None
                if key in ("label", "help"):
                    try:
                        spec[key] = ast.literal_eval(sv)
                    except Exception:
                        spec[key] = None
            out.append((wname, spec))
    return out


mode = sys.argv[1] if len(sys.argv) > 1 else "live"
use_orig = mode == "orig"

tot = {"label": 0, "help": 0}
zh = {"label": 0, "help": 0}
bad = []
for mod, var in FILES:
    for wname, spec in walk(mod, var, use_orig):
        for kind in ("label", "help"):
            v = spec.get(kind)
            if not isinstance(v, str) or not v.strip():
                continue
            tot[kind] += 1
            if has_cjk(v):
                zh[kind] += 1
            else:
                bad.append((mod, wname, kind, v))

print(f"mode: {'pristine .orig' if use_orig else 'live patched files'}")
print(f"label : {zh['label']} / {tot['label']} contain Chinese")
print(f"help  : {zh['help']} / {tot['help']} contain Chinese")
print(f"\nstill English ({len(bad)}):")
for mod, wname, kind, v in bad:
    print(f"  [{kind:5}] {mod}::{wname}")
    print(f"          {v[:110]}")
