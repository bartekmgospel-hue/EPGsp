import epg_generator as e

HTML = """
<html><body><h1>CANAL+ Sport - Live on TV, TV listings</h1>
<a href='/station/pl-canal-sport-2'>CANAL+ Sport 2</a>
<a href='/station/pl-eleven-sports-1'>Eleven Sports 1</a>
<a href='/event/watch/123'>Team A - Team B</a>
</body></html>
"""
items=e.extract_station_catalog(HTML,'https://sport-tv-guide.live/station/pl-canal-sport','pl')
assert any(x['label']=='CANAL+ Sport 2' for x in items)
assert not any('/event/' in x['url'] for x in items)
cat={'entries':[],'channel_map':{}}
for x in items: e.catalog_add(cat,x['label'],x['url'],x.get('country'))
m=e.catalog_match_channel({'name':'PL CANAL+ SPORT 2','id':'x'},{'sportguide_country':'pl'},cat,{'catalog_min_score':0.76})
assert m and 'canal-sport-2' in m[0]['url']

strong=e.audit_external_match(.84,{'title_score':.61,'context_score':.70,'entity_overlap':2,'bonuses':['same_league'],'time_delta_minutes':20},'high',{'external_live_risky_score_below':.66,'external_live_time_tolerance_minutes':150})
assert strong['grade']=='strong'
risky=e.audit_external_match(.62,{'title_score':.2,'context_score':.25,'entity_overlap':0,'bonuses':[],'time_delta_minutes':None},'medium',{'external_live_risky_score_below':.66,'external_live_time_tolerance_minutes':150})
assert risky['grade']=='risky'

print('v3.5 tests OK')
