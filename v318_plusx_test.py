import xml.etree.ElementTree as ET
import epg_generator as e

plusx = ET.fromstring("""
<tv>
  <channel id="px-cplus-sport"><display-name>CANAL+ SPORT</display-name></channel>
  <programme channel="px-cplus-sport" start="20260914120000 +0200" stop="20260914140000 +0200"><title>Piłka nożna: Arsenal - Manchester City</title></programme>
</tv>
""")
base = ET.fromstring("""
<tv>
  <channel id="CANAL+.Sport.HD.pl"><display-name>CANAL+ Sport HD</display-name></channel>
  <programme channel="CANAL+.Sport.HD.pl" start="20260914120000 +0200" stop="20260914140000 +0200"><title>Mecz</title></programme>
</tv>
""")
ch={
  "name":"PL CANAL+ SPORT", "id":"canalplussport.pl", "source":"poland",
  "source_ids":["CANAL+.Sport.HD.pl"],
  "priority_sources":[{"source":"poland_plusx","source_ids":["CANAL+.Sport.HD.pl"],"autodiscover":True}]
}
settings={
  "priority_source_autodiscovery_enabled":True, "source_autodiscovery_enabled":True,
  "source_autodiscovery_min_score":0.70, "source_autodiscovery_max_suggestions":5,
  "source_recommendation_brand_required":True, "source_recommendation_strict_numbers":True,
  "source_recommendation_require_critical_descriptors":True, "source_recommendation_strict_variants":True,
  "source_prefer_nonempty_candidate":True
}
source, sid, _, count, meta=e.resolve_channel_source(ch,{"poland_plusx":plusx,"poland":base},settings,[])
assert source=="poland_plusx", (source,sid,count,meta)
assert sid=="px-cplus-sport", (source,sid,count,meta)
assert count==1 and meta["mode"]=="priority_autodiscovered", meta

source2, sid2, _, count2, meta2=e.resolve_channel_source(ch,{"poland":base},settings,[])
assert source2=="poland" and sid2=="CANAL+.Sport.HD.pl" and count2==1, (source2,sid2,count2,meta2)
print("v3.18 PlusX tests OK")
