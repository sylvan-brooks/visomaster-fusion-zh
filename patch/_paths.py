"""Locate the VisoMaster Fusion checkout.

Order: env VISOMASTER_REPO -> ../VisoMaster-Fusion next to this repo's parent
(i.e. drop this repo folder beside the launcher) -> ../../VisoMaster-Fusion.
"""
import os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find_repo():
    env = os.environ.get("VISOMASTER_REPO")
    cands = [Path(env)] if env else []
    cands += [HERE.parent.parent / "VisoMaster-Fusion", HERE.parent / "VisoMaster-Fusion",
              HERE.parent.parent.parent / "VisoMaster-Fusion"]
    for c in cands:
        if (c / "app" / "ui" / "widgets").is_dir():
            return c
    sys.exit("VisoMaster-Fusion not found. Put this folder next to it, or set VISOMASTER_REPO.")


REPO = find_repo()
WIDGETS = REPO / "app" / "ui" / "widgets"
MAIN_WINDOW = REPO / "app" / "ui" / "core" / "main_window.py"
