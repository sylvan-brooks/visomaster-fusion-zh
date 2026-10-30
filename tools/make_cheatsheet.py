"""Generate a Chinese cheat-sheet from the ORIGINAL (English) layout data,
grouped exactly the way the right-hand panel nests them, so the user can scan
top-to-bottom against the real window instead of reading prose.
"""
import ast, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import REPO
WIDGETS = REPO / "app" / "ui" / "widgets"

TABS = [
    ("swapper_layout_data", "SWAPPER_LAYOUT_DATA", "Face Swap 换脸"),
    ("common_layout_data", "COMMON_LAYOUT_DATA", "Common 通用 (修复/增强/检测)"),
    ("denoiser_layout_data", "DENOISER_LAYOUT_DATA", "Denoiser 去噪"),
    ("face_editor_layout_data", "FACE_EDITOR_LAYOUT_DATA", "Face Editor 面部编辑"),
    ("settings_layout_data", "SETTINGS_LAYOUT_DATA", "Settings 设置"),
]

# Group headers MUST stay English in the app: layout_actions.py:70 derives
# section_id via re.sub(r"[^a-z0-9]+", "_", name.lower()), so any Chinese name
# collapses to an empty id and every translated group would share one id,
# breaking the expand/collapse memory. Verified 2026-08-23. So the Chinese for
# group headers lives here in the cheat-sheet instead.
GROUP_ZH = {
    "Swapper": "换脸核心",
    "Swap strength and likeness": "换脸强度与相似度",
    "Masks": "遮罩",
    "Original Face Parsers": "原脸部件保留",
    "Textures and colors": "纹理与颜色",
    "Face Landmarks Correction": "面部关键点校正",
    "Blend Adjustments": "融合调整",
    "Face Re-Aging": "面部年龄调整",
    "Face Restorer": "面部修复",
    "Face expressions": "面部表情",
    "ReF-LDM Denoiser": "ReF-LDM 去噪器",
    "Appearance": "外观",
    "General": "通用",
    "Output Settings": "输出设置",
    "Video Playback Settings": "视频播放设置",
    "Video Recording Settings": "视频录制设置",
    "Swap settings": "换脸设置",
    "Detectors": "人脸检测器",
    "Face Tracking": "人脸追踪",
    "Frame Enhancer": "画面增强",
    "Webcam and Virtualcam Settings": "摄像头与虚拟摄像头",
    "Misc": "杂项",
    "": "面部编辑器",
}

strings = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))


def _unesc(s: str) -> str:
    """strings.json keys hold the RAW escaped source text (regex capture), while
    ast.literal_eval yields the unescaped value. Index both forms so the 2 help
    strings containing \\" / \\n still resolve."""
    try:
        return json.loads('"' + s + '"')
    except Exception:
        return s


def _index(kind):
    d = {}
    for r in strings:
        if r["kind"] != kind or not r["zh"]:
            continue
        d[r["en"]] = r["zh"]
        d.setdefault(_unesc(r["en"]), r["zh"])
    return d


zh_label = _index("label")
zh_help = _index("help")


def _lit(node):
    """Best-effort literal extraction; non-literals (function refs) -> None."""
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def load(mod_name, var):
    """Parse the pristine .orig snapshot with ast.

    Cannot exec these modules: they import control_actions, which is a circular
    import when a layout module is the entry point (reproduced identically on
    unpatched files, so it is upstream structure, not caused by the patch).
    """
    src = WIDGETS / (mod_name + ".py.orig")
    if not src.is_file():
        src = WIDGETS / (mod_name + ".py")
    tree = ast.parse(src.read_text(encoding="utf-8"))

    target = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            names = node.targets
        elif isinstance(node, ast.AnnAssign):
            names = [node.target]
        else:
            continue
        for t in names:
            if isinstance(t, ast.Name) and t.id == var and isinstance(node.value, ast.Dict):
                target = node.value
    if target is None:
        raise ValueError(f"{var} not found in {src.name}")

    out = {}
    for gk, gv in zip(target.keys, target.values):
        gname = gk.value if isinstance(gk, ast.Constant) else "<expr>"
        if not isinstance(gv, ast.Dict):
            continue
        widgets = {}
        for wk, wv in zip(gv.keys, gv.values):
            wname = wk.value if isinstance(wk, ast.Constant) else "<expr>"
            if not isinstance(wv, ast.Dict):
                continue
            spec = {}
            for sk, sv in zip(wv.keys, wv.values):
                key = sk.value if isinstance(sk, ast.Constant) else None
                if key is None:
                    continue
                val = _lit(sv)
                if val is not None:
                    spec[key] = val
            widgets[wname] = spec
        out[gname] = widgets
    return out


def zh_of(en, mapping):
    v = mapping.get(en, "")
    return v or ""


def label_cell(en):
    zh = zh_of(en, zh_label)
    if not zh:
        return f"`{en}`"
    # translations already look like "中文 (English)"
    return zh if "(" in zh else f"{zh} (`{en}`)"


out = ["# VisoMaster Fusion · 中文速查表", "",
       "> 自动生成, 与安装版本的实际控件一一对应. 按右侧面板的嵌套顺序排列.",
       "> 标签格式为 `中文 (English)`, 保留英文以便搜英文教程和 GitHub issue.", ""]

for mod, var, title in TABS:
    try:
        data = load(mod, var)
    except Exception as e:
        out.append(f"## {title}\n\n(读取失败: {type(e).__name__} {e})\n")
        continue

    out.append(f"## {title}")
    out.append("")

    for group, items in data.items():
        if not isinstance(items, dict):
            continue
        gz = GROUP_ZH.get(group, "")
        head = f"{gz} · `{group}`" if gz else f"`{group}`"
        out.append(f"### {head}")
        out.append("")
        out.append("| 控件 | 说明 | 可选值 / 默认 |")
        out.append("|---|---|---|")
        for key, spec in items.items():
            if not isinstance(spec, dict):
                continue
            en_label = spec.get("label", key)
            en_help = spec.get("help", "")
            help_zh = zh_of(en_help, zh_help) or en_help
            help_zh = help_zh.replace("|", "/").replace("\n", " ")
            if len(help_zh) > 160:
                help_zh = help_zh[:157] + "..."

            opts = spec.get("options")
            default = spec.get("default", None)
            bits = []
            if isinstance(opts, list) and opts:
                shown = ", ".join(str(o) for o in opts[:6])
                if len(opts) > 6:
                    shown += f", …({len(opts)})"
                bits.append(shown)
            if default is not None:
                bits.append(f"默认 **{default}**")
            mn, mx = spec.get("min_value"), spec.get("max_value")
            if mn is not None and mx is not None:
                bits.append(f"范围 {mn}–{mx}")
            meta = " · ".join(bits) if bits else "—"

            dep = spec.get("parentSelection")
            name = label_cell(en_label)
            if dep:
                need = spec.get("requiredSelectionValue")
                name += f"<br><sub>仅当 {dep} = {need} 时出现</sub>"

            out.append(f"| {name} | {help_zh} | {meta} |")
        out.append("")

dst = Path(sys.argv[2])
dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text("\n".join(out), encoding="utf-8")
n_tables = sum(1 for l in out if l.startswith("| 控件"))
print(f"wrote {dst}")
print(f"sections {n_tables}, lines {len(out)}")
print(f"label coverage {len(zh_label)} / {sum(1 for r in strings if r['kind']=='label')}")
print(f"help  coverage {len(zh_help)} / {sum(1 for r in strings if r['kind']=='help')}")
