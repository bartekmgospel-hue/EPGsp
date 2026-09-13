import epg_generator as e

# v3.16 real-world pattern: one medium-confidence External LIVE anomaly should lower 100 -> 96,
# but should not itself create a warning/critical status.
trend={
    "persistent_regressions":[],
    "single_anomalies":[{"metric":"external_live","confidence":"medium","change_pct":-17.8,"current":83,"baseline":101}],
    "confidence":"medium"
}
current={"source_unavailable":0,"external_channels_unavailable":0,"external_same_channel_event_reuse":0,
         "external_duplicate_event_matches":0,"external_data_age_max_hours":0.022}
settings={"health_score_single_anomaly_penalty_enabled":True,
          "health_score_single_anomaly_penalty_low":1,"health_score_single_anomaly_penalty_medium":4,
          "health_score_single_anomaly_penalty_high":7,"health_score_single_anomaly_penalty_max":12}
score,parts=e.calculate_health_score([],trend,current,settings)
assert score==96,(score,parts)
assert parts["single_anomaly_penalty"]==4,parts
assert parts["single_anomaly_penalty_details"][0]["metric"]=="external_live",parts

# Confidence-aware levels.
for conf,expected in [("low",99),("medium",96),("high",93)]:
    tr={"persistent_regressions":[],"single_anomalies":[{"metric":"external_live","confidence":conf}]}
    sc,_=e.calculate_health_score([],tr,current,settings)
    assert sc==expected,(conf,sc)

# Multiple anomalies are capped.
tr={"persistent_regressions":[],"single_anomalies":[
    {"metric":"external_live","confidence":"high"},
    {"metric":"channels_active","confidence":"high"},
    {"metric":"quality_average","confidence":"high"},
]}
sc,parts=e.calculate_health_score([],tr,current,settings)
assert parts["single_anomaly_penalty"]==12,parts
assert sc==88,(sc,parts)

# Disabled means exact v3.16 scoring behavior.
sc,parts=e.calculate_health_score([],trend,current,{"health_score_single_anomaly_penalty_enabled":False})
assert sc==100,(sc,parts)

# Persistent regression remains stronger and is not double-counted as a single anomaly.
tr={"persistent_regressions":[{"metric":"external_live"}],"single_anomalies":[]}
sc,parts=e.calculate_health_score([],tr,current,settings)
assert sc==95 and parts["persistent_trend_penalty"]==5,(sc,parts)

print("v3.17 tests OK")
