import epg_generator as e
e.LEAGUE_RULES = e.load_yaml(e.LEAGUES_FILE).get("leagues", [])
from epg_generator import similarity, parse_sportguide_events, clean_external_event_text
from datetime import datetime

assert similarity(
    "Nogomet - Bundesliga: Leverkusen - Bayern",
    "Bayer Leverkusen - Bayern Munich Bundesliga"
) > 0.45

clean, t = clean_external_event_text("18:00 Tennis 18:00 Yibing Wu - Novak Djokovic ATP Wimbledon")
assert t == "18:00"
assert "Yibing Wu" in clean
assert "18:00" not in clean

sample = """
<html><body>
<h2>Live on TV - Sport TV 2</h2>
<div>12 Sep</div>
<a href="/event/1">18:00 Tennis 18:00 Yibing Wu - Novak Djokovic ATP Wimbledon</a>
<div>Sat. info - Sport TV 2</div>
</body></html>
"""
events = parse_sportguide_events(sample, datetime(2026, 9, 12))
assert events and events[0]["date"] == "2026-09-12"
assert events[0]["time"] == "18:00"
assert "Novak Djokovic" in events[0]["title"]
print("smoke tests OK")

assert e.league_from_text("Premier League: Arsenal - Liverpool")["name"] == "Premier League"

# v3.3 /event/ parser
sample_event_href = """<html><body><div>Live on TV - Test</div><section><div>12 Sep</div><a href="/event/live-football-test/123">18:00 Football 18:00 Arsenal - Liverpool Premier League</a></section><div>Sat. info - Test</div></body></html>"""
events2 = parse_sportguide_events(sample_event_href, datetime(2026,9,12))
assert events2 and events2[0]["date"] == "2026-09-12"
assert events2[0]["time"] == "18:00"
assert "Arsenal - Liverpool" in events2[0]["title"]
