from datetime import datetime
import xml.etree.ElementTree as ET
from epg_generator import analyze_schedule, parse_sportguide_events, sportguide_url_candidates
p1=ET.Element("programme",{"channel":"x","start":"20260912003000 +0200","stop":"20260912023000 +0200"}); ET.SubElement(p1,"title").text="A"
p2=ET.Element("programme",{"channel":"x","start":"20260912023000 +0000","stop":"20260912043000 +0000"}); ET.SubElement(p2,"title").text="B"
q=analyze_schedule([p1,p2],{"quality_overlap_warning_minutes":5,"quality_gap_warning_minutes":180,"quality_use_wall_clock_for_mixed_offsets":True,"quality_mixed_offset_overlap_ratio":0.5})
assert q["mixed_timezone_offsets"]
assert "https://sport-tv-guide.live/station/pt-sport-tv-1" in sportguide_url_candidates("https://sport-tv-guide.live/tv-guide-live/pt-sport-tv-1",{"try_station_alias":True})
sample="""<html><body><div>12 Sep</div><a href='/event/live-football-x/1'>Football Arsenal - Liverpool Premier League</a></body></html>"""
ev=parse_sportguide_events(sample,datetime(2026,9,12)); assert ev and ev[0]["date"]=="2026-09-12"
print("v3.3 regression tests OK")
