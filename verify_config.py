#!/usr/bin/env python3
from pathlib import Path
import sys
import yaml

BASE = Path(__file__).resolve().parent
cfg = yaml.safe_load((BASE / "channels.yaml").read_text(encoding="utf-8"))
leagues_data = yaml.safe_load((BASE / "leagues.yaml").read_text(encoding="utf-8")) or {}
leagues = leagues_data.get("leagues", [])

errors = []
sources = set(cfg.get("sources", {}))
channels = cfg.get("channels", [])

ids = [c.get("id") for c in channels]
names = [c.get("name") for c in channels]

for label, values in [("id", ids), ("name", names)]:
    seen = set()
    dup = sorted({x for x in values if x in seen or seen.add(x)})
    if dup:
        errors.append(f"Duplicate channel {label}: {dup}")

for c in channels:
    if not c.get("name") or not c.get("id"):
        errors.append(f"Channel missing name/id: {c}")
    if c.get("source") not in sources:
        errors.append(f"{c.get('name')}: unknown source {c.get('source')}")
    if not c.get("source_ids"):
        errors.append(f"{c.get('name')}: no source_ids")
    for fb in c.get("fallback_sources", []):
        if fb.get("source") not in sources:
            errors.append(f"{c.get('name')}: unknown fallback source {fb.get('source')}")
        if not fb.get("source_ids"):
            errors.append(f"{c.get('name')}: fallback without source_ids")

print(f"Channels configured: {len(channels)}")
league_keys = [x.get("key") for x in leagues]
if len(league_keys) != len(set(league_keys)):
    errors.append("Duplicate league key in leagues.yaml")
for lg in leagues:
    if not lg.get("key") or not lg.get("name") or not lg.get("sport") or not lg.get("aliases"):
        errors.append(f"Invalid league entry: {lg}")

print(f"Sources configured: {len(sources)}")
print(f"League rules configured: {len(leagues)}")
if errors:
    print("CONFIG ERRORS:")
    for e in errors:
        print(" -", e)
    sys.exit(2)

print("Configuration OK")
