from datetime import datetime, timezone
import epg_generator as e

settings={
    'target_language':'pl','use_emoji':True,'add_live_prefix':True,'add_replay_prefix':True,
    'add_stage_prefix':True,'add_sport_prefix':True,'add_unknown_sport_prefix_for_live':True,
    'external_live_enrich_title_with_participants':True,'external_live_enrich_generic_only':True,
    'external_live_title_enrichment_min_score':0.68,
}
repl={}

# Morning Ekstraklasa repeat mislabeled LIVE -> suppress LIVE and mark replay.
start=datetime(2026,9,20,5,30,tzinfo=timezone.utc) # 07:30 Europe/Warsaw in DST
stop=datetime(2026,9,20,7,30,tzinfo=timezone.utc)
title,meta=e.format_title('Ekstraklasa LIVE: Legia Warszawa - Lech Poznań','',settings,repl,
                          None,channel_name='PL CANAL+ SPORT',prog_dt=start,stop_dt=stop,station_timezone='Europe/Warsaw')
assert meta['live'] is False, (title,meta)
assert meta['replay'] is True, (title,meta)
assert meta['live_morning_suppressed'] is True, (title,meta)
assert '🔴' not in title, title

# Evening same type stays LIVE.
start2=datetime(2026,9,20,18,0,tzinfo=timezone.utc) # 20:00 local
stop2=datetime(2026,9,20,20,0,tzinfo=timezone.utc)
title2,meta2=e.format_title('Ekstraklasa LIVE: Legia Warszawa - Lech Poznań','',settings,repl,
                            None,channel_name='PL CANAL+ SPORT',prog_dt=start2,stop_dt=stop2,station_timezone='Europe/Warsaw')
assert meta2['live'] is True and meta2['replay'] is False, (title2,meta2)
assert '🔴' in title2, title2

# Event-looking evening match without LIVE gets conservative inferred LIVE.
title3,meta3=e.format_title('Liga włoska: mecz: SS Lazio - AC Milan','',settings,repl,
                            None,channel_name='PL ELEVEN SPORTS 1',prog_dt=start2,stop_dt=stop2,station_timezone='Europe/Warsaw')
assert meta3['live'] is True and meta3['live_inferred'] is True, (title3,meta3)
assert '🔴' in title3, title3

# Explicit replay term always wins.
title4,meta4=e.format_title('LIVE Ekstraklasa - powtórka','',settings,repl,
                            None,channel_name='PL CANAL+ SPORT',prog_dt=start2,stop_dt=stop2,station_timezone='Europe/Warsaw')
assert meta4['live'] is False and meta4['replay'] is True, (title4,meta4)

print('v3.18 live-fix tests OK')
