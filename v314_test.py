import json, tempfile
from pathlib import Path
import epg_generator as e


def base_report(ext_live=100, ext_channels=30, active=255, matched=272, quality=98.9, network_failures=0, age=0.1):
    return {
        "version":"3.14","generated_at_utc":"2026-09-13T08:00:00+00:00",
        "summary":{
            "programmes":16000,"channels_total":272,"channels_matched":matched,"channels_missing":272-matched,
            "channels_active":active,"channels_empty":272-active,"quality_average":quality,
            "external_live":ext_live,"external_live_high":80,"external_live_medium":20,
            "external_channels_with_events":ext_channels,"external_channels_current":ext_channels,
            "external_channels_fresh_cache":0,"external_channels_stale_cache":0,"external_channels_event_lkg":0,
            "external_channels_unavailable":0,"external_data_age_max_hours":age,"external_data_age_avg_hours":age/2,
            "source_degraded":1,"source_unavailable":0,"source_salvaged_feeds":1,"source_coverage_warnings":4,
            "verified_fallbacks_applied":1,"channel_lkg_recoveries":0,
            "external_same_channel_event_reuse":0,"external_duplicate_event_matches":0,
        },
        "external_live":{"events_found":200,"network_failures":network_failures},
        "sources":{"a":{"ok":True,"current_ok":True,"health":"healthy","degraded":False,
                        "configured_channel_coverage_pct":100.0,"source_programmes":1000,"source_channels":10}},
    }

# Snapshot shape.
s=e.health_snapshot_from_report(base_report())
assert s["external_live"]==100 and s["sources"]["a"]["health"]=="healthy"

# 35% External LIVE drop => warning.
with tempfile.TemporaryDirectory() as td:
    old=e.BASE_DIR
    try:
        e.BASE_DIR=Path(td)
        seed={"version":1,"source":"test","snapshot":e.health_snapshot_from_report(base_report(ext_live=100))}
        Path(td,"seed.json").write_text(json.dumps(seed))
        settings={"health_history_file":".cache/h.json","health_seed_baseline_file":"seed.json",
                  "health_history_max_builds":30,"health_external_live_drop_warn_pct":30,
                  "health_external_live_drop_critical_pct":60,"health_external_channels_drop_warn_pct":30,
                  "health_external_channels_drop_critical_pct":60,"health_channels_matched_drop_critical":1,
                  "health_channels_active_drop_warn":2,"health_quality_drop_warn":1.0,
                  "health_network_failures_warn":5,"health_network_failures_critical":20,
                  "health_external_data_age_warn_hours":6,"health_external_data_age_critical_hours":12,
                  "health_source_programme_drop_warn_pct":50,"health_source_coverage_drop_warn_points":20}
        out,h=e.build_health_evaluation(base_report(ext_live=65),settings)
        assert out["status"]=="warning",out
        assert any(a["code"]=="external_live_drop" for a in out["alerts"]),out
        assert out["comparison"]["external_live_drop_pct"]==35.0
    finally: e.BASE_DIR=old

# 70% drop => critical.
with tempfile.TemporaryDirectory() as td:
    old=e.BASE_DIR
    try:
        e.BASE_DIR=Path(td)
        seed={"version":1,"source":"test","snapshot":e.health_snapshot_from_report(base_report(ext_live=100))}
        Path(td,"seed.json").write_text(json.dumps(seed))
        settings={"health_history_file":".cache/h.json","health_seed_baseline_file":"seed.json",
                  "health_history_max_builds":30,"health_external_live_drop_warn_pct":30,
                  "health_external_live_drop_critical_pct":60,"health_external_channels_drop_warn_pct":30,
                  "health_external_channels_drop_critical_pct":60,"health_channels_matched_drop_critical":1,
                  "health_channels_active_drop_warn":2,"health_quality_drop_warn":1.0,
                  "health_network_failures_warn":5,"health_network_failures_critical":20,
                  "health_external_data_age_warn_hours":6,"health_external_data_age_critical_hours":12,
                  "health_source_programme_drop_warn_pct":50,"health_source_coverage_drop_warn_points":20}
        out,h=e.build_health_evaluation(base_report(ext_live=30),settings)
        assert out["status"]=="critical",out
    finally: e.BASE_DIR=old

# Source health regression is detected.
with tempfile.TemporaryDirectory() as td:
    old=e.BASE_DIR
    try:
        e.BASE_DIR=Path(td)
        prev=e.health_snapshot_from_report(base_report())
        Path(td,"seed.json").write_text(json.dumps({"snapshot":prev,"source":"test"}))
        cur=base_report(); cur["sources"]["a"].update({"current_ok":False,"health":"degraded","degraded":True,
                                                       "configured_channel_coverage_pct":50.0,"source_programmes":300})
        settings={"health_history_file":".cache/h.json","health_seed_baseline_file":"seed.json",
                  "health_history_max_builds":30,"health_external_live_drop_warn_pct":30,
                  "health_external_live_drop_critical_pct":60,"health_external_channels_drop_warn_pct":30,
                  "health_external_channels_drop_critical_pct":60,"health_channels_matched_drop_critical":1,
                  "health_channels_active_drop_warn":2,"health_quality_drop_warn":1.0,
                  "health_network_failures_warn":5,"health_network_failures_critical":20,
                  "health_external_data_age_warn_hours":6,"health_external_data_age_critical_hours":12,
                  "health_source_programme_drop_warn_pct":50,"health_source_coverage_drop_warn_points":20}
        out,h=e.build_health_evaluation(cur,settings)
        assert out["source_regressions"] and out["status"] in ("warning","critical")
    finally: e.BASE_DIR=old

# Healthy identical build remains healthy and history persists.
with tempfile.TemporaryDirectory() as td:
    old=e.BASE_DIR
    try:
        e.BASE_DIR=Path(td)
        Path(td,"seed.json").write_text(json.dumps({"snapshot":e.health_snapshot_from_report(base_report()),"source":"test"}))
        settings={"health_history_file":".cache/h.json","health_seed_baseline_file":"seed.json","health_history_max_builds":3,
                  "health_external_live_drop_warn_pct":30,"health_external_live_drop_critical_pct":60,
                  "health_external_channels_drop_warn_pct":30,"health_external_channels_drop_critical_pct":60,
                  "health_channels_matched_drop_critical":1,"health_channels_active_drop_warn":2,"health_quality_drop_warn":1.0,
                  "health_network_failures_warn":5,"health_network_failures_critical":20,
                  "health_external_data_age_warn_hours":6,"health_external_data_age_critical_hours":12,
                  "health_source_programme_drop_warn_pct":50,"health_source_coverage_drop_warn_points":20}
        out,h=e.build_health_evaluation(base_report(),settings)
        assert out["status"]=="healthy",out
        out2,h2=e.build_health_evaluation(base_report(ext_live=101),settings)
        assert len(h2["builds"])==2
    finally: e.BASE_DIR=old

print("v3.14 tests OK")
