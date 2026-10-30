"""Patch the left-panel / menu strings inside the generated Qt file.

Targets only the literal inside
    QCoreApplication.translate("MainWindow", u"<here>", None)
so surrounding generated code is untouched. Rebuilds from main_window.py.orig
every time -> idempotent, and refuses to write a file that will not parse.

Usage:
  python apply_mainwindow.py ui_strings.json apply
  python apply_mainwindow.py ui_strings.json revert
  python apply_mainwindow.py ui_strings.json status
"""
import ast, json, re, shutil, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import MAIN_WINDOW as SRC
ORIG = SRC.with_suffix(".py.orig")

PAT = re.compile(
    r'(QCoreApplication\.translate\(\s*"MainWindow"\s*,\s*u")((?:[^"\\]|\\.)*)(")'
)

rows = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
action = sys.argv[2] if len(sys.argv) > 2 else "status"
table = {r["en"]: r["zh"] for r in rows if r.get("zh")}


def has_cjk(s):
    return any("一" <= c <= "鿿" for c in s)


def esc(s):
    """Escape for a python double-quoted literal; json's rules match here."""
    return json.dumps(s, ensure_ascii=False)[1:-1]


def do_status():
    text = SRC.read_text(encoding="utf-8")
    hits = [m.group(2) for m in PAT.finditer(text)]
    zh = sum(1 for h in hits if has_cjk(h))
    print(f"main_window.py : {zh}/{len(hits)} Chinese")
    print(f"backup         : {'yes' if ORIG.is_file() else 'NO'}")
    print(f"translations   : {len(table)}")


def do_revert():
    if ORIG.is_file():
        shutil.copy2(ORIG, SRC)
        print("restored main_window.py")
    else:
        print("no backup, nothing to do")


def do_apply():
    if not ORIG.is_file():
        shutil.copy2(SRC, ORIG)
    src = ORIG.read_text(encoding="utf-8")

    hit = miss = 0
    missed = []

    def repl(m):
        nonlocal hit, miss
        head, body, tail = m.group(1), m.group(2), m.group(3)
        zh = table.get(body)
        if not zh or zh == body:
            if body.strip():
                miss += 1
                missed.append(body)
            return m.group(0)
        hit += 1
        return head + esc(zh) + tail

    out = PAT.sub(repl, src)

    try:
        ast.parse(out)
    except SyntaxError as e:
        print(f"ABORTED, would not parse: line {e.lineno}: {e.msg}")
        return

    SRC.write_text(out, encoding="utf-8")
    print(f"translated {hit}, left as-is {miss}")
    for s in missed[:10]:
        print(f"  kept: {s[:70]}")


{"apply": do_apply, "revert": do_revert, "status": do_status}.get(action, do_status)()
