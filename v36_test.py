from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import epg_generator as e

def prog(title, desc, start="20260912190000 +0000"):
    p=ET.Element("programme", {"start":start,"stop":"20260912210000 +0000","channel":"x"})
    ET.SubElement(p,"title").text=title
    ET.SubElement(p,"desc").text=desc
    return p

# Brand identity: correct brands match; "Premium" alone is not enough.
sc, ident = e.channel_identity_score("NO TV 2 SPORT PREMIUM", "V Sport Premium", True, True, True)
assert sc == 0.0 and ident.get("brand_match") is False
sc, ident = e.channel_identity_score("NO V SPORT PREMIER LEAGUE 2", "V Sport Premier League", True, True, True)
assert sc == 0.0  # target has channel number 2, candidate does not
sc, ident = e.channel_identity_score("IT EUROSPORT 1", "Eurosport 1", True, True, True)
assert sc >= 0.9 and ident["brand_match"]

# Catalog exact seed label should match despite country prefix in configured channel name.
cat={"entries":[{"label":"Sky Sports Main Event","url":"https://sport-tv-guide.live/station/sky-sports-main-event",
                 "country":"uk","source":"seed-explicit"}],"channel_map":{}}
matches=e.catalog_match_channel(
    {"name":"UK SKY SPORTS MAIN EVENT","id":"skysportsmainevent.uk"},
    {"sportguide_country":"uk"}, cat,
    {"catalog_min_score":0.70,"catalog_brand_match_required":True,"catalog_strict_numbers":True}
)
assert matches and matches[0]["score"] >= 0.9

# One-to-one: once an external event is accepted it cannot match a second programme.
event={"date":"2026-09-12","time":"20:00","title":"Arsenal - Liverpool Premier League",
       "source":"sportguide","source_url":"https://example/station/x","href":"https://example/event/1","live":True}
events=[event]
settings={
    "target_language":"pl","external_live_min_score":0.60,"external_live_high_confidence":0.78,
    "external_live_time_tolerance_minutes":150,"external_live_min_title_score":0.30,
    "external_live_use_description":True,"external_live_date_tolerance_days":1,
    "external_live_entity_min_overlap":2,"external_live_reject_risky":False,
    "external_live_one_to_one":True,"external_live_event_reuse_allowed":False,
    "add_live_prefix":True,"add_replay_prefix":True,"add_stage_prefix":True,
    "add_sport_prefix":True,"add_league_category":True,"use_emoji":False,
    "preserve_original_title":False,
}
stats={"live_matches":[],"external_live_high":0,"external_live_medium":0,
       "external_live_rejected_risky":0,"programmes":0,"live":0,"live_explicit":0,
       "external_live":0,"replay":0,"stages":0,"translated":0,
       "sports":__import__("collections").defaultdict(int),
       "leagues":__import__("collections").defaultdict(int)}
p1=prog("Premier League","Arsenal - Liverpool")
p2=prog("Premier League","Arsenal - Liverpool", "20260912190500 +0000")
e.transform_programme(p1,"x",settings,{},events,stats,"Europe/London")
e.transform_programme(p2,"x",settings,{},events,stats,"Europe/London")
assert stats["external_live"] == 1, stats
assert len(stats["live_matches"]) == 1
assert event.get("_used") is True

print("v3.6 tests OK")
