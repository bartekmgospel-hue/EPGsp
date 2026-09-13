import tempfile, time, copy
from pathlib import Path
import xml.etree.ElementTree as ET
import epg_generator as e

def xml(programmes=1, cid="x"):
    parts=['<tv>',f'<channel id="{cid}"><display-name>Sport 1</display-name></channel>']
    for i in range(programmes):
        parts.append(f'<programme channel="{cid}" start="20260913{i:02d}0000 +0000" stop="20260913{i:02d}3000 +0000"><title>P{i}</title></programme>')
    parts.append('</tv>')
    return ''.join(parts).encode()

def truncated(cid="x"):
    return (f'<tv><channel id="{cid}"><display-name>Sport 1</display-name></channel>'
            f'<programme channel="{cid}" start="20260913080000 +0000" stop="20260913090000 +0000"><title>A</title></programme>'
            f'<programme channel="{cid}" start="20260913090000 +0000"><title>B</title>').encode()

base=e.BASE_DIR
orig=e.fetch_bytes
try:
    # Retry BEFORE salvage: first two malformed, third valid -> current feed must win.
    calls=[]
    payloads=[truncated(),truncated(),xml(2)]
    def fake(url,timeout=60,user_agent='x'):
        calls.append(url); return payloads.pop(0)
    e.fetch_bytes=fake
    root,st=e.load_xmltv_source('retrytest',{'url':'https://x'},
        {'source_fetch_retries':3,'source_fetch_retry_backoff_seconds':0,'source_cache_enabled':False,
         'source_salvage_truncated_xml':True,'source_salvage_after_retries':True},
        [{'channel_id':'x','name':'X','source_ids':['x']}])
    assert st['current_ok'] is True and st['salvaged'] is False and st['attempts']==3, st
    assert len(root.findall('programme'))==2

    # Fresh last-known-good is preferred over salvage after all live attempts fail.
    with tempfile.TemporaryDirectory(dir=base) as td:
        rel=str(Path(td).relative_to(base))
        settings={'source_fetch_retries':2,'source_fetch_retry_backoff_seconds':0,'source_cache_enabled':True,
                  'source_cache_dir':rel,'source_cache_max_age_hours':168,'source_salvage_truncated_xml':True,
                  'source_salvage_after_retries':True,'source_prefer_fresh_cache_before_salvage':True}
        e.save_source_cache('cachetest',xml(3),settings)
        e.fetch_bytes=lambda *a,**k: truncated()
        root,st=e.load_xmltv_source('cachetest',{'url':'https://x'},settings,[{'channel_id':'x','name':'X','source_ids':['x']}])
        assert st['used_cache'] and not st['salvaged'] and st['attempts']==2 and st['recovery_priority']=='fresh_cache', st
        assert len(root.findall('programme'))==3

    # Salvage only after all retries when no cache exists; recovery percent is reported.
    e.fetch_bytes=lambda *a,**k: truncated()
    root,st=e.load_xmltv_source('salvagetest',{'url':'https://x'},
        {'source_fetch_retries':3,'source_fetch_retry_backoff_seconds':0,'source_cache_enabled':False,
         'source_salvage_truncated_xml':True,'source_salvage_after_retries':True},
        [{'channel_id':'x','name':'X','source_ids':['x']}])
    assert st['salvaged'] and st['attempts']==3 and st['salvage_candidates']==3, st
    assert st['salvage_retained_bytes_pct'] > 0

    # Stale cache can supplement a configured channel absent from salvage.
    salvage=ET.fromstring(xml(1,'a')); cache=ET.fromstring(xml(2,'b'))
    merged,rows=e.merge_missing_required_from_cache(salvage,cache,[{'channel_id':'B','name':'B','source_ids':['b']}])
    assert rows and len([p for p in merged.findall('programme') if p.get('channel')=='b'])==2

    # Whitelisted verified fallback: empty Slovak Sport1 may use populated Polish Sport1.
    sk=ET.fromstring('<tv><channel id="Sport1.HD.sk"><display-name>Sport 1</display-name></channel></tv>')
    pl=ET.fromstring(xml(3,'Sport.1.pl'))
    ch={'name':'SK SPORT 1','id':'sport1.sk','source':'slovakia','source_ids':['Sport1.HD.sk']}
    settings={'source_prefer_nonempty_candidate':True,'source_autodiscovery_enabled':False,
              'verified_fallback_enabled':True,'verified_fallback_min_identity_score':0.95,
              'verified_fallback_min_schedule_consensus':0.90,'verified_fallback_min_same_slot_matches':20}
    whitelist=[{'channel_id':'sport1.sk','approved':True,'source':'poland','source_ids':['Sport.1.pl'],
                'evidence':{'identity_score':1.0,'schedule_consensus':0.99,'same_slot_matches':99,'schedule_verified':True}}]
    src,sid,channel,count,res=e.resolve_channel_source(ch,{'slovakia':sk,'poland':pl},settings,whitelist)
    assert src=='poland' and sid=='Sport.1.pl' and count==3 and res['mode']=='verified_fallback', (src,sid,count,res)
finally:
    e.fetch_bytes=orig

print('v3.10 tests OK')
