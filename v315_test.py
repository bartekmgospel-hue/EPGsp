import json, tempfile
from pathlib import Path
import epg_generator as e

# Stable three-build sequence.
settings={"health_trend_min_builds":3,"health_trend_window_builds":5}
r=e.classify_metric_trend("external_live",[101,101,101],settings)
assert r["classification"]=="stable",r
# One-off anomaly.
r=e.classify_metric_trend("external_live",[101,101,70],settings)
assert r["classification"]=="single_anomaly",r
# Persistent regression: two latest observations below old baseline.
r=e.classify_metric_trend("external_live",[101,70,68],settings)
assert r["classification"]=="persistent_regression",r
# Bad-direction metric: data age increasing persistently.
r=e.classify_metric_trend("external_data_age_max_hours",[0.2,3.5,4.2],settings)
assert r["classification"]=="persistent_regression",r
# Improving sequence.
r=e.classify_metric_trend("external_live",[80,90,101],settings)
assert r["classification"]=="improving",r

# Score is 100 for stable healthy build; warning and critical reduce it.
current={"source_unavailable":0,"external_channels_unavailable":0,"external_same_channel_event_reuse":0,
         "external_duplicate_event_matches":0,"external_data_age_max_hours":0.4}
trend={"persistent_regressions":[]}
score,parts=e.calculate_health_score([],trend,current)
assert score==100,(score,parts)
score2,_=e.calculate_health_score([{"severity":"warning"}],trend,current)
assert score2==92,score2
score3,_=e.calculate_health_score([{"severity":"critical"}],trend,current)
assert score3==75,score3

# Seed+history+current are de-duplicated and windowed.
with tempfile.TemporaryDirectory() as td:
    old=e.BASE_DIR
    try:
        e.BASE_DIR=Path(td)
        seed={"builds":[
            {"snapshot":{"version":"3.13","generated_at_utc":"2026-09-13T07:28:00+00:00","external_live":101}},
            {"snapshot":{"version":"3.14","generated_at_utc":"2026-09-13T07:51:00+00:00","external_live":101}}
        ]}
        (e.BASE_DIR/"seed.json").write_text(json.dumps(seed))
        settings2={"health_trend_seed_file":"seed.json","health_trend_window_builds":5}
        rows=e.collect_health_trend_snapshots({"builds":[]},{"version":"3.15","generated_at_utc":"2026-09-13T08:20:00+00:00","external_live":101},settings2)
        assert [x["version"] for x in rows]==["3.13","3.14","3.15"],rows
    finally:
        e.BASE_DIR=old
print("v3.15 tests OK")
