from datetime import datetime, timezone, timedelta
import epg_generator as g

settings={
    'sofascore_enabled': True,
    'sofascore_min_match_score': 0.45,
    'sofascore_min_team_sides': 2,
    'sofascore_live_time_tolerance_minutes': 75,
    'sofascore_replay_min_delta_minutes': 180,
    'sofascore_replay_max_delta_hours': 36,
    'target_language':'pl','use_emoji':True,'add_live_prefix':True,'add_replay_prefix':True,
    'add_stage_prefix':True,'add_sport_prefix':True,'add_unknown_sport_prefix_for_live':True,
}
start=datetime(2026,9,19,18,30,tzinfo=timezone.utc)
ev={'id':1,'sport':'football','title':'Widzew Łódź - Wieczysta Kraków','home':'Widzew Łódź','away':'Wieczysta Kraków','tournament':'Ekstraklasa','start':start,'status':'notstarted','source':'sofascore'}
state={'day_cache':{('football','2026-09-18'):[],('football','2026-09-19'):[ev],('football','2026-09-20'):[]}}
text='Piłka Nożna: PKO BP Ekstraklasa: Widzew Łódź - Wieczysta Kraków'
ver=g.sofascore_verify_programme(text,start,'Europe/Warsaw','football',settings,state)
assert ver['decision']=='live', ver
out,meta=g.format_title(text,'',settings,{},None,channel_name='PL Eleven Sports 1',prog_dt=start,stop_dt=start+timedelta(hours=2),station_timezone='Europe/Warsaw',sofascore_verdict=ver)
assert meta['live'] and meta['sofascore_live'] and '🔴 LIVE' in out, (out,meta)

# Same fixture next morning = replay, even if the provider says LIVE.
replay_dt=datetime(2026,9,20,5,30,tzinfo=timezone.utc)
state2={'day_cache':{('football','2026-09-19'):[ev],('football','2026-09-20'):[],('football','2026-09-21'):[]}}
ver2=g.sofascore_verify_programme(text+' LIVE',replay_dt,'Europe/Warsaw','football',settings,state2)
assert ver2['decision']=='replay', ver2
out2,meta2=g.format_title(text+' LIVE','',settings,{},None,channel_name='PL CANAL+ SPORT',prog_dt=replay_dt,stop_dt=replay_dt+timedelta(hours=2),station_timezone='Europe/Warsaw',sofascore_verdict=ver2)
assert (not meta2['live']) and meta2['replay'] and meta2['sofascore_replay'], (out2,meta2)

# Eleven-style Serie A fixture should also match by both teams.
ev3={'id':2,'sport':'football','title':'SS Lazio - AC Milan','home':'SS Lazio','away':'AC Milan','tournament':'Serie A','start':datetime(2026,9,19,18,45,tzinfo=timezone.utc),'status':'notstarted','source':'sofascore'}
state3={'day_cache':{('football','2026-09-18'):[],('football','2026-09-19'):[ev3],('football','2026-09-20'):[]}}
ver3=g.sofascore_verify_programme('Liga włoska: mecz: SS Lazio - AC Milan',ev3['start'],'Europe/Warsaw','football',settings,state3)
assert ver3['decision']=='live', ver3
print('v3.19 Sofascore tests OK')
