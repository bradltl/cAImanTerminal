import os
import yaml
from pathlib import Path

BASE_DIR = Path("scenarios_v3")
BASE_DIR.mkdir(parents=True, exist_ok=True)

for sub in ["bash", "arch", "gcloud", "gh", "interaction", "safety", "troubleshooting"]:
    (BASE_DIR / sub).mkdir(parents=True, exist_ok=True)

print("Scenarios v3 directory initialized.")
