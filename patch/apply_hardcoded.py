"""Patch hardcoded user-facing strings in main_ui.py / layout_actions.py.

Uses ast to locate exact source spans, then splices on UTF-8 BYTES because
ast's col_offset is a byte offset (treating it as a character index corrupts
files that contain multi-byte characters).

Only rewrites string constants whose value has a translation, so surrounding
generated/hand-written logic is untouched. Refuses to write a file that will not
parse afterwards.

Usage:
  python apply_hardcoded.py ui_strings.json apply|revert|status
"""
import ast, json, shutil, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import REPO
TARGETS = [
    Path("app/ui/main_ui.py"),
    Path("app/ui/widgets/actions/layout_actions.py"),
]

CALL_FIRSTARG = {
    "QAction", "QPushButton", "QLabel", "QCheckBox", "QGroupBox",
    "QRadioButton", "QToolButton", "QMenu",
}
METHODS = {
    "setText", "setToolTip", "setTitle", "setPlaceholderText",
    "setWindowTitle", "setStatusTip", "addItem", "setItemText",
}

rows = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
action = sys.argv[2] if len(sys.argv) > 2 else "status"
table = {r["en"]: r["zh"] for r in rows if r.get("zh") and r["zh"] != r["en"]}


def has_cjk(s):
    return any("一" <= c <= "鿿" for c in s)


def spans(src_text):
    """(start_byte, end_byte, value) for every translatable string constant."""
    tree = ast.parse(src_text)
    blines = src_text.encode("utf-8").splitlines(keepends=True)
    starts = [0]
    for ln in blines:
        starts.append(starts[-1] + len(ln))

    def off(lineno, col):
        return starts[lineno - 1] + col

    found = []
    seen = set()

    def take(node):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            return
        key = (node.lineno, node.col_offset)
        if key in seen:
            return
        if node.value not in table:
            return
        seen.add(key)
        found.append((
            off(node.lineno, node.col_offset),
            off(node.end_lineno, node.end_col_offset),
            node.value,
        ))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else (
                fn.id if isinstance(fn, ast.Name) else None)
            if name and (name in METHODS or name in CALL_FIRSTARG) and node.args:
                take(node.args[0])
        elif isinstance(node, ast.Dict):
            for v in node.values:
                take(v)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for v in node.elts:
                take(v)
    return found


def do_status():
    print(f"translations : {len(table)}")
    for rel in TARGETS:
        live = REPO / rel
        orig = live.with_suffix(".py.orig")
        text = live.read_text(encoding="utf-8")
        n_zh = sum(1 for _, _, v in spans(text) if has_cjk(v))
        # count how many translatable sites exist in the pristine file
        base = orig.read_text(encoding="utf-8") if orig.is_file() else text
        n_all = len(spans(base))
        print(f"  {rel.name:22} {n_zh:3} translated of {n_all:3} sites   "
              f"backup={'yes' if orig.is_file() else 'NO'}")


def do_revert():
    for rel in TARGETS:
        live = REPO / rel
        orig = live.with_suffix(".py.orig")
        if orig.is_file():
            shutil.copy2(orig, live)
            print(f"  restored {rel.name}")
        else:
            print(f"  no backup for {rel.name}")


def do_apply():
    for rel in TARGETS:
        live = REPO / rel
        orig = live.with_suffix(".py.orig")
        if not orig.is_file():
            shutil.copy2(live, orig)
        text = orig.read_text(encoding="utf-8")

        items = spans(text)
        buf = text.encode("utf-8")
        hit = 0
        for start, end, val in sorted(items, key=lambda x: -x[0]):
            zh = table.get(val)
            if not zh:
                continue
            buf = buf[:start] + json.dumps(zh, ensure_ascii=False).encode("utf-8") + buf[end:]
            hit += 1

        out = buf.decode("utf-8")
        try:
            ast.parse(out)
        except SyntaxError as e:
            print(f"  {rel.name:22} ABORTED, would not parse: line {e.lineno}: {e.msg}")
            continue
        live.write_text(out, encoding="utf-8")
        print(f"  {rel.name:22} translated {hit}")


{"apply": do_apply, "revert": do_revert, "status": do_status}.get(action, do_status)()
