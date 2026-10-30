"""AST-based extraction of untranslated label/help values.

Replaces the regex approach, which silently missed:
  1. single-quoted values      'help': '...'
  2. values with inner quotes  "help": "Check \"View Face Mask\" ..."
     (the [^"\\] class stopped at the first inner quote)
Both classes produced a false "0 left in English" report.

ast.literal_eval gives the true logical string regardless of quote style,
escapes, or implicit concatenation.
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


def find_root(tree, var):
    found = None
    for n in ast.walk(tree):
        tg = n.targets if isinstance(n, ast.Assign) else (
            [n.target] if isinstance(n, ast.AnnAssign) else [])
        for t in tg:
            if isinstance(t, ast.Name) and t.id == var and isinstance(n.value, ast.Dict):
                found = n.value
    return found


rows = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
known = {(r["kind"], r["en"]) for r in rows}

added = 0
for mod, var in FILES:
    src = WIDGETS / (mod + ".py.orig")
    if not src.is_file():
        src = WIDGETS / (mod + ".py")
    root = find_root(ast.parse(src.read_text(encoding="utf-8")), var)
    if root is None:
        print(f"{var}: not found")
        continue
    for gk, gv in zip(root.keys, root.values):
        if not isinstance(gv, ast.Dict):
            continue
        for wk, wv in zip(gv.keys, gv.values):
            if not isinstance(wv, ast.Dict):
                continue
            for sk, sv in zip(wv.keys, wv.values):
                kind = sk.value if isinstance(sk, ast.Constant) else None
                if kind not in ("label", "help"):
                    continue
                try:
                    val = ast.literal_eval(sv)
                except Exception:
                    continue
                if not isinstance(val, str) or not val.strip():
                    continue
                if has_cjk(val):
                    continue  # already translated in a prior pass
                if (kind, val) in known:
                    continue
                rows.append({"kind": kind, "en": val, "zh": "", "sites": [mod]})
                known.add((kind, val))
                added += 1

Path(sys.argv[1]).write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                            encoding="utf-8")
todo = [r for r in rows if not r["zh"]]
print(f"added {added} newly-discovered strings")
print(f"total rows {len(rows)}, untranslated {len(todo)}")
for r in todo[:30]:
    print(f"  [{r['kind']:5}] {r['en'][:96]}")
