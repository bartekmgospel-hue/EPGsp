import xml.etree.ElementTree as ET
import epg_generator as e

e.LEAGUE_RULES = e.load_yaml(e.LEAGUES_FILE).get("leagues", [])

# Strong match: title has teams, description supplies league/sport context.
p = ET.Element("programme", {"start":"20260912180000 +0000", "stop":"20260912200000 +0000", "channel":"x"})
ET.SubElement(p,"title").text = "Arsenal - Liverpool"
ET.SubElement(p,"desc").text = "Premier League football"
stats = {
    "programmes":0,"live":0,"live_explicit":0,"external_live":0,"external_live_high":0,
    "external_live_medium":0,"replay":0,"stages":0,"translated":0,
    "sports":__import__('collections').defaultdict(int),"leagues":__import__('collections').defaultdict(int),"live_matches":[]
}
ext = [{"date":"2026-09-12","time":"18:00","title":"Arsenal - Liverpool Premier League","source":"sportguide","source_url":"https://example.test"}]
out = e.transform_programme(p,"test.channel",{
    "external_live_min_score":0.64,"external_live_min_title_score":0.48,"external_live_high_confidence":0.78,
    "external_live_time_tolerance_minutes":120,"target_language":"pl","use_emoji":True,
    "add_live_prefix":True,"add_replay_prefix":True,"add_stage_prefix":True,"add_sport_prefix":True,
    "preserve_original_title":True,"add_league_category":True,"debug_provenance_in_desc":False,
}, {}, ext, stats)
assert stats["live"] == 1
assert stats["external_live"] == 1
assert stats["leagues"]["Premier League"] == 1
assert "LIVE" in out.findtext("title")
assert any((c.text or '') == "Premier League" for c in out.findall("category"))

# Sport conflict must reject the external match.
match, score, details = e.best_external_match(
    "ATP: Sinner - Alcaraz", __import__('datetime').date(2026,9,12),
    [{"date":"2026-09-12","title":"NBA: Lakers - Celtics","source":"sportguide"}],
    0.64, min_title_score=0.10
)
assert match is None
print("integration tests OK")
