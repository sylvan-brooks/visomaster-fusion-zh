"""AST-driven patcher: replaces label/help values regardless of quote style,
inner quotes, or escapes.

The earlier regex patcher could not see single-quoted values, and its [^"\\]
character class truncated at the first inner quote -- both produced a false
"0 left in English". ast gives exact source offsets, so replacement is precise.

Always rebuilds from the pristine .orig snapshot -> idempotent.

Usage:
  python apply_ast.py strings.json apply
  python apply_ast.py strings.json revert
  python apply_ast.py strings.json status
"""
import ast, json, shutil, sys
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

strings_path = Path(sys.argv[1])
action = sys.argv[2] if len(sys.argv) > 2 else "status"
rows = json.loads(strings_path.read_text(encoding="utf-8"))

# key on the logical (unescaped) string, which is what ast.literal_eval yields
table = {}
for r in rows:
    if not r.get("zh"):
        continue
    table[(r["kind"], r["en"])] = r["zh"]
    try:
        table.setdefault((r["kind"], json.loads('"' + r["en"] + '"')), r["zh"])
    except Exception:
        pass


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


def collect(src_text, var):
    """Yield (start, end, kind, value) as BYTE offsets into UTF-8 source.

    ast's col_offset is a UTF-8 BYTE offset, not a character index. These files
    contain multi-byte chars (e.g. the arrows in "Test -> CDF Histogram"), so
    treating col_offset as a character index shifted every later replacement on
    those lines and spliced into the next dict key.
    """
    tree = ast.parse(src_text)
    root = find_root(tree, var)
    if root is None:
        return []
    # byte-oriented line table to match col_offset semantics
    blines = src_text.encode("utf-8").splitlines(keepends=True)
    starts = [0]
    for ln in blines:
        starts.append(starts[-1] + len(ln))

    def off(lineno, col):
        return starts[lineno - 1] + col

    out = []
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
                out.append((
                    off(sv.lineno, sv.col_offset),
                    off(sv.end_lineno, sv.end_col_offset),
                    kind, val,
                ))
    return out


def do_status():
    print(f"translations available : {len(rows)}")
    for mod, var in FILES:
        live = WIDGETS / (mod + ".py")
        orig = WIDGETS / (mod + ".py.orig")
        items = collect(live.read_text(encoding="utf-8"), var)
        zh = sum(1 for _, _, _, v in items if has_cjk(v))
        print(f"  {mod:28} {zh:4}/{len(items):4} Chinese   backup="
              f"{'yes' if orig.is_file() else 'NO'}")


def do_revert():
    for mod, _ in FILES:
        live = WIDGETS / (mod + ".py")
        orig = WIDGETS / (mod + ".py.orig")
        if orig.is_file():
            shutil.copy2(orig, live)
            print(f"  restored {mod}.py")
        else:
            print(f"  no backup for {mod}.py")


def do_apply():
    total_hit = total_miss = 0
    for mod, var in FILES:
        live = WIDGETS / (mod + ".py")
        orig = WIDGETS / (mod + ".py.orig")
        if not orig.is_file():
            shutil.copy2(live, orig)
        text = orig.read_text(encoding="utf-8")
        items = collect(text, var)

        # splice on bytes, since collect() returns byte offsets
        buf = text.encode("utf-8")
        hit = miss = 0
        # back-to-front so earlier offsets stay valid as we mutate
        for start, end, kind, val in sorted(items, key=lambda x: -x[0]):
            zh = table.get((kind, val))
            if not zh:
                miss += 1
                continue
            lit = json.dumps(zh, ensure_ascii=False).encode("utf-8")
            buf = buf[:start] + lit + buf[end:]
            hit += 1

        out = buf.decode("utf-8")
        # never ship a file that does not parse
        try:
            ast.parse(out)
        except SyntaxError as e:
            print(f"  {mod:28} ABORTED, would not parse: line {e.lineno}: {e.msg}")
            continue
        live.write_text(out, encoding="utf-8")
        print(f"  {mod:28} translated {hit:4}  untranslated {miss:4}")
        total_hit += hit
        total_miss += miss
    print(f"applied: {total_hit} translated, {total_miss} left in English")


{"apply": do_apply, "revert": do_revert, "status": do_status}.get(action, do_status)()
