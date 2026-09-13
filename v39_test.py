import xml.etree.ElementTree as ET
import epg_generator as e

raw = b'''<?xml version="1.0" encoding="UTF-8"?>
<tv>
<channel id="x"><display-name>X</display-name></channel>
<programme channel="x" start="20260913080000 +0000" stop="20260913090000 +0000"><title>A</title></programme>
<programme channel="x" start="20260913090000 +0000" stop="20260913100000 +0000"><title>B</title>'''
root, fixed, err = e.salvage_truncated_xmltv(raw)
assert root is not None and err is None
assert len(root.findall("programme")) == 1
assert root.findall("programme")[0].findtext("title") == "A"

e.LEAGUE_RULES = [{"key":"del","name":"DEL","sport":"hockey","aliases":["deutsche eishockey liga","del"],
                   "ambiguous_alias_require_terms":{"del":["hockey","eishockey","hokej"]}}]
assert e.league_from_text("Kolarstwo: Vuelta a Espana - etapa del dia") is None
assert e.league_from_text("Hockey: DEL - Berlin vs Mannheim")["key"] == "del"

e.LEAGUE_RULES = []

def mk(start, title, desc=""):
    p=ET.Element("programme",{"start":start,"stop":start,"channel":"x"})
    ET.SubElement(p,"title").text=title
    if desc:
        ET.SubElement(p,"desc").text=desc
    return p

a=e.programme_fingerprint(mk("20260913180000 +0000","Football: Arsenal - Liverpool","Arsenal Liverpool"))
b=e.programme_fingerprint(mk("20260913183000 +0000","Piłka nożna: Arsenal - Liverpool","Arsenal Liverpool"))
sc, d=e.fingerprint_pair_score(a,b,360,45,60,360)
assert d["slot_relation"]=="same_slot", d
assert sc >= 0.62, (sc,d)

c=e.programme_fingerprint(mk("20260913200500 +0000","Football: Arsenal - Liverpool","Arsenal Liverpool"))
sc2, d2=e.fingerprint_pair_score(a,c,360,45,60,360)
assert d2["slot_relation"]=="repeat_or_replay", d2

res=e.fingerprint_schedule_consensus([a],[c],{
    "source_recommendation_fingerprint_pair_min_score":0.62,
    "source_recommendation_fingerprint_time_tolerance_minutes":360,
    "source_recommendation_fingerprint_same_slot_tolerance_minutes":45,
    "source_recommendation_fingerprint_repeat_min_delay_minutes":60,
    "source_recommendation_fingerprint_repeat_max_delay_minutes":360,
    "source_recommendation_fingerprint_min_evidence":4,
})
assert res["same_slot_matched"] == 0, res
assert res["repeat_matched"] == 1, res
assert res["score"] == 0.0, res

print("v3.9 tests OK")
