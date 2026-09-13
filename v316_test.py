import json, tempfile
from pathlib import Path
import epg_generator as e

settings={
    "health_trend_min_builds":3,"health_trend_window_builds":5,
    "health_trend_confidence_enabled":True,"health_trend_confidence_medium_builds":3,
    "health_trend_confidence_high_builds":5,"health_trend_confidence_medium_score":55,"health_trend_confidence_high_score":85,
}
# Confidence grows with history depth.
r=e.classify_metric_trend("external_live",[101,101],settings)
assert r["confidence"]=="low",r
r=e.classify_metric_trend("external_live",[101,101,101,101],settings)
assert r["classification"]=="stable" and r["confidence"]=="medium",r
r=e.classify_metric_trend("external_live",[101,101,101,101,101],settings)
assert r["confidence"]=="high",r
# Persistent regression receives persistence evidence but not false high confidence from only 3 points.
r=e.classify_metric_trend("external_live",[101,70,68],settings)
assert r["classification"]=="persistent_regression" and r["confidence"] in ("medium","high"),r
# Unified history merges canonical, legacy and seed without duplicates.
with tempfile.TemporaryDirectory() as td:
    old=e.BASE_DIR
    try:
        e.BASE_DIR=Path(td)
        (e.BASE_DIR/"seed.json").write_text(json.dumps({"builds":[
            {"version":"3.13","generated_at_utc":"2026-09-13T07:28:00+00:00","snapshot":{"version":"3.13","generated_at_utc":"2026-09-13T07:28:00+00:00","external_live":101}},
            {"version":"3.14","generated_at_utc":"2026-09-13T07:51:00+00:00","snapshot":{"version":"3.14","generated_at_utc":"2026-09-13T07:51:00+00:00","external_live":101}}]}))
        (e.BASE_DIR/"legacy.json").write_text(json.dumps({"builds":[
            {"version":"3.14","generated_at_utc":"2026-09-13T07:51:00+00:00","snapshot":{"version":"3.14","generated_at_utc":"2026-09-13T07:51:00+00:00","external_live":101}},
            {"version":"3.15","generated_at_utc":"2026-09-13T08:21:00+00:00","snapshot":{"version":"3.15","generated_at_utc":"2026-09-13T08:21:00+00:00","external_live":101}}]}))
        st={"health_history_file":"canonical.json","health_legacy_history_file":"legacy.json","health_unified_seed_file":"seed.json",
            "health_trend_seed_file":"missing.json","health_seed_baseline_file":"missing2.json","health_history_max_builds":30}
        h=e.load_health_history(st)
        assert [x["version"] for x in h["builds"]]==["3.13","3.14","3.15"],h
        cur={"version":"3.16","generated_at_utc":"2026-09-13T09:00:00+00:00","external_live":101,"external_channels_with_events":32,
             "channels_active":255,"channels_matched":272,"quality_average":98.9,"external_network_failures":0,"external_data_age_max_hours":0.2}
        tr=e.evaluate_health_trends(h,cur,{**settings,"health_trend_seed_file":"missing.json"})
        assert tr["window_builds"]==4 and tr["confidence"]=="medium",tr
    finally:
        e.BASE_DIR=old
print("v3.16 tests OK")
