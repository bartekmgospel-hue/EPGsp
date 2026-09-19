import epg_generator as e
from datetime import datetime, timezone, timedelta
settings={'target_language':'pl','use_emoji':True,'add_live_prefix':True,'add_replay_prefix':True,'add_stage_prefix':True,'add_sport_prefix':True,'add_unknown_sport_prefix_for_live':True}
t='Piłka Nożna: PKO BP Ekstraklasa: Widzew Łódź - Wieczysta Kraków'
# No explicit LIVE and even no timestamp -> high-confidence fixture may still infer LIVE.
title,meta=e.format_title(t,'',settings,{},None,channel_name='CANAL+ SPORT',prog_dt=None,stop_dt=None,station_timezone='Europe/Warsaw')
assert meta['live'] is True and meta['live_inferred'] is True, (title,meta)
assert '🔴 LIVE' in title and '⚽' in title, title
# Morning airing remains suppressed even for this high-confidence fixture.
dt=datetime(2026,9,18,5,30,tzinfo=timezone.utc) # 07:30 Warsaw
stop=dt+timedelta(hours=2)
title2,meta2=e.format_title(t,'',settings,{},None,channel_name='CANAL+ SPORT',prog_dt=dt,stop_dt=stop,station_timezone='Europe/Warsaw')
assert meta2['live'] is False, (title2,meta2)
# Explicit replay always wins.
title3,meta3=e.format_title(t+' - powtórka','',settings,{},None,channel_name='CANAL+ SPORT',prog_dt=None,stop_dt=None,station_timezone='Europe/Warsaw')
assert meta3['live'] is False and meta3['replay'] is True, (title3,meta3)
print('v3.18 livefix2 tests: OK')
