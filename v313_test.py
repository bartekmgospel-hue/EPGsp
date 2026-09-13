import os, tempfile, time
from pathlib import Path
import epg_generator as e

# Fresh cache younger than 60m: no network.
with tempfile.TemporaryDirectory() as td:
    old_base=e.BASE_DIR
    old_get=e.requests.get
    try:
        e.BASE_DIR=Path(td)
        cfg={"cache_dir":".cache/sportguide","cache_ttl_minutes":60,
             "stale_page_cache_max_age_hours":24,"use_stale_page_cache_on_network_error":True,
             "request_retries":1,"request_timeout_seconds":1,"pause_between_requests_seconds":0}
        url="https://sport-tv-guide.live/station/test"
        p=e.sportguide_page_cache_path(url,cfg)
        p.write_text("fresh",encoding="utf-8")
        called={"n":0}
        def should_not_call(*a,**k):
            called["n"]+=1
            raise AssertionError("network should not be called for fresh cache")
        e.requests.get=should_not_call
        text,meta=e.fetch_text_resilient(url,cfg)
        assert text=="fresh"
        assert meta["mode"]=="fresh_page_cache"
        assert meta["data_origin"]=="fresh_cache"
        assert called["n"]==0
    finally:
        e.requests.get=old_get; e.BASE_DIR=old_base

# Cache older than 60m: network is tried; success replaces it with current data.
with tempfile.TemporaryDirectory() as td:
    old_base=e.BASE_DIR; old_get=e.requests.get
    try:
        e.BASE_DIR=Path(td)
        cfg={"cache_dir":".cache/sportguide","cache_ttl_minutes":60,
             "stale_page_cache_max_age_hours":24,"use_stale_page_cache_on_network_error":True,
             "request_retries":1,"request_timeout_seconds":1,"pause_between_requests_seconds":0}
        url="https://sport-tv-guide.live/station/test"
        p=e.sportguide_page_cache_path(url,cfg); p.write_text("old",encoding="utf-8")
        old=time.time()-90*60; os.utime(p,(old,old))
        class R:
            text="new"
            def raise_for_status(self): pass
        called={"n":0}
        def ok(*a,**k): called["n"]+=1; return R()
        e.requests.get=ok
        text,meta=e.fetch_text_resilient(url,cfg)
        assert text=="new" and meta["mode"]=="current" and meta["data_origin"]=="current"
        assert called["n"]==1
    finally:
        e.requests.get=old_get; e.BASE_DIR=old_base

# Cache older than 60m + network failure: use stale cache up to 24h.
with tempfile.TemporaryDirectory() as td:
    old_base=e.BASE_DIR; old_get=e.requests.get
    try:
        e.BASE_DIR=Path(td)
        cfg={"cache_dir":".cache/sportguide","cache_ttl_minutes":60,
             "stale_page_cache_max_age_hours":24,"use_stale_page_cache_on_network_error":True,
             "request_retries":1,"request_timeout_seconds":1,"pause_between_requests_seconds":0}
        url="https://sport-tv-guide.live/station/test"
        p=e.sportguide_page_cache_path(url,cfg); p.write_text("stale",encoding="utf-8")
        old=time.time()-90*60; os.utime(p,(old,old))
        def fail(*a,**k): raise RuntimeError("dns")
        e.requests.get=fail
        text,meta=e.fetch_text_resilient(url,cfg)
        assert text=="stale"
        assert meta["mode"]=="stale_page_cache" and meta["data_origin"]=="stale_cache"
        assert 1.4 <= meta["age_hours"] <= 1.6
    finally:
        e.requests.get=old_get; e.BASE_DIR=old_base

# Event LKG provenance remains explicit.
with tempfile.TemporaryDirectory() as td:
    old_base=e.BASE_DIR
    try:
        e.BASE_DIR=Path(td)
        cfg={"event_cache_enabled":True,"event_cache_dir":".cache/events","event_cache_max_age_hours":24}
        stamp=e.datetime.now(e.timezone.utc).isoformat()
        e.save_external_event_cache("x",[{"title":"A - B","date":"2026-09-13","time":"20:00"}],cfg,stamp,"https://x")
        events,meta=e.load_external_event_cache("x",cfg)
        assert events and events[0]["external_data_status"]=="event_lkg"
        assert meta["expired"] is False
    finally:
        e.BASE_DIR=old_base

print("v3.13 tests OK")
