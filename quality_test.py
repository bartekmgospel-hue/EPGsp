from datetime import datetime
import xml.etree.ElementTree as ET
import epg_generator as e

e.LEAGUE_RULES = e.load_yaml(e.LEAGUES_FILE).get("leagues", [])
assert e.league_from_text("UEFA Champions League: Arsenal - Inter")["key"] == "uefa_champions_league"
assert e.league_from_text("NBA: Lakers - Celtics")["key"] == "nba"

sample = []
for start, stop, title in [
    ("20260912100000 +0000","20260912110000 +0000","A"),
    ("20260912110000 +0000","20260912120000 +0000","B"),
    ("20260912110000 +0000","20260912120000 +0000","B"),
    ("20260912150000 +0000","20260912160000 +0000","C"),
]:
    p=ET.Element("programme", {"start":start,"stop":stop})
    ET.SubElement(p,"title").text=title
    sample.append(p)

dedup, removed = e.deduplicate_programmes(sample)
assert removed == 1
q = e.analyze_schedule(dedup, {"quality_gap_warning_minutes":120,"quality_overlap_warning_minutes":5,"quality_low_programme_threshold":1}, removed)
assert q["large_gaps"] == 1
assert q["exact_duplicates_removed"] == 1
print("quality tests OK")
