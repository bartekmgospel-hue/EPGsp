import yaml
from pathlib import Path

cfg=yaml.safe_load(Path("channels.yaml").read_text(encoding="utf-8"))
chs={c["id"]:c for c in cfg["channels"]}
for n in range(1,8):
    cid=f"canalplusextra{n}.pl"
    assert cid in chs, cid
    c=chs[cid]
    assert c["source"]=="poland_plusx", c
    assert c.get("priority_sources"), c
    assert c["priority_sources"][0].get("autodiscover") is True, c
print("Canal+ Extra 1-7 test OK")
