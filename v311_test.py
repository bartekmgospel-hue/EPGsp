import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
import epg_generator as e

# Source health: recovered feed with 0% configured coverage is degraded.
st=e.decorate_source_health({"ok":True,"current_ok":False,"salvaged":True,
    "coverage":{"configured_groups_total":2,"configured_coverage_pct":0.0}},
    {"source_degraded_configured_coverage_threshold_pct":90})
assert st["degraded"] and st["health"]=="degraded", st

# Current feed with selected empty channels gets a warning, not whole-source degraded status.
st2=e.decorate_source_health({"ok":True,"current_ok":True,
    "coverage":{"configured_groups_total":10,"configured_coverage_pct":80.0}},
    {"source_degraded_configured_coverage_threshold_pct":90})
assert not st2["degraded"] and st2["health"]=="healthy_with_gaps" and st2["coverage_warning"], st2

# Retention metrics use LKG baseline and do not claim byte-level completeness.
base=ET.fromstring('<tv><channel id="a"/><channel id="b"/><programme channel="a"/><programme channel="b"/></tv>')
rec=ET.fromstring('<tv><channel id="a"/><programme channel="a"/></tv>')
r=e.source_recovery_retention_metrics(rec,base)
assert r["salvage_channel_retention_pct"]==50.0 and r["salvage_programme_retention_estimate_pct"]==50.0, r

# Per-channel LKG round-trip.
with tempfile.TemporaryDirectory(dir=e.BASE_DIR) as td:
    rel=str(Path(td).relative_to(e.BASE_DIR))
    settings={"channel_lkg_enabled":True,"channel_lkg_dir":rel,"channel_lkg_max_age_hours":48,
              "channel_lkg_recent_grace_hours":10000,"channel_lkg_min_programmes":1}
    chcfg={"id":"movistar1.es","name":"ES MOVISTAR 1"}
    ch=ET.fromstring('<channel id="M1"><display-name>M1</display-name></channel>')
    p=ET.fromstring('<programme channel="M1" start="20260913080000 +0000" stop="20270913090000 +0000"><title>Test</title></programme>')
    e.save_channel_lkg(chcfg,"spain","M1",ch,[p],settings)
    root,meta=e.load_channel_lkg(chcfg,settings)
    assert root is not None and meta["available"] and meta["cached_source_id"]=="M1", meta
    assert len(root.findall("programme"))==1

# Recommendation history only promotes after 3 consecutive qualifying observations.
with tempfile.TemporaryDirectory(dir=e.BASE_DIR) as td:
    rel=str(Path(td).relative_to(e.BASE_DIR)/'history.json')
    settings={"recommendation_history_file":rel,"recommendation_history_max_builds":12,
              "recommendation_history_required_builds":3,"recommendation_history_min_consensus":0.60,
              "recommendation_history_min_identity_score":0.95,"recommendation_history_min_same_slot_matches":20}
    for i in range(3):
        report={"generated_at_utc":f"2026-09-1{i+3}T00:00:00+00:00","channels":[{
            "id":"x","name":"X","cross_source_recommendations":[{
                "source":"other","source_id":"X.other","label":"X","score":1.0,
                "schedule_consensus_max":0.72,"schedule_consensus_same_slot_matched":30,
                "schedule_consensus_repeat_matched":0,"schedule_consensus_evidence":40}]}]}
        hist,cands=e.update_recommendation_history(report,settings)
        if i<2: assert not cands, cands
    assert len(cands)==1 and cands[0]["promotion_ready"] and not cands[0]["auto_apply"], cands

print('v3.11 tests OK')
