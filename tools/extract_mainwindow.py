"""Extract the left-panel / menu strings from the generated Qt file.

These live in app/ui/core/main_window.py as
    QCoreApplication.translate("MainWindow", u"Text", None)
and were never covered by the layout_data work, which is why the left panel and
menus stayed English.
"""
import json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import MAIN_WINDOW as SRC
PAT = re.compile(r'QCoreApplication\.translate\(\s*"MainWindow"\s*,\s*u"((?:[^"\\]|\\.)*)"')

text = SRC.read_text(encoding="utf-8")
found = [m.group(1) for m in PAT.finditer(text)]

out_path = Path(sys.argv[1])
rows = []
if out_path.is_file():
    rows = json.loads(out_path.read_text(encoding="utf-8"))
known = {r["en"] for r in rows}

added = 0
for s in found:
    if not s.strip() or s in known:
        continue
    rows.append({"kind": "ui", "en": s, "zh": "", "sites": ["main_window.py"]})
    known.add(s)
    added += 1

out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"occurrences {len(found)}, unique added {added}, total rows {len(rows)}")
print(f"untranslated {sum(1 for r in rows if not r['zh'])}")
