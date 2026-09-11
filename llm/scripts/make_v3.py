import os
import yaml
from pathlib import Path

OUT_DIR = Path("scenarios_v3")

def save(sub, s_dict):
    p = OUT_DIR / sub / f"{s_dict['id']}.yaml"
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(s_dict, f, sort_keys=False)

print("make_v3 helper ready")
