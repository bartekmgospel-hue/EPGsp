import epg_generator as e

# Brand precedence and generic Sport1 fallback
assert e.canonical_brand("SK SPORT 1") == "sport1"
assert e.canonical_brand("PREMIER SPORT 1 HD") == "premier sport"
assert e.canonical_brand("RMC Sport 1") == "rmc sport"
assert e.canonical_brand("MAX Sport 1") == "max sport"

score, info = e.channel_identity_score(
    "SK SPORT 1", "PREMIER SPORT 1 HD",
    require_brand=True, strict_numbers=True, require_critical=True, strict_variants=True
)
assert score == 0.0

# Variant safety
score, info = e.channel_identity_score(
    "NO V SPORT 2", "V Sport Live 2",
    require_brand=True, strict_numbers=True, require_critical=True, strict_variants=True
)
assert score == 0.0 and info.get("variant_match") is False

score, info = e.channel_identity_score(
    "NO EUROSPORT N", "Eurosport 1",
    require_brand=True, strict_numbers=True, require_critical=True, strict_variants=True
)
assert score == 0.0

score, info = e.channel_identity_score(
    "NO V SPORT PREMIER LEAGUE 2", "V Sport Premier League 2",
    require_brand=True, strict_numbers=True, require_critical=True, strict_variants=True
)
assert score >= 0.9 and info.get("variant_match") is True

# External event dedupe
events = [
    {"href":"https://x/event/1","title":"A - B","date":"2026-09-12","time":"20:00","source":"sportguide"},
    {"href":"https://x/event/1","title":"A - B","date":"2026-09-12","time":"20:00","source":"sportguide"},
]
deduped, removed = e.dedupe_external_events(events)
assert len(deduped) == 1 and removed == 1

# Same-channel reuse versus cross-channel simulcast.
matches = [
    {"channel_id":"a","external_event_key":"event:x"},
    {"channel_id":"b","external_event_key":"event:x"},  # valid simulcast
    {"channel_id":"a","external_event_key":"event:y"},
]
u = e.external_usage_metrics(matches)
assert u["same_channel_reuse"] == 0
assert u["cross_channel_simulcast_events"] == 1
assert u["cross_channel_simulcast_extra_matches"] == 1

bad = matches + [{"channel_id":"a","external_event_key":"event:y"}]
u2 = e.external_usage_metrics(bad)
assert u2["same_channel_reuse"] == 1

print("v3.7 tests OK")
