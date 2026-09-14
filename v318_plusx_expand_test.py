import xml.etree.ElementTree as ET
import epg_generator as e

xml='''<tv>
<channel id="Sky.Sports.F1.uk"><display-name>Sky Sports F1</display-name></channel>
<channel id="BBC.One.uk"><display-name>BBC One</display-name></channel>
<channel id="ESPN.us"><display-name>ESPN</display-name></channel>
<channel id="DAZN.1.de"><display-name>DAZN 1</display-name></channel>
<channel id="NOVA.SPORT.1.cz"><display-name>NOVA SPORT 1</display-name></channel>
<channel id="JOJ.SPORT.sk"><display-name>JOJ Šport</display-name></channel>
<channel id="Sportsnet.One.ca"><display-name>Sportsnet One</display-name></channel>
<channel id="Arena.Sport.1.hr"><display-name>Arena Sport 1</display-name></channel>
<programme channel="Sky.Sports.F1.uk" start="20260914120000 +0000" stop="20260914130000 +0000"><title>Formula 1</title></programme>
<programme channel="BBC.One.uk" start="20260914120000 +0000" stop="20260914130000 +0000"><title>News</title></programme>
<programme channel="ESPN.us" start="20260914120000 +0000" stop="20260914130000 +0000"><title>SportsCenter</title></programme>
<programme channel="DAZN.1.de" start="20260914120000 +0000" stop="20260914130000 +0000"><title>Live</title></programme>
<programme channel="NOVA.SPORT.1.cz" start="20260914120000 +0000" stop="20260914130000 +0000"><title>Sport</title></programme>
<programme channel="JOJ.SPORT.sk" start="20260914120000 +0000" stop="20260914130000 +0000"><title>Sport</title></programme>
<programme channel="Sportsnet.One.ca" start="20260914120000 +0000" stop="20260914130000 +0000"><title>Hockey</title></programme>
<programme channel="Arena.Sport.1.hr" start="20260914120000 +0000" stop="20260914130000 +0000"><title>Football</title></programme>
</tv>'''
root=ET.fromstring(xml)
config={"channels":[{"name":"UK SKY SPORTS F1","id":"existing.sky.f1","source":"united_kingdom","source_ids":["Sky.Sports.F1.uk"]}]}
settings={"plusx_autoimport_enabled":True,"plusx_autoimport_global_sport":True,"plusx_autoimport_country_codes":["uk","us","de","cz","sk","ca"]}
rows,report=e.discover_plusx_channels(root,config,settings)
ids={x['id'] for x in rows}
assert 'Sky.Sports.F1.uk' not in ids
assert 'BBC.One.uk' not in ids
assert 'ESPN.us' in ids
assert 'DAZN.1.de' in ids
assert 'NOVA.SPORT.1.cz' in ids
assert 'JOJ.SPORT.sk' in ids
assert 'Sportsnet.One.ca' in ids
assert 'Arena.Sport.1.hr' in ids  # SPORT category / global sport fallback
assert report['added']==6, report
print('v3.18 PlusX expansion tests OK')
