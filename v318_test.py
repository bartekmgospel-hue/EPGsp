import epg_generator as e

rows_same_snapshot = [
    {"version":"a","generated_at_utc":"2026-09-13T10:00:00+00:00","external_live": 101, "external_channels_with_events": 32, "channels_active": 255, "channels_matched": 272, "quality_average": 98.9, "external_network_failures": 0, "external_data_age_max_hours": 0.02, "external_snapshot_id": "snap-a"},
    {"version":"b","generated_at_utc":"2026-09-13T11:00:00+00:00","external_live": 101, "external_channels_with_events": 32, "channels_active": 255, "channels_matched": 272, "quality_average": 98.9, "external_network_failures": 0, "external_data_age_max_hours": 0.41, "external_snapshot_id": "snap-b"},
    {"version":"c","generated_at_utc":"2026-09-13T12:00:00+00:00","external_live": 101, "external_channels_with_events": 32, "channels_active": 255, "channels_matched": 272, "quality_average": 98.9, "external_network_failures": 0, "external_data_age_max_hours": 0.90, "external_snapshot_id": "snap-c"},
    {"version":"d","generated_at_utc":"2026-09-13T13:00:00+00:00","external_live": 83,  "external_channels_with_events": 32, "channels_active": 257, "channels_matched": 272, "quality_average": 98.9, "external_network_failures": 0, "external_data_age_max_hours": 0.40, "external_snapshot_id": "snap-d"},
    {"version":"e","generated_at_utc":"2026-09-13T14:00:00+00:00","external_live": 83,  "external_channels_with_events": 32, "channels_active": 257, "channels_matched": 272, "quality_average": 98.9, "external_network_failures": 0, "external_data_age_max_hours": 0.43, "external_snapshot_id": "snap-d"},
]
trend=e.evaluate_health_trends({"builds":[{"snapshot":r, "version":str(i)} for i,r in enumerate(rows_same_snapshot[:-1],1)]}, rows_same_snapshot[-1], {"health_trend_window_builds":5, "health_trend_min_builds":3, "health_trend_external_live_watch_pct":15.0, "health_trend_confidence_enabled":True, "health_trend_confidence_medium_builds":3, "health_trend_confidence_high_builds":5, "health_trend_confidence_high_score":85, "health_trend_confidence_medium_score":55, "health_trend_external_unique_snapshots_required":2})
metric = next(x for x in trend["metrics"] if x["metric"]=="external_live")
assert metric["classification"] == "single_anomaly", metric
assert metric.get("awaiting_snapshot_confirmation") is True, metric

rows_new_snapshot = rows_same_snapshot[:-1] + [{**rows_same_snapshot[-1], "version":"f", "generated_at_utc":"2026-09-13T15:00:00+00:00", "external_snapshot_id": "snap-e"}]
trend2=e.evaluate_health_trends({"builds":[{"snapshot":r, "version":str(i)} for i,r in enumerate(rows_new_snapshot[:-1],1)]}, rows_new_snapshot[-1], {"health_trend_window_builds":5, "health_trend_min_builds":3, "health_trend_external_live_watch_pct":15.0, "health_trend_confidence_enabled":True, "health_trend_confidence_medium_builds":3, "health_trend_confidence_high_builds":5, "health_trend_confidence_high_score":85, "health_trend_confidence_medium_score":55, "health_trend_external_unique_snapshots_required":2})
metric2 = next(x for x in trend2["metrics"] if x["metric"]=="external_live")
assert metric2["classification"] == "persistent_regression", metric2

replacements = {"football": "Piłka nożna", "baseball": "Baseball"}
new_title, meta = e.format_title("MLB Network", "", {"target_language":"pl", "use_emoji":True, "add_live_prefix":True, "add_replay_prefix":True, "add_stage_prefix":True, "add_sport_prefix":True, "external_live_enrich_title_with_participants":True, "external_live_enrich_generic_only":True, "external_live_title_enrichment_min_score":0.68, "add_unknown_sport_prefix_for_live":True}, replacements, {"title":"MLB: New York Yankees vs Boston Red Sox"}, external_score=0.91, channel_name="MLB Network")
assert "Yankees" in new_title and "Red Sox" in new_title, new_title
assert meta["participants_enriched"] is True, meta
assert meta["sport"] == "baseball", meta
print("v3.18 tests OK")

# Better Polish translation of common sports programme vocabulary.
translated, changed = e.phrase_translate(
    "Women's Regular Season Game 3 - Highlights",
    {
        "women's":"kobiet",
        "regular season":"sezon zasadniczy",
        "game":"mecz",
        "highlights":"skrót",
    },
)
assert changed is True, translated
assert "kobiet" in translated.lower() and "sezon zasadniczy" in translated.lower() and "mecz" in translated.lower() and "skrót" in translated.lower(), translated

# translated_title_only must leave exactly one Polish title and must not add an Original/Oryginał subtitle.
import xml.etree.ElementTree as ET
from collections import defaultdict
prog=ET.Element("programme", {"channel":"x","start":"20260913200000 +0000","stop":"20260913220000 +0000"})
ET.SubElement(prog,"title",{"lang":"en"}).text="Football Live Match"
ET.SubElement(prog,"title",{"lang":"de"}).text="Fußball Live"
ET.SubElement(prog,"sub-title",{"lang":"en"}).text="Football Live Match"
stats={"programmes":0,"live":0,"live_explicit":0,"external_live":0,"external_live_high":0,"external_live_medium":0,"external_live_rejected_risky":0,"replay":0,"stages":0,"translated":0,"sports":defaultdict(int),"leagues":defaultdict(int),"live_matches":[]}
out=e.transform_programme(prog,"test.channel",{
    "target_language":"pl","use_emoji":True,"add_live_prefix":True,"add_replay_prefix":True,"add_stage_prefix":True,"add_sport_prefix":True,
    "preserve_original_title":False,"translated_title_only":True,"external_live_min_score":0.6,"external_live_time_tolerance_minutes":150,
    "external_live_min_title_score":0.3,"external_live_use_description":True,"external_live_date_tolerance_days":1,"external_live_entity_min_overlap":2,
    "external_live_reject_risky":True,"add_unknown_sport_prefix_for_live":True,"add_league_category":True,
}, {"football":"piłka nożna","live match":"mecz na żywo"}, [], stats)
titles=out.findall("title")
assert len(titles)==1, [x.text for x in titles]
assert titles[0].get("lang")=="pl", ET.tostring(out,encoding="unicode")
assert "piłka nożna" in (titles[0].text or "").lower(), titles[0].text
assert all(not ((s.text or "").lower().startswith("oryginał:") or (s.text or "").lower().startswith("original:")) for s in out.findall("sub-title")), ET.tostring(out,encoding="unicode")
print("v3.18 translation-only tests OK")
