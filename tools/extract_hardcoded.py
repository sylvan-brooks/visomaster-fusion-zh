"""Extract hardcoded user-facing strings from main_ui.py / layout_actions.py.

These menus are built at runtime with QAction("...") / .setText("...") and never
pass through QCoreApplication.translate, which is why the File/Edit/View/Help
menus stayed partly English even after main_window.py was patched. main_ui.py
also OVERRIDES some main_window.py texts via setText, so the visible label
differs from the one in the generated file.

ast is used (not regex) so single quotes, inner quotes and escapes all work.
"""
import ast, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import REPO
TARGETS = [
    Path("app/ui/main_ui.py"),
    Path("app/ui/widgets/actions/layout_actions.py"),
]

# calls whose first string argument is shown to the user
CALL_FIRSTARG = {
    "QAction", "QPushButton", "QLabel", "QCheckBox", "QGroupBox",
    "QRadioButton", "QToolButton", "QMenu",
}
# methods whose single string argument is shown to the user
METHODS = {
    "setText", "setToolTip", "setTitle", "setPlaceholderText",
    "setWindowTitle", "setStatusTip", "addItem", "setItemText",
}

SKIP_EXACT = {"", " ", "-", "--", "...", ":", "/"}


def looks_technical(s: str) -> bool:
    if s in SKIP_EXACT:
        return False
    if len(s) < 2:
        return True
    # object names, paths, format strings, css
    if any(ch in s for ch in ("\\", "{", "}", "://")):
        return True
    if s.startswith((".", "#", "_")):
        return True
    if ":" in s and " " not in s:
        return True
    # needs at least one lowercase run to look like prose
    return not any(c.isalpha() for c in s)


def prose_like(s: str) -> bool:
    """Heuristic for 'this is shown to a human'.

    Needed because menu captions also live as dict values
    ({"diff": "Differencing Mask"}) and as tuple members
    (("faces", "facesPanelCheckBox", "Faces / Embeddings")), neither of which is
    a call argument. Requires a capitalised word and a space, or a known caption
    shape, so identifiers like 'facesPanelCheckBox' are rejected.
    """
    if looks_technical(s) or len(s) < 4:
        return False
    if s != s.strip():
        return False
    words = s.split()
    if len(words) < 2:
        return False
    # reject camelCase / snake_case identifiers
    for w in words:
        if "_" in w:
            return False
        if w[:1].islower() and any(c.isupper() for c in w[1:]):
            return False
    # at least one capitalised word, like a caption
    return any(w[:1].isupper() for w in words)


def collect(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []

    for node in ast.walk(tree):
        # 1. call arguments  QAction("..."), .setText("...")
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else (
                fn.id if isinstance(fn, ast.Name) else None)
            if name and (name in METHODS or name in CALL_FIRSTARG) and node.args:
                a0 = node.args[0]
                if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                    if not looks_technical(a0.value):
                        out.append((a0.value, name, a0.lineno))
            continue

        # 2. dict values   {"diff": "Differencing Mask"}
        if isinstance(node, ast.Dict):
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    if prose_like(v.value):
                        out.append((v.value, "dict-value", v.lineno))
            continue

        # 3. tuple members  ("faces", "facesPanelCheckBox", "Faces / Embeddings")
        if isinstance(node, (ast.Tuple, ast.List)):
            for v in node.elts:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    if prose_like(v.value):
                        out.append((v.value, "seq-member", v.lineno))
            continue

    return out


rows = []
p = Path(sys.argv[1])
if p.is_file():
    rows = json.loads(p.read_text(encoding="utf-8"))
known = {r["en"] for r in rows}

added = 0
report = []
for rel in TARGETS:
    src = REPO / rel
    if not src.is_file():
        print(f"MISSING {rel}")
        continue
    items = collect(src)
    report.append((rel.name, len(items)))
    for val, how, lineno in items:
        if val in known:
            continue
        rows.append({
            "kind": "ui",
            "en": val,
            "zh": "",
            "sites": [f"{rel.name}:{lineno} via {how}"],
        })
        known.add(val)
        added += 1

p.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
for name, n in report:
    print(f"  {name:24} {n} candidate strings")
print(f"\nadded {added}, total rows {len(rows)}, untranslated "
      f"{sum(1 for r in rows if not r['zh'])}")
for r in rows:
    if not r["zh"]:
        print(f"  {r['en'][:78]}")
