"""Post-patch verification: every file we touch must still parse, and report
how much of the UI is actually Chinese right now.

Exists because a hand-rolled escape once shipped an unterminated string literal,
and because a regex-based coverage count reported "0 left in English" while 24
strings were still English (single-quoted values and values with inner quotes
were invisible to it). ast sees all of them.
"""
import ast, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import REPO

LAYOUT = [
    ("app/ui/widgets/swapper_layout_data.py", "SWAPPER_LAYOUT_DATA"),
    ("app/ui/widgets/common_layout_data.py", "COMMON_LAYOUT_DATA"),
    ("app/ui/widgets/settings_layout_data.py", "SETTINGS_LAYOUT_DATA"),
    ("app/ui/widgets/face_editor_layout_data.py", "FACE_EDITOR_LAYOUT_DATA"),
    ("app/ui/widgets/denoiser_layout_data.py", "DENOISER_LAYOUT_DATA"),
]
OTHERS = [
    "app/ui/core/main_window.py",
    "app/ui/main_ui.py",
    "app/ui/widgets/actions/layout_actions.py",
]
TRANSLATE = re.compile(
    r'QCoreApplication\.translate\(\s*"MainWindow"\s*,\s*u"((?:[^"\\]|\\.)*)"'
)


def cjk(s):
    return any("一" <= c <= "鿿" for c in s)


def root_of(tree, var):
    found = None
    for n in ast.walk(tree):
        tg = n.targets if isinstance(n, ast.Assign) else (
            [n.target] if isinstance(n, ast.AnnAssign) else [])
        for t in tg:
            if isinstance(t, ast.Name) and t.id == var and isinstance(n.value, ast.Dict):
                found = n.value
    return found


bad_syntax = []
print("=== 语法校验 ===")
for rel, _ in LAYOUT:
    for path in (rel,):
        p = REPO / path
        try:
            ast.parse(p.read_text(encoding="utf-8"))
            print(f"  OK   {path}")
        except SyntaxError as e:
            print(f"  FAIL {path}  line {e.lineno}: {e.msg}")
            bad_syntax.append(path)
for rel in OTHERS:
    p = REPO / rel
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        print(f"  OK   {rel}")
    except SyntaxError as e:
        print(f"  FAIL {rel}  line {e.lineno}: {e.msg}")
        bad_syntax.append(rel)

print("\n=== 汉化覆盖率 ===")
tot = zh = 0
for rel, var in LAYOUT:
    p = REPO / rel
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError:
        continue
    r = root_of(tree, var)
    if r is None:
        continue
    n = c = 0
    for gk, gv in zip(r.keys, r.values):
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
                n += 1
                if cjk(val):
                    c += 1
    tot += n
    zh += c
    print(f"  {Path(rel).name:30} {c:4}/{n:4}")

mw = (REPO / "app/ui/core/main_window.py").read_text(encoding="utf-8")
hits = [m.group(1) for m in TRANSLATE.finditer(mw)]
mzh = sum(1 for h in hits if cjk(h))
print(f"  {'main_window.py':30} {mzh:4}/{len(hits):4}")

pct = 0 if (tot + len(hits)) == 0 else (zh + mzh) * 100.0 / (tot + len(hits))
print(f"\n  合计 {zh + mzh} / {tot + len(hits)}  ({pct:.1f}%)")

if bad_syntax:
    print("\n*** 有文件语法错误, 请运行 汉化-还原英文.bat ***")
    sys.exit(1)
print("\n全部文件语法正常。")
