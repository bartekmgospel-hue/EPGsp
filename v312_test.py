import json, os, tempfile, time
from pathlib import Path
import epg_generator as e

# Resilient stale-page fallback after network failure.
with tempfile.TemporaryDirectory() as td:
    old_base = e.BASE_DIR
    try:
        e.BASE_DIR = Path(td)
        cfg = {
            "cache_dir":".cache/sportguide",
            "cache_ttl_minutes":1,
            "stale_page_cache_max_age_hours":24,
            "use_stale_page_cache_on_network_error":True,
            "request_retries":1,
            "request_timeout_seconds":1,
            "user_agent":"test",
            "accept_language":"en",
            "pause_between_requests_seconds":0,
        }
        url="https://sport-tv-guide.live/station/test"
        p=e.sportguide_page_cache_path(url,cfg)
        p.write_text("<html><body>cached</body></html>",encoding="utf-8")
        stale=time.time()-2*3600
        os.utime(p,(stale,stale))

        old_get=e.requests.get
        def fail(*a,**k):
            raise RuntimeError("dns down")
        e.requests.get=fail
        text,meta=e.fetch_text_resilient(url,cfg)
        assert "cached" in text
        assert meta["mode"]=="stale_page_cache"
        assert meta["stale"] is True
        assert meta["network_error"]
    finally:
        e.requests.get=old_get
        e.BASE_DIR=old_base

# Event LKG preserves original timestamp and expires.
with tempfile.TemporaryDirectory() as td:
    old_base=e.BASE_DIR
    try:
        e.BASE_DIR=Path(td)
        cfg={"event_cache_enabled":True,"event_cache_dir":".cache/events","event_cache_max_age_hours":24}
        stamp=e.datetime.now(e.timezone.utc).isoformat()
        events=[{"title":"Arsenal - Liverpool","date":"2026-09-13","time":"20:00","source":"sportguide","href":"/event/1"}]
        e.save_external_event_cache("x",events,cfg,stamp,"https://example")
        loaded,meta=e.load_external_event_cache("x",cfg)
        assert len(loaded)==1
        assert loaded[0]["source"]=="sportguide-event-cache"
        assert meta["expired"] is False
    finally:
        e.BASE_DIR=old_base

# Catalog LKG must be retained and marked valid within TTL.
with tempfile.TemporaryDirectory() as td:
    old_base=e.BASE_DIR
    try:
        e.BASE_DIR=Path(td)
        cfg={"catalog_cache_file":".cache/catalog.json","catalog_lkg_max_age_hours":168}
        cat={"version":1,"updated_at_utc":e.datetime.now(e.timezone.utc).isoformat(),
             "entries":[{"label":"Sport 1","url":"https://sport-tv-guide.live/station/sport-1","country":"pl","source":"seed"}],
             "channel_map":{"sport1.pl":{"url":"https://sport-tv-guide.live/station/sport-1"}}}
        e.save_sportguide_catalog(cat,cfg,touch_timestamp=False)
        loaded=e.load_sportguide_catalog(cfg)
        assert loaded["_loaded_from_cache"] is True
        assert loaded["_cache_valid"] is True
        assert len(loaded["entries"])==1
        assert "sport1.pl" in loaded["channel_map"]
    finally:
        e.BASE_DIR=old_base

# Bootstrap copies only missing cache files from previous sibling versions.
with tempfile.TemporaryDirectory() as td:
    parent=Path(td)
    current=parent/"sports-epg-v3.12"
    prev=parent/"sports-epg-v3.11"
    current.mkdir(); (prev/".cache/sportguide").mkdir(parents=True)
    (prev/".cache/sportguide/a.html").write_text("ok")
    old_base=e.BASE_DIR
    try:
        e.BASE_DIR=current
        result=e.bootstrap_previous_version_cache({"cache_bootstrap_previous_versions":True,"cache_bootstrap_max_versions":4})
        assert result["files_copied"]==1, result
        assert (current/".cache/sportguide/a.html").exists()
    finally:
        e.BASE_DIR=old_base

print("v3.12 tests OK")
