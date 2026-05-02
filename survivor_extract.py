"""Extract Top_Down_Survivor.zip once into assets/survivor_packed/."""
from __future__ import annotations

import os
import zipfile

_ASSETS = os.path.join(os.path.dirname(__file__), "assets")
_ZIP = os.path.join(_ASSETS, "Top_Down_Survivor.zip")
_ROOT = os.path.join(_ASSETS, "survivor_packed")
_MARKER = os.path.join(_ROOT, "Top_Down_Survivor", "handgun", "move", "survivor-move_handgun_0.png")


def ensure_survivor() -> str:
    if os.path.isfile(_MARKER):
        return os.path.join(_ROOT, "Top_Down_Survivor")
    os.makedirs(_ROOT, exist_ok=True)
    if not os.path.isfile(_ZIP):
        raise FileNotFoundError(f"Missing {_ZIP} — download from OpenGameArt (Animated Top Down Survivor).")
    with zipfile.ZipFile(_ZIP, "r") as zf:
        zf.extractall(_ROOT)
    return os.path.join(_ROOT, "Top_Down_Survivor")
