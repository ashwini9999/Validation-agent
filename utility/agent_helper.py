# utility/agent_helper.py
import os
from datetime import datetime


# ---------------- FS helpers ----------------
def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def _ts() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")

# ---------------- axe-core helpers ----------------
AXE_LOCAL_PATHS = [
    "third_party/axe.min.js",        # preferred vendored path
    "axe.min.js"                     # fallback if you drop it in project root
]