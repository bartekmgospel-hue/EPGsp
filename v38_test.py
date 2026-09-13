import xml.etree.ElementTree as ET
import epg_generator as e

def p(start, title, desc="", cat=""):
    x=ET.Element("programme", {"start":start,"stop":start,"channel":"x"})
    ET.SubElement(x,"title").text=title
    if desc:
        ET.SubElement(x,"desc").text=desc
    if cat:
        ET.SubElement(x,"category").text=cat
    return x

# Same event, different languages/format, same absolute time.
a = e.programme_fingerprint(p(
    "20260912200000 +0200",
    "Piłka nożna: Arsenal - Liverpool",
    "Premier League. Arsenal kontra Liverpool",
    "Football"
))
b = e.programme_fingerprint(p(
    "20260912180000 +0000",
    "Football: Arsenal v Liverpool",
    "Premier League - Arsenal vs Liverpool",
    "Football"
))
assert a and b
sc, d = e.fingerprint_pair_score(a,b,180)
assert sc >= 0.80, (sc,d)
assert d["time_delta_minutes"] == 0.0
assert d["entity_overlap"] >= 2

# Different participants at same time should not become the same event merely because sport matches.
c = e.programme_fingerprint(p(
    "20260912180000 +0000",
    "Football: Chelsea v Tottenham",
    "Premier League",
    "Football"
))
sc2, d2 = e.fingerprint_pair_score(a,c,180)
assert sc2 < 0.62, (sc2,d2)

# Build two localized schedules with six matching events: consensus should be strong.
root1=ET.Element("tv"); root2=ET.Element("tv")
teams=[("Arsenal","Liverpool"),("Chelsea","Tottenham"),("Milan","Inter"),("Real Madrid","Barcelona"),
       ("Bayern","Dortmund"),("Ajax","PSV")]
for idx,(t1,t2) in enumerate(teams):
    hh=12+idx
    x=ET.SubElement(root1,"programme",{"start":f"20260912{hh:02d}0000 +0200","stop":f"20260912{hh+1:02d}0000 +0200","channel":"A"})
    ET.SubElement(x,"title").text=f"Piłka nożna: {t1} - {t2}"
    ET.SubElement(x,"desc").text=f"{t1} kontra {t2}"
    ET.SubElement(x,"category").text="Football"

    y=ET.SubElement(root2,"programme",{"start":f"20260912{hh-2:02d}0000 +0000","stop":f"20260912{hh-1:02d}0000 +0000","channel":"B"})
    ET.SubElement(y,"title").text=f"Football: {t1} v {t2}"
    ET.SubElement(y,"desc").text=f"{t1} vs {t2}"
    ET.SubElement(y,"category").text="Football"

fa=e.schedule_fingerprint_items(root1,"A")
fb=e.schedule_fingerprint_items(root2,"B")
res=e.fingerprint_schedule_consensus(fa,fb,{
    "source_recommendation_fingerprint_pair_min_score":0.62,
    "source_recommendation_fingerprint_time_tolerance_minutes":180,
    "source_recommendation_fingerprint_min_evidence":4,
})
assert res["matched"] == 6, res
assert res["score"] >= 0.90, res

# Low evidence cannot be promoted to a misleading perfect strong signal.
low=e.fingerprint_schedule_consensus(fa[:1],fb[:1],{
    "source_recommendation_fingerprint_pair_min_score":0.62,
    "source_recommendation_fingerprint_time_tolerance_minutes":180,
    "source_recommendation_fingerprint_min_evidence":4,
})
assert low["score"] < 0.70, low

print("v3.8 tests OK")
