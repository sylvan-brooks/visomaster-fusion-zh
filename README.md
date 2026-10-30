# VisoMaster Fusion 中文界面补丁

给开源换脸软件 [VisoMaster Fusion](https://github.com/VisoMasterFusion/VisoMaster-Fusion) 加中文界面。双击开启，双击还原，不改软件本身的功能。

Chinese UI patch for VisoMaster Fusion. One click to apply, one click to revert.

## 效果

- 参数名双语：`换脸模型 (Swapper Model)`。中文看得懂，英文还能拿去搜教程和 GitHub issue。
- 鼠标悬停的说明是纯中文。这是最有用的部分：每个参数到底管什么，原版只有英文长句。
- 菜单用通用叫法：文件 / 编辑 / 视图 / 帮助。
- 覆盖率：955 处界面文字翻了 951 处（99.6%）。剩下 4 处是窗口标题里的版本号和两个 `Test` 占位符，故意不动。
- 附一份 [中英对照速查表](docs/中英对照速查表.md)，按右侧面板的顺序列出每个参数的中文名、说明和可选值。

在上游 2026-10-04 的 `main` 分支（`f2d6f5e`）上测过：打补丁后所有文件都能正常解析，还原后和上游一字节不差。

## 用法

1. 把整个仓库放进 VisoMaster 便携版的安装文件夹，和 `VisoMaster-Fusion` 文件夹放在同一层：

   ```
   VisoMaster/
   ├── Start_Portable.bat
   ├── VisoMaster-Fusion/
   ├── portable-files/
   └── visomaster-fusion-zh/      ← 这个仓库
   ```

2. 双击 `patch/apply_zh.bat`，再用 `Start_Portable.bat` 启动。
3. 想换回英文，双击 `patch/revert_en.bat`。

不是便携版也行：设环境变量 `VISOMASTER_REPO` 指向 `VisoMaster-Fusion` 文件夹，用自己的 Python 跑 `patch/` 里的脚本。

## 几件要知道的事

- 启动器会提示「Tracked files changed」，那是这个补丁改的，不是出错。
- **别点启动器里的「Repair Installation」**。它会把源码还原成英文，再双击一次 `apply_zh.bat` 就回来了。
- 软件更新以后重新双击一次 `apply_zh.bat`。补丁每次都从原文件的快照重打，重复跑不会翻译两遍。
- 更新后新加的参数还是英文，用 `tools/` 里的脚本提取出来，翻完再打（见下）。

## 怎么做的

这个软件没有多语言框架，界面文字直接写在 Python 源码里，散在四种地方：参数表的字典、Qt Designer 生成的窗口代码、业务代码里的 `setText` / `QAction`，还有藏在字典值和元组里的菜单名。

- 用 Python 自带的 `ast` 解析源码，按语法树找字符串、按字节位置替换，不用正则。正则会漏单引号和带转义引号的字符串，最开始那版就因此漏了 24 条，统计还显示「0 条剩英文」。
- 写盘前先解析一遍生成的代码，解析不过就不写。
- 被当成内部 ID 用的字符串、快捷键、版本号不翻。
- 覆盖率用另一套独立的脚本统计，不和提取用同一种方法，避免自己证明自己。
- 翻译交给 DeepSeek 分批做，术语表固定保留模型名（Inswapper128、GFPGAN、TensorRT 等），我再逐条校对。

## 目录

| 路径 | 内容 |
|---|---|
| `patch/apply_zh.bat` / `revert_en.bat` | 一键开启 / 还原 |
| `patch/apply_*.py` | 三个打补丁脚本：参数面板、主窗口、硬编码的菜单和按钮 |
| `patch/verify_patch.py` | 检查改过的文件都能解析，统计覆盖率 |
| `patch/strings.json` / `ui_strings.json` | 翻译表 |
| `tools/extract_*.py` | 软件更新后提取新增的英文 |
| `tools/audit_coverage.py` | 独立的覆盖率审计 |
| `tools/make_cheatsheet.py` | 生成速查表 |
| `SKILL.md` | 给 AI 助手用：给任何 Python / Qt 开源软件做中文界面的流程 |

## 软件更新后补翻新词

```bash
set VISOMASTER_REPO=...\VisoMaster-Fusion
python tools/extract_ast.py patch/strings.json          # 新的参数名和说明追加进翻译表, zh 留空
python tools/extract_hardcoded.py patch/ui_strings.json  # 新的菜单和按钮
```

把 `zh` 填上，再双击 `apply_zh.bat`。提取前先跑一次 `revert_en.bat`，不然会把已经翻成中文的字当成新词。

## 许可

GPL-3.0，和 VisoMaster Fusion 一致。翻译表里的英文原文来自 VisoMaster Fusion 的源码。

这个仓库只做界面翻译，不提供模型，也不鼓励拿换脸软件去做未经本人同意的内容。
