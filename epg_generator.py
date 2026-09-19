#!/usr/bin/env python3
from __future__ import annotations

import copy
import gzip
import hashlib
import html
import json
import re
import shutil
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

import requests
import yaml
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "channels.yaml"
TRANSLATIONS_FILE = BASE_DIR / "translations.yaml"
OVERRIDES_FILE = BASE_DIR / "live_overrides.yaml"
LEAGUES_FILE = BASE_DIR / "leagues.yaml"
LEAGUE_RULES = []

SPORTS = [
    {"key":"football","pl":"Piłka nożna","en":"Football","emoji":"⚽",
     "terms":["piłka nożna","mecz piłkarski","nogomet","fudbal","football","soccer","premier league","la liga","serie a",
              "bundesliga","champions league","europa league","conference league","liga prvaka",
              "uefa","fifa","ekstraklasa","super liga","superliga","fotbal","futbal","labdarúgás","fodbold","fotboll","fotball","jalkapallo","futbol"]},
    {"key":"basketball","pl":"Koszykówka","en":"Basketball","emoji":"🏀",
     "terms":["koszykówka","koszykarska","košarka","kosarka","basketball","nba","euroleague","eurocup","aba liga","basket league","basketbal","kosárlabda","basketbol"]},
    {"key":"baseball","pl":"Baseball","en":"Baseball","emoji":"⚾",
     "terms":["baseball","mlb","major league baseball","world series"]},
    {"key":"american_football","pl":"Futbol amerykański","en":"American football","emoji":"🏈",
     "terms":["american football","nfl","ncaa football","college football","super bowl"]},
    {"key":"tennis","pl":"Tenis","en":"Tennis","emoji":"🎾",
     "terms":["tenis","turniej tenisowy","tennis","atp ","wta ","roland garros","wimbledon","us open","australian open"]},
    {"key":"volleyball","pl":"Siatkówka","en":"Volleyball","emoji":"🏐",
     "terms":["siatkówka","siatkarska","plusliga","tauron liga","odbojka","volleyball","cev","vnl","volejbal","röplabda","volleyboll","lentopallo","voleybol"]},
    {"key":"handball","pl":"Piłka ręczna","en":"Handball","emoji":"🤾",
     "terms":["piłka ręczna","szczypiorniak","orlen superliga","rukomet","handball","ehf","házená","hádzaná","kézilabda","håndbold","håndball","handboll","käsipallo","hentbol"]},
    {"key":"hockey","pl":"Hokej","en":"Hockey","emoji":"🏒",
     "terms":["hokej","hokej na lodzie","hockey","nhl","khl","lední hokej","ľadový hokej","jégkorong","ishockey","jääkiekko"]},
    {"key":"motorsport","pl":"Motorsport","en":"Motorsport","emoji":"🏎️",
     "terms":["formuła 1","formula 1","formula 2","formula 3","f1 ","f2 ","motogp","moto gp","wrc","nascar","indycar","motorsport"]},
    {"key":"speedway","pl":"Żużel","en":"Speedway","emoji":"🏍️",
     "terms":["żużel","zuzel","speedway","pge ekstraliga","metalkas 2. ekstraliga","metalkas 2 ekstraliga"]},
    {"key":"motocross","pl":"Motocross","en":"Motocross","emoji":"🏍️",
     "terms":["motocross","mxgp","mx2","fim motocross"]},
    {"key":"water_polo","pl":"Piłka wodna","en":"Water polo","emoji":"🤽",
     "terms":["vaterpolo","water polo"]},
    {"key":"boxing","pl":"Boks","en":"Boxing","emoji":"🥊","terms":["boks","walka bokserska","boxing"]},
    {"key":"mma","pl":"MMA","en":"MMA","emoji":"🥋","terms":["mma","ksw","ufc","pfl"]},
    {"key":"athletics","pl":"Lekkoatletyka","en":"Athletics","emoji":"🏃","terms":["lekkoatletyka","atletika","athletics","diamond league","maraton"]},
    {"key":"cycling","pl":"Kolarstwo","en":"Cycling","emoji":"🚴","terms":["kolarstwo","biciklizam","cycling","tour de france","giro d'italia","vuelta","cyklistika","cykling","sykling","pyöräily"]},
    {"key":"skiing","pl":"Narciarstwo","en":"Skiing","emoji":"⛷️","terms":["narciarstwo","skijanje","skiing","alpine ski"]},
    {"key":"darts","pl":"Dart","en":"Darts","emoji":"🎯","terms":["darts","world darts championship"]},
    {"key":"snooker","pl":"Snooker","en":"Snooker","emoji":"🎱","terms":["snooker"]},
    {"key":"golf","pl":"Golf","en":"Golf","emoji":"⛳","terms":["golf","golfe","pga","liv golf"]},
    {"key":"rugby","pl":"Rugby","en":"Rugby","emoji":"🏉","terms":["rugby","rugby union"]},
    {"key":"padel","pl":"Padel","en":"Padel","emoji":"🎾","terms":["padel","premier padel"]},
]


# v3.19: Sofascore schedule verification.  Sofascore is used as a conservative
# reference clock for real sporting events, not as a source of TV listings.
SOFASCORE_SPORT_SLUGS = {
    "football": "football",
    "basketball": "basketball",
    "tennis": "tennis",
    "volleyball": "volleyball",
    "handball": "handball",
    "hockey": "ice-hockey",
    "baseball": "baseball",
    "american_football": "american-football",
    "rugby": "rugby",
    "water_polo": "water-polo",
    "futsal": "futsal",
}

LIVE_EXPLICIT = [
    r"\buživo\b", r"\buzivo\b", r"\blive\b", r"\bdirektno\b", r"\bdirect\b",
    r"\bprijenos uživo\b", r"\bprenos uživo\b", r"\ben vivo\b", r"\bao vivo\b", r"\bživě\b", r"\bnaživo\b", r"\bélő\b", r"\bcanlı\b", r"\bsuora\b"
]
REPLAY_TERMS = [
    r"\brepriza\b", r"\bsnimka\b", r"\breplay\b", r"\brerun\b",
    r"\bponovljeno\b", r"\bhighlights\b", r"\bpregled\b", r"\brepetição\b", r"\brepeticion\b", r"\brepetición\b", r"\bwiederholung\b", r"\bherhaling\b", r"\bzáznam\b", r"\bismétlés\b", r"\btekrar\b", r"\brepris\b", r"\bgenudsendelse\b", r"\buusinta\b",
    r"\bpowt[oó]rka\b", r"\bpowt\.?\b", r"\bretransmisja\b", r"\bzapis(?: meczu| spotkania| transmisji)?\b",
    r"\barchiwum\b", r"\bpowt[oó]rzenie\b", r"\bre-live\b", r"\brecorded\b", r"\bencore\b"
]
STAGES = [
    ("final", [r"\bfinale\b", r"\bfinal\b"]),
    ("semifinal", [r"\bpolufinale\b", r"\bsemi[- ]?final\b", r"\bsemifinále\b", r"\byarı final\b"]),
    ("quarterfinal", [r"\bčetvrtfinale\b", r"\bcetvrtfinale\b", r"\bquarter[- ]?final\b", r"\b1/4\s*final", r"\bčtvrtfinále\b", r"\bçeyrek final\b"]),
    ("round16", [r"\bosmina finala\b", r"\bround of 16\b", r"\b1/8\s*final"]),
    ("qualifying", [r"\bkvalifikacije\b", r"\bqualifying\b", r"\bqualification\b"]),
]
STAGE_LABELS = {
    "pl":{"final":"FINAŁ","semifinal":"PÓŁFINAŁ","quarterfinal":"ĆWIERĆFINAŁ","round16":"1/8 FINAŁU","qualifying":"KWALIFIKACJE"},
    "en":{"final":"FINAL","semifinal":"SEMIFINAL","quarterfinal":"QUARTERFINAL","round16":"ROUND OF 16","qualifying":"QUALIFYING"},
}

STOPWORDS = {
    "the","and","of","liga","league","live","uzivo","uživo","nogomet","fudbal","kosarka","košarka",
    "tenis","tennis","mecz","match","tv","sport","sports","prijenos","prenos","hd","hr","rs"
}
MONTHS = {
    "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
    "sij":1,"velj":2,"ožu":3,"ozu":3,"tra":4,"svi":5,"lip":6,"srp":7,"kol":8,"ruj":9,"lis":10,"stu":11,"pro":12,
    "ene":1,"abr":4,"ago":8,"dic":12,"fev":2,"mai":5,"jun":6,"jul":7,"set":9,"out":10,"dez":12,
    "mrt":3,"mei":5,"okt":10,"des":12
}

def load_yaml(path: Path):
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}

def normalized(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", " ", text).strip()

def ascii_fold(text: str) -> str:
    text = normalized(text).translate(str.maketrans({
        "ł":"l", "Ł":"L", "đ":"d", "Đ":"D", "ð":"d", "Ð":"D",
        "þ":"th", "Þ":"Th", "æ":"ae", "Æ":"AE", "ø":"o", "Ø":"O",
    }))
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()

def token_set(text: str) -> set[str]:
    folded = ascii_fold(text)
    words = re.findall(r"[a-z0-9]+", folded)
    return {w for w in words if len(w) > 1 and w not in STOPWORDS}

def similarity(a: str, b: str) -> float:
    aa, bb = ascii_fold(a), ascii_fold(b)
    seq = SequenceMatcher(None, aa, bb).ratio()
    ta, tb = token_set(a), token_set(b)
    jac = len(ta & tb) / max(1, len(ta | tb))
    containment = len(ta & tb) / max(1, min(len(ta), len(tb))) if ta and tb else 0.0
    return max(seq, 0.60 * jac + 0.40 * containment)

EVENT_GENERIC_TOKENS = {
    "club","friendly","season","round","match","game","week","day","women","woman","men","man",
    "final","semifinal","quarterfinal","qualifying","qualification","championship","champion",
    "cup","super","national","international","world","open","series","tour","grand","prix",
    "fc","cf","ac","sc","afc","fk","bk","hc","bc","u19","u20","u21","u23","reserves",
    "live","sport","sports","tv","hd"
}

def participant_tokens(text: str) -> set[str]:
    """Tokens likely to represent teams, players, venues or event-specific entities."""
    toks = set(token_set(text))
    toks -= EVENT_GENERIC_TOKENS
    for sport in SPORTS:
        for term in sport.get("terms", []):
            toks -= token_set(term)
    for league in LEAGUE_RULES:
        toks -= token_set(league.get("name", ""))
        for alias in league.get("aliases", []):
            toks -= token_set(alias)
    return {t for t in toks if len(t) >= 3 and not t.isdigit()}

COUNTRY_PREFIX_RE = re.compile(
    r"^(?:HR|SR|RS|PT|BE|AT|DE|NL|CH|ES|UK|GB|IT|FR|PL|GR|RO|AU|CA|CZ|SK|HU|BG|DK|SE|NO|FI|TR|US)\s+",
    flags=re.I,
)

def strip_country_prefix(name: str) -> str:
    name = normalized(name)
    return COUNTRY_PREFIX_RE.sub("", name).strip()

def slugify_station_name(name: str) -> str:
    folded = ascii_fold(strip_country_prefix(name))
    folded = folded.replace("+", " ")
    folded = re.sub(r"\bhd\b", " ", folded)
    folded = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
    return folded

def localize_datetime(dt: datetime | None, tz_name: str | None) -> datetime | None:
    if dt is None or not tz_name or dt.tzinfo is None:
        return dt
    try:
        return dt.astimezone(ZoneInfo(tz_name))
    except Exception:
        return dt

def contains_any(text: str, patterns) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)

SPORT_STRONG_PATTERNS = [
    ("volleyball", [
        r"\bsiatkowk[aiy]\b", r"\bsiatkarsk(?:a|i|ie|iej|ich)?\b", r"\bplusliga\b", r"\btauron liga\b",
        r"\bvolleyball\b", r"\bvolley\b", r"\bcev\b", r"\bvnl\b", r"\bvolleyball nations league\b",
        r"\bodbojka\b", r"\bvolejbal\b", r"\broplabda\b", r"\bvoleybol\b", r"\blentopallo\b"
    ]),
    ("handball", [
        r"\bpilka reczna\b", r"\bszczypiorniak\b", r"\breczna\b", r"\bhandball\b", r"\behf\b",
        r"\borlen superliga\b", r"\bsuperliga kobiet\b", r"\brukomet\b", r"\bhazena\b", r"\bhadzana\b",
        r"\bkezilabda\b", r"\bhandbold\b", r"\bhandball\b", r"\bhandboll\b", r"\bkasipallo\b", r"\bhentbol\b"
    ]),
    ("basketball", [
        r"\bkoszykowk[aiy]\b", r"\bkoszykarsk(?:a|i|ie|iej|ich)?\b", r"\bbasketball\b", r"\bnba\b",
        r"\beuroleague\b", r"\beurocup\b", r"\baba liga\b", r"\bplk\b", r"\born basket liga\b"
    ]),
    ("hockey", [r"\bhokej\b", r"\bhockey\b", r"\bnhl\b", r"\bkhl\b", r"\bdel hockey\b", r"\bliiga\b", r"\bshl\b"]),
    ("tennis", [r"\btenis\b", r"\btennis\b", r"\batp\b", r"\bwta\b", r"\bwimbledon\b", r"\broland garros\b", r"\baustralian open\b", r"\bus open\b"]),
    ("american_football", [r"\bfutbol amerykanski\b", r"\bamerican football\b", r"\bnfl\b", r"\bsuper bowl\b", r"\bncaa football\b", r"\bcollege football\b"]),
    ("baseball", [r"\bbaseball\b", r"\bmlb\b", r"\bmajor league baseball\b", r"\bworld series\b"]),
    ("motorsport", [r"\bformula 1\b", r"\bformula one\b", r"\bformula 1 grand prix\b", r"\bformu[lł]a 1\b", r"\bf1\b", r"\bformula 2\b", r"\bf2\b", r"\bmotogp\b", r"\bwrc\b", r"\bnascar\b", r"\bindycar\b", r"\bmotorsport\b"]),
    ("speedway", [r"\bzuzel\b", r"\bspeedway\b", r"\bpge ekstraliga\b", r"\bmetalkas 2\.? ekstraliga\b", r"\bpolfinal ekstraligi\b", r"\bfinal ekstraligi\b"]),
    ("motocross", [r"\bmotocross\b", r"\bmotocross world\b", r"\bmxgp\b", r"\bmx2\b", r"\bfim motocross\b"]),
    ("boxing", [r"\bboks\b", r"\bboxing\b"]),
    ("mma", [r"\bmma\b", r"\bufc\b", r"\bpfl\b", r"\bksw\b"]),
    ("cycling", [r"\bkolarstw[oa]\b", r"\bcycling\b", r"\btour de france\b", r"\bgiro d[' ]?[a-z]+\b", r"\bgiro d'italia\b", r"\bvuelta\b"]),
    ("athletics", [r"\blekkoatletyk[ai]\b", r"\bathletics\b", r"\bdiamond league\b", r"\bmaraton\b", r"\bmarathon\b"]),
    ("skiing", [r"\bnarciarstwow?\b", r"\bskiing\b", r"\balpine ski\b", r"\bslalom\b"]),
    ("darts", [r"\bdart(?:s)?\b"]),
    ("snooker", [r"\bsnooker\b"]),
    ("golf", [r"\bgolf\b", r"\bpga\b", r"\bliv golf\b"]),
    ("rugby", [r"\brugby\b"]),
    ("water_polo", [r"\bpilka wodna\b", r"\bwater polo\b", r"\bvaterpolo\b"]),
    ("football", [
        r"\bpilka nozna\b", r"\bmecz pilkarski\b", r"\bfootball\b", r"\bsoccer\b", r"\bfutbol\b",
        r"\bpremier league\b", r"\bla liga\b", r"\bliga hiszpanska\b", r"\bserie a\b", r"\bliga wloska\b",
        r"\bbundesliga\b", r"\bliga niemiecka\b", r"\bliga portugalska\b", r"\bliga portugal(?: betclic)?\b", r"\bprimeira liga\b", r"\bekstraklasa\b",
        r"\bchampions league\b", r"\beuropa league\b", r"\bconference league\b", r"\buefa\b", r"\bfifa\b"
    ]),
]

def sport_from_text(text: str):
    """Deterministic sport classifier with high-signal aliases first.

    v3.18: uses word-boundary patterns and Polish competition names so sport icons are
    consistently added even when programme titles are short or already translated.
    """
    hay = ascii_fold(text or "")
    for key, patterns in SPORT_STRONG_PATTERNS:
        if any(re.search(p, hay, flags=re.I) for p in patterns):
            return next((s for s in SPORTS if s["key"] == key), None)
    # Conservative fallback to legacy aliases, now using token boundaries where possible.
    for sport in SPORTS:
        for term in sport.get("terms", []):
            folded = ascii_fold(term).strip()
            if not folded:
                continue
            if re.search(r"(?<![a-z0-9])" + re.escape(folded) + r"(?![a-z0-9])", hay, flags=re.I):
                return sport
    return None

def league_from_text(text: str):
    hay = ascii_fold(text)
    detected_sport = sport_from_text(text)
    best = None
    best_len = -1
    for league in LEAGUE_RULES:
        league_sport = league.get("sport")
        if detected_sport and league_sport and detected_sport.get("key") != league_sport:
            continue
        ambiguous_require = {
            ascii_fold(k).strip(): [ascii_fold(x) for x in v]
            for k, v in (league.get("ambiguous_alias_require_terms") or {}).items()
        }
        for alias in league.get("aliases", []):
            folded = ascii_fold(alias).strip()
            if not folded:
                continue
            if len(folded) <= 4:
                matched = re.search(r"(?<![a-z0-9])" + re.escape(folded) + r"(?![a-z0-9])", hay) is not None
            else:
                matched = folded in hay
            if not matched:
                continue
            required_terms = ambiguous_require.get(folded, [])
            if required_terms and not any(term in hay for term in required_terms):
                continue
            if len(folded) > best_len:
                best, best_len = league, len(folded)
    return best

def add_category_unique(programme: ET.Element, text: str, lang: str = "en"):
    wanted = ascii_fold(text)
    for cat in programme.findall("category"):
        if ascii_fold(cat.text or "") == wanted:
            return
    ET.SubElement(programme, "category", {"lang":lang}).text = text

def confidence_label(score: float, high_threshold: float) -> str:
    return "high" if score >= high_threshold else "medium"

def stage_from_text(text: str):
    for key, patterns in STAGES:
        if contains_any(text, patterns):
            return key
    return None

def phrase_translate(text: str, replacements: dict[str,str]) -> tuple[str,bool]:
    original = normalized(text)
    out = original
    for src, dst in sorted(replacements.items(), key=lambda kv: len(kv[0]), reverse=True):
        pat = re.compile(r"(?<!\w)" + re.escape(src) + r"(?!\w)", re.IGNORECASE)
        out = pat.sub(dst, out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out, out != original

def strip_live_words(text: str) -> str:
    out = text
    for p in LIVE_EXPLICIT:
        out = re.sub(p, "", out, flags=re.IGNORECASE)
    out = re.sub(r"\s{2,}", " ", out).strip(" |–—:-")
    return out

def parse_xmltv_datetime(value: str) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    m = re.match(r"^(\d{14})(?:\s+([+-]\d{4}))?", value)
    if not m:
        return None
    dt = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
    off = m.group(2)
    if off:
        sign = 1 if off[0] == "+" else -1
        mins = int(off[1:3]) * 60 + int(off[3:5])
        dt = dt.replace(tzinfo=timezone(sign * timedelta(minutes=mins)))
    return dt

def detect_explicit_live(text: str) -> bool:
    return (not contains_any(text, REPLAY_TERMS)) and contains_any(text, LIVE_EXPLICIT)

EUROPEAN_MORNING_REPLAY_HINTS = [
    r"\bekstraklasa\b", r"\bpko bp ekstraklasa\b", r"\b1 liga\b", r"\b2 liga\b",
    r"\bpremier league\b", r"\bla liga\b", r"\bliga hiszpa[nń]ska\b", r"\bserie a\b",
    r"\bliga w[lł]oska\b", r"\bbundesliga\b", r"\bliga niemiecka\b", r"\bligue 1\b",
    r"\bliga portugal\b", r"\bliga portugalska\b", r"\bchampions league\b",
    r"\bliga mistrz[oó]w\b", r"\beuropa league\b", r"\bliga europy\b",
    r"\bconference league\b", r"\bliga konferencji\b", r"\bpge ekstraliga\b",
    r"\bmetalkas 2\.? ekstraliga\b", r"\borlen superliga\b", r"\bplusliga\b"
]

EVENT_LIKE_TERMS = [
    r"\bmecz\b", r"\bvs\.?\b", r"\bv\.?\b", r"\s[-–—]\s", r"\bgrand prix\b",
    r"\bp[oó][lł]fina[lł]\b", r"\b[fć]wier[cć]fina[lł]\b", r"\bfina[lł]\b",
    r"\bkolejka\b", r"\bturniej\b", r"\bwy[sś]cig\b", r"\betap\b"
]

# High-confidence competition + fixture patterns. These are used when a provider does not
# explicitly tag a genuine live event. The morning replay guard still has priority.
HIGH_CONFIDENCE_LIVE_COMPETITIONS = [
    r"\bpko(?: bp)? ekstraklasa\b", r"\bekstraklasa\b",
    r"\buefa champions league\b", r"\bchampions league\b",
    r"\beuropa league\b", r"\bconference league\b",
    r"\bla liga\b", r"\bserie a\b", r"\bbundesliga\b",
    r"\bliga portugal(?: betclic)?\b", r"\bpremier league\b",
    r"\bplusliga\b", r"\borlen superliga\b", r"\bpge ekstraliga\b",
]

def high_confidence_fixture(text: str) -> bool:
    hay = ascii_fold(text or "")
    # Require a competition signal AND a real fixture-like separator / explicit match token.
    has_comp = any(re.search(p, hay, flags=re.I) for p in HIGH_CONFIDENCE_LIVE_COMPETITIONS)
    has_fixture = bool(re.search(r"\b[^:|]{2,}\s[-–—]\s[^:|]{2,}\b", text or "", flags=re.I)) or bool(re.search(r"\b(?:mecz|vs\.?|v\.?)\b", hay, flags=re.I))
    return has_comp and has_fixture

def programme_local_time(prog_dt: datetime | None, station_timezone: str | None) -> datetime | None:
    return localize_datetime(prog_dt, station_timezone) if prog_dt is not None else None

def suspicious_morning_replay(text: str, prog_dt: datetime | None, station_timezone: str | None,
                              external_match: dict | None = None) -> bool:
    """Suppress misleading LIVE labels on overnight/morning reruns of European sports.
    A confident external event match always wins over this heuristic.
    """
    if external_match is not None:
        return False
    local = programme_local_time(prog_dt, station_timezone)
    if local is None:
        return False
    hour = local.hour + local.minute / 60.0
    if not (4.0 <= hour < 10.5):
        return False
    hay = ascii_fold(text)
    return any(re.search(p, hay, flags=re.I) for p in EUROPEAN_MORNING_REPLAY_HINTS)

def infer_likely_live_event(text: str, prog_dt: datetime | None, stop_dt: datetime | None,
                            station_timezone: str | None, external_match: dict | None = None) -> bool:
    """Conservative fallback for programmes that look like a live sporting event but lack a LIVE token.
    Used mostly for Polish/local XMLTV feeds. Morning reruns are intentionally excluded.
    """
    if external_match is not None:
        return True
    if contains_any(text, REPLAY_TERMS):
        return False
    sport = sport_from_text(text)
    if not sport:
        return False
    if not contains_any(text, EVENT_LIKE_TERMS):
        return False
    local = programme_local_time(prog_dt, station_timezone)
    # Domestic/European sports are very rarely live in the early morning.
    if suspicious_morning_replay(text, prog_dt, station_timezone, None):
        return False
    # A strong competition+fixture title (e.g. "PKO BP Ekstraklasa: Widzew Łódź - Wieczysta Kraków")
    # may be safely inferred even when the XMLTV feed omits a usable start timestamp.
    if local is None:
        return high_confidence_fixture(text)
    hour = local.hour + local.minute / 60.0
    earliest = {
        "football": 10.5, "volleyball": 9.5, "handball": 9.5, "speedway": 10.0,
        "motorsport": 7.0, "motocross": 7.0, "cycling": 8.0, "tennis": 7.0,
        "basketball": 9.0, "hockey": 9.0,
    }.get(sport.get("key"), 8.0)
    if hour < earliest or hour >= 24.0:
        return False
    if stop_dt is not None and prog_dt is not None:
        try:
            dur = (stop_dt - prog_dt).total_seconds() / 60.0
            if dur < 30 or dur > 360:
                return False
        except Exception:
            pass
    return True


def sofascore_cache_path(sport_slug: str, date_str: str, settings: dict) -> Path:
    cache_dir = BASE_DIR / settings.get("sofascore_cache_dir", ".cache/sofascore")
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{sport_slug}-{date_str}.json"


def _sofascore_read_cache(path: Path, max_age_hours: float | None = None) -> dict | None:
    try:
        if not path.exists():
            return None
        if max_age_hours is not None:
            age_h = (time.time() - path.stat().st_mtime) / 3600.0
            if age_h > max_age_hours:
                return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def sofascore_fetch_day(sport_key: str, date_str: str, settings: dict, state: dict) -> list[dict]:
    """Fetch/cached scheduled events for one sport/day. Network failures are non-fatal."""
    slug = SOFASCORE_SPORT_SLUGS.get(sport_key)
    if not slug or not settings.get("sofascore_enabled", True):
        return []
    cache_key = (slug, date_str)
    if cache_key in state.setdefault("day_cache", {}):
        return state["day_cache"][cache_key]

    path = sofascore_cache_path(slug, date_str, settings)
    fresh_h = float(settings.get("sofascore_cache_max_age_hours", 6.0))
    stale_h = float(settings.get("sofascore_stale_cache_max_age_hours", 48.0))
    payload = _sofascore_read_cache(path, fresh_h)
    origin = "fresh-cache" if payload else None
    url_tpl = settings.get("sofascore_api_url", "https://www.sofascore.com/api/v1/sport/{sport}/scheduled-events/{date}")
    url = url_tpl.format(sport=slug, date=date_str)

    if payload is None:
        try:
            r = requests.get(url, timeout=int(settings.get("sofascore_timeout_seconds", 20)), headers={
                "User-Agent": settings.get("sofascore_user_agent", "Mozilla/5.0 (compatible; SportsEPG/3.19)"),
                "Accept": "application/json,text/plain,*/*",
            })
            r.raise_for_status()
            payload = r.json()
            if not isinstance(payload, dict):
                raise ValueError("unexpected JSON")
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            origin = "network"
            state["requests_ok"] = state.get("requests_ok", 0) + 1
        except Exception as exc:
            state["requests_failed"] = state.get("requests_failed", 0) + 1
            state.setdefault("errors", []).append({"sport": sport_key, "date": date_str, "error": str(exc)[:240]})
            payload = _sofascore_read_cache(path, stale_h)
            if payload:
                origin = "stale-cache"
                state["stale_cache_hits"] = state.get("stale_cache_hits", 0) + 1

    rows = []
    for ev in (payload or {}).get("events", []) or []:
        try:
            ts = ev.get("startTimestamp")
            if ts is None:
                continue
            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            home = ((ev.get("homeTeam") or {}).get("name") or "").strip()
            away = ((ev.get("awayTeam") or {}).get("name") or "").strip()
            name = (ev.get("name") or "").strip()
            title = f"{home} - {away}" if home and away else name
            tournament = (((ev.get("tournament") or {}).get("name")) or "").strip()
            rows.append({
                "id": ev.get("id"), "sport": sport_key, "title": title,
                "home": home, "away": away, "tournament": tournament,
                "start": dt, "status": ((ev.get("status") or {}).get("type") or ""),
                "source": "sofascore", "source_url": url, "origin": origin,
            })
        except Exception:
            continue
    state["day_cache"][cache_key] = rows
    state["events_loaded"] = state.get("events_loaded", 0) + len(rows)
    return rows


def _team_tokens(text: str) -> set[str]:
    stop = {"fc","cf","ac","sc","ks","rks","mks","ssa","club","klub","the","team","women","men","u19","u20","u21","u23"}
    toks = [x for x in re.findall(r"[a-z0-9]+", ascii_fold(text or "")) if len(x) >= 3 and x not in stop]
    return set(toks)


def _sofascore_event_title_score(programme_text: str, event: dict) -> tuple[float, int]:
    hay = ascii_fold(programme_text or "")
    pt = _team_tokens(hay)
    home_t = _team_tokens(event.get("home", ""))
    away_t = _team_tokens(event.get("away", ""))
    all_t = home_t | away_t
    overlap = len(pt & all_t)
    # Require evidence from both sides when possible; protects against common club names.
    sides = int(bool(pt & home_t)) + int(bool(pt & away_t))
    seq = SequenceMatcher(None, ascii_fold(event.get("title", "")), hay).ratio()
    token_score = overlap / max(2, min(max(len(all_t), 1), 6))
    return min(1.0, 0.72 * token_score + 0.28 * seq), sides


def sofascore_verify_programme(text: str, prog_dt: datetime | None, station_timezone: str | None,
                               sport_key: str | None, settings: dict, state: dict) -> dict:
    """Return confirmed/replay/no-evidence decision by matching programme to Sofascore event clock."""
    out = {"decision": "none", "score": 0.0, "event": None, "time_delta_minutes": None, "reason": ""}
    if not prog_dt or not sport_key or sport_key not in SOFASCORE_SPORT_SLUGS or not settings.get("sofascore_enabled", True):
        return out
    # Only fixture-like programmes are safe to verify.
    if not contains_any(text, EVENT_LIKE_TERMS):
        return out
    local = programme_local_time(prog_dt, station_timezone) or prog_dt
    dates = [(local.date() + timedelta(days=d)).isoformat() for d in (-1, 0, 1)]
    candidates = []
    for ds in dates:
        candidates.extend(sofascore_fetch_day(sport_key, ds, settings, state))
    if not candidates:
        return out

    best = None
    for ev in candidates:
        score, sides = _sofascore_event_title_score(text, ev)
        if sides < int(settings.get("sofascore_min_team_sides", 2)):
            continue
        delta = abs((prog_dt.astimezone(timezone.utc) - ev["start"]).total_seconds()) / 60.0
        # Prefer team identity first, then temporal closeness.
        rank = score * 100.0 - min(delta, 1440.0) / 180.0
        if best is None or rank > best[0]:
            best = (rank, score, sides, delta, ev)
    if best is None:
        return out
    _, score, sides, delta, ev = best
    out.update({"score": round(score, 3), "event": ev, "time_delta_minutes": round(delta, 1)})
    min_score = float(settings.get("sofascore_min_match_score", 0.52))
    live_tol = float(settings.get("sofascore_live_time_tolerance_minutes", 75))
    replay_delta = float(settings.get("sofascore_replay_min_delta_minutes", 180))
    replay_window = float(settings.get("sofascore_replay_max_delta_hours", 36)) * 60.0
    if score >= min_score and delta <= live_tol:
        out.update({"decision": "live", "reason": "matched_event_time"})
    elif score >= min_score and replay_delta <= delta <= replay_window:
        out.update({"decision": "replay", "reason": "same_fixture_different_time"})
    return out


def fetch_bytes(url: str, timeout: int = 60, user_agent: str = "SportsEPG-v2/2.0") -> bytes:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": user_agent})
    r.raise_for_status()
    data = r.content
    if url.lower().endswith(".gz") or data[:2] == b"\x1f\x8b":
        return gzip.decompress(data)
    return data

def salvage_truncated_xmltv(data: bytes) -> tuple[ET.Element | None, bytes | None, str | None]:
    try:
        text = data.decode("utf-8", errors="replace")
    except Exception as exc:
        return None, None, f"decode failed: {exc}"
    tv_pos = text.find("<tv")
    if tv_pos < 0:
        return None, None, "missing <tv root"
    text = text[tv_pos:]
    cut = text.rfind("</programme>")
    if cut >= 0:
        cut += len("</programme>")
    else:
        cut = text.rfind("</channel>")
        if cut >= 0:
            cut += len("</channel>")
    if cut < 0:
        return None, None, "no complete channel/programme boundary"
    candidate = (text[:cut] + "\n</tv>\n").encode("utf-8")
    try:
        root = ET.fromstring(candidate)
        return root, candidate, None
    except Exception as exc:
        return None, None, str(exc)

def source_cache_file(name: str, settings: dict) -> Path:
    cache_dir = BASE_DIR / settings.get("source_cache_dir", ".cache/xmltv_sources")
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", name)
    return cache_dir / f"{safe}.xml"

def load_source_cache(name: str, settings: dict, allow_stale: bool = False):
    path = source_cache_file(name, settings)
    if not path.exists():
        return None, None
    age_hours = max(0.0, (time.time() - path.stat().st_mtime) / 3600.0)
    max_age = float(settings.get("source_cache_max_age_hours", 168))
    if age_hours > max_age and not allow_stale:
        return None, age_hours
    try:
        root = ET.fromstring(path.read_bytes())
        return root, age_hours
    except Exception:
        return None, age_hours

def save_source_cache(name: str, xml_bytes: bytes, settings: dict):
    if not settings.get("source_cache_enabled", True):
        return
    path = source_cache_file(name, settings)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(xml_bytes)
    ET.fromstring(tmp.read_bytes())
    tmp.replace(path)

def source_programme_counts(root: ET.Element) -> dict[str,int]:
    counts=defaultdict(int)
    for p in root.findall("programme"):
        cid=p.get("channel")
        if cid: counts[cid]+=1
    return dict(counts)

def required_source_groups(config: dict, source_name: str) -> list[dict]:
    rows=[]
    for ch in config.get("channels", []):
        if ch.get("source") == source_name:
            rows.append({"channel_id":ch.get("id"), "name":ch.get("name"), "source_ids":list(ch.get("source_ids") or [])})
        for fb in ch.get("fallback_sources", []) or []:
            if fb.get("source") == source_name:
                rows.append({"channel_id":ch.get("id"), "name":ch.get("name"), "source_ids":list(fb.get("source_ids") or [])})
    return rows

def configured_group_coverage(root: ET.Element, required_groups: list[dict]) -> dict:
    counts=source_programme_counts(root)
    covered=[]; empty=[]; missing=[]
    channel_ids={x.get("id") for x in root.findall("channel")}
    for group in required_groups:
        ids=group.get("source_ids") or []
        populated=[cid for cid in ids if counts.get(cid,0)>0]
        existing=[cid for cid in ids if cid in channel_ids]
        row={"channel_id":group.get("channel_id"),"name":group.get("name"),"source_ids":ids}
        if populated:
            row["matched_source_id"]=max(populated,key=lambda x:counts.get(x,0)); row["programmes"]=counts[row["matched_source_id"]]; covered.append(row)
        elif existing:
            row["matched_source_id"]=existing[0]; row["programmes"]=0; empty.append(row)
        else:
            missing.append(row)
    total=len(required_groups)
    return {
        "configured_groups_total":total,
        "configured_groups_with_programmes":len(covered),
        "configured_groups_empty":len(empty),
        "configured_groups_missing":len(missing),
        "configured_coverage_pct":round(100.0*len(covered)/max(1,total),1),
        "empty_channels":empty,
        "missing_channels":missing,
    }

def source_recovery_retention_metrics(recovered_root: ET.Element, baseline_root: ET.Element | None) -> dict:
    if baseline_root is None:
        return {
            "salvage_channel_retention_pct": None,
            "salvage_programme_retention_estimate_pct": None,
            "baseline_channels": None,
            "baseline_programmes": None,
        }
    rc=len(recovered_root.findall("channel")); rp=len(recovered_root.findall("programme"))
    bc=len(baseline_root.findall("channel")); bp=len(baseline_root.findall("programme"))
    return {
        "salvage_channel_retention_pct": round(min(100.0, 100.0*rc/max(1,bc)),1),
        "salvage_programme_retention_estimate_pct": round(min(100.0, 100.0*rp/max(1,bp)),1),
        "baseline_channels": bc,
        "baseline_programmes": bp,
    }

def decorate_source_health(status: dict, settings: dict) -> dict:
    status = dict(status or {})
    cov = status.get("coverage") or {}
    pct = float(cov.get("configured_coverage_pct", 0.0) or 0.0)
    threshold = float(settings.get("source_degraded_configured_coverage_threshold_pct", 90.0))
    status["configured_channel_coverage_pct"] = pct
    status["coverage_threshold_pct"] = threshold
    status["degraded"] = False
    status["degraded_reason"] = None
    status["coverage_warning"] = False
    if not status.get("ok"):
        status["health"] = "unavailable"
        status["degraded"] = True
        status["degraded_reason"] = "source_unavailable"
    elif status.get("current_ok"):
        # A current feed can legitimately contain zero-programme channels. Warn, but do not
        # call the entire country feed degraded just because selected channels are empty.
        if pct < threshold and int(cov.get("configured_groups_total",0)) > 0:
            status["health"] = "healthy_with_gaps"
            status["coverage_warning"] = True
        else:
            status["health"] = "healthy"
    else:
        if pct < threshold:
            status["health"] = "degraded"
            status["degraded"] = True
            status["degraded_reason"] = f"recovered_feed_configured_coverage_below_{threshold:g}_pct"
        else:
            status["health"] = "recovered"
    return status

def channel_lkg_file(channel_id: str, settings: dict) -> Path:
    cache_dir = BASE_DIR / settings.get("channel_lkg_dir", ".cache/channel_lkg")
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", channel_id)
    return cache_dir / f"{safe}.xml"

def save_channel_lkg(ch_cfg: dict, source_name: str | None, source_id: str | None,
                     source_channel: ET.Element | None, programmes: list[ET.Element], settings: dict):
    if not settings.get("channel_lkg_enabled", True):
        return
    if len(programmes) < int(settings.get("channel_lkg_min_programmes",1)):
        return
    root=ET.Element("tv", {
        "logical_channel_id":str(ch_cfg.get("id") or ""),
        "logical_channel_name":str(ch_cfg.get("name") or ""),
        "source_name":str(source_name or ""),
        "source_id":str(source_id or ""),
        "saved_at_utc":datetime.now(timezone.utc).isoformat(),
    })
    if source_channel is not None:
        root.append(copy.deepcopy(source_channel))
    elif source_id:
        ch=ET.SubElement(root,"channel",{"id":source_id})
        ET.SubElement(ch,"display-name").text=ch_cfg.get("name", source_id)
    for p in programmes:
        root.append(copy.deepcopy(p))
    path=channel_lkg_file(ch_cfg.get("id","channel"),settings)
    tmp=path.with_suffix(path.suffix+".tmp")
    ET.ElementTree(root).write(tmp,encoding="utf-8",xml_declaration=True)
    ET.fromstring(tmp.read_bytes())
    tmp.replace(path)

def load_channel_lkg(ch_cfg: dict, settings: dict) -> tuple[ET.Element | None, dict]:
    path=channel_lkg_file(ch_cfg.get("id","channel"),settings)
    if not path.exists():
        return None,{"available":False,"reason":"not_cached"}
    age=max(0.0,(time.time()-path.stat().st_mtime)/3600.0)
    max_age=float(settings.get("channel_lkg_max_age_hours",48))
    if age > max_age:
        return None,{"available":False,"reason":"cache_too_old","age_hours":round(age,2)}
    try:
        root=ET.fromstring(path.read_bytes())
    except Exception as exc:
        return None,{"available":False,"reason":"cache_parse_error","error":str(exc),"age_hours":round(age,2)}
    grace=float(settings.get("channel_lkg_recent_grace_hours",6))
    cutoff=datetime.now(timezone.utc)-timedelta(hours=grace)
    keep=[]
    for p in root.findall("programme"):
        dt=parse_xmltv_datetime(p.get("stop","") or p.get("start",""))
        if dt is None:
            continue
        if dt.tzinfo is None:
            dt=dt.replace(tzinfo=timezone.utc)
        else:
            dt=dt.astimezone(timezone.utc)
        if dt >= cutoff:
            keep.append(p)
    if not keep:
        return None,{"available":False,"reason":"no_recent_programmes","age_hours":round(age,2)}
    out=ET.Element("tv",dict(root.attrib))
    for ch in root.findall("channel"):
        out.append(copy.deepcopy(ch))
    for p in keep:
        out.append(copy.deepcopy(p))
    return out,{
        "available":True,"age_hours":round(age,2),"programmes":len(keep),
        "cached_source":root.get("source_name"),"cached_source_id":root.get("source_id"),
        "saved_at_utc":root.get("saved_at_utc"),
    }

def load_recommendation_history(settings: dict) -> dict:
    path=BASE_DIR/settings.get("recommendation_history_file",".cache/recommendation_history.json")
    if not path.exists():
        return {"version":"3.18","items":{}}
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data,dict): raise ValueError("history is not an object")
        data.setdefault("items",{})
        return data
    except Exception:
        return {"version":"3.18","items":{}}

def save_recommendation_history(history: dict, settings: dict):
    path=BASE_DIR/settings.get("recommendation_history_file",".cache/recommendation_history.json")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(history,ensure_ascii=False,indent=2),encoding="utf-8")

def update_recommendation_history(report: dict, settings: dict) -> tuple[dict,list[dict]]:
    history=load_recommendation_history(settings)
    items=history.setdefault("items",{})
    max_builds=int(settings.get("recommendation_history_max_builds",12))
    generated=report.get("generated_at_utc")
    for ch in report.get("channels",[]):
        for rec in ch.get("cross_source_recommendations",[]) or []:
            key="|".join([str(ch.get("id")),str(rec.get("source")),str(rec.get("source_id"))])
            arr=items.setdefault(key,[])
            row={
                "generated_at_utc":generated,"channel_id":ch.get("id"),"channel_name":ch.get("name"),
                "source":rec.get("source"),"source_id":rec.get("source_id"),"label":rec.get("label"),
                "identity_score":float(rec.get("score",0.0) or 0.0),
                "schedule_consensus":float(rec.get("schedule_consensus_max",0.0) or 0.0),
                "same_slot_matches":int(rec.get("schedule_consensus_same_slot_matched",0) or 0),
                "repeat_matches":int(rec.get("schedule_consensus_repeat_matched",0) or 0),
                "evidence_slots":int(rec.get("schedule_consensus_evidence",0) or 0),
            }
            if not arr or arr[-1].get("generated_at_utc") != generated:
                arr.append(row)
            items[key]=arr[-max_builds:]
    history["version"]="3.11"; history["updated_at_utc"]=generated
    save_recommendation_history(history,settings)

    required=int(settings.get("recommendation_history_required_builds",3))
    min_cons=float(settings.get("recommendation_history_min_consensus",0.60))
    min_identity=float(settings.get("recommendation_history_min_identity_score",0.95))
    min_slots=int(settings.get("recommendation_history_min_same_slot_matches",20))
    candidates=[]
    for key,arr in items.items():
        if len(arr) < required:
            continue
        recent=arr[-required:]
        if all(x.get("identity_score",0)>=min_identity and x.get("schedule_consensus",0)>=min_cons and x.get("same_slot_matches",0)>=min_slots for x in recent):
            latest=recent[-1]
            candidates.append({
                "channel_id":latest.get("channel_id"),"channel_name":latest.get("channel_name"),
                "source":latest.get("source"),"source_id":latest.get("source_id"),"label":latest.get("label"),
                "consecutive_qualifying_builds":required,"observations":recent,
                "promotion_ready":True,"auto_apply":False,
            })
    candidates.sort(key=lambda x:(x["channel_id"] or "",x["source"] or "",x["source_id"] or ""))
    return history,candidates

def merge_missing_required_from_cache(salvaged_root: ET.Element, cache_root: ET.Element, required_groups: list[dict]):
    salv_counts=source_programme_counts(salvaged_root)
    cache_counts=source_programme_counts(cache_root)
    salv_channels={x.get("id"):x for x in salvaged_root.findall("channel")}
    cache_channels={x.get("id"):x for x in cache_root.findall("channel")}
    supplemented=[]
    for group in required_groups:
        ids=group.get("source_ids") or []
        if any(salv_counts.get(cid,0)>0 for cid in ids):
            continue
        candidates=[cid for cid in ids if cache_counts.get(cid,0)>0]
        if not candidates:
            continue
        cid=max(candidates,key=lambda x:cache_counts.get(x,0))
        if cid not in salv_channels and cid in cache_channels:
            salvaged_root.append(copy.deepcopy(cache_channels[cid]))
            salv_channels[cid]=True
        n=0
        for p in cache_root.findall("programme"):
            if p.get("channel") == cid:
                salvaged_root.append(copy.deepcopy(p)); n+=1
        if n:
            supplemented.append({"channel_id":group.get("channel_id"),"name":group.get("name"),"source_id":cid,"programmes_added":n})
    return salvaged_root, supplemented

def load_xmltv_source(name: str, src: dict, settings: dict, required_groups: list[dict] | None = None) -> tuple[ET.Element | None, dict]:
    required_groups = required_groups or []
    urls = [src.get("url")] + list(src.get("fallback_urls") or [])
    urls = [u for u in urls if u]
    retries = max(1, int(settings.get("source_fetch_retries", 3)))
    backoff = float(settings.get("source_fetch_retry_backoff_seconds", 2.0))
    timeout = int(settings.get("source_request_timeout_seconds", 75))
    salvage_enabled = bool(settings.get("source_salvage_truncated_xml", True))
    errors=[]; attempts=0; salvage_candidates=[]

    # v3.10: all retries and fallback URLs are exhausted BEFORE salvage is accepted.
    for url in urls:
        for attempt in range(1, retries+1):
            attempts += 1
            try:
                data=fetch_bytes(url, timeout=timeout, user_agent="SportsEPG-v3.11/3.11")
                try:
                    root=ET.fromstring(data)
                    save_source_cache(name,data,settings)
                    cov=configured_group_coverage(root,required_groups)
                    return root, {
                        "ok":True,"current_ok":True,"used_cache":False,"salvaged":False,"attempts":attempts,
                        "url_used":url,"cache_age_hours":0.0,"errors":errors,"fallback_url_used":url != src.get("url"),
                        "salvage_available":bool(salvage_candidates),"recovery_priority":"current","coverage":cov,
                    }
                except Exception as parse_exc:
                    errors.append(f"{url} attempt {attempt}: parse: {parse_exc}")
                    if salvage_enabled:
                        sr,sbytes,serr=salvage_truncated_xmltv(data)
                        if sr is not None and sbytes is not None:
                            pct=round(100.0*len(sbytes)/max(1,len(data)),2)
                            salvage_candidates.append({
                                "root":sr,"bytes":sbytes,"url":url,"attempt":attempt,"retained_bytes_pct":pct,
                                "channels":len(sr.findall('channel')),"programmes":len(sr.findall('programme')),
                                "coverage":configured_group_coverage(sr,required_groups),
                            })
                        elif serr:
                            errors.append(f"{url} attempt {attempt}: salvage: {serr}")
            except Exception as exc:
                errors.append(f"{url} attempt {attempt}: fetch: {exc}")
            if attempt < retries and backoff > 0:
                time.sleep(backoff*attempt)

    # Priority after all live attempts: fresh LKG cache -> salvage -> stale cache.
    if settings.get("source_cache_enabled", True) and settings.get("source_prefer_fresh_cache_before_salvage", True):
        cache_root,age=load_source_cache(name,settings,allow_stale=False)
        if cache_root is not None:
            return cache_root, {
                "ok":True,"current_ok":False,"used_cache":True,"salvaged":False,"attempts":attempts,
                "url_used":None,"cache_age_hours":round(age,2),"errors":errors,"cache_stale":False,
                "salvage_available":bool(salvage_candidates),"recovery_priority":"fresh_cache",
                "coverage":configured_group_coverage(cache_root,required_groups),
            }

    if salvage_candidates and settings.get("source_salvage_after_retries", True):
        best=max(salvage_candidates,key=lambda x:(x["retained_bytes_pct"],x["programmes"]))
        root=best["root"]; supplemented=[]; cache_age=None
        # A stale LKG can supplement only configured channels with zero programmes in salvage.
        baseline_root=None
        if settings.get("source_cache_enabled", True) and settings.get("source_salvage_merge_stale_cache_missing_channels", True):
            cache_root,age=load_source_cache(name,settings,allow_stale=True)
            baseline_root=cache_root
            cache_age=age
            if cache_root is not None:
                root,supplemented=merge_missing_required_from_cache(root,cache_root,required_groups)
        retention=source_recovery_retention_metrics(root,baseline_root)
        cov=configured_group_coverage(root,required_groups)
        return root, {
            "ok":True,"current_ok":False,"used_cache":bool(supplemented),"salvaged":True,"attempts":attempts,
            "url_used":best["url"],"cache_age_hours":round(cache_age,2) if cache_age is not None else None,
            "errors":errors,"salvage_retained_bytes_pct":best["retained_bytes_pct"],
            "salvage_channels":best["channels"],"salvage_programmes":best["programmes"],
            "salvage_candidates":len(salvage_candidates),"cache_supplemented_channels":supplemented,
            **retention,
            "recovery_priority":"salvage" + ("+stale_cache_merge" if supplemented else ""),"coverage":cov,
        }

    if settings.get("source_cache_enabled", True) and settings.get("source_cache_use_stale_if_all_fail", True):
        cache_root,age=load_source_cache(name,settings,allow_stale=True)
        if cache_root is not None:
            return cache_root, {
                "ok":True,"current_ok":False,"used_cache":True,"salvaged":False,"attempts":attempts,
                "url_used":None,"cache_age_hours":round(age,2),"cache_stale":True,"errors":errors,
                "salvage_available":False,"recovery_priority":"stale_cache",
                "coverage":configured_group_coverage(cache_root,required_groups),
            }

    return None, {"ok":False,"current_ok":False,"used_cache":False,"salvaged":False,"attempts":attempts,
                  "url_used":None,"cache_age_hours":None,"errors":errors,"recovery_priority":"unavailable",
                  "coverage":configured_group_coverage(ET.Element('tv'),required_groups)}

def bootstrap_previous_version_cache(settings: dict) -> dict:
    """Import missing generated cache files from nearby previous version folders.

    This matters for users who unzip each version into a new sibling directory.
    Files are copied only when the current cache path is missing, and mtimes are preserved.
    """
    result = {"enabled": bool(settings.get("cache_bootstrap_previous_versions", True)),
              "files_copied": 0, "source_dirs": []}
    if not result["enabled"]:
        return result
    parent = BASE_DIR.parent
    current_cache = BASE_DIR / ".cache"
    current_cache.mkdir(parents=True, exist_ok=True)

    def verkey(path: Path):
        m = re.search(r"v(\d+)\.(\d+)(?:\.(\d+))?", path.name)
        return tuple(int(x or 0) for x in m.groups()) if m else (0,0,0)

    candidates = [
        p for p in parent.iterdir()
        if p.is_dir() and p != BASE_DIR and re.match(r"^sports-epg-v3\.\d+", p.name)
        and (p / ".cache").exists()
    ]
    candidates.sort(key=verkey, reverse=True)
    max_versions = int(settings.get("cache_bootstrap_max_versions", 4))
    for cand in candidates[:max_versions]:
        copied_here = 0
        src_cache = cand / ".cache"
        for p in src_cache.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(src_cache)
            target = current_cache / rel
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
            copied_here += 1
        if copied_here:
            result["files_copied"] += copied_here
            result["source_dirs"].append({"path": str(cand), "files_copied": copied_here})
    return result

def sportguide_page_cache_path(url: str, external_cfg: dict) -> Path:
    cache_dir = BASE_DIR / external_cfg.get("cache_dir", ".cache/sportguide")
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()[:24] + ".html"
    return cache_dir / key

def fetch_text_resilient(url: str, external_cfg: dict) -> tuple[str, dict]:
    cache = sportguide_page_cache_path(url, external_cfg)
    now = time.time()
    ttl = int(external_cfg.get("cache_ttl_minutes", 120)) * 60
    if cache.exists():
        age = max(0.0, now - cache.stat().st_mtime)
        if age < ttl:
            return cache.read_text(encoding="utf-8", errors="replace"), {
                "mode":"fresh_page_cache", "data_origin":"fresh_cache", "cached":True, "stale":False,
                "age_hours":round(age/3600.0,3),
                "fetched_at_utc":datetime.fromtimestamp(cache.stat().st_mtime, timezone.utc).isoformat(),
                "network_attempts":0, "network_error":None,
            }

    timeout = int(external_cfg.get("request_timeout_seconds", 30))
    headers = {
        "User-Agent": external_cfg.get("user_agent", "Mozilla/5.0 SportsEPG/3.14"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": external_cfg.get("accept_language", "en-US,en;q=0.9"),
        "Cache-Control": "no-cache",
    }
    retries = max(1, int(external_cfg.get("request_retries", 2)))
    backoff = float(external_cfg.get("request_retry_backoff_seconds", 0.5))
    last_exc = None
    for attempt in range(1, retries+1):
        try:
            r = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
            r.raise_for_status()
            cache.write_text(r.text, encoding="utf-8")
            pause = float(external_cfg.get("pause_between_requests_seconds", 0.35))
            if pause:
                time.sleep(pause)
            return r.text, {
                "mode":"current", "data_origin":"current", "cached":False, "stale":False,
                "age_hours":0.0, "fetched_at_utc":datetime.now(timezone.utc).isoformat(),
                "network_attempts":attempt, "network_error":None,
            }
        except Exception as exc:
            last_exc = exc
            if attempt < retries and backoff > 0:
                time.sleep(backoff * attempt)

    if external_cfg.get("use_stale_page_cache_on_network_error", True) and cache.exists():
        age = max(0.0, now - cache.stat().st_mtime)
        max_age = float(external_cfg.get("stale_page_cache_max_age_hours", 24)) * 3600
        if age <= max_age:
            return cache.read_text(encoding="utf-8", errors="replace"), {
                "mode":"stale_page_cache", "data_origin":"stale_cache", "cached":True, "stale":True,
                "age_hours":round(age/3600.0,3),
                "fetched_at_utc":datetime.fromtimestamp(cache.stat().st_mtime, timezone.utc).isoformat(),
                "network_attempts":retries, "network_error":str(last_exc),
            }
    raise last_exc if last_exc is not None else RuntimeError(f"Unable to fetch {url}")

def fetch_text_cached(url: str, external_cfg: dict) -> str:
    text, _ = fetch_text_resilient(url, external_cfg)
    return text

def external_event_cache_file(channel_id: str, external_cfg: dict) -> Path:
    cache_dir = BASE_DIR / external_cfg.get("event_cache_dir", ".cache/sportguide_events")
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", channel_id)
    return cache_dir / f"{safe}.json"

def save_external_event_cache(channel_id: str, events: list[dict], external_cfg: dict,
                              fetched_at_utc: str | None = None, source_url: str | None = None):
    if not external_cfg.get("event_cache_enabled", True) or not events:
        return
    clean = []
    for ev in events:
        row = {k:v for k,v in ev.items() if not str(k).startswith("_")}
        row["source"] = "sportguide-event-cache"
        clean.append(row)
    payload = {
        "version":1,
        "channel_id":channel_id,
        "updated_at_utc":fetched_at_utc or datetime.now(timezone.utc).isoformat(),
        "source_url":source_url,
        "events":clean,
    }
    path = external_event_cache_file(channel_id, external_cfg)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def load_external_event_cache(channel_id: str, external_cfg: dict) -> tuple[list[dict], dict | None]:
    if not external_cfg.get("event_cache_enabled", True):
        return [], None
    path = external_event_cache_file(channel_id, external_cfg)
    if not path.exists():
        return [], None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        updated = datetime.fromisoformat(payload.get("updated_at_utc"))
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - updated.astimezone(timezone.utc)).total_seconds()/3600.0
        max_h = float(external_cfg.get("event_cache_max_age_hours", 24))
        if age_h < 0 or age_h > max_h:
            return [], {"expired":True,"age_hours":round(age_h,3),"path":str(path)}
        events = []
        for ev in payload.get("events", []):
            row = dict(ev)
            row["source"] = "sportguide-event-cache"
            row["external_data_status"] = "event_lkg"
            events.append(row)
        return events, {
            "expired":False,"age_hours":round(age_h,3),"path":str(path),
            "updated_at_utc":payload.get("updated_at_utc"),"source_url":payload.get("source_url"),
        }
    except Exception as exc:
        return [], {"error":str(exc),"path":str(path)}


def parse_date_label(text: str, reference: datetime) -> datetime.date | None:
    t = ascii_fold(text).replace(".", " ")
    m = re.search(r"\b(\d{1,2})\s+([a-z]{3,5})\b", t)
    if not m:
        return None
    day, mon = int(m.group(1)), m.group(2)[:3]
    month = MONTHS.get(mon)
    if not month:
        return None
    year = reference.year
    try:
        d = datetime(year, month, day).date()
    except ValueError:
        return None
    # year rollover heuristic
    if (d - reference.date()).days > 180:
        d = datetime(year - 1, month, day).date()
    elif (reference.date() - d).days > 180:
        d = datetime(year + 1, month, day).date()
    return d

def clean_external_event_text(text: str) -> tuple[str, str | None]:
    text = normalized(text)
    times = re.findall(r"\b([0-2]?\d:[0-5]\d)\b", text)
    event_time = times[0] if times else None
    text = re.sub(r"\b[0-2]?\d:[0-5]\d\b", " ", text)
    labels = [
        "Football","Basketball","Handball","Tennis","Cycling","Motorsport","Boxing","MMA",
        "Futsal","Golf","Snooker","Darts","Rugby Union","Ice Hockey","Volleyball",
        "Athletics","Alpine Ski","Ski Jumping","Biathlon","Winter Sports","Padel","Squash",
        "Am. Football","Baseball","Horse Racing","Beach Soccer","WWE"
    ]
    for label in sorted(labels, key=len, reverse=True):
        text = re.sub(r"(?<!\w)" + re.escape(label) + r"(?!\w)", " ", text, flags=re.I)
    return normalized(re.sub(r"\s{2,}", " ", text).strip(" |-–—")), event_time


def nearest_date_before(node, reference: datetime):
    for prev in node.find_all_previous(["time","h2","h3","h4","div","span","p","li"], limit=80):
        txt = normalized(prev.get_text(" ", strip=True))
        if txt and len(txt) <= 48:
            d = parse_date_label(txt, reference)
            if d:
                return d
    return None


def parse_sportguide_events(page_html: str, reference: datetime | None = None) -> list[dict]:
    reference = reference or datetime.now()
    soup = BeautifulSoup(page_html, "html.parser")
    events = []

    # Primary: current event-detail URLs are /event/... and are more stable than CSS/layout.
    for a in soup.find_all("a", href=True):
        href = normalized(a.get("href", ""))
        if "/event/" not in href:
            continue
        raw = normalized(a.get_text(" ", strip=True) or a.get("title", "") or a.get("aria-label", ""))
        clean, event_time = clean_external_event_text(raw)
        if not clean or len(clean) < 4:
            continue
        d = nearest_date_before(a, reference)
        events.append({"date": d.isoformat() if d else None, "time":event_time, "title":clean, "href":href})

    # Secondary: old/localized variants where event hrefs are not exposed.
    if not events:
        current_date = None
        live_started = False
        live_markers = ["live on tv","uzivo na tv","uživo na tv","ao vivo","en vivo","live op tv","v zivo na tv","v živo na tv"]
        end_markers = ["sat info","sat. info","info de satelite","info de satélite","satellite info"]
        for node in soup.find_all(["h1","h2","h3","h4","div","span","p","a","li","time"]):
            text = normalized(node.get_text(" ", strip=True))
            if not text:
                continue
            low = ascii_fold(text)
            if any(ascii_fold(m) in low for m in live_markers):
                live_started = True
            if live_started and any(ascii_fold(m) in low for m in end_markers):
                break
            if not live_started:
                continue
            d = parse_date_label(text, reference)
            if d and len(text) <= 48:
                current_date = d
                continue
            if node.name == "a" and current_date:
                clean, event_time = clean_external_event_text(text)
                low_clean = ascii_fold(clean)
                if not clean or any(x in low_clean for x in ["mobile app","calendar","highlights","privacy","contact","cookies","best vpn"]):
                    continue
                if not (re.search(r"\s[-–—]\s", clean) or sport_from_text(clean) or league_from_text(clean)):
                    continue
                events.append({"date":current_date.isoformat(),"time":event_time,"title":clean,"href":node.get("href","")})

    # Last chance: pre-rendered fragments embedded in script tags.
    if not events:
        for script in soup.find_all("script"):
            txt = script.string or script.get_text(" ", strip=False)
            if not txt or "/event/" not in txt:
                continue
            frag = BeautifulSoup(html.unescape(txt), "html.parser")
            for a in frag.find_all("a", href=True):
                if "/event/" not in a.get("href", ""):
                    continue
                clean, event_time = clean_external_event_text(a.get_text(" ", strip=True))
                if clean:
                    events.append({"date":None,"time":event_time,"title":clean,"href":a.get("href","")})

    dedup = {}
    for ev in events:
        dedup[(ev.get("date"), ev.get("time"), ascii_fold(ev.get("title","")))] = ev
    return list(dedup.values())


def sportguide_url_candidates(url: str, external_cfg: dict) -> list[str]:
    urls = [url]
    if not external_cfg.get("try_station_alias", True):
        return urls
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    slug = path.rsplit("/",1)[-1]
    base = f"{parsed.scheme}://{parsed.netloc}"
    if "/tv-guide-live/" in path:
        urls.append(f"{base}/station/{slug}")
    elif "/station/" in path:
        urls.append(f"{base}/tv-guide-live/{slug}")
    if slug:
        urls.append(f"{base}/station/{slug}")
    out=[]
    for u in urls:
        if u not in out:
            out.append(u)
    return out



def station_name_key(text: str) -> str:
    text = normalized_channel_label(text)
    # Common branding variants should compare cleanly.
    text = re.sub(r"\bdeutschland\b|\bitalia\b|\bfrance\b|\bpoland\b|\bnorway\b|\bsweden\b|\bdenmark\b", " ", text)
    return normalized(text)



COUNTRY_WORDS = {
    "poland","polska","uk","united","kingdom","great","britain","england","italy","italia",
    "germany","deutschland","france","greece","greek","czech","republic","czechia","sweden",
    "norway","denmark","finland","austria","belgium","netherlands","holland","switzerland",
    "spain","portugal","serbia","croatia","slovakia","hungary","bulgaria","romania","turkey",
    "usa","canada","australia","rs","hr","pl","de","fr","it","gr","cz","se","no","dk","fi",
    "at","be","nl","ch","es","pt","sk","hu","bg","ro","tr","us","ca","au"
}
CHANNEL_GENERIC = {
    "sport","sports","tv","television","channel","hd","uhd","4k","direct","network"
}
CRITICAL_DESCRIPTOR_TOKENS = {
    "premium","premier","league","football","f1","tennis","golf","main","event","action","news",
    "cricket","calcio","motogp","nba","plus","fight","hockey","motor","fotboll","foot","uno",
    "arena","max","world","360","extra","live","n"
}
VARIANT_TOKENS = set(CRITICAL_DESCRIPTOR_TOKENS)

# Specific brands must come before any generic fallback.
BRAND_PATTERNS = [
    ("sky sport", [r"\bsky\s+sports?\b"]),
    ("canal plus", [r"\bcanal\s*(?:plus|\+)\b", r"\bcanalplus\b"]),
    ("tnt sports", [r"\btnt\s+sports?\b"]),
    ("eurosport", [r"\beurosport\b"]),
    ("bein sports", [r"\bbein\s+sports?\b"]),
    ("eleven sports", [r"\beleven\s+sports?\b", r"\beleven\s+pro\s+league\b"]),
    ("polsat sport", [r"\bpolsat\s+sport\b"]),
    ("premier sport", [r"\bpremier\s+sports?\b"]),
    ("rmc sport", [r"\brmc\s+sports?\b"]),
    ("max sport", [r"\bmax\s+sport\b"]),
    ("dazn", [r"\bdazn\b"]),
    ("cosmote sport", [r"\bcosmote\s+sport\b"]),
    ("novasports", [r"\bnovasports\b"]),
    ("nova sport", [r"\bnova\s+sport\b"]),
    ("digi sport", [r"\bdigi\s+sport\b"]),
    ("prima sport", [r"\bprima\s+sport\b"]),
    ("espn", [r"\bespn\b"]),
    ("fox sports", [r"\bfox\s+sports?\b"]),
    ("sportsnet", [r"\bsportsnet\b"]),
    ("sport tv", [r"\bsport\s+tv\b"]),
    ("arena sport", [r"\barena\s+(?:premium\s+)?sport\b", r"\barena\s+sport\b"]),
    ("sportklub", [r"\bsport\s*klub\b", r"\bsportklub\b"]),
    ("tv2 sport", [r"\btv\s*2\s+sport\b"]),
    ("v sport", [r"\bv\s+sport\b", r"\bviasport\b"]),
    ("viaplay", [r"\bviaplay\b"]),
    ("s sport", [r"\bs\s+sport\b"]),
    ("tivibu sport", [r"\btivibu\s+spor\b", r"\btivibu\s+sport\b"]),
    ("trt spor", [r"\btrt\s+spor\b", r"\btrt\s+sport\b"]),
    ("diema sport", [r"\bdiema\s+sport\b"]),
    ("m4 sport", [r"\bm\s*4\s+sport\b"]),
    ("movistar", [r"\bmovistar\b", r"\bm\+\b"]),
    ("blue sport", [r"\bblue\s+sport\b"]),
    ("rds", [r"\brds\s*2?\b"]),
    ("tsn", [r"\btsn\b"]),
]

def _identity_words(text: str) -> list[str]:
    folded = normalized_channel_label(text)
    words = re.findall(r"[a-z0-9]+", folded)
    return [w for w in words if w not in COUNTRY_WORDS]

def canonical_brand(text: str) -> str | None:
    folded = ascii_fold(strip_country_prefix(text)).replace("+", " plus ")
    for brand, patterns in BRAND_PATTERNS:
        if any(re.search(p, folded, flags=re.I) for p in patterns):
            return brand

    # Sport 1 / Sport 2 are fallback brands only when they are the whole identity,
    # not a suffix of Premier Sport 1, RMC Sport 1, MAX Sport 1, etc.
    compact = " ".join(_identity_words(text))
    if re.fullmatch(r"sport\s*1(?:\s+plus)?", compact):
        return "sport1"
    if re.fullmatch(r"sport\s*2(?:\s+plus)?", compact):
        return "sport2"
    return None

def channel_numbers(text: str) -> tuple[str, ...]:
    folded = normalized_channel_label(text)
    return tuple(re.findall(r"\d+", folded))

def channel_variant_tokens(text: str) -> set[str]:
    words = set(_identity_words(text))
    brand = canonical_brand(text)
    if brand:
        words -= set(re.findall(r"[a-z0-9]+", brand))
    # Normalize a few equivalent sport-channel descriptors.
    if "fotboll" in words or "foot" in words:
        words.add("football")
        words.discard("fotboll")
        words.discard("foot")
    return words & VARIANT_TOKENS

def channel_descriptor_tokens(text: str) -> set[str]:
    words = set(_identity_words(text))
    brand = canonical_brand(text)
    words -= CHANNEL_GENERIC
    words -= set(channel_numbers(text))
    if brand:
        words -= set(re.findall(r"[a-z0-9]+", brand))
    words -= {"sky","canal","tnt","bein","eleven","polsat","dazn","cosmote","nova","novasports",
              "digi","prima","espn","fox","sportsnet","arena","sportklub","tv2","viaplay","tivibu",
              "trt","max","diema","movistar","blue","rds","tsn","rmc"}
    return {w for w in words if w}

def strict_number_compatible(target: str, candidate: str) -> bool:
    a, b = channel_numbers(target), channel_numbers(candidate)
    if a:
        return a == b
    # A target with no number should not silently become a numbered variant if it has
    # a named variant such as Eurosport N.
    if channel_variant_tokens(target) and b:
        return False
    return True

def channel_identity_score(target: str, candidate: str, require_brand: bool = True,
                           strict_numbers: bool = True, require_critical: bool = False,
                           strict_variants: bool = False) -> tuple[float, dict]:
    tb = canonical_brand(target)
    cb = canonical_brand(candidate)
    brand_match = bool(tb and cb and tb == cb)

    if require_brand:
        if tb:
            if not brand_match:
                return 0.0, {"brand_match":False,"target_brand":tb,"candidate_brand":cb}
        else:
            # Unknown brands only pass when the complete normalized name is extremely close.
            if similarity(station_name_key(target), station_name_key(candidate)) < 0.92:
                return 0.0, {"brand_match":False,"target_brand":None,"candidate_brand":cb}

    number_match = strict_number_compatible(target, candidate)
    if strict_numbers and not number_match:
        return 0.0, {
            "brand_match":brand_match,"target_brand":tb,"candidate_brand":cb,"number_match":False,
            "target_numbers":list(channel_numbers(target)),"candidate_numbers":list(channel_numbers(candidate))
        }

    tv = channel_variant_tokens(target)
    cv = channel_variant_tokens(candidate)
    variant_match = tv == cv
    if strict_variants and not variant_match:
        return 0.0, {
            "brand_match":brand_match,"target_brand":tb,"candidate_brand":cb,
            "number_match":number_match,"variant_match":False,
            "target_variants":sorted(tv),"candidate_variants":sorted(cv)
        }

    td = channel_descriptor_tokens(target)
    cd = channel_descriptor_tokens(candidate)
    critical = td & CRITICAL_DESCRIPTOR_TOKENS
    descriptor_overlap = len(td & cd) / max(1, len(td | cd)) if (td or cd) else 1.0
    if require_critical and critical and not (critical & cd):
        return 0.0, {
            "brand_match":brand_match,"target_brand":tb,"candidate_brand":cb,
            "number_match":number_match,"variant_match":variant_match,
            "critical_missing":sorted(critical)
        }

    text_score = similarity(station_name_key(target), station_name_key(candidate))
    score = (
        0.46 * (1.0 if brand_match else text_score) +
        0.17 * (1.0 if number_match else 0.0) +
        0.17 * (1.0 if variant_match else 0.0) +
        0.10 * descriptor_overlap +
        0.10 * text_score
    )
    if station_name_key(target) == station_name_key(candidate):
        score = 1.0
    return min(1.0, score), {
        "brand_match":brand_match,
        "target_brand":tb,
        "candidate_brand":cb,
        "number_match":number_match,
        "target_numbers":list(channel_numbers(target)),
        "candidate_numbers":list(channel_numbers(candidate)),
        "variant_match":variant_match,
        "target_variants":sorted(tv),
        "candidate_variants":sorted(cv),
        "descriptor_overlap":round(descriptor_overlap,3),
        "target_descriptors":sorted(td),
        "candidate_descriptors":sorted(cd),
        "text_score":round(text_score,3),
    }

def external_event_key(ev: dict) -> str:
    href = normalized(ev.get("href",""))
    if href:
        return "href:" + href
    src = normalized(ev.get("source_url",""))
    title = ascii_fold(ev.get("title",""))
    return "event:" + "|".join([src, str(ev.get("date") or ""), str(ev.get("time") or ""), title])

def dedupe_external_events(events: list[dict]) -> tuple[list[dict], int]:
    seen = {}
    order = []
    removed = 0
    for ev in events:
        k = external_event_key(ev)
        if k in seen:
            removed += 1
            # Manual override wins if the same logical event is duplicated.
            if ev.get("source") == "manual" and seen[k].get("source") != "manual":
                seen[k] = ev
            continue
        seen[k] = ev
        order.append(k)
    return [seen[k] for k in order], removed

def external_usage_metrics(matches: list[dict]) -> dict:
    per_channel = defaultdict(int)
    event_channels = defaultdict(set)
    total_by_event = defaultdict(int)
    for m in matches:
        key = m.get("external_event_key")
        channel = m.get("channel_id")
        if not key or not channel:
            continue
        per_channel[(channel, key)] += 1
        event_channels[key].add(channel)
        total_by_event[key] += 1

    same_channel_reuse = sum(v - 1 for v in per_channel.values() if v > 1)
    simulcast_events = sum(1 for chans in event_channels.values() if len(chans) > 1)
    simulcast_extra = sum(len(chans) - 1 for chans in event_channels.values() if len(chans) > 1)
    return {
        "unique_events_global": len(event_channels),
        "unique_channel_events": len(per_channel),
        "same_channel_reuse": same_channel_reuse,
        "cross_channel_simulcast_events": simulcast_events,
        "cross_channel_simulcast_extra_matches": simulcast_extra,
        "max_channels_per_event": max((len(v) for v in event_channels.values()), default=0),
    }

def load_sportguide_catalog(external_cfg: dict) -> dict:
    path = BASE_DIR / external_cfg.get("catalog_cache_file", ".cache/sportguide_catalog.json")
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("entries", [])
                data.setdefault("channel_map", {})
                updated_raw = data.get("updated_at_utc")
                age_h = None
                if updated_raw:
                    updated = datetime.fromisoformat(updated_raw)
                    if updated.tzinfo is None:
                        updated = updated.replace(tzinfo=timezone.utc)
                    age_h = (datetime.now(timezone.utc) - updated.astimezone(timezone.utc)).total_seconds()/3600.0
                elif path.exists():
                    age_h = (time.time() - path.stat().st_mtime)/3600.0
                max_h = float(external_cfg.get("catalog_lkg_max_age_hours", 168))
                data["_cache_age_hours"] = round(age_h,3) if age_h is not None else None
                data["_cache_valid"] = bool(age_h is None or (0 <= age_h <= max_h))
                data["_loaded_from_cache"] = True
                if data["_cache_valid"]:
                    return data
        except Exception:
            pass
    return {"version":1,"updated_at_utc":None,"entries":[],"channel_map":{},
            "_loaded_from_cache":False,"_cache_valid":False,"_cache_age_hours":None}


def save_sportguide_catalog(catalog: dict, external_cfg: dict, touch_timestamp: bool = True):
    path = BASE_DIR / external_cfg.get("catalog_cache_file", ".cache/sportguide_catalog.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    if touch_timestamp:
        catalog["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    serializable = {k:v for k,v in catalog.items() if not k.startswith("_")}
    path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


def catalog_add(catalog: dict, label: str, url: str, country: str | None = None, source: str = "page"):
    label = normalized(label)
    if not label or not url:
        return
    if url.startswith("/"):
        url = urljoin("https://sport-tv-guide.live", url)
    if "sport-tv-guide.live" not in url:
        return
    if "/event/" in url:
        return
    key = (ascii_fold(label), url)
    for e in catalog.setdefault("entries", []):
        if (ascii_fold(e.get("label","")), e.get("url")) == key:
            if country and not e.get("country"):
                e["country"] = country
            return
    catalog["entries"].append({"label":label,"url":url,"country":country,"source":source})


def extract_station_catalog(page_html: str, base_url: str, country: str | None = None) -> list[dict]:
    soup = BeautifulSoup(page_html, "html.parser")
    found = []
    for a in soup.find_all("a", href=True):
        href = normalized(a.get("href", ""))
        if not ("/station/" in href or "/tv-guide-live/" in href):
            continue
        if "/event/" in href:
            continue
        label = normalized(a.get_text(" ", strip=True) or a.get("title", ""))
        if not label or len(label) > 80:
            continue
        url = urljoin(base_url, href)
        found.append({"label":label,"url":url,"country":country})
    # Include the page itself with the page H1/H2 identity.
    title = None
    for tag in ["h1","h2"]:
        node = soup.find(tag)
        if node:
            t = normalized(node.get_text(" ", strip=True))
            if t:
                title = re.sub(r"\s+-\s+Live on TV.*$", "", t, flags=re.I)
                break
    if title:
        found.append({"label":title,"url":base_url,"country":country})
    dedup = {}
    for x in found:
        dedup[(ascii_fold(x["label"]), x["url"])] = x
    return list(dedup.values())


def compatible_channel_numbers(target: str, label: str) -> bool:
    return strict_number_compatible(target, label)

def catalog_match_channel(ch_cfg: dict, source_cfg: dict, catalog: dict, external_cfg: dict) -> list[dict]:
    cc = source_cfg.get("sportguide_country")
    target = strip_country_prefix(ch_cfg.get("name", ""))
    scored = []
    for e in catalog.get("entries", []):
        # Known, conflicting countries are rejected. Unknown-country catalog entries remain eligible.
        if cc and e.get("country") and e.get("country") != cc:
            continue
        label = e.get("label", "")
        sc, identity = channel_identity_score(
            target, label,
            require_brand=bool(external_cfg.get("catalog_brand_match_required", True)),
            strict_numbers=bool(external_cfg.get("catalog_strict_numbers", True)),
            require_critical=True,
            strict_variants=bool(external_cfg.get("catalog_strict_variants", True)),
        )
        if sc >= float(external_cfg.get("catalog_min_score", 0.70)):
            scored.append({**e, "score":round(sc,3), "identity":identity})
    scored.sort(key=lambda x:(x["score"], x.get("source")=="seed-explicit"), reverse=True)
    out=[]; seen=set()
    for x in scored:
        if x["url"] not in seen:
            out.append(x); seen.add(x["url"])
    return out[:3]

def prime_sportguide_catalog(catalog: dict, external_cfg: dict, report: dict):
    if not external_cfg.get("catalog_enabled", True):
        return
    if catalog.get("_loaded_from_cache") and catalog.get("_cache_valid"):
        report["external_live"]["catalog_lkg_loaded"] += 1
        report["external_live"]["catalog_lkg_age_hours"] = catalog.get("_cache_age_hours")
        report["external_live"]["catalog_entries_retained"] = len(catalog.get("entries", []))

    touched = False
    for seed in external_cfg.get("catalog_seed_urls", []):
        if isinstance(seed, str):
            seed = {"url":seed,"country":None}
        url = seed.get("url")
        if not url:
            continue
        if seed.get("label"):
            catalog_add(catalog, seed["label"], url, seed.get("country"), "seed-explicit")
        report["external_live"]["catalog_seed_urls_tried"] += 1
        try:
            page, meta = fetch_text_resilient(url, external_cfg)
            report["external_live"]["network_attempts"] += int(meta.get("network_attempts",0))
            report["external_live"]["catalog_seed_pages_ok"] += 1
            if meta.get("cached"):
                report["external_live"]["catalog_seed_pages_cached"] += 1
            else:
                report["external_live"]["catalog_seed_pages_current"] += 1
            for item in extract_station_catalog(page, url, seed.get("country")):
                catalog_add(catalog, item["label"], item["url"], item.get("country"), "seed")
            if meta.get("mode") in ("current","fresh_page_cache"):
                touched = True
        except Exception as exc:
            report["external_live"]["catalog_seed_pages_failed"] += 1
            report["external_live"]["network_failures"] += 1
            report["external_live"]["catalog_seed_errors"].append({"url":url,"error":str(exc)})
    report["external_live"]["catalog_entries"] = len(catalog.get("entries", []))
    if touched:
        save_sportguide_catalog(catalog, external_cfg, touch_timestamp=True)

def generated_sportguide_urls(ch_cfg: dict, source_cfg: dict, external_cfg: dict) -> list[str]:
    # v3.5 keeps this only as an optional legacy fallback. Catalog discovery is preferred.
    if external_cfg.get("legacy_slug_fallback") is False:
        return []
    if not external_cfg.get("autodiscover_enabled", False):
        return []
    name = strip_country_prefix(ch_cfg.get("name", ""))
    slug = slugify_station_name(name)
    if not slug:
        return []
    cc = source_cfg.get("sportguide_country")
    base = "https://sport-tv-guide.live"
    candidates=[]
    if cc: candidates.append(f"{base}/tv-guide-live/{cc}-{slug}")
    candidates += [f"{base}/station/{slug}", f"{base}/tv-guide-live/{slug}"]
    return list(dict.fromkeys(candidates))[:int(external_cfg.get("autodiscover_max_candidates",2))]

def load_manual_events() -> list[dict]:
    data = load_yaml(OVERRIDES_FILE)
    return data.get("events", []) if isinstance(data, dict) else []

def external_events_for_channel(ch_cfg: dict, source_cfg: dict, external_cfg: dict,
                                report: dict, catalog: dict,
                                allow_autodiscovery: bool = True) -> list[dict]:
    out = []
    configured_urls = list(ch_cfg.get("external_live_urls") or [])
    if ch_cfg.get("external_live_url"):
        configured_urls.insert(0, ch_cfg["external_live_url"])

    mode = "configured"
    if not configured_urls and allow_autodiscovery and external_cfg.get("catalog_enabled", True):
        mapped = catalog.get("channel_map", {}).get(ch_cfg.get("id"))
        if mapped and mapped.get("url"):
            configured_urls = [mapped["url"]]
            mode = "catalog-cache"
            report["external_live"]["catalog_cache_hits"] += 1
        else:
            matches = catalog_match_channel(ch_cfg, source_cfg, catalog, external_cfg)
            if matches:
                configured_urls = [x["url"] for x in matches[:1]]
                mode = "catalog"
                report["external_live"]["catalog_matches"] += 1
                if (matches[0].get("identity") or {}).get("brand_match"):
                    report["external_live"]["catalog_brand_matches"] += 1

    if not configured_urls and allow_autodiscovery:
        legacy = generated_sportguide_urls(ch_cfg, source_cfg, external_cfg)
        if legacy:
            configured_urls = legacy
            mode = "legacy-guess"

    tried=[]
    current_events = []
    fresh_cache_events = []
    stale_cache_events = []
    event_lkg_events = []
    cached_events = []  # compatibility aggregate
    any_provider_response = False
    network_failure_seen = False
    current_page_seen = False
    fresh_cache_page_seen = False
    stale_cache_page_seen = False
    cached_page_seen = False  # compatibility aggregate
    last_fetch_meta = None
    successful_url = None

    if external_cfg.get("enabled") and configured_urls:
        for configured in configured_urls:
            candidates = [configured] if mode.startswith("catalog") else sportguide_url_candidates(configured, external_cfg)
            for url in candidates:
                if url in tried:
                    continue
                tried.append(url)
                report["external_live"]["urls_tried"] += 1
                if mode == "legacy-guess":
                    report["external_live"]["legacy_urls_tried"] += 1
                try:
                    page, meta = fetch_text_resilient(url, external_cfg)
                    last_fetch_meta = meta
                    report["external_live"]["network_attempts"] += int(meta.get("network_attempts",0))
                    if meta.get("network_error"):
                        network_failure_seen = True
                        report["external_live"]["network_failures"] += 1

                    report["external_live"]["pages_ok"] += 1
                    fetch_mode = meta.get("mode")
                    if fetch_mode == "fresh_page_cache":
                        fresh_cache_page_seen = True
                        cached_page_seen = True
                        report["external_live"]["pages_cached"] += 1
                        report["external_live"]["pages_fresh_cache"] += 1
                    elif fetch_mode == "stale_page_cache":
                        stale_cache_page_seen = True
                        cached_page_seen = True
                        report["external_live"]["pages_cached"] += 1
                        report["external_live"]["pages_stale_cache"] += 1
                        report["external_live"]["stale_page_cache_hits"] += 1
                    else:
                        current_page_seen = True
                        report["external_live"]["pages_current"] += 1
                    any_provider_response = True

                    cc = source_cfg.get("sportguide_country")
                    discovered = extract_station_catalog(page, url, cc)
                    for item in discovered:
                        catalog_add(catalog,item["label"],item["url"],item.get("country"),"neighbor")
                    parsed = parse_sportguide_events(page)

                    fetched_at = meta.get("fetched_at_utc") or datetime.now(timezone.utc).isoformat()
                    if mode in ("catalog","catalog-cache") or configured in configured_urls:
                        catalog.setdefault("channel_map", {})[ch_cfg["id"]] = {
                            "url":url, "country":cc, "last_ok_utc":fetched_at, "mode":mode
                        }

                    if parsed:
                        report["external_live"]["pages_with_events"] += 1
                        fetch_mode = meta.get("mode")
                        if fetch_mode == "fresh_page_cache":
                            source_name = "sportguide-fresh-cache"
                            data_status = "fresh_cache"
                        elif fetch_mode == "stale_page_cache":
                            source_name = "sportguide-stale-cache"
                            data_status = "stale_cache"
                        else:
                            source_name = "sportguide-catalog" if mode.startswith("catalog") else "sportguide"
                            data_status = "current"
                        for ev in parsed:
                            ev.update({"source":source_name, "source_url":url, "live":True,
                                       "external_data_status":data_status})
                            if ev.get("href"):
                                ev["href"] = urljoin(url,ev["href"])
                        if fetch_mode == "fresh_page_cache":
                            fresh_cache_events.extend(parsed)
                            cached_events.extend(parsed)
                            report["external_live"]["events_found_fresh_cache"] += len(parsed)
                            report["external_live"]["events_found_cached"] += len(parsed)
                        elif fetch_mode == "stale_page_cache":
                            stale_cache_events.extend(parsed)
                            cached_events.extend(parsed)
                            report["external_live"]["events_found_stale_cache"] += len(parsed)
                            report["external_live"]["events_found_cached"] += len(parsed)
                        else:
                            current_events.extend(parsed)
                            report["external_live"]["events_found_current"] += len(parsed)
                        out.extend(parsed)
                        report["external_live"]["events_found"] += len(parsed)
                        successful_url = url

                        # Preserve original fetch time when deriving event cache from page cache.
                        save_external_event_cache(ch_cfg["id"], parsed, external_cfg,
                                                  fetched_at_utc=fetched_at, source_url=url)
                        if meta.get("mode") in ("current","fresh_page_cache"):
                            save_sportguide_catalog(catalog, external_cfg, touch_timestamp=True)
                        else:
                            save_sportguide_catalog(catalog, external_cfg, touch_timestamp=False)
                        break

                    report["external_live"]["pages_empty"] += 1
                    if mode.startswith("catalog"):
                        break

                except Exception as exc:
                    network_failure_seen = True
                    report["external_live"]["pages_failed"] += 1
                    report["external_live"]["network_failures"] += 1
                    report["external_live"]["errors"].append(
                        {"channel":ch_cfg["id"],"url":url,"error":str(exc),"mode":mode}
                    )
                    # v3.12: transient network failure must NOT delete a previously valid catalog mapping.
                    # It remains LKG until its catalog TTL expires.
            if out or mode.startswith("catalog"):
                break

    # Provider unavailable: fall back to event LKG for this logical channel.
    event_cache_meta = None
    if (not out and network_failure_seen and external_cfg.get("event_cache_fallback_on_network_error", True)):
        cached, event_cache_meta = load_external_event_cache(ch_cfg["id"], external_cfg)
        if cached:
            out.extend(cached)
            event_lkg_events.extend(cached)
            cached_events.extend(cached)
            report["external_live"]["event_cache_hits"] += 1
            report["external_live"]["events_found_event_lkg"] += len(cached)
            report["external_live"]["events_found_cached"] += len(cached)
            report["external_live"]["events_found"] += len(cached)

    # Manual overrides are independent of provider availability.
    manual_count = 0
    for ev in load_manual_events():
        if ev.get("channel_id") == ch_cfg["id"]:
            e=dict(ev); e["source"]="manual"; e["external_data_status"]="manual"; out.append(e); manual_count += 1

    if external_cfg.get("dedupe_events", True):
        out, removed = dedupe_external_events(out)
        report["external_live"]["events_deduplicated"] += removed

    provider_events = [e for e in out if e.get("source") != "manual"]
    if provider_events:
        report["external_live"]["channels_with_events"] += 1

    data_age_hours = None
    data_origin = None
    if current_events:
        status = "external_current"
        data_origin = "current"
        data_age_hours = 0.0
        report["external_live"]["channels_current"] += 1
    elif fresh_cache_events:
        status = "external_fresh_cache"
        data_origin = "fresh_cache"
        data_age_hours = (last_fetch_meta or {}).get("age_hours")
        report["external_live"]["channels_fresh_cache"] += 1
        report["external_live"]["channels_cached"] += 1
    elif stale_cache_events:
        status = "external_stale_cache"
        data_origin = "stale_cache"
        data_age_hours = (last_fetch_meta or {}).get("age_hours")
        report["external_live"]["channels_stale_cache"] += 1
        report["external_live"]["channels_cached"] += 1
    elif event_lkg_events:
        status = "external_event_lkg"
        data_origin = "event_lkg"
        data_age_hours = (event_cache_meta or {}).get("age_hours")
        report["external_live"]["channels_event_lkg"] += 1
        report["external_live"]["channels_cached"] += 1
    elif configured_urls and network_failure_seen and not any_provider_response:
        status = "external_unavailable"
        data_origin = "unavailable"
        report["external_live"]["channels_unavailable"] += 1
    elif any_provider_response:
        if current_page_seen:
            status = "external_current_empty"
            data_origin = "current"
            data_age_hours = 0.0
            report["external_live"]["channels_current_empty"] += 1
        elif fresh_cache_page_seen:
            status = "external_fresh_cache_empty"
            data_origin = "fresh_cache"
            data_age_hours = (last_fetch_meta or {}).get("age_hours")
            report["external_live"]["channels_fresh_cache_empty"] += 1
            report["external_live"]["channels_cached_empty"] += 1
        else:
            status = "external_stale_cache_empty"
            data_origin = "stale_cache"
            data_age_hours = (last_fetch_meta or {}).get("age_hours")
            report["external_live"]["channels_stale_cache_empty"] += 1
            report["external_live"]["channels_cached_empty"] += 1
    else:
        status = "external_not_configured"
        data_origin = "not_configured"

    if data_age_hours is not None:
        try:
            age_value = max(0.0, float(data_age_hours))
            report["external_live"]["data_age_hours_values"].append(age_value)
            report["external_live"]["data_age_max_hours"] = max(report["external_live"]["data_age_max_hours"], age_value)
        except (TypeError, ValueError):
            pass

    report["external_live"]["channel_status"][ch_cfg["id"]] = {
        "name":ch_cfg.get("name"),
        "status":status,
        "data_origin":data_origin,
        "data_age_hours":round(float(data_age_hours),3) if data_age_hours is not None else None,
        "mode":mode,
        "configured_urls":configured_urls,
        "events":len(provider_events),
        "manual_events":manual_count,
        "network_failure_seen":network_failure_seen,
        "current_page_seen":current_page_seen,
        "cached_page_seen":cached_page_seen,
        "fetch_meta":last_fetch_meta,
        "event_cache_meta":event_cache_meta,
        "successful_url":successful_url,
    }

    report["external_live"]["catalog_entries"] = len(catalog.get("entries", []))
    return out


def best_external_match(title: str, prog_date, events: list[dict], min_score: float,
                        prog_dt: datetime | None = None, time_tolerance_minutes: int = 150,
                        min_title_score: float = 0.30, context_text: str = "",
                        station_timezone: str | None = None, date_tolerance_days: int = 0,
                        entity_min_overlap: int = 2) -> tuple[dict|None,float,dict]:
    best, best_score, best_details = None, 0.0, {}
    combined = normalized(" ".join([title, context_text[:1200]]))
    detection_context = combined
    title_sport = sport_from_text(detection_context)
    title_league = league_from_text(detection_context)
    prog_local = localize_datetime(prog_dt, station_timezone)
    local_date = prog_local.date() if prog_local else prog_date
    programme_entities = participant_tokens(combined)

    for ev in events:
        if ev.get("_used") and not bool(ev.get("_reuse_allowed")):
            continue
        ev_date = None
        if ev.get("date"):
            try:
                ev_date = datetime.fromisoformat(ev["date"]).date()
            except Exception:
                pass
        if ev_date and local_date:
            if abs((ev_date - local_date).days) > int(date_tolerance_days):
                continue

        event_title = ev.get("title", "")
        event_entities = participant_tokens(event_title)
        common_entities = programme_entities & event_entities
        entity_overlap = len(common_entities)
        entity_containment = (
            entity_overlap / max(1, min(len(programme_entities), len(event_entities)))
            if programme_entities and event_entities else 0.0
        )

        title_score = similarity(title, event_title)
        context_score = similarity(combined, event_title)
        base = max(title_score, context_score)

        ev_sport = sport_from_text(event_title)
        ev_league = league_from_text(event_title)
        same_sport = bool(title_sport and ev_sport and title_sport["key"] == ev_sport["key"])
        different_sport = bool(title_sport and ev_sport and title_sport["key"] != ev_sport["key"])
        same_league = bool(title_league and ev_league and title_league["key"] == ev_league["key"])
        different_league = bool(title_league and ev_league and title_league["key"] != ev_league["key"])

        if different_sport:
            continue

        score = base
        bonuses = []

        # Strong entity overlap is useful when XMLTV title is generic and teams/players are in <desc>.
        if entity_overlap >= entity_min_overlap and entity_containment >= 0.45:
            score = max(score, min(0.82, 0.54 + 0.09 * min(entity_overlap, 3)))
            bonuses.append("entity_overlap")
        elif entity_overlap >= 1 and entity_containment >= 0.50:
            score = max(score, 0.52)
            bonuses.append("entity_overlap_1")

        if same_sport:
            score += 0.03
            bonuses.append("same_sport")
        if same_league:
            score += 0.08
            bonuses.append("same_league")
        elif different_league:
            score -= 0.04
            bonuses.append("different_league")

        common_tokens = token_set(combined) & token_set(event_title)
        if len(common_tokens) >= 3:
            score += 0.03
            bonuses.append("token_overlap")

        time_delta = None
        if prog_local is not None and ev.get("time"):
            try:
                hh, mm = map(int, ev["time"].split(":"))
                ev_dt = prog_local.replace(hour=hh, minute=mm, second=0, microsecond=0)
                time_delta = abs((prog_local - ev_dt).total_seconds()) / 60
                if time_delta > time_tolerance_minutes * 2:
                    continue
                if time_delta <= time_tolerance_minutes:
                    score += 0.06
                    bonuses.append("time_close")
            except Exception:
                pass

        # Relax title threshold only when independent evidence is strong.
        evidence_ok = (
            title_score >= min_title_score or
            context_score >= min_title_score or
            entity_overlap >= entity_min_overlap or
            (same_league and time_delta is not None and time_delta <= time_tolerance_minutes)
        )
        if ev.get("source") != "manual" and not evidence_ok:
            continue

        if same_league and entity_overlap >= 1:
            score = max(score, 0.61)
        if same_league and time_delta is not None and time_delta <= time_tolerance_minutes and entity_overlap >= 1:
            score = max(score, 0.66)
        # Translation-independent safety net: one shared participant + same sport + very close time
        # is often enough to identify the same live fixture even when the competition/title language differs.
        if same_sport and entity_overlap >= 1 and time_delta is not None and time_delta <= 45:
            score = max(score, 0.68)
            bonuses.append("participant_time_strong")

        if ev.get("source") == "manual":
            score = max(score, 0.95)
            bonuses.append("manual_override")

        score = max(0.0, min(1.0, score))
        if score > best_score:
            best, best_score = ev, score
            best_details = {
                "title_score": round(title_score, 3),
                "context_score": round(context_score, 3),
                "final_score": round(score, 3),
                "bonuses": bonuses,
                "time_delta_minutes": round(time_delta, 1) if time_delta is not None else None,
                "common_tokens": sorted(common_tokens)[:16],
                "common_entities": sorted(common_entities)[:12],
                "entity_overlap": entity_overlap,
                "entity_containment": round(entity_containment, 3),
                "league": (title_league or ev_league or {}).get("name"),
                "station_timezone": station_timezone,
            }

    if best is not None and best_score >= min_score:
        return best, best_score, best_details
    return None, best_score, best_details


def audit_external_match(score: float, details: dict, confidence: str, settings: dict) -> dict:
    title_score = float(details.get("title_score") or 0)
    context_score = float(details.get("context_score") or 0)
    entities = int(details.get("entity_overlap") or 0)
    bonuses = set(details.get("bonuses") or [])
    risky_below = float(settings.get("external_live_risky_score_below", 0.66))
    reasons=[]
    if score < risky_below: reasons.append("low_final_score")
    if entities == 0 and title_score < 0.35 and context_score < 0.40 and "same_league" not in bonuses:
        reasons.append("weak_text_evidence")
    td = details.get("time_delta_minutes")
    if td is not None and td > int(settings.get("external_live_time_tolerance_minutes",150)) and entities == 0:
        reasons.append("weak_time_alignment")
    if reasons:
        grade="risky"
    elif confidence == "high" and (entities >= 1 or title_score >= 0.55 or context_score >= 0.62 or "manual_override" in bonuses):
        grade="strong"
    else:
        grade="review"
    return {"grade":grade,"reasons":reasons}

GENERIC_PROGRAMME_TITLE_PATTERNS = [
    r"^live$", r"^sport(?:s)?$", r"^game$", r"^match$", r"^event$", r"^studio$", r"^pregame$", r"^postgame$",
    r"^football$", r"^soccer$", r"^basketball$", r"^baseball$", r"^hockey$", r"^tennis$", r"^golf$",
    r"^futbol$", r"^fútbol$", r"^mlb network$", r"^mlb baseball$", r"^tudn$", r"^sportscenter$",
]

CHANNEL_SPORT_FALLBACKS = [
    (r"\bmlb\b", "baseball"),
    (r"\bnba\b", "basketball"),
    (r"\bnhl\b", "hockey"),
    (r"\bnfl\b", "american_football"),
    (r"tennis channel", "tennis"),
    (r"golf channel", "golf"),
]

def sport_by_key(key: str | None):
    if not key:
        return None
    for sport in SPORTS:
        if sport.get("key") == key:
            return sport
    return None

def fallback_sport_from_channel(channel_name: str | None):
    hay = ascii_fold(channel_name or "")
    for pattern, key in CHANNEL_SPORT_FALLBACKS:
        if re.search(pattern, hay, flags=re.I):
            return sport_by_key(key)
    return None

def is_generic_programme_title(title: str) -> bool:
    title = normalized(strip_live_words(title))
    folded = ascii_fold(title)
    if not folded:
        return True
    if any(re.fullmatch(p, folded, flags=re.I) for p in GENERIC_PROGRAMME_TITLE_PATTERNS):
        return True
    entities = participant_tokens(title)
    sport = sport_from_text(title)
    league = league_from_text(title)
    if entities:
        return False
    if sport and not league and len(token_set(title)) <= 3:
        return True
    return False

def split_matchup(text: str) -> tuple[str, str] | None:
    hay = normalized(text)
    separators = [r"\s+vs\.?\s+", r"\s+v\.?\s+", r"\s+@\s+", r"\s+-\s+", r"\s+–\s+", r"\s+—\s+", r"\s+x\s+"]
    for pattern in separators:
        parts = re.split(pattern, hay, maxsplit=1, flags=re.I)
        if len(parts) != 2:
            continue
        left, right = normalized(parts[0]), normalized(parts[1])
        if not left or not right:
            continue
        if len(left.split()) > 7 or len(right.split()) > 7:
            continue
        if participant_tokens(left) and participant_tokens(right):
            return left, right
    return None

def enrich_external_event_title(raw_title: str, channel_name: str | None = None) -> dict:
    title = normalized(raw_title)
    if not title:
        return {"title": "", "participants": [], "has_participants": False, "competition": None}
    competition = None
    matchup_text = title
    if ":" in title:
        left, right = title.split(":", 1)
        if split_matchup(right):
            competition, matchup_text = normalized(left), normalized(right)
    if competition is None and " - " in title:
        left, right = title.split(" - ", 1)
        if split_matchup(right) and len(left.split()) <= 7:
            competition, matchup_text = normalized(left), normalized(right)
    matchup = split_matchup(matchup_text)
    league = league_from_text(title)
    sport = sport_from_text(title) or fallback_sport_from_channel(channel_name)
    if competition is None and league:
        competition = league.get("name")
    elif competition is None and channel_name and re.search(r"\bmlb\b", ascii_fold(channel_name), flags=re.I):
        competition = "MLB"
    if matchup:
        display = f"{matchup[0]} – {matchup[1]}"
        if competition and ascii_fold(competition) not in ascii_fold(display):
            display = f"{competition}: {display}"
        return {
            "title": display,
            "participants": [matchup[0], matchup[1]],
            "has_participants": True,
            "competition": competition,
            "sport": (sport or {}).get("key"),
            "league": (league or {}).get("key"),
        }
    return {
        "title": title,
        "participants": [],
        "has_participants": False,
        "competition": competition,
        "sport": (sport or {}).get("key"),
        "league": (league or {}).get("key"),
    }

def should_prefer_external_title(original_title: str, translated_title: str, external_title: str, external_meta: dict, settings: dict) -> bool:
    if not settings.get("external_live_enrich_title_with_participants", True):
        return False
    if not external_title:
        return False
    if settings.get("external_live_enrich_generic_only", True):
        return is_generic_programme_title(original_title) or bool(external_meta.get("has_participants"))
    return len(external_title) > len(normalized(translated_title))

def format_title(original_title: str, context_text: str, settings: dict, replacements: dict,
                 external_match: dict|None = None, external_score: float | None = None,
                 channel_name: str | None = None, prog_dt: datetime | None = None,
                 stop_dt: datetime | None = None, station_timezone: str | None = None,
                 sofascore_verdict: dict | None = None) -> tuple[str,dict]:
    external_title = external_match.get("title","") if external_match else ""
    context = normalized(" ".join([original_title, context_text, external_title, channel_name or ""]))
    replay = contains_any(context, REPLAY_TERMS)
    explicit_live_raw = detect_explicit_live(context)
    sofa_decision = (sofascore_verdict or {}).get("decision", "none")
    sofa_live = sofa_decision == "live"
    sofa_replay = sofa_decision == "replay"
    morning_guard = suspicious_morning_replay(context, prog_dt, station_timezone, external_match if not sofa_replay else None)
    inferred_live = infer_likely_live_event(context, prog_dt, stop_dt, station_timezone, external_match)
    explicit_live = bool(explicit_live_raw and not morning_guard and not replay and not sofa_replay)
    if (morning_guard and explicit_live_raw) or sofa_replay:
        replay = True
    # v3.19 precedence: Sofascore confirmed event time > Sport TV Guide > explicit provider LIVE > heuristic.
    # A Sofascore same-fixture/different-time match is a hard replay veto.
    live = (sofa_live or external_match is not None or explicit_live or inferred_live) and not replay

    sport = sport_from_text(context) or fallback_sport_from_channel(channel_name)
    league = league_from_text(context)
    stage = stage_from_text(context)
    base = strip_live_words(original_title) if live else original_title
    translated, changed = phrase_translate(base, replacements)

    participant_meta = {}
    if external_match:
        participant_meta = enrich_external_event_title(external_title, channel_name)
        min_score = float(settings.get("external_live_title_enrichment_min_score", 0.68))
        if (external_score is None or external_score >= min_score) and should_prefer_external_title(base, translated, participant_meta.get("title", ""), participant_meta, settings):
            translated = participant_meta.get("title") or translated
            changed = True

    lang = settings.get("target_language","pl")
    emoji = bool(settings.get("use_emoji",True))
    parts = []

    if replay and settings.get("add_replay_prefix", True):
        parts.append(("↻ " if emoji else "") + ("POWTÓRKA" if lang == "pl" else "REPLAY"))
    elif live and settings.get("add_live_prefix", True):
        parts.append(("🔴 " if emoji else "") + "LIVE")

    if stage and settings.get("add_stage_prefix", True):
        parts.append(("🏆 " if emoji else "") + STAGE_LABELS[lang][stage])

    if sport and settings.get("add_sport_prefix", True):
        parts.append((sport["emoji"] + " " if emoji else "") + sport.get(lang, sport["en"]))
    elif live and settings.get("add_unknown_sport_prefix_for_live", True):
        parts.append(("🏟️ " if emoji else "") + ("Sport" if lang == "pl" else "Sport"))

    new_title = " | ".join(parts + [translated]) if parts else translated
    return new_title, {
        "live": live,
        "explicit_live": explicit_live,
        "replay": replay,
        "external_live": external_match is not None,
        "sport": sport["key"] if sport else None,
        "league": league["key"] if league else None,
        "league_name": league["name"] if league else None,
        "stage": stage,
        "translated": changed or (base != original_title),
        "participants_enriched": bool(participant_meta.get("has_participants")),
        "participant_title": participant_meta.get("title"),
        "live_inferred": bool(inferred_live and external_match is None and not explicit_live),
        "live_morning_suppressed": bool(morning_guard and explicit_live_raw),
        "sofascore_live": bool(sofa_live),
        "sofascore_replay": bool(sofa_replay),
        "sofascore_decision": sofa_decision,
    }

def programme_count_by_channel(root: ET.Element) -> dict[str, int]:
    counts = defaultdict(int)
    for p in root.findall("programme"):
        cid = p.get("channel")
        if cid:
            counts[cid] += 1
    return counts


def choose_source_id(root: ET.Element, candidates: list[str], prefer_nonempty: bool = True) -> tuple[str|None, int]:
    available = {x.get("id") for x in root.findall("channel")}
    existing = [c for c in candidates if c in available]
    if not existing:
        return None, 0
    counts = programme_count_by_channel(root)
    if prefer_nonempty:
        populated = [(c, counts.get(c, 0)) for c in existing if counts.get(c, 0) > 0]
        if populated:
            return max(populated, key=lambda x: x[1])
    c = existing[0]
    return c, counts.get(c, 0)

def normalized_channel_label(text: str) -> str:
    text = ascii_fold(strip_country_prefix(text))
    text = text.replace("+", " plus ")
    text = re.sub(r"\b(hd|uhd|4k|tv|channel)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return normalized(text)

def source_autodiscovery(root: ET.Element, target_name: str, settings: dict) -> tuple[str|None,int,float,list[dict]]:
    counts = programme_count_by_channel(root)
    scored = []
    for ch in root.findall("channel"):
        cid = ch.get("id") or ""
        count = counts.get(cid, 0)
        if count <= 0:
            continue
        labels = [cid.replace(".", " ")] + [x.text or "" for x in ch.findall("display-name")]
        best_score, best_label, best_identity = 0.0, "", {}
        for label in labels:
            sc, identity = channel_identity_score(
                target_name, label,
                require_brand=bool(settings.get("source_recommendation_brand_required", True)),
                strict_numbers=bool(settings.get("source_recommendation_strict_numbers", True)),
                require_critical=bool(settings.get("source_recommendation_require_critical_descriptors", True)),
                strict_variants=bool(settings.get("source_recommendation_strict_variants", True)),
            )
            if sc > best_score:
                best_score, best_label, best_identity = sc, label, identity
        if best_score > 0:
            scored.append((best_score, count, cid, best_label, best_identity))
    scored.sort(reverse=True)
    suggestions = [
        {"source_id": cid, "score": round(score, 3), "programmes": count, "label": label,
         "identity": identity, "recommendation_grade": "same_brand_strong" if score >= 0.86 else "review"}
        for score, count, cid, label, identity in scored[:int(settings.get("source_autodiscovery_max_suggestions", 5))]
    ]
    if scored and scored[0][0] >= float(settings.get("source_autodiscovery_min_score", 0.86)):
        score, count, cid, _, _ = scored[0]
        return cid, count, score, suggestions
    return None, 0, scored[0][0] if scored else 0.0, suggestions

def verified_fallback_for_channel(ch_cfg: dict, roots: dict, settings: dict, verified_fallbacks: list[dict] | None):
    if not settings.get("verified_fallback_enabled", True):
        return None
    for entry in verified_fallbacks or []:
        if entry.get("channel_id") != ch_cfg.get("id") or not entry.get("approved"):
            continue
        ev=entry.get("evidence") or {}
        if not ev.get("schedule_verified"):
            continue
        if float(ev.get("identity_score",0)) < float(settings.get("verified_fallback_min_identity_score",0.95)):
            continue
        if float(ev.get("schedule_consensus",0)) < float(settings.get("verified_fallback_min_schedule_consensus",0.90)):
            continue
        if int(ev.get("same_slot_matches",0)) < int(settings.get("verified_fallback_min_same_slot_matches",20)):
            continue
        source_name=entry.get("source")
        root=roots.get(source_name)
        if root is None:
            continue
        source_id,count=choose_source_id(root,entry.get("source_ids",[]),True)
        if not source_id or count <= 0:
            continue
        ch=next((x for x in root.findall("channel") if x.get("id")==source_id),None)
        labels=[source_id.replace('.',' ')] + ([x.text or '' for x in ch.findall('display-name')] if ch is not None else [])
        best_identity=0.0; best_meta={}
        for label in labels:
            sc,meta=channel_identity_score(ch_cfg.get("name",""),label,require_brand=True,strict_numbers=True,require_critical=True,strict_variants=True)
            if sc > best_identity: best_identity,best_meta=sc,meta
        if best_identity < float(settings.get("verified_fallback_min_identity_score",0.95)):
            continue
        return source_name,source_id,ch,count,{
            "mode":"verified_fallback","score":round(best_identity,3),"suggestions":[],"verified_fallback":True,
            "verified_fallback_reason":entry.get("reason"),"verified_fallback_evidence":ev,
            "verified_fallback_identity":best_meta,
        }
    return None

def resolve_channel_source(ch_cfg: dict, roots: dict, settings: dict | None = None, verified_fallbacks: list[dict] | None = None) -> tuple[str | None, str | None, ET.Element | None, int, dict]:
    settings = settings or {}
    first_existing = None

    # v3.18 PlusX layer: optional priority sources are tried before the normal configured source.
    # If the priority source is unavailable or cannot be matched confidently, the existing
    # configured source continues to act as an automatic fallback.
    if settings.get("priority_source_autodiscovery_enabled", True):
        for item in list(ch_cfg.get("priority_sources", [])):
            source_name = item.get("source")
            root = roots.get(source_name)
            if root is None:
                continue
            source_id, count = choose_source_id(
                root, item.get("source_ids", []),
                bool(settings.get("source_prefer_nonempty_candidate", True))
            )
            if source_id and count > 0:
                ch = next((x for x in root.findall("channel") if x.get("id") == source_id), None)
                return source_name, source_id, ch, count, {
                    "mode":"priority_configured","score":1.0,"suggestions":[],"priority_source":True
                }
            if item.get("autodiscover", False) and settings.get("source_autodiscovery_enabled", True):
                auto_id, auto_count, score, suggestions = source_autodiscovery(root, ch_cfg.get("name", ""), settings)
                if auto_id and auto_count > 0:
                    ch = next((x for x in root.findall("channel") if x.get("id") == auto_id), None)
                    return source_name, auto_id, ch, auto_count, {
                        "mode":"priority_autodiscovered","score":round(score,3),
                        "suggestions":suggestions,"priority_source":True
                    }

    groups = [{"source": ch_cfg.get("source"), "source_ids": ch_cfg.get("source_ids", [])}] + list(ch_cfg.get("fallback_sources", []))

    for idx, item in enumerate(groups):
        source_name = item.get("source")
        root = roots.get(source_name)
        if root is None:
            continue
        source_id, count = choose_source_id(
            root, item.get("source_ids", []),
            bool(settings.get("source_prefer_nonempty_candidate", True))
        )
        if source_id and count > 0:
            ch = next((x for x in root.findall("channel") if x.get("id") == source_id), None)
            return source_name, source_id, ch, count, {
                "mode": "configured" if idx == 0 else "fallback",
                "score": 1.0,
                "suggestions": [],
            }
        if source_id and first_existing is None:
            ch = next((x for x in root.findall("channel") if x.get("id") == source_id), None)
            first_existing = (source_name, source_id, ch, count)

    verified = verified_fallback_for_channel(ch_cfg, roots, settings, verified_fallbacks)
    if verified is not None:
        return verified

    # Same-source fuzzy autodiscovery is deliberately conservative and only considers populated IDs.
    if settings.get("source_autodiscovery_enabled", True):
        source_name = ch_cfg.get("source")
        root = roots.get(source_name)
        if root is not None:
            auto_id, count, score, suggestions = source_autodiscovery(root, ch_cfg.get("name", ""), settings)
            if auto_id:
                ch = next((x for x in root.findall("channel") if x.get("id") == auto_id), None)
                return source_name, auto_id, ch, count, {
                    "mode": "autodiscovered",
                    "score": round(score, 3),
                    "suggestions": suggestions,
                }
            if first_existing is not None:
                return (*first_existing, {
                    "mode": "configured_empty",
                    "score": round(score, 3),
                    "suggestions": suggestions,
                })

    if first_existing is not None:
        return (*first_existing, {"mode": "configured_empty", "score": 0.0, "suggestions": []})
    return None, None, None, 0, {"mode": "missing", "score": 0.0, "suggestions": []}



_SCHEDULE_TITLE_CACHE = {}
_SCHEDULE_FINGERPRINT_CACHE = {}

def schedule_title_set(root: ET.Element, source_id: str, max_items: int = 160) -> set[str]:
    key = (id(root), source_id, max_items)
    if key in _SCHEDULE_TITLE_CACHE:
        return _SCHEDULE_TITLE_CACHE[key]
    out = set()
    for p in root.findall("programme"):
        if p.get("channel") != source_id:
            continue
        title = normalized((p.findtext("title") or ""))
        title = re.sub(r"^(?:🔴\s*)?(?:live|na żywo|powtórka|replay)\s*[:|\-]\s*", "", title, flags=re.I)
        folded = ascii_fold(title)
        if len(folded) >= 4:
            out.add(folded)
        if len(out) >= max_items:
            break
    _SCHEDULE_TITLE_CACHE[key] = out
    return out

def schedule_consensus(a: set[str], b: set[str]) -> float:
    """Legacy literal-title consensus, retained only as a fallback."""
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, min(len(a), len(b)))

def programme_fingerprint_context(p: ET.Element) -> str:
    title = p.findtext("title") or ""
    subtitle = p.findtext("sub-title") or ""
    desc = p.findtext("desc") or ""
    cats = " ".join((x.text or "") for x in p.findall("category"))
    return normalized(" ".join([title, subtitle, desc[:900], cats]))

def programme_fingerprint(p: ET.Element) -> dict | None:
    start = parse_xmltv_datetime(p.get("start", ""))
    if start is None:
        return None
    if start.tzinfo is not None:
        start_utc = start.astimezone(timezone.utc)
    else:
        start_utc = start.replace(tzinfo=timezone.utc)

    title = normalized(p.findtext("title") or "")
    context = programme_fingerprint_context(p)
    sport = sport_from_text(context)
    league = league_from_text(context)
    entities = participant_tokens(context)

    title_tokens = token_set(title) - EVENT_GENERIC_TOKENS
    if sport:
        title_tokens -= {ascii_fold(x) for x in sport.get("terms", [])}
    if league:
        title_tokens -= token_set(league.get("name", ""))
        for alias in league.get("aliases", []):
            title_tokens -= token_set(alias)

    # A fingerprint needs some event-specific signal. This avoids comparing generic
    # magazine/news slots solely because they start at the same time.
    has_signal = bool(sport or league or len(entities) >= 2 or len(title_tokens) >= 3)
    if not has_signal:
        return None

    return {
        "start_utc": start_utc,
        "start_iso": start_utc.isoformat(),
        "title": title,
        "title_folded": ascii_fold(title),
        "sport": sport.get("key") if sport else None,
        "league": league.get("key") if league else None,
        "league_name": league.get("name") if league else None,
        "entities": set(entities),
        "title_tokens": set(title_tokens),
    }

def schedule_fingerprint_items(root: ET.Element, source_id: str, max_items: int = 220) -> list[dict]:
    key = (id(root), source_id, max_items)
    if key in _SCHEDULE_FINGERPRINT_CACHE:
        return _SCHEDULE_FINGERPRINT_CACHE[key]
    out = []
    for p in root.findall("programme"):
        if p.get("channel") != source_id:
            continue
        fp = programme_fingerprint(p)
        if fp:
            out.append(fp)
        if len(out) >= max_items:
            break
    out.sort(key=lambda x: x["start_utc"])
    _SCHEDULE_FINGERPRINT_CACHE[key] = out
    return out

def fingerprint_pair_score(a: dict, b: dict, time_tolerance_minutes: int = 360,
                           same_slot_tolerance_minutes: int = 45,
                           repeat_min_delay_minutes: int = 60,
                           repeat_max_delay_minutes: int = 360) -> tuple[float, dict]:
    diff = abs((a["start_utc"] - b["start_utc"]).total_seconds()) / 60.0
    if diff <= same_slot_tolerance_minutes:
        slot_relation = "same_slot"
    elif repeat_min_delay_minutes <= diff <= repeat_max_delay_minutes:
        slot_relation = "repeat_or_replay"
    else:
        slot_relation = "different_slot"
    if diff > time_tolerance_minutes:
        return 0.0, {"time_delta_minutes": round(diff,1), "slot_relation": slot_relation}

    if a.get("sport") and b.get("sport") and a["sport"] != b["sport"]:
        return 0.0, {"time_delta_minutes":round(diff,1),"slot_relation":slot_relation,"sport_conflict":True}
    if a.get("league") and b.get("league") and a["league"] != b["league"]:
        # Different recognized competitions at the same time are not the same event.
        return 0.0, {"time_delta_minutes":round(diff,1),"slot_relation":slot_relation,"league_conflict":True}

    ea, eb = a.get("entities", set()), b.get("entities", set())
    common_entities = ea & eb
    entity_overlap = len(common_entities)
    entity_containment = (
        entity_overlap / max(1, min(len(ea), len(eb))) if ea and eb else 0.0
    )

    ta, tb = a.get("title_tokens", set()), b.get("title_tokens", set())
    common_title = ta & tb
    title_containment = (
        len(common_title) / max(1, min(len(ta), len(tb))) if ta and tb else 0.0
    )

    same_sport = bool(a.get("sport") and b.get("sport") and a["sport"] == b["sport"])
    same_league = bool(a.get("league") and b.get("league") and a["league"] == b["league"])
    title_sim = similarity(a.get("title",""), b.get("title",""))

    # Event identity evidence dominates language-dependent title similarity.
    score = 0.0
    reasons = []
    if entity_overlap >= 2 and entity_containment >= 0.50:
        score = max(score, 0.78 + min(0.12, 0.04 * (entity_overlap - 2)))
        reasons.append("participants")
    elif entity_overlap >= 1 and entity_containment >= 0.50:
        score = max(score, 0.62)
        reasons.append("participant")

    if same_league:
        score = max(score, 0.66)
        reasons.append("league")
    if same_sport and entity_overlap >= 1:
        score += 0.06
        reasons.append("sport")
    if same_league and entity_overlap >= 1:
        score += 0.08
        reasons.append("league+participant")
    if title_containment >= 0.60 and len(common_title) >= 2:
        score = max(score, 0.68)
        reasons.append("title_tokens")
    if title_sim >= 0.82:
        score = max(score, 0.72)
        reasons.append("title_similarity")

    # For individual sports/motorsport feeds, league + time can be enough even when
    # translated descriptions do not expose competitors consistently.
    if same_league and same_sport and diff <= 45:
        score = max(score, 0.74)
        reasons.append("league+sport+time")

    # Time is supporting evidence, not identity by itself.
    if score > 0:
        if diff <= 15:
            score += 0.08
            reasons.append("time<=15")
        elif diff <= 45:
            score += 0.05
            reasons.append("time<=45")
        elif slot_relation == "repeat_or_replay":
            score -= 0.10
            reasons.append("repeat_slot")
        else:
            score -= 0.15
            reasons.append("different_slot")

    score = max(0.0, min(1.0, score))
    return score, {
        "time_delta_minutes":round(diff,1),
        "slot_relation":slot_relation,
        "same_sport":same_sport,
        "same_league":same_league,
        "entity_overlap":entity_overlap,
        "entity_containment":round(entity_containment,3),
        "common_entities":sorted(common_entities)[:8],
        "title_token_overlap":len(common_title),
        "title_containment":round(title_containment,3),
        "title_similarity":round(title_sim,3),
        "reasons":reasons,
    }

def fingerprint_schedule_consensus(a: list[dict], b: list[dict], settings: dict) -> dict:
    pair_min = float(settings.get("source_recommendation_fingerprint_pair_min_score", 0.62))
    time_tol = int(settings.get("source_recommendation_fingerprint_time_tolerance_minutes", 360))
    same_slot_tol = int(settings.get("source_recommendation_fingerprint_same_slot_tolerance_minutes", 45))
    repeat_min = int(settings.get("source_recommendation_fingerprint_repeat_min_delay_minutes", 60))
    repeat_max = int(settings.get("source_recommendation_fingerprint_repeat_max_delay_minutes", 360))
    min_evidence = int(settings.get("source_recommendation_fingerprint_min_evidence", 4))
    if not a or not b:
        return {"score":0.0,"raw_score":0.0,"matched":0,"same_slot_matched":0,"repeat_matched":0,
                "a_count":len(a),"b_count":len(b),"evidence":min(len(a),len(b)),
                "method":"fingerprint","examples":[],"repeat_examples":[]}
    same_candidates, repeat_candidates = [], []
    for i, fa in enumerate(a):
        for j, fb in enumerate(b):
            diff = abs((fa["start_utc"] - fb["start_utc"]).total_seconds()) / 60.0
            if diff > time_tol:
                continue
            sc, details = fingerprint_pair_score(fa, fb, time_tol, same_slot_tol, repeat_min, repeat_max)
            if sc < pair_min:
                continue
            if details.get("slot_relation") == "same_slot":
                same_candidates.append((sc, i, j, details))
            elif details.get("slot_relation") == "repeat_or_replay":
                repeat_candidates.append((sc, i, j, details))
    same_candidates.sort(reverse=True, key=lambda x:x[0])
    used_a, used_b, same_matches = set(), set(), []
    for sc, i, j, details in same_candidates:
        if i in used_a or j in used_b:
            continue
        used_a.add(i); used_b.add(j); same_matches.append((sc, i, j, details))
    repeat_candidates.sort(reverse=True, key=lambda x:x[0])
    repeat_used_a, repeat_used_b, repeat_matches = set(used_a), set(used_b), []
    for sc, i, j, details in repeat_candidates:
        if i in repeat_used_a or j in repeat_used_b:
            continue
        repeat_used_a.add(i); repeat_used_b.add(j); repeat_matches.append((sc, i, j, details))
    evidence = min(len(a), len(b))
    matched = len(same_matches)
    raw = matched / max(1, evidence)
    evidence_factor = min(1.0, evidence / max(1, min_evidence))
    adjusted = raw * (0.55 + 0.45 * evidence_factor)
    def ex(rows):
        out=[]
        for sc, i, j, details in rows[:5]:
            out.append({
                "score":round(sc,3), "a_title":a[i]["title"], "b_title":b[j]["title"],
                "a_start":a[i]["start_iso"], "b_start":b[j]["start_iso"],
                "league":a[i].get("league_name") or b[j].get("league_name"),
                "common_entities":details.get("common_entities",[]),
                "time_delta_minutes":details.get("time_delta_minutes"),
                "slot_relation":details.get("slot_relation"),
            })
        return out
    return {
        "score":round(adjusted,3), "raw_score":round(raw,3), "matched":matched,
        "same_slot_matched":matched, "repeat_matched":len(repeat_matches),
        "a_count":len(a), "b_count":len(b), "evidence":evidence, "method":"fingerprint",
        "same_slot_tolerance_minutes":same_slot_tol,
        "examples":ex(same_matches), "repeat_examples":ex(repeat_matches),
    }

def annotate_schedule_consensus(rows: list[dict], roots: dict, settings: dict) -> list[dict]:
    if not settings.get("source_recommendation_schedule_consensus", True):
        return rows

    moderate = float(settings.get("source_recommendation_schedule_consensus_moderate", 0.35))
    strong = float(settings.get("source_recommendation_schedule_consensus_strong", 0.60))
    max_items = int(settings.get("source_recommendation_fingerprint_max_items", 220))
    verify_identity = float(settings.get("source_recommendation_schedule_verified_identity_score", 0.95))
    preferred_method = settings.get("source_recommendation_schedule_consensus_method", "fingerprint")

    for i, row in enumerate(rows):
        root = roots.get(row.get("source"))
        fps_a = schedule_fingerprint_items(root, row.get("source_id"), max_items) if root is not None else []
        titles_a = schedule_title_set(root, row.get("source_id")) if root is not None else set()

        best, best_details, peers = 0.0, None, []
        for j, other in enumerate(rows):
            if i == j or row.get("source") == other.get("source"):
                continue
            oroot = roots.get(other.get("source"))
            fps_b = schedule_fingerprint_items(oroot, other.get("source_id"), max_items) if oroot is not None else []

            if preferred_method == "fingerprint" and fps_a and fps_b:
                details = fingerprint_schedule_consensus(fps_a, fps_b, settings)
                sc = details["score"]
            else:
                titles_b = schedule_title_set(oroot, other.get("source_id")) if oroot is not None else set()
                sc = schedule_consensus(titles_a, titles_b)
                details = {
                    "score":round(sc,3),"raw_score":round(sc,3),
                    "matched":len(titles_a & titles_b),"a_count":len(titles_a),"b_count":len(titles_b),
                    "evidence":min(len(titles_a),len(titles_b)),"method":"exact_title","examples":[]
                }

            if sc > best:
                best, best_details = sc, details
            if sc >= moderate:
                peers.append({
                    "source":other.get("source"),"source_id":other.get("source_id"),
                    "score":round(sc,3),"method":details.get("method"),
                    "matched":details.get("matched"),"evidence":details.get("evidence")
                })

        grade = "strong" if best >= strong else ("moderate" if best >= moderate else "none")
        identity_score = float(row.get("score", 0.0))
        matched = int((best_details or {}).get("matched", 0))
        min_evidence = int(settings.get("source_recommendation_fingerprint_min_evidence", 4))
        schedule_verified = bool(
            grade == "strong" and identity_score >= verify_identity and matched >= min_evidence
        )

        row["schedule_consensus_max"] = round(best,3)
        row["schedule_consensus_grade"] = grade
        row["schedule_consensus_method"] = (best_details or {}).get("method", preferred_method)
        row["schedule_consensus_matched"] = matched
        row["schedule_consensus_same_slot_matched"] = int((best_details or {}).get("same_slot_matched", matched))
        row["schedule_consensus_repeat_matched"] = int((best_details or {}).get("repeat_matched", 0))
        row["schedule_consensus_evidence"] = int((best_details or {}).get("evidence", 0))
        row["schedule_consensus_raw"] = round(float((best_details or {}).get("raw_score",0.0)),3)
        row["schedule_consensus_same_slot_tolerance_minutes"] = int((best_details or {}).get("same_slot_tolerance_minutes", settings.get("source_recommendation_fingerprint_same_slot_tolerance_minutes", 45)))
        row["schedule_consensus_examples"] = (best_details or {}).get("examples",[])[:3]
        row["schedule_repeat_examples"] = (best_details or {}).get("repeat_examples",[])[:3]
        row["schedule_consensus_peers"] = sorted(peers, key=lambda x:x["score"], reverse=True)[:3]
        row["schedule_verified"] = schedule_verified
    return rows

def cross_source_recommendations(ch_cfg: dict, roots: dict, config: dict, limit: int = 8) -> list[dict]:
    target_name = ch_cfg.get("name", "")
    target_source = ch_cfg.get("source")
    source_cfgs = config.get("sources", {})
    target_country = (source_cfgs.get(target_source) or {}).get("sportguide_country")
    min_score = float(config.get("settings", {}).get("source_recommendation_min_score", 0.68))
    scored=[]

    for source_name, root in roots.items():
        counts = programme_count_by_channel(root)
        candidate_country = (source_cfgs.get(source_name) or {}).get("sportguide_country")
        for ch in root.findall("channel"):
            cid = ch.get("id") or ""
            count = counts.get(cid,0)
            if count <= 0:
                continue
            labels=[cid.replace("."," ")] + [x.text or "" for x in ch.findall("display-name")]
            best_score, best_label, best_identity = 0.0, "", {}
            for label in labels:
                sc, identity = channel_identity_score(
                    target_name, label,
                    require_brand=True,
                    strict_numbers=True,
                    require_critical=True,
                    strict_variants=bool(config.get("settings", {}).get("source_recommendation_strict_variants", True)),
                )
                if sc > best_score:
                    best_score, best_label, best_identity = sc, label, identity
            if best_score < min_score:
                continue

            same_source = source_name == target_source
            same_country = bool(target_country and candidate_country and target_country == candidate_country)
            # We never auto-apply cross-country schedules. Recommendations are diagnostic only.
            if same_source and best_score >= 0.90:
                grade = "strong_same_source"
            elif same_country and best_score >= 0.88:
                grade = "strong_same_country"
            elif best_score >= 0.90:
                grade = "brand_exact_cross_country"
            else:
                grade = "review"

            scored.append({
                "source":source_name,"source_id":cid,"label":best_label,
                "score":round(best_score,3),"programmes":count,
                "same_source":same_source,"same_country":same_country,
                "target_country":target_country,"candidate_country":candidate_country,
                "identity":best_identity,"recommendation_grade":grade,
                "auto_apply":False,
            })

    scored.sort(key=lambda x:(
        x["same_source"], x["same_country"],
        x["recommendation_grade"] in ("strong_same_source","strong_same_country"),
        x["score"], x["programmes"]
    ), reverse=True)
    out=[]; seen=set()
    for x in scored:
        k=(x["source"],x["source_id"])
        if k not in seen:
            out.append(x); seen.add(k)
        if len(out)>=limit:
            break
    return annotate_schedule_consensus(out, roots, config.get("settings", {}))

def make_channel_element(target_id: str, name: str, source_channel: ET.Element|None):
    ch = ET.Element("channel", {"id":target_id})
    ET.SubElement(ch, "display-name").text = name
    if source_channel is not None:
        for icon in source_channel.findall("icon"):
            ch.append(copy.deepcopy(icon))
    return ch

def programme_signature(prog: ET.Element) -> tuple:
    title = normalized((prog.findtext("title") or ""))
    return (prog.get("start", ""), prog.get("stop", ""), ascii_fold(title))

def deduplicate_programmes(programmes: list[ET.Element]) -> tuple[list[ET.Element], int]:
    seen, out, removed = set(), [], 0
    for p in programmes:
        sig = programme_signature(p)
        if sig in seen:
            removed += 1
            continue
        seen.add(sig)
        out.append(p)
    return out, removed

def xmltv_offset_minutes(value: str) -> int | None:
    m = re.match(r"^\d{14}(?:\s+([+-])(\d{2})(\d{2}))?", (value or "").strip())
    if not m or not m.group(1):
        return None
    mins=int(m.group(2))*60+int(m.group(3))
    return mins if m.group(1)=="+" else -mins


def parse_xmltv_wall_clock(value: str) -> datetime | None:
    m=re.match(r"^(\d{14})",(value or "").strip())
    return datetime.strptime(m.group(1),"%Y%m%d%H%M%S") if m else None


def overlap_list(intervals, warn_minutes: int):
    rows=[]
    for prev,cur in zip(intervals,intervals[1:]):
        delta=(cur[0]-prev[1]).total_seconds()/60
        if delta<=-warn_minutes:
            rows.append({"from":cur[0].isoformat(),"to":prev[1].isoformat(),"minutes":round(abs(delta),1)})
    return rows


def analyze_schedule(programmes: list[ET.Element], settings: dict, duplicates_removed: int = 0) -> dict:
    gap_warn=int(settings.get("quality_gap_warning_minutes",180)); overlap_warn=int(settings.get("quality_overlap_warning_minutes",5)); low_threshold=int(settings.get("quality_low_programme_threshold",8))
    valid=[]; wall_valid=[]; invalid=0; starts_seen=defaultdict(int); offsets=[]
    for p in programmes:
        sr,er=p.get("start",""),p.get("stop",""); start=parse_xmltv_datetime(sr); stop=parse_xmltv_datetime(er)
        if not start or not stop or stop<=start:
            invalid+=1; continue
        valid.append((start,stop,p)); starts_seen[sr]+=1
        ws,we=parse_xmltv_wall_clock(sr),parse_xmltv_wall_clock(er)
        if ws and we and we>ws: wall_valid.append((ws,we,p))
        off=xmltv_offset_minutes(sr)
        if off is not None: offsets.append(off)
    valid.sort(key=lambda x:x[0]); wall_valid.sort(key=lambda x:x[0])
    gaps=[]; overlaps_utc=[]
    for prev,cur in zip(valid,valid[1:]):
        delta=(cur[0]-prev[1]).total_seconds()/60
        if delta>=gap_warn: gaps.append({"from":prev[1].isoformat(),"to":cur[0].isoformat(),"minutes":round(delta,1)})
        elif delta<=-overlap_warn: overlaps_utc.append({"from":cur[0].isoformat(),"to":prev[1].isoformat(),"minutes":round(abs(delta),1)})
    overlaps_wall=overlap_list(wall_valid,overlap_warn)
    unique_offsets=sorted(set(offsets)); mixed=len(unique_offsets)>1; overlaps=overlaps_utc; mode="absolute_time"
    if mixed and settings.get("quality_use_wall_clock_for_mixed_offsets",True) and overlaps_utc:
        if len(overlaps_wall)/max(1,len(overlaps_utc)) <= float(settings.get("quality_mixed_offset_overlap_ratio",0.5)):
            overlaps=overlaps_wall; mode="wall_clock_due_to_mixed_offsets"
    duplicate_start_slots=sum(v-1 for v in starts_seen.values() if v>1)
    first=valid[0][0] if valid else None; last=max((x[1] for x in valid),default=None); coverage=round((last-first).total_seconds()/3600,1) if first and last else 0.0
    score=100.0; warnings=[]
    if not programmes: score=10.0; warnings.append("no_programmes")
    else:
        if len(programmes)<low_threshold: score-=12; warnings.append("low_programme_count")
        if invalid: score-=min(25,invalid*2.5); warnings.append("invalid_times")
        if duplicates_removed: score-=min(10,duplicates_removed*1.5); warnings.append("exact_duplicates")
        if overlaps: score-=min(18,len(overlaps)*2.0); warnings.append("overlaps")
        if gaps: score-=min(12,len(gaps)*0.75); warnings.append("large_gaps")
        if duplicate_start_slots: score-=min(10,duplicate_start_slots); warnings.append("duplicate_start_slots")
        if coverage and coverage<12: score-=8; warnings.append("short_coverage")
        if mixed: warnings.append("mixed_timezone_offsets")
    return {"technical_score":round(max(0,score),1),"programmes_analyzed":len(programmes),"valid_intervals":len(valid),"invalid_times":invalid,"exact_duplicates_removed":duplicates_removed,"duplicate_start_slots":duplicate_start_slots,"large_gaps":len(gaps),"overlaps":len(overlaps),"overlaps_raw_utc":len(overlaps_utc),"overlaps_wall_clock":len(overlaps_wall),"overlap_analysis_mode":mode,"timezone_offsets_minutes":unique_offsets,"mixed_timezone_offsets":mixed,"coverage_hours":coverage,"first_start":first.isoformat() if first else None,"last_stop":last.isoformat() if last else None,"warnings":warnings,"gap_examples":gaps[:5],"overlap_examples":overlaps[:5]}


def cleanup_mixed_offset_programmes(programmes: list[ET.Element], settings: dict,
                                    source_timezone: str | None) -> tuple[list[ET.Element], int, dict]:
    info = {"applied": False, "removed": 0, "chosen_offset_minutes": None, "reason": None}
    if not settings.get("mixed_offset_cleanup_enabled", True) or len(programmes) < 2:
        return programmes, 0, info

    offsets = defaultdict(list)
    no_offset = []
    for p in programmes:
        off = xmltv_offset_minutes(p.get("start", ""))
        if off is None:
            no_offset.append(p)
        else:
            offsets[off].append(p)

    if len(offsets) <= 1:
        return programmes, 0, info

    raw_quality = analyze_schedule(programmes, {**settings, "quality_use_wall_clock_for_mixed_offsets": False}, 0)
    if raw_quality.get("overlaps_raw_utc", 0) < int(settings.get("mixed_offset_cleanup_min_overlaps", 8)):
        return programmes, 0, info

    chosen = None
    if source_timezone and settings.get("mixed_offset_cleanup_prefer_source_timezone", True):
        starts = [parse_xmltv_datetime(p.get("start", "")) for p in programmes]
        starts = [x for x in starts if x is not None and x.tzinfo is not None]
        if starts:
            sample = sorted(starts)[len(starts)//2]
            try:
                expected = int(sample.astimezone(ZoneInfo(source_timezone)).utcoffset().total_seconds() // 60)
                if expected in offsets:
                    chosen = expected
                    info["reason"] = "source_timezone"
            except Exception:
                pass

    if chosen is None:
        chosen = max(offsets, key=lambda x: len(offsets[x]))
        info["reason"] = "largest_offset_group"

    ratio = len(offsets[chosen]) / max(1, sum(len(v) for v in offsets.values()))
    if ratio < float(settings.get("mixed_offset_cleanup_min_group_ratio", 0.20)):
        return programmes, 0, info

    kept = list(offsets[chosen]) + no_offset
    kept.sort(key=lambda p: p.get("start", ""))
    removed = len(programmes) - len(kept)
    info.update({
        "applied": removed > 0,
        "removed": removed,
        "chosen_offset_minutes": chosen,
        "group_counts": {str(k): len(v) for k, v in sorted(offsets.items())},
    })
    return kept, removed, info


def transform_programme(prog: ET.Element, target_id: str, settings: dict, replacements: dict,
                        external_events: list[dict], stats: dict, station_timezone: str | None = None,
                        sofascore_state: dict | None = None):
    p = copy.deepcopy(prog)
    p.set("channel", target_id)
    title_el = p.find("title")
    if title_el is None or not normalized(title_el.text):
        return p

    original = normalized(title_el.text)
    desc = " ".join(normalized(x.text) for x in p.findall("desc"))
    cats = " ".join(normalized(x.text) for x in p.findall("category"))
    context = " ".join([desc, cats])

    start_dt = parse_xmltv_datetime(p.get("start", ""))
    stop_dt = parse_xmltv_datetime(p.get("stop", ""))
    prog_date = start_dt.date() if start_dt else None
    ext, ext_score, match_details = best_external_match(
        original,
        prog_date,
        external_events,
        float(settings.get("external_live_min_score", 0.64)),
        prog_dt=start_dt,
        time_tolerance_minutes=int(settings.get("external_live_time_tolerance_minutes", 120)),
        min_title_score=float(settings.get("external_live_min_title_score", 0.48)),
        context_text=context if settings.get("external_live_use_description", True) else cats,
        station_timezone=station_timezone,
        date_tolerance_days=int(settings.get("external_live_date_tolerance_days", 0)),
        entity_min_overlap=int(settings.get("external_live_entity_min_overlap", 2)),
    )

    # v3.19: verify the actual event clock independently of the TV guide.
    sofa_state = sofascore_state if sofascore_state is not None else {}
    preliminary_sport = sport_from_text(" ".join([original, context, target_id]))
    sofa = sofascore_verify_programme(
        " ".join([original, context]), start_dt, station_timezone,
        preliminary_sport.get("key") if preliminary_sport else None, settings, sofa_state
    )
    if sofa.get("decision") == "live":
        stats["sofascore_live_confirmed"] = stats.get("sofascore_live_confirmed", 0) + 1
    elif sofa.get("decision") == "replay":
        stats["sofascore_replays_suppressed"] = stats.get("sofascore_replays_suppressed", 0) + 1

    pre_audit = None
    if ext:
        pre_conf = confidence_label(ext_score, float(settings.get("external_live_high_confidence", 0.78)))
        pre_audit = audit_external_match(ext_score, match_details, pre_conf, settings)
        if settings.get("external_live_reject_risky", False) and pre_audit.get("grade") == "risky":
            stats["external_live_rejected_risky"] += 1
            ext = None

    new_title, meta = format_title(original, context, settings, replacements, ext, external_score=ext_score if ext else None, channel_name=target_id, prog_dt=start_dt, stop_dt=stop_dt, station_timezone=station_timezone, sofascore_verdict=sofa)
    title_el.text = new_title
    title_el.set("lang", settings.get("target_language", "pl"))

    # v3.18 translated-title-only mode: keep exactly one output title. Some XMLTV
    # sources expose the same programme title in several languages; leaving those siblings
    # makes TiviMate display the untranslated/original title next to our Polish one.
    if settings.get("translated_title_only", False):
        for other_title in list(p.findall("title")):
            if other_title is not title_el:
                p.remove(other_title)
        for subtitle in list(p.findall("sub-title")):
            st_text = normalized(subtitle.text or "")
            if (st_text and ascii_fold(st_text) == ascii_fold(original)) or re.match(r"^(?:oryginał|original)\s*:", st_text, flags=re.I):
                p.remove(subtitle)

    if settings.get("preserve_original_title", True) and new_title != original and p.find("sub-title") is None:
        st = ET.SubElement(p, "sub-title", {"lang":"mul"})
        st.text = ("Oryginał: " if settings.get("target_language") == "pl" else "Original: ") + original

    if meta["live"]:
        add_category_unique(p, "Live", "en")
    if meta["replay"]:
        add_category_unique(p, "Replay", "en")
    if meta["stage"]:
        add_category_unique(p, meta["stage"], "en")
    if meta["sport"]:
        sport = next(s for s in SPORTS if s["key"] == meta["sport"])
        lang = settings.get("target_language","pl")
        add_category_unique(p, sport.get(lang, sport["en"]), lang)
    if meta["league"] and settings.get("add_league_category", True):
        add_category_unique(p, meta["league_name"], "en")

    if ext:
        if settings.get("external_live_one_to_one", True) and not settings.get("external_live_event_reuse_allowed", False):
            ext["_used"] = True
        event_key = external_event_key(ext)
        high_threshold = float(settings.get("external_live_high_confidence", 0.78))
        conf = confidence_label(ext_score, high_threshold)
        match_row = {
            "external_event_key": event_key,
            "channel_id": target_id,
            "start": p.get("start"),
            "original_title": original,
            "output_title": new_title,
            "external_title": ext.get("title"),
            "external_source": ext.get("source"),
            "external_url": ext.get("source_url"),
            "score": round(ext_score, 3),
            "confidence": conf,
            "details": match_details,
            "audit": pre_audit or audit_external_match(ext_score, match_details, conf, settings),
            "league": meta.get("league_name"),
            "sport": meta.get("sport"),
        }
        stats["live_matches"].append(match_row)
        stats["external_live_high"] += int(conf == "high")
        stats["external_live_medium"] += int(conf == "medium")

        if settings.get("debug_provenance_in_desc", False):
            desc_el = p.find("desc")
            note = f"[LIVE match: {ext.get('source','external')}, score={ext_score:.2f}, confidence={conf}]"
            if desc_el is None:
                desc_el = ET.SubElement(p, "desc", {"lang":"en"})
                desc_el.text = note
            else:
                desc_el.text = normalized((desc_el.text or "") + " " + note)

    stats["programmes"] += 1
    stats["live"] += int(meta["live"])
    stats["live_explicit"] += int(meta["explicit_live"] and not meta["external_live"])
    stats["external_live"] += int(meta["external_live"])
    stats["replay"] += int(meta["replay"])
    stats["stages"] += int(bool(meta["stage"]))
    stats["translated"] += int(meta["translated"])
    stats["live_inferred"] = stats.get("live_inferred", 0) + int(bool(meta.get("live_inferred")))
    stats["live_morning_suppressed"] = stats.get("live_morning_suppressed", 0) + int(bool(meta.get("live_morning_suppressed")))
    stats["sofascore_live"] = stats.get("sofascore_live", 0) + int(bool(meta.get("sofascore_live")))
    stats["sofascore_replay"] = stats.get("sofascore_replay", 0) + int(bool(meta.get("sofascore_replay")))
    if meta["sport"]:
        stats["sports"][meta["sport"]] += 1
    stats["participant_enriched"] = stats.get("participant_enriched", 0) + int(bool(meta.get("participants_enriched")))
    if meta["league"]:
        stats["leagues"][meta["league_name"]] += 1
    return p


def external_snapshot_metadata(report: dict) -> dict:
    ex = report.get("external_live", {}) or {}
    channel_status = ex.get("channel_status") or {}
    rows = []
    if isinstance(channel_status, dict):
        for cid in sorted(channel_status):
            row = channel_status.get(cid) or {}
            fetch_meta = row.get("fetch_meta") or {}
            rows.append({
                "channel_id": cid,
                "status": row.get("status"),
                "data_origin": row.get("data_origin"),
                "events": row.get("events", 0),
                "successful_url": row.get("successful_url"),
                "fetched_at_utc": fetch_meta.get("fetched_at_utc"),
            })
    basis = {
        "events_found": ex.get("events_found", 0),
        "channels_with_events": ex.get("channels_with_events", 0),
        "pages_current": ex.get("pages_current", 0),
        "pages_fresh_cache": ex.get("pages_fresh_cache", 0),
        "pages_stale_cache": ex.get("pages_stale_cache", 0),
        "rows": rows,
    }
    raw = json.dumps(basis, sort_keys=True, ensure_ascii=False)
    snapshot_id = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16] if rows else None
    if ex.get("pages_current", 0):
        origin = "current"
    elif ex.get("pages_fresh_cache", 0):
        origin = "fresh_cache"
    elif ex.get("pages_stale_cache", 0):
        origin = "stale_cache"
    elif ex.get("events_found_event_lkg", 0):
        origin = "event_lkg"
    else:
        origin = None
    return {
        "external_snapshot_id": snapshot_id,
        "external_snapshot_origin": origin,
        "external_snapshot_channels": len(rows),
        "external_snapshot_events_found": ex.get("events_found", 0),
    }


def health_snapshot_from_report(report: dict) -> dict:
    s = report.get("summary", {})
    ex = report.get("external_live", {})
    metric_keys = [
        "programmes","channels_total","channels_matched","channels_missing","channels_active","channels_empty",
        "quality_average","external_live","external_live_high","external_live_medium","external_channels_with_events",
        "external_channels_current","external_channels_fresh_cache","external_channels_stale_cache","external_channels_event_lkg",
        "external_channels_unavailable","external_data_age_max_hours","external_data_age_avg_hours",
        "source_degraded","source_unavailable","source_salvaged_feeds","source_coverage_warnings",
        "verified_fallbacks_applied","channel_lkg_recoveries","external_same_channel_event_reuse","external_duplicate_event_matches",
    ]
    snap = {k:s.get(k,0) for k in metric_keys}
    snap.update({
        "version":report.get("version"),
        "generated_at_utc":report.get("generated_at_utc"),
        "external_events_found":ex.get("events_found",0),
        "external_network_failures":ex.get("network_failures",0),
        "sources":{},
    })
    snap.update(external_snapshot_metadata(report))
    for name,row in (report.get("sources") or {}).items():
        snap["sources"][name]={
            "ok":bool(row.get("ok")),
            "current_ok":bool(row.get("current_ok")),
            "health":row.get("health"),
            "degraded":bool(row.get("degraded")),
            "coverage_pct":row.get("configured_channel_coverage_pct"),
            "source_programmes":row.get("source_programmes",0),
            "source_channels":row.get("source_channels",0),
        }
    return snap

def _history_rows_from_file(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        rows=data.get("builds",[]) if isinstance(data,dict) else []
        return [x for x in rows if isinstance(x,dict)]
    except Exception:
        return []

def _dedupe_history_rows(rows: list[dict]) -> list[dict]:
    dedup={}
    order=[]
    for item in rows:
        snap=(item or {}).get("snapshot") or {}
        key=(item.get("generated_at_utc") or snap.get("generated_at_utc"), item.get("version") or snap.get("version"))
        if key==(None,None):
            continue
        if key not in dedup: order.append(key)
        merged=dict(dedup.get(key,{}) or {})
        merged.update(item)
        if not merged.get("snapshot") and snap: merged["snapshot"]=snap
        merged.setdefault("generated_at_utc",snap.get("generated_at_utc"))
        merged.setdefault("version",snap.get("version"))
        dedup[key]=merged
    out=[dedup[k] for k in order]
    out.sort(key=lambda x: x.get("generated_at_utc") or "")
    return out

def load_health_history(settings: dict) -> dict:
    """Canonical unified history. Imports legacy cache and old seed files automatically."""
    rows=[]
    canonical=BASE_DIR / settings.get("health_history_file", ".cache/build_history.json")
    rows.extend(_history_rows_from_file(canonical))
    legacy=BASE_DIR / settings.get("health_legacy_history_file", ".cache/build_health_history.json")
    if legacy != canonical:
        rows.extend(_history_rows_from_file(legacy))
    unified_seed=BASE_DIR / settings.get("health_unified_seed_file","build_history_seed.json")
    rows.extend(_history_rows_from_file(unified_seed))
    # Backward compatibility with v3.15 seed/history layout.
    old_trend_seed=BASE_DIR / settings.get("health_trend_seed_file","build_health_trend_seed.json")
    if old_trend_seed.exists():
        try:
            data=json.loads(old_trend_seed.read_text(encoding="utf-8"))
            for row in data.get("builds",[]):
                snap=(row or {}).get("snapshot")
                if isinstance(snap,dict):
                    rows.append({"generated_at_utc":snap.get("generated_at_utc"),"version":snap.get("version"),"snapshot":snap})
        except Exception:
            pass
    rows=_dedupe_history_rows(rows)
    max_builds=max(2,int(settings.get("health_history_max_builds",30)))
    return {"version":2,"builds":rows[-max_builds:]}


def load_health_seed(settings: dict) -> tuple[dict|None,str|None]:
    path=BASE_DIR / settings.get("health_seed_baseline_file","build_health_seed.json")
    if path.exists():
        try:
            data=json.loads(path.read_text(encoding="utf-8"))
            snap=data.get("snapshot") if isinstance(data,dict) else None
            if isinstance(snap,dict):
                return snap, data.get("source") or "seed_file"
        except Exception:
            pass
    return None,None


def discover_previous_version_health_baseline(settings: dict) -> tuple[dict|None,str|None]:
    """Prefer a real sibling version's generated docs/report.json on the first v3.14 run."""
    parent=BASE_DIR.parent
    candidates=[]
    for p in parent.iterdir():
        if not p.is_dir() or p==BASE_DIR:
            continue
        m=re.match(r"^sports-epg-v(\d+)\.(\d+)(?:\.(\d+))?$",p.name)
        if not m:
            continue
        ver=tuple(int(x or 0) for x in m.groups())
        report_path=p/"docs"/"report.json"
        if report_path.exists():
            candidates.append((ver,report_path,p.name))
    candidates.sort(reverse=True,key=lambda x:x[0])
    for _,path,name in candidates:
        try:
            r=json.loads(path.read_text(encoding="utf-8"))
            snap=health_snapshot_from_report(r)
            if snap.get("channels_total"):
                return snap,f"sibling:{name}/docs/report.json"
        except Exception:
            continue
    return load_health_seed(settings)


def pct_drop(previous, current) -> float:
    try:
        previous=float(previous); current=float(current)
    except (TypeError,ValueError):
        return 0.0
    if previous <= 0 or current >= previous:
        return 0.0
    return 100.0*(previous-current)/previous



def load_health_trend_seed(settings: dict) -> list[dict]:
    path=BASE_DIR / settings.get("health_trend_seed_file","build_health_trend_seed.json")
    if not path.exists():
        return []
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        rows=data.get("builds",[]) if isinstance(data,dict) else []
        out=[]
        for row in rows:
            snap=row.get("snapshot") if isinstance(row,dict) else None
            if isinstance(snap,dict): out.append(snap)
        return out
    except Exception:
        return []


def collect_health_trend_snapshots(history: dict, current: dict, settings: dict) -> list[dict]:
    """Combine seed + persistent history + current, de-duplicated chronologically."""
    rows=[]
    rows.extend(load_health_trend_seed(settings))
    for item in history.get("builds",[]):
        snap=(item or {}).get("snapshot")
        if isinstance(snap,dict): rows.append(snap)
    rows.append(current)
    dedup={}
    order=[]
    for snap in rows:
        key=(snap.get("generated_at_utc"),snap.get("version"))
        if key not in dedup: order.append(key)
        dedup[key]=snap
    rows=[dedup[k] for k in order]
    rows.sort(key=lambda x: x.get("generated_at_utc") or "")
    window=max(3,int(settings.get("health_trend_window_builds",5)))
    return rows[-window:]


def _median(values):
    vals=sorted(float(x) for x in values if x is not None)
    if not vals: return 0.0
    n=len(vals); mid=n//2
    return vals[mid] if n%2 else (vals[mid-1]+vals[mid])/2.0


def trend_confidence(builds: int, classification: str, persistent: bool, settings: dict, independent_builds: int | None = None) -> tuple[str,int]:
    """Confidence grows with independent evidence, not just repeated executions."""
    if not settings.get("health_trend_confidence_enabled",True):
        return "disabled",0
    evidence_builds = max(0, int(independent_builds if independent_builds is not None else builds))
    medium_builds=max(3,int(settings.get("health_trend_confidence_medium_builds",3)))
    high_builds=max(medium_builds+1,int(settings.get("health_trend_confidence_high_builds",5)))
    if evidence_builds < medium_builds:
        score=max(15,min(45,15*evidence_builds))
    elif evidence_builds < high_builds:
        score=60 + 12*(evidence_builds-medium_builds)
    else:
        score=85 + min(15,3*(evidence_builds-high_builds))
    if persistent: score+=5
    elif classification=="single_anomaly": score+=2
    elif classification=="improving": score+=3
    score=max(0,min(100,int(round(score))))
    high=int(settings.get("health_trend_confidence_high_score",85))
    medium=int(settings.get("health_trend_confidence_medium_score",55))
    label="high" if score>=high else ("medium" if score>=medium else "low")
    return label,score


def _apply_trend_confidence(result: dict, settings: dict) -> dict:
    label,score=trend_confidence(int(result.get("builds",0)),str(result.get("classification")),bool(result.get("persistent")),settings,independent_builds=int(result.get("independent_observations", result.get("builds",0)) or 0))
    result["confidence"]=label
    result["confidence_score"]=score
    return result


def classify_metric_trend(name: str, values: list[float], settings: dict, rows: list[dict] | None = None) -> dict:
    """Classify stable/improving/single anomaly/persistent regression.
    V3.18 makes external metrics snapshot-aware so repeated builds against the same
    cached Sport TV Guide snapshot do not overstate confidence or persistence.
    """
    n=len(values)
    min_builds=max(3,int(settings.get("health_trend_min_builds",3)))
    snapshot_aware = name in {"external_live","external_channels_with_events","external_network_failures","external_data_age_max_hours"}
    snapshot_ids=[]
    if snapshot_aware and rows:
        for row in rows:
            sid=(row or {}).get("external_snapshot_id")
            if sid:
                snapshot_ids.append(sid)
    independent=len(list(dict.fromkeys(snapshot_ids))) if snapshot_ids else n
    result={"metric":name,"values":values,"builds":n,"independent_observations":independent,
            "snapshot_aware":snapshot_aware,"classification":"insufficient_history","persistent":False,
            "current":values[-1] if values else None,"baseline":None,"change":0.0,"change_pct":0.0}
    if n < min_builds:
        return _apply_trend_confidence(result,settings)
    higher_better=name in {"external_live","external_channels_with_events","channels_active","channels_matched","quality_average"}
    lower_better=name in {"external_network_failures","external_data_age_max_hours"}
    baseline_values=values[:-1] or values
    baseline=_median(baseline_values)
    cur=float(values[-1]); result["baseline"]=round(baseline,3)
    delta=cur-baseline; result["change"]=round(delta,3)
    if baseline:
        result["change_pct"]=round(100.0*delta/abs(baseline),1)
    if name=="external_live": threshold=max(1.0,baseline*float(settings.get("health_trend_external_live_watch_pct",15))/100.0)
    elif name=="external_channels_with_events": threshold=max(1.0,baseline*float(settings.get("health_trend_external_channels_watch_pct",15))/100.0)
    elif name=="channels_active": threshold=float(settings.get("health_trend_active_drop_watch",1))
    elif name=="channels_matched": threshold=1.0
    elif name=="quality_average": threshold=float(settings.get("health_trend_quality_drop_watch",0.5))
    elif name=="external_network_failures": threshold=float(settings.get("health_trend_network_failures_watch",5))
    elif name=="external_data_age_max_hours": threshold=float(settings.get("health_trend_data_age_watch_hours",3.0))
    else: threshold=1.0
    result["watch_threshold"]=round(threshold,3)
    if higher_better:
        bad=(baseline-cur)>=threshold
        good=(cur-baseline)>=threshold
        bad_fn=lambda v,b: (b-v)>=threshold
    elif lower_better:
        bad=(cur-baseline)>=threshold
        good=(baseline-cur)>=threshold
        bad_fn=lambda v,b: (v-b)>=threshold
    else:
        bad=good=False; bad_fn=lambda v,b: False
    if good:
        result["classification"]="improving"
        return _apply_trend_confidence(result,settings)

    monotonic=False
    if len(values)>=3:
        a,b,c=map(float,values[-3:])
        if higher_better: monotonic=(a>b>c and (a-c)>=threshold)
        elif lower_better: monotonic=(a<b<c and (c-a)>=threshold)
    unique_required=max(2,int(settings.get("health_trend_external_unique_snapshots_required",2)))
    if monotonic:
        if snapshot_aware and rows:
            latest_three=[r.get("external_snapshot_id") for r in rows[-3:] if r.get("external_snapshot_id")]
            result["latest_unique_snapshots"]=len(list(dict.fromkeys(latest_three)))
            if result["latest_unique_snapshots"] < unique_required:
                monotonic=False
                result["awaiting_snapshot_confirmation"]=True
        if monotonic:
            result["persistent"]=True
            result["classification"]="persistent_regression"
            return _apply_trend_confidence(result,settings)
    if not bad:
        result["classification"]="stable"
        return _apply_trend_confidence(result,settings)
    persistent_points=max(2,int(settings.get("health_trend_persistent_points",2)))
    earlier=values[:-persistent_points]
    ref=_median(earlier) if earlier else baseline
    latest=values[-persistent_points:]
    both_bad=len(latest)>=persistent_points and all(bad_fn(float(v),ref) for v in latest)
    if snapshot_aware and rows:
        latest_ids=[r.get("external_snapshot_id") for r in rows[-persistent_points:] if r.get("external_snapshot_id")]
        result["latest_unique_snapshots"]=len(list(dict.fromkeys(latest_ids)))
        if both_bad and result["latest_unique_snapshots"] < unique_required:
            both_bad=False
            result["awaiting_snapshot_confirmation"]=True
    result["persistent"]=bool(both_bad)
    result["classification"]="persistent_regression" if result["persistent"] else "single_anomaly"
    return _apply_trend_confidence(result,settings)


def evaluate_health_trends(history: dict, current: dict, settings: dict) -> dict:
    rows=collect_health_trend_snapshots(history,current,settings)
    metrics=["external_live","external_channels_with_events","channels_active","channels_matched","quality_average",
             "external_network_failures","external_data_age_max_hours"]
    evaluated=[]
    for metric in metrics:
        vals=[]
        for row in rows:
            v=row.get(metric,0)
            try: vals.append(float(v or 0))
            except (TypeError,ValueError): vals.append(0.0)
        evaluated.append(classify_metric_trend(metric,vals,settings,rows=rows))
    persistent=[x for x in evaluated if x.get("classification")=="persistent_regression"]
    anomalies=[x for x in evaluated if x.get("classification")=="single_anomaly"]
    improving=[x for x in evaluated if x.get("classification")=="improving"]
    status="persistent_regression" if persistent else ("single_anomaly" if anomalies else ("improving" if improving else "stable"))
    confidence_scores=[int(x.get("confidence_score",0) or 0) for x in evaluated]
    confidence_score=min(confidence_scores) if confidence_scores else 0
    high=int(settings.get("health_trend_confidence_high_score",85)); medium=int(settings.get("health_trend_confidence_medium_score",55))
    confidence="high" if confidence_score>=high else ("medium" if confidence_score>=medium else "low")
    return {
        "version":"3.18","window_builds":len(rows),"configured_window":settings.get("health_trend_window_builds",5),
        "min_builds":settings.get("health_trend_min_builds",3),"status":status,
        "confidence":confidence,"confidence_score":confidence_score,
        "metrics":evaluated,"persistent_regressions":persistent,"single_anomalies":anomalies,"improving_metrics":improving,
        "series":[{"version":r.get("version"),"generated_at_utc":r.get("generated_at_utc"),
                   "external_live":r.get("external_live"),"external_channels_with_events":r.get("external_channels_with_events"),
                   "channels_active":r.get("channels_active"),"channels_matched":r.get("channels_matched"),
                   "quality_average":r.get("quality_average"),"external_network_failures":r.get("external_network_failures"),
                   "external_data_age_max_hours":r.get("external_data_age_max_hours"),
                   "external_snapshot_id":r.get("external_snapshot_id"),"external_snapshot_origin":r.get("external_snapshot_origin")} for r in rows]
    }

def calculate_health_score(alerts: list[dict], trend: dict, current: dict, settings: dict|None=None) -> tuple[int,dict]:
    """Baseline-aware operational score.

    V3.18 keeps the confidence-aware penalty and adds snapshot-aware trend evidence for one-off trend anomalies. This keeps a build
    operationally healthy while avoiding a misleading perfect 100/100 when the trend monitor has
    already detected a meaningful deviation. Persistent regressions remain penalized more strongly.
    """
    settings=settings or {}
    score=100
    components={"start":100,"critical_alert_penalty":0,"warning_alert_penalty":0,"persistent_trend_penalty":0,
                "single_anomaly_penalty":0,"single_anomaly_penalty_details":[],
                "unavailable_penalty":0,"integrity_penalty":0,"stale_data_penalty":0}
    crit=sum(1 for a in alerts if a.get("severity")=="critical")
    warn=sum(1 for a in alerts if a.get("severity")=="warning")
    components["critical_alert_penalty"]=min(60,25*crit); score-=components["critical_alert_penalty"]
    components["warning_alert_penalty"]=min(32,8*warn); score-=components["warning_alert_penalty"]
    persistent=len(trend.get("persistent_regressions",[]))
    components["persistent_trend_penalty"]=min(20,5*persistent); score-=components["persistent_trend_penalty"]

    # A single anomaly is intentionally not promoted to a warning by itself, but v3.18 lets it
    # shave a few points off the score according to trend confidence. Low/medium/high defaults are
    # 1/4/7 points per anomaly, capped globally at 12 points.
    if settings.get("health_score_single_anomaly_penalty_enabled",True):
        penalty_map={
            "low":int(settings.get("health_score_single_anomaly_penalty_low",1)),
            "medium":int(settings.get("health_score_single_anomaly_penalty_medium",4)),
            "high":int(settings.get("health_score_single_anomaly_penalty_high",7)),
        }
        raw=0; details=[]
        for anomaly in trend.get("single_anomalies",[]) or []:
            confidence=str(anomaly.get("confidence") or trend.get("confidence") or "low")
            points=max(0,int(penalty_map.get(confidence,penalty_map["low"])))
            if points:
                raw+=points
                details.append({"metric":anomaly.get("metric"),"confidence":confidence,"points":points,
                                "change_pct":anomaly.get("change_pct"),"current":anomaly.get("current"),
                                "baseline":anomaly.get("baseline")})
        cap=max(0,int(settings.get("health_score_single_anomaly_penalty_max",12)))
        components["single_anomaly_penalty"]=min(cap,raw)
        components["single_anomaly_penalty_details"]=details
        score-=components["single_anomaly_penalty"]

    unavailable=int(current.get("source_unavailable",0) or 0)+int(current.get("external_channels_unavailable",0) or 0)
    components["unavailable_penalty"]=min(20,4*unavailable); score-=components["unavailable_penalty"]
    integrity=max(int(current.get("external_same_channel_event_reuse",0) or 0),int(current.get("external_duplicate_event_matches",0) or 0))
    if integrity:
        components["integrity_penalty"]=25; score-=25
    age=float(current.get("external_data_age_max_hours",0) or 0)
    if age>=12: components["stale_data_penalty"]=15
    elif age>=6: components["stale_data_penalty"]=6
    score-=components["stale_data_penalty"]
    score=max(0,min(100,int(round(score))))
    components["final"]=score
    return score,components

def build_health_evaluation(report: dict, settings: dict) -> tuple[dict,dict]:
    history=load_health_history(settings)
    current=health_snapshot_from_report(report)
    builds=history.get("builds",[])
    previous=builds[-1].get("snapshot") if builds else None
    baseline_source="history" if previous else None
    if not previous:
        previous,baseline_source=discover_previous_version_health_baseline(settings)

    alerts=[]
    source_regressions=[]
    def alert(severity,code,message,current_value=None,previous_value=None,threshold=None):
        alerts.append({"severity":severity,"code":code,"message":message,
                       "current":current_value,"previous":previous_value,"threshold":threshold})

    if previous:
        matched_drop=int(previous.get("channels_matched",0))-int(current.get("channels_matched",0))
        matched_threshold=int(settings.get("health_channels_matched_drop_critical",1))
        if matched_drop >= matched_threshold:
            alert("critical","channels_matched_drop",f"Matched channels dropped by {matched_drop}.",
                  current.get("channels_matched"),previous.get("channels_matched"),matched_threshold)

        active_drop=int(previous.get("channels_active",0))-int(current.get("channels_active",0))
        active_threshold=int(settings.get("health_channels_active_drop_warn",2))
        if active_drop >= active_threshold:
            alert("warning","channels_active_drop",f"Active channels dropped by {active_drop}.",
                  current.get("channels_active"),previous.get("channels_active"),active_threshold)

        ext_drop=pct_drop(previous.get("external_live",0),current.get("external_live",0))
        ext_warn=float(settings.get("health_external_live_drop_warn_pct",30))
        ext_critical=float(settings.get("health_external_live_drop_critical_pct",60))
        if ext_drop >= ext_critical:
            alert("critical","external_live_drop",f"External LIVE dropped by {ext_drop:.1f}%.",
                  current.get("external_live"),previous.get("external_live"),ext_critical)
        elif ext_drop >= ext_warn:
            alert("warning","external_live_drop",f"External LIVE dropped by {ext_drop:.1f}%.",
                  current.get("external_live"),previous.get("external_live"),ext_warn)

        extch_drop=pct_drop(previous.get("external_channels_with_events",0),current.get("external_channels_with_events",0))
        ch_warn=float(settings.get("health_external_channels_drop_warn_pct",30))
        ch_critical=float(settings.get("health_external_channels_drop_critical_pct",60))
        if extch_drop >= ch_critical:
            alert("critical","external_channels_drop",f"External event channel coverage dropped by {extch_drop:.1f}%.",
                  current.get("external_channels_with_events"),previous.get("external_channels_with_events"),ch_critical)
        elif extch_drop >= ch_warn:
            alert("warning","external_channels_drop",f"External event channel coverage dropped by {extch_drop:.1f}%.",
                  current.get("external_channels_with_events"),previous.get("external_channels_with_events"),ch_warn)

        quality_drop=float(previous.get("quality_average",0) or 0)-float(current.get("quality_average",0) or 0)
        qthr=float(settings.get("health_quality_drop_warn",1.0))
        if quality_drop >= qthr:
            alert("warning","quality_drop",f"Average quality dropped by {quality_drop:.1f} points.",
                  current.get("quality_average"),previous.get("quality_average"),qthr)

        prev_sources=previous.get("sources") or {}
        curr_sources=current.get("sources") or {}
        prog_drop_thr=float(settings.get("health_source_programme_drop_warn_pct",50))
        cov_drop_thr=float(settings.get("health_source_coverage_drop_warn_points",20))
        for name,cur in curr_sources.items():
            prev=prev_sources.get(name)
            if not prev:
                continue
            reasons=[]
            severity="warning"
            if prev.get("ok") and not cur.get("ok"):
                reasons.append("source became unavailable"); severity="critical"
            elif prev.get("current_ok") and not cur.get("current_ok"):
                reasons.append("current feed stopped being directly usable")
            health_rank={None:0,"healthy":0,"healthy_with_gaps":1,"recovered":1,"degraded":2,"unavailable":3}
            if health_rank.get(cur.get("health"),0) > health_rank.get(prev.get("health"),0):
                reasons.append(f"health {prev.get('health')} → {cur.get('health')}")
                if cur.get("health")=="unavailable": severity="critical"
            pcov=prev.get("coverage_pct"); ccov=cur.get("coverage_pct")
            if pcov is not None and ccov is not None and float(pcov)-float(ccov) >= cov_drop_thr:
                reasons.append(f"configured coverage {pcov}% → {ccov}%")
            pprog=float(prev.get("source_programmes",0) or 0); cprog=float(cur.get("source_programmes",0) or 0)
            prog_drop=pct_drop(pprog,cprog)
            if pprog >= 100 and prog_drop >= prog_drop_thr:
                reasons.append(f"programme count dropped {prog_drop:.1f}%")
            if reasons:
                source_regressions.append({"source":name,"severity":severity,"reasons":reasons,"previous":prev,"current":cur})
        if source_regressions:
            crit=sum(1 for x in source_regressions if x["severity"]=="critical")
            sev="critical" if crit else "warning"
            alert(sev,"source_regressions",f"Detected regressions in {len(source_regressions)} source(s).",
                  len(source_regressions),0,None)

    net=int(current.get("external_network_failures",0) or 0)
    net_warn=int(settings.get("health_network_failures_warn",5)); net_crit=int(settings.get("health_network_failures_critical",20))
    if net >= net_crit:
        alert("critical","network_failures",f"External provider had {net} network failures.",net,None,net_crit)
    elif net >= net_warn:
        alert("warning","network_failures",f"External provider had {net} network failures.",net,None,net_warn)

    age=float(current.get("external_data_age_max_hours",0) or 0)
    age_warn=float(settings.get("health_external_data_age_warn_hours",6)); age_crit=float(settings.get("health_external_data_age_critical_hours",12))
    if age >= age_crit:
        alert("critical","external_data_stale",f"Oldest External LIVE data is {age:.2f}h old.",age,None,age_crit)
    elif age >= age_warn:
        alert("warning","external_data_stale",f"Oldest External LIVE data is {age:.2f}h old.",age,None,age_warn)

    if int(current.get("source_unavailable",0) or 0)>0:
        alert("critical","source_unavailable",f"{current.get('source_unavailable')} XMLTV source(s) unavailable.",current.get("source_unavailable"),None,0)
    if int(current.get("external_channels_unavailable",0) or 0)>0:
        alert("warning","external_channels_unavailable",f"{current.get('external_channels_unavailable')} External LIVE channel(s) unavailable.",current.get("external_channels_unavailable"),None,0)
    if int(current.get("external_same_channel_event_reuse",0) or 0)>0 or int(current.get("external_duplicate_event_matches",0) or 0)>0:
        alert("critical","external_one_to_one_violation","External one-to-one integrity violation detected.",
              max(int(current.get("external_same_channel_event_reuse",0) or 0),int(current.get("external_duplicate_event_matches",0) or 0)),0,0)

    trend=evaluate_health_trends(history,current,settings) if settings.get("health_trend_enabled",True) else {"status":"disabled","persistent_regressions":[],"single_anomalies":[],"metrics":[],"series":[]}
    if settings.get("health_trend_alert_persistent",True) and trend.get("persistent_regressions"):
        names=", ".join(x.get("metric","") for x in trend.get("persistent_regressions",[]))
        alert("warning","persistent_trend_regression",f"Persistent regression detected in: {names}.",len(trend.get("persistent_regressions",[])),0,None)

    severity_rank={"healthy":0,"warning":1,"critical":2}
    status="healthy"
    for a in alerts:
        if severity_rank.get(a["severity"],0)>severity_rank[status]: status=a["severity"]

    comparison={}
    if previous:
        for k in ["channels_matched","channels_active","channels_empty","quality_average","external_live","external_channels_with_events",
                  "external_data_age_max_hours","source_degraded","source_unavailable"]:
            cv=current.get(k); pv=previous.get(k)
            if isinstance(cv,(int,float)) and isinstance(pv,(int,float)):
                comparison[k]={"current":cv,"previous":pv,"delta":round(cv-pv,3)}
        comparison["external_live_drop_pct"]=round(pct_drop(previous.get("external_live",0),current.get("external_live",0)),1)
        comparison["external_channels_drop_pct"]=round(pct_drop(previous.get("external_channels_with_events",0),current.get("external_channels_with_events",0)),1)

    health_score,health_score_components=calculate_health_score(alerts,trend,current,settings) if settings.get("health_score_enabled",True) else (None,{})
    build_entry={"generated_at_utc":current.get("generated_at_utc"),"version":current.get("version"),"status":status,
                 "alert_count":len(alerts),"health_score":health_score,"trend_status":trend.get("status"),
                 "trend_confidence":trend.get("confidence"),"trend_confidence_score":trend.get("confidence_score"),"snapshot":current}
    builds.append(build_entry)
    max_builds=max(2,int(settings.get("health_history_max_builds",30)))
    history={"version":2,"updated_at_utc":current.get("generated_at_utc"),"builds":builds[-max_builds:]}
    path=BASE_DIR / settings.get("health_history_file", ".cache/build_health_history.json")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(history,ensure_ascii=False,indent=2),encoding="utf-8")

    result={
        "version":"3.18","generated_at_utc":current.get("generated_at_utc"),"status":status,
        "health_score":health_score,"health_score_components":health_score_components,"trend":trend,
        "baseline_source":baseline_source,"previous_available":bool(previous),"previous":previous,
        "current":current,"comparison":comparison,"alerts":alerts,"source_regressions":source_regressions,
        "history_builds":len(history["builds"]),"recent_history":[
            {"generated_at_utc":x.get("generated_at_utc"),"version":x.get("version"),"status":x.get("status"),
             "alert_count":x.get("alert_count"),"health_score":x.get("health_score"),"trend_status":x.get("trend_status"),
             "trend_confidence":x.get("trend_confidence"),"trend_confidence_score":x.get("trend_confidence_score"),
             "external_live":(x.get("snapshot") or {}).get("external_live"),
             "channels_active":(x.get("snapshot") or {}).get("channels_active"),
             "quality_average":(x.get("snapshot") or {}).get("quality_average"),
             "network_failures":(x.get("snapshot") or {}).get("external_network_failures"),
             "data_age_max_hours":(x.get("snapshot") or {}).get("external_data_age_max_hours")}
            for x in history["builds"][-12:]
        ],
        "thresholds":{
            "external_live_drop_warn_pct":settings.get("health_external_live_drop_warn_pct",30),
            "external_live_drop_critical_pct":settings.get("health_external_live_drop_critical_pct",60),
            "external_channels_drop_warn_pct":settings.get("health_external_channels_drop_warn_pct",30),
            "external_data_age_warn_hours":settings.get("health_external_data_age_warn_hours",6),
            "external_data_age_critical_hours":settings.get("health_external_data_age_critical_hours",12),
        }
    }
    return result,history

def write_status_html(path: Path, report: dict):
    rows = []
    warn_below = report.get("settings", {}).get("quality_score_warn_below", 75)
    for ch in report["channels"]:
        q = ch.get("quality", {})
        score = q.get("technical_score", 0)
        status = "✅" if ch.get("active") and score >= warn_below else ("⚠️" if ch.get("active") else ("🟡" if ch.get("empty") else "❌"))
        warnings = ", ".join(q.get("warnings", [])) or "—"
        league_top = sorted(ch.get("leagues", {}).items(), key=lambda kv: kv[1], reverse=True)[:2]
        league_text = ", ".join(f"{html.escape(k)} ({v})" for k,v in league_top) or "—"
        rows.append(
            f'<tr data-name="{html.escape(ch["name"].lower())}" data-score="{score}">'
            f"<td>{status}</td><td><b>{html.escape(ch['name'])}</b></td>"
            f"<td>{'active' if ch.get('active') else ('empty' if ch.get('empty') else 'missing')}</td>"
            f"<td>{score:.1f}</td><td>{ch['programmes']}</td><td>{ch['live']}</td>"
            f"<td>{ch.get('external_live_high',0)}/{ch.get('external_live_medium',0)}</td>"
            f"<td>{ch['replay']}</td><td>{q.get('large_gaps',0)}</td><td>{q.get('overlaps',0)}</td>"
            f"<td>{q.get('exact_duplicates_removed',0)}</td><td>{q.get('coverage_hours',0)}</td>"
            f"<td>{league_text}</td><td>{html.escape(warnings)}</td>"
            f"<td>{html.escape(str(ch.get('source') or '—'))}</td>"
            f"<td>{html.escape(str(ch.get('source_id') or '—'))}</td></tr>"
        )

    s = report["summary"]
    top_leagues = sorted(s.get("leagues", {}).items(), key=lambda kv: kv[1], reverse=True)[:12]
    top_leagues_html = "".join(f"<li>{html.escape(k)} <b>{v}</b></li>" for k,v in top_leagues) or "<li>Brak danych</li>"
    body = f'''<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sports EPG v3.18 — status</title>
<style>
body{{font-family:system-ui,-apple-system,sans-serif;margin:0;background:#f6f7f9;color:#18212f}}
main{{max-width:1600px;margin:auto;padding:24px}} h1{{margin-bottom:4px}} .muted{{color:#667085}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:20px 0}}
.card{{background:white;border:1px solid #e4e7ec;border-radius:12px;padding:14px}} .big{{font-size:1.5rem;font-weight:700}}
.toolbar{{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}} input,select{{padding:9px 12px;border:1px solid #d0d5dd;border-radius:8px;background:white}}
.wrap{{overflow:auto;background:white;border:1px solid #e4e7ec;border-radius:12px}}
table{{border-collapse:collapse;width:100%;font-size:13px}} td,th{{border-bottom:1px solid #eee;padding:9px;text-align:left;white-space:nowrap}}
th{{position:sticky;top:0;background:#f9fafb;z-index:1}} tr:hover{{background:#fafcff}}
.grid2{{display:grid;grid-template-columns:2fr 1fr;gap:16px}} .panel{{background:white;border:1px solid #e4e7ec;border-radius:12px;padding:16px}}
@media(max-width:900px){{.grid2{{grid-template-columns:1fr}}}}
</style></head><body><main>
<h1>Sports EPG v3.18</h1><div class="muted">Wygenerowano: {html.escape(report['generated_at_utc'])}</div>
<div class="cards">
<div class="card"><div class="muted">Skonfigurowane</div><div class="big">{s['channels_total']}</div></div>
<div class="card"><div class="muted">Matched</div><div class="big">{s['channels_matched']}</div></div>
<div class="card"><div class="muted">Active EPG</div><div class="big">{s.get('channels_active',0)}</div></div>
<div class="card"><div class="muted">Empty</div><div class="big">{s.get('channels_empty',0)}</div></div>
<div class="card"><div class="muted">Programy</div><div class="big">{s['programmes']}</div></div>
<div class="card"><div class="muted">LIVE</div><div class="big">{s['live']}</div></div>
<div class="card"><div class="muted">External LIVE</div><div class="big">{s.get('external_live',0)}</div></div>
<div class="card"><div class="muted">Sofascore LIVE</div><div class="big">{s.get('sofascore_live',0)}</div></div>
<div class="card"><div class="muted">Sofascore replay veto</div><div class="big">{s.get('sofascore_replay',0)}</div></div>
<div class="card"><div class="muted">Build health</div><div class="big">{html.escape(str(s.get('health_status','—')).upper())}</div></div>
<div class="card"><div class="muted">Health score</div><div class="big">{s.get('health_score','—')}/100</div></div>
<div class="card"><div class="muted">Trend</div><div class="big">{html.escape(str(s.get('health_trend_status','—')).upper())}</div></div>
<div class="card"><div class="muted">Trend confidence</div><div class="big">{html.escape(str(s.get('health_trend_confidence','—')).upper())}</div><div class="muted">{s.get('health_trend_confidence_score',0)}/100</div></div>
<div class="card"><div class="muted">Health alerts</div><div class="big">{s.get('health_alerts_total',0)}</div></div>
<div class="card"><div class="muted">SportGuide events</div><div class="big">{report.get('external_live',{}).get('events_found',0)}</div></div>
<div class="card"><div class="muted">Kanały ext. z eventami</div><div class="big">{report.get('external_live',{}).get('channels_with_events',0)}</div></div>
<div class="card"><div class="muted">Auto-discovery ext.</div><div class="big">{report.get('external_live',{}).get('auto_pages_with_events',0)}</div></div>
<div class="card"><div class="muted">External match rate</div><div class="big">{s.get('external_match_rate_pct',0):.1f}%</div></div>
<div class="card"><div class="muted">LIVE audit strong</div><div class="big">{s.get('live_audit_strong',0)}</div></div>
<div class="card"><div class="muted">LIVE do przeglądu</div><div class="big">{s.get('live_audit_review',0)}</div></div>
<div class="card"><div class="muted">Catalog mappings</div><div class="big">{s.get('sportguide_catalog_cached_channels',0)}</div></div>
<div class="card"><div class="muted">Catalog matches</div><div class="big">{report.get('external_live',{}).get('catalog_matches',0)}</div></div>
<div class="card"><div class="muted">Unique ext. events used</div><div class="big">{s.get('external_unique_events_used',0)}</div></div>
<div class="card"><div class="muted">Same-channel reuse</div><div class="big">{s.get('external_same_channel_event_reuse',0)}</div></div>
<div class="card"><div class="muted">Cross-channel simulcast</div><div class="big">{s.get('external_cross_channel_simulcast_events',0)}</div></div>
<div class="card"><div class="muted">Schedule verified</div><div class="big">{s.get('source_recommendation_schedule_verified',0)}</div></div>
<div class="card"><div class="muted">Strong schedule consensus</div><div class="big">{s.get('source_recommendation_schedule_strong',0)}</div></div>
<div class="card"><div class="muted">Źródła z cache</div><div class="big">{s.get('source_cache_fallbacks',0)}</div></div>
<div class="card"><div class="muted">Źródła salvaged</div><div class="big">{s.get('source_salvaged_feeds',0)}</div></div>
<div class="card"><div class="muted">Źródła degraded</div><div class="big">{s.get('source_degraded',0)}</div></div>
<div class="card"><div class="muted">Channel LKG recovery</div><div class="big">{s.get('channel_lkg_recoveries',0)}</div></div>
<div class="card"><div class="muted">Fallback promotion</div><div class="big">{s.get('fallback_promotion_candidates',0)}</div></div>
<div class="card"><div class="muted">Repeat fingerprints</div><div class="big">{s.get('schedule_repeat_matches',0)}</div></div>
<div class="card"><div class="muted">TZ cleanup</div><div class="big">{s.get('mixed_offset_programmes_removed',0)}</div></div>
<div class="card"><div class="muted">Śr. quality</div><div class="big">{s.get('quality_average',0):.1f}</div></div>
<div class="card"><div class="muted">Kanały z ostrzeżeniami</div><div class="big">{s.get('quality_warning_channels',0)}</div></div>
<div class="card"><div class="muted">Luki</div><div class="big">{s.get('large_gaps',0)}</div></div>
<div class="card"><div class="muted">Nakładki</div><div class="big">{s.get('overlaps',0)}</div></div>
</div>
<div class="grid2"><div class="panel"><b>Interpretacja quality score</b><p class="muted">To techniczna ocena spójności ramówki (czasy, duplikaty, luki, nakładki, pokrycie). Nie jest oceną prawdziwości programu ani jakości stacji.</p></div>
<div class="panel"><b>Najczęściej wykrywane rozgrywki</b><ol>{top_leagues_html}</ol></div></div>
<div class="panel" style="margin-top:16px"><b>External LIVE diagnostics</b><p class="muted">URLs tried: {report.get('external_live',{}).get('urls_tried',0)} · auto channels: {report.get('external_live',{}).get('auto_channels_attempted',0)} · pages with events: {report.get('external_live',{}).get('pages_with_events',0)} · empty pages: {report.get('external_live',{}).get('pages_empty',0)} · failed: {report.get('external_live',{}).get('pages_failed',0)} · events found: {report.get('external_live',{}).get('events_found',0)}</p></div>
<div class="panel" style="margin-top:16px"><b>Sofascore verification</b><p class="muted">requests OK: {report.get('sofascore',{}).get('requests_ok',0)} · failed: {report.get('sofascore',{}).get('requests_failed',0)} · stale cache: {report.get('sofascore',{}).get('stale_cache_hits',0)} · events loaded: {report.get('sofascore',{}).get('events_loaded',0)}</p></div>
<div class="toolbar"><input id="q" placeholder="Filtruj kanał…"><select id="quality"><option value="all">Wszystkie</option><option value="warn">Tylko ostrzeżenia</option></select><a href="report.json">report.json</a><a href="quality_report.json">quality_report.json</a><a href="live_matches.json">live_matches.json</a><a href="empty_channels.json">empty_channels.json</a><a href="live_audit.json">live_audit.json</a><a href="source_recommendations.json">source_recommendations.json</a><a href="sportguide_catalog.json">sportguide_catalog.json</a><a href="sofascore_live.json">sofascore_live.json</a></div>
<div class="wrap"><table id="tbl"><thead><tr><th></th><th>Kanał</th><th>Stan</th><th>Quality</th><th>Programy</th><th>LIVE</th><th>High/Med</th><th>Replay</th><th>Luki</th><th>Nakładki</th><th>Duplikaty</th><th>Pokrycie h</th><th>Top ligi</th><th>Ostrzeżenia</th><th>Źródło</th><th>Source ID</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<script>
const q=document.getElementById('q'), sel=document.getElementById('quality');
function f(){{const s=q.value.toLowerCase();document.querySelectorAll('#tbl tbody tr').forEach(r=>{{const okName=r.dataset.name.includes(s);const okQ=sel.value==='all'||Number(r.dataset.score)<{warn_below};r.style.display=okName&&okQ?'':'none';}})}}
q.addEventListener('input',f);sel.addEventListener('change',f);
</script></main></body></html>'''
    path.write_text(body, encoding="utf-8")

PLUSX_SPORT_NETWORK_TERMS = [
    "sport", "sports", "dazn", "espn", "eurosport", "tnt", "bein", "arena", "premier sport",
    "sky sport", "sky sports", "canal+ sport", "canal plus sport", "nova sport", "oneplay sport",
    "sportklub", "sport klub", "polsat sport", "eleven sports", "golf channel", "tennis channel",
    "mlb network", "nba tv", "nfl network", "nhl network", "fight network", "rds", "tsn", "sportsnet",
    "fox sports", "cbs sports", "nbc sports", "sec network", "acc network", "big ten network", "one soccer"
]

def plusx_country_code(channel_id: str, labels: list[str]) -> str | None:
    hay = ascii_fold(" ".join([channel_id] + labels))
    # Common XMLTV ids end in .uk/.us/.de/.cz/.sk/.ca; also accept standalone prefixes.
    m = re.search(r"\.(uk|gb|us|de|cz|sk|ca)(?:\b|$)", hay)
    if m:
        code=m.group(1)
        return "uk" if code=="gb" else code
    m = re.match(r"^(uk|gb|us|de|cz|sk|ca)[ .:_-]", hay)
    if m:
        code=m.group(1)
        return "uk" if code=="gb" else code
    return None

def plusx_is_sport_channel(channel_id: str, labels: list[str]) -> bool:
    hay = ascii_fold(" ".join([channel_id] + labels))
    if any(ascii_fold(term) in hay for term in PLUSX_SPORT_NETWORK_TERMS):
        return True
    return sport_from_text(hay) is not None

def discover_plusx_channels(root: ET.Element | None, config: dict, settings: dict) -> tuple[list[dict], dict]:
    """Dynamically import additional sport channels from the user's PlusX XMLTV feed.

    The XMLTV format itself does not expose IPTV group/category names, so v3.18 uses
    stable country hints in tvg-id/display-name plus a conservative sports-network classifier.
    This covers the requested SPORT + UK/US/DE/CZ/SK/CA scope without flooding the output
    with unrelated general-entertainment channels.
    """
    result={"enabled":False,"source":"poland_plusx","selected_countries":[],"source_channels":0,
            "sport_candidates":0,"added":0,"skipped_existing":0,"added_channels":[]}
    if root is None or not settings.get("plusx_autoimport_enabled", True):
        return [], result
    selected={str(x).lower() for x in settings.get("plusx_autoimport_country_codes", ["uk","us","de","cz","sk","ca"])}
    result["enabled"]=True; result["selected_countries"]=sorted(selected)
    counts=programme_count_by_channel(root)
    existing_ids={str(ch.get("id") or "") for ch in config.get("channels",[])}
    existing_source_ids=set()
    for ch in config.get("channels",[]):
        existing_source_ids.update(str(x) for x in (ch.get("source_ids") or []))
        for fb in ch.get("fallback_sources",[]) or []:
            if fb.get("source")=="poland_plusx":
                existing_source_ids.update(str(x) for x in (fb.get("source_ids") or []))
    result["source_channels"]=len(root.findall("channel"))
    added=[]
    for ch in root.findall("channel"):
        cid=ch.get("id") or ""
        labels=[normalized(x.text or "") for x in ch.findall("display-name") if normalized(x.text or "")]
        if not cid or counts.get(cid,0)<=0:
            continue
        country=plusx_country_code(cid,labels)
        sport=plusx_is_sport_channel(cid,labels)
        # SPORT means any confidently sport-like station; country groups add sport stations
        # specifically from UK/US/DE/CZ/SK/CA.
        if not sport:
            continue
        if country and country not in selected and not settings.get("plusx_autoimport_global_sport", True):
            continue
        result["sport_candidates"]+=1
        if cid in existing_ids or cid in existing_source_ids:
            result["skipped_existing"]+=1
            continue
        label=labels[0] if labels else cid.replace("."," ")
        prefix=(country or "SPORT").upper()
        logical_id=cid
        row={
            "name": f"{prefix} {label}",
            "id": logical_id,
            "source": "poland_plusx",
            "source_ids": [cid],
            "autoimported_plusx": True,
            "plusx_country": country,
        }
        added.append(row)
        result["added_channels"].append({"id":cid,"name":label,"country":country,"programmes":counts.get(cid,0)})
    result["added"]=len(added)
    return added,result


def main():
    global LEAGUE_RULES
    config = load_yaml(CONFIG_FILE)
    translations = load_yaml(TRANSLATIONS_FILE)
    league_data = load_yaml(LEAGUES_FILE)
    LEAGUE_RULES = league_data.get("leagues", []) if isinstance(league_data, dict) else []

    settings = config["settings"]
    lang = settings.get("target_language","pl")
    replacements = translations.get(lang,{}).get("replacements",{})
    external_cfg = config.get("external_live",{})

    cache_bootstrap = bootstrap_previous_version_cache(settings)

    roots, errors, source_status = {}, {}, {}
    for name, src in config["sources"].items():
        print(f"[EPG] {name}")
        root, status = load_xmltv_source(name, src, settings, required_source_groups(config, name))
        status = decorate_source_health(status, settings)
        source_status[name] = status
        if root is not None:
            roots[name] = root
            if status.get("used_cache"):
                print(f"[CACHE] {name}: last-known-good ({status.get('cache_age_hours')}h)")
            elif status.get("salvaged"):
                print(f"[SALVAGED] {name}: truncated XML recovered", file=sys.stderr)
        else:
            err = " | ".join(status.get("errors") or ["source unavailable"])
            errors[name] = err
            print(f"[ERROR] {name}: {err}", file=sys.stderr)

    plusx_auto_channels, plusx_auto_report = discover_plusx_channels(roots.get("poland_plusx"), config, settings)
    if plusx_auto_channels:
        config["channels"].extend(plusx_auto_channels)
        print(f"[PLUSX] auto-imported {len(plusx_auto_channels)} additional sport channels")

    report = {
        "version":"3.18",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "target_language":lang,
        "settings":{
            "external_live_min_score": settings.get("external_live_min_score"),
            "external_live_high_confidence": settings.get("external_live_high_confidence"),
            "quality_score_warn_below": settings.get("quality_score_warn_below"),
            "quality_gap_warning_minutes": settings.get("quality_gap_warning_minutes"),
            "quality_overlap_warning_minutes": settings.get("quality_overlap_warning_minutes"),
        },
        "sources":{},
        "external_live":{
            "enabled":bool(external_cfg.get("enabled")),
            "urls_tried":0,"pages_ok":0,"pages_with_events":0,"pages_empty":0,
            "pages_failed":0,"pages_current":0,"pages_cached":0,"pages_fresh_cache":0,"pages_stale_cache":0,
            "stale_page_cache_hits":0,
            "events_found":0,"events_found_current":0,"events_found_cached":0,
            "events_found_fresh_cache":0,"events_found_stale_cache":0,"events_found_event_lkg":0,
            "channels_with_events":0,
            "channels_current":0,"channels_cached":0,"channels_fresh_cache":0,"channels_stale_cache":0,
            "channels_event_lkg":0,"channels_unavailable":0,
            "channels_current_empty":0,"channels_cached_empty":0,"channels_fresh_cache_empty":0,"channels_stale_cache_empty":0,
            "event_cache_hits":0,"network_attempts":0,"network_failures":0,
            "data_age_max_hours":0.0,"data_age_hours_values":[],
            "auto_channels_attempted":0,"auto_urls_tried":0,"auto_pages_with_events":0,
            "catalog_entries":0,"catalog_matches":0,"catalog_cache_hits":0,"legacy_urls_tried":0,
            "catalog_brand_matches":0,"events_deduplicated":0,
            "catalog_lkg_loaded":0,"catalog_lkg_age_hours":None,"catalog_entries_retained":0,
            "catalog_seed_urls_tried":0,"catalog_seed_pages_ok":0,"catalog_seed_pages_current":0,
            "catalog_seed_pages_cached":0,"catalog_seed_pages_failed":0,"catalog_seed_errors":[],
            "channel_status":{},
            "errors":[]
        },
        "cache_bootstrap":cache_bootstrap,
        "plusx_autoimport":plusx_auto_report,
        "channels":[],
        "summary":{},
    }
    for name, src in config["sources"].items():
        root = roots.get(name)
        st = source_status.get(name, {})
        report["sources"][name] = {
            "url":src["url"], "ok":name in roots, "current_ok":bool(st.get("current_ok")),
            "used_cache":bool(st.get("used_cache")), "salvaged":bool(st.get("salvaged")),
            "attempts":st.get("attempts",0), "url_used":st.get("url_used"),
            "cache_age_hours":st.get("cache_age_hours"),
            "recovery_priority":st.get("recovery_priority"),
            "fallback_url_used":bool(st.get("fallback_url_used")),
            "salvage_retained_bytes_pct":st.get("salvage_retained_bytes_pct"),
            "salvage_channel_retention_pct":st.get("salvage_channel_retention_pct"),
            "salvage_programme_retention_estimate_pct":st.get("salvage_programme_retention_estimate_pct"),
            "salvage_baseline_channels":st.get("baseline_channels"),
            "salvage_baseline_programmes":st.get("baseline_programmes"),
            "salvage_candidates":st.get("salvage_candidates",0),
            "cache_supplemented_channels":st.get("cache_supplemented_channels",[]),
            "configured_coverage":st.get("coverage",{}),
            "configured_channel_coverage_pct":st.get("configured_channel_coverage_pct"),
            "health":st.get("health"),"degraded":bool(st.get("degraded")),
            "degraded_reason":st.get("degraded_reason"),"coverage_warning":bool(st.get("coverage_warning")),
            "error": errors.get(name) or (" | ".join(st.get("errors") or []) if not st.get("current_ok") else None),
            "source_channels": len(root.findall("channel")) if root is not None else 0,
            "source_programmes": len(root.findall("programme")) if root is not None else 0,
        }

    sportguide_catalog = load_sportguide_catalog(external_cfg)
    prime_sportguide_catalog(sportguide_catalog, external_cfg, report)
    sofascore_state = {"day_cache": {}, "requests_ok": 0, "requests_failed": 0, "stale_cache_hits": 0, "events_loaded": 0, "errors": []}

    out_root = ET.Element("tv", {"generator-info-name":settings.get("generator_name","Sports EPG v3.18")})
    resolved = []
    for ch_cfg in config["channels"]:
        resolved_source, source_id, source_channel, source_programme_count, resolution = resolve_channel_source(ch_cfg, roots, settings, config.get("verified_fallbacks", []))
        out_root.append(make_channel_element(ch_cfg["id"], ch_cfg["name"], source_channel))
        resolved.append((ch_cfg, resolved_source, source_id, source_channel, source_programme_count, resolution))

    total_keys = ["programmes","live","live_explicit","external_live","external_live_high","external_live_medium","external_live_rejected_risky","replay","stages","translated","live_inferred","live_morning_suppressed","sofascore_live","sofascore_replay","sofascore_live_confirmed","sofascore_replays_suppressed"]
    totals = {k:0 for k in total_keys}
    totals["sports"] = defaultdict(int)
    totals["leagues"] = defaultdict(int)
    all_live_matches = []
    quality_rows = []

    for ch_cfg, resolved_source, source_id, source_channel, source_programme_count, resolution in resolved:
        stats = {
            "name":ch_cfg["name"],"id":ch_cfg["id"],"configured_source":ch_cfg["source"],
            "source":resolved_source,"source_id":source_id,"matched":bool(source_id),
            "source_programme_count":source_programme_count,"active":False,"empty":False,
            "source_resolution":resolution.get("mode"),"source_discovery_score":resolution.get("score",0.0),
            "source_suggestions":resolution.get("suggestions",[]),
            "verified_fallback":bool(resolution.get("verified_fallback")),
            "verified_fallback_reason":resolution.get("verified_fallback_reason"),
            "verified_fallback_evidence":resolution.get("verified_fallback_evidence"),
            "channel_lkg_recovered":bool(resolution.get("channel_lkg_recovered")),
            "channel_lkg_meta":resolution.get("channel_lkg_meta"),
            "programmes":0,"live":0,"live_explicit":0,"external_live":0,
            "external_live_high":0,"external_live_medium":0,"external_live_rejected_risky":0,"replay":0,"stages":0,"translated":0,
            "live_inferred":0,"live_morning_suppressed":0,"sofascore_live":0,"sofascore_replay":0,
            "sofascore_live_confirmed":0,"sofascore_replays_suppressed":0,
            "sports":defaultdict(int),"leagues":defaultdict(int),"live_matches":[]
        }
        stats["has_icon"] = bool(source_channel is not None and source_channel.find("icon") is not None)

        root = roots.get(resolved_source) if resolved_source else None
        programmes = []
        if root is not None and source_id:
            programmes = [p for p in root.findall("programme") if p.get("channel") == source_id]
            programmes.sort(key=lambda p: p.get("start", ""))

        # v3.11: if the configured country feed is degraded/unavailable and this logical
        # channel has no programmes, recover only this channel from its own LKG cache.
        target_status = source_status.get(ch_cfg.get("source"), {})
        if (not programmes and settings.get("channel_lkg_enabled",True)
                and settings.get("channel_lkg_recover_when_source_degraded",True)
                and (target_status.get("degraded") or target_status.get("health")=="unavailable")):
            lkg_root,lkg_meta=load_channel_lkg(ch_cfg,settings)
            if lkg_root is not None:
                cached_sid=lkg_meta.get("cached_source_id")
                cached_programmes=[p for p in lkg_root.findall("programme") if not cached_sid or p.get("channel")==cached_sid]
                if cached_programmes:
                    cached_channel=next((x for x in lkg_root.findall("channel") if not cached_sid or x.get("id")==cached_sid),None)
                    programmes=sorted(cached_programmes,key=lambda p:p.get("start",""))
                    source_channel=cached_channel or source_channel
                    resolved_source="channel_lkg"
                    source_id=cached_sid or source_id or ch_cfg.get("id")
                    source_programme_count=len(programmes)
                    resolution={
                        "mode":"channel_lkg_recovery","score":1.0,"suggestions":[],
                        "channel_lkg_recovered":True,"channel_lkg_meta":lkg_meta,
                        "original_resolution":resolution.get("mode"),
                    }

        source_cfg = config["sources"].get(resolved_source, {}) if resolved_source else {}
        target_source_cfg = config["sources"].get(ch_cfg.get("source"), source_cfg)
        source_timezone = target_source_cfg.get("timezone") or source_cfg.get("timezone")
        programmes, mixed_removed, mixed_cleanup = cleanup_mixed_offset_programmes(
            programmes, settings, source_timezone
        )
        stats["mixed_offset_cleanup"] = mixed_cleanup

        duplicates_removed = 0
        if settings.get("deduplicate_exact_programmes", True):
            programmes, duplicates_removed = deduplicate_programmes(programmes)

        # Update logical-channel LKG only from a trustworthy live source or approved verified fallback.
        resolved_status=source_status.get(resolved_source,{})
        can_update_channel_lkg=bool(programmes) and not resolution.get("channel_lkg_recovered") and (
            resolution.get("verified_fallback") or resolved_status.get("current_ok") or resolved_status.get("health")=="recovered"
        )
        if can_update_channel_lkg:
            save_channel_lkg(ch_cfg,resolved_source,source_id,source_channel,programmes,settings)

        # Do not spend external requests on channels with no usable EPG.
        external_events = external_events_for_channel(
            ch_cfg, target_source_cfg, external_cfg, report, sportguide_catalog, allow_autodiscovery=bool(programmes)
        ) if programmes else []
        stats["external_events_available"] = len(external_events)

        stats["active"] = bool(source_id and programmes)
        stats["empty"] = bool(source_id and not programmes)
        stats["cross_source_recommendations"] = cross_source_recommendations(ch_cfg, roots, config) if stats["empty"] else []
        quality = analyze_schedule(programmes, settings, duplicates_removed)
        quality["mixed_offset_programmes_removed"] = mixed_removed
        if not stats["has_icon"] and quality["technical_score"] > 0:
            quality["technical_score"] = round(max(0, quality["technical_score"] - 2), 1)
            quality["warnings"].append("missing_icon")
        if not source_id:
            quality["technical_score"] = 0.0
            quality["warnings"] = ["channel_not_matched"]
        stats["quality"] = quality

        for prog in programmes:
            out_root.append(transform_programme(
                prog, ch_cfg["id"], settings, replacements, external_events, stats,
                station_timezone=source_timezone, sofascore_state=sofascore_state
            ))

        all_live_matches.extend(stats.pop("live_matches"))
        report["channels"].append({
            **{k:v for k,v in stats.items() if k not in ("sports","leagues")},
            "sports":dict(stats["sports"]), "leagues":dict(stats["leagues"])
        })
        quality_rows.append({
            "name": ch_cfg["name"], "id": ch_cfg["id"], "matched": bool(source_id), "active":bool(source_id and programmes), "empty":bool(source_id and not programmes),
            "source": resolved_source, "source_id": source_id,
            "source_resolution": resolution.get("mode"),
            "source_discovery_score": resolution.get("score",0.0),
            "source_suggestions": resolution.get("suggestions",[]),
            "verified_fallback": bool(resolution.get("verified_fallback")),
            "channel_lkg_recovered": bool(resolution.get("channel_lkg_recovered")),
            **quality
        })

        for k in total_keys: totals[k] += stats[k]
        for k,v in stats["sports"].items(): totals["sports"][k] += v
        for k,v in stats["leagues"].items(): totals["leagues"][k] += v

        flag = "ACTIVE" if stats["active"] else ("EMPTY" if stats["empty"] else "MISSING")
        print(f"[{flag}] {ch_cfg['name']}: {stats['programmes']} programmes, LIVE={stats['live']}, quality={quality['technical_score']}")

    matched_quality = [q["technical_score"] for q in quality_rows if q.get("active")]
    live_audit_counts = defaultdict(int)
    for m in all_live_matches:
        live_audit_counts[(m.get("audit") or {}).get("grade","unknown")] += 1
    warn_below = float(settings.get("quality_score_warn_below", 75))
    usage = external_usage_metrics(all_live_matches)
    recommendation_history,promotion_candidates=update_recommendation_history(report,settings) if settings.get("recommendation_history_enabled",True) else ({"items":{}},[])

    report["sofascore"] = {
        "enabled": bool(settings.get("sofascore_enabled", True)),
        "requests_ok": sofascore_state.get("requests_ok", 0),
        "requests_failed": sofascore_state.get("requests_failed", 0),
        "stale_cache_hits": sofascore_state.get("stale_cache_hits", 0),
        "events_loaded": sofascore_state.get("events_loaded", 0),
        "days_cached": len(sofascore_state.get("day_cache", {})),
        "errors": sofascore_state.get("errors", [])[-30:],
    }

    report["summary"] = {
        **{k:v for k,v in totals.items() if k not in ("sports","leagues")},
        "sports":dict(totals["sports"]), "leagues":dict(totals["leagues"]),
        "channels_total":len(config["channels"]),
        "channels_matched":sum(1 for x in report["channels"] if x["matched"]),
        "channels_missing":sum(1 for x in report["channels"] if not x["matched"]),
        "channels_active":sum(1 for x in report["channels"] if x.get("active")),
        "channels_empty":sum(1 for x in report["channels"] if x.get("empty")),
        "quality_average": round(sum(matched_quality)/len(matched_quality), 1) if matched_quality else 0.0,
        "quality_average_active": round(sum(matched_quality)/len(matched_quality), 1) if matched_quality else 0.0,
        "quality_warning_channels": sum(1 for q in quality_rows if q.get("active") and q["technical_score"] < warn_below),
        "large_gaps": sum(q["large_gaps"] for q in quality_rows),
        "overlaps": sum(q["overlaps"] for q in quality_rows),
        "overlaps_raw_utc": sum(q.get("overlaps_raw_utc",q["overlaps"]) for q in quality_rows),
        "mixed_timezone_channels": sum(1 for q in quality_rows if q.get("mixed_timezone_offsets")),
        "exact_duplicates_removed": sum(q["exact_duplicates_removed"] for q in quality_rows),
        "invalid_times": sum(q["invalid_times"] for q in quality_rows),
        "mixed_offset_programmes_removed": sum(q.get("mixed_offset_programmes_removed",0) for q in quality_rows),
        "source_autodiscovered_channels": sum(1 for x in report["channels"] if x.get("source_resolution") in ("autodiscovered","priority_autodiscovered")),
        "polish_plusx_channels_used": sum(1 for x in report["channels"] if x.get("source")=="poland_plusx"),
        "external_channels_with_events": report["external_live"].get("channels_with_events",0),
        "external_channels_current": report["external_live"].get("channels_current",0),
        "external_channels_cached": report["external_live"].get("channels_cached",0),
        "external_channels_fresh_cache": report["external_live"].get("channels_fresh_cache",0),
        "external_channels_stale_cache": report["external_live"].get("channels_stale_cache",0),
        "external_channels_event_lkg": report["external_live"].get("channels_event_lkg",0),
        "external_channels_unavailable": report["external_live"].get("channels_unavailable",0),
        "external_event_cache_hits": report["external_live"].get("event_cache_hits",0),
        "external_stale_page_cache_hits": report["external_live"].get("stale_page_cache_hits",0),
        "external_events_current": report["external_live"].get("events_found_current",0),
        "external_events_cached": report["external_live"].get("events_found_cached",0),
        "external_events_fresh_cache": report["external_live"].get("events_found_fresh_cache",0),
        "external_events_stale_cache": report["external_live"].get("events_found_stale_cache",0),
        "external_events_event_lkg": report["external_live"].get("events_found_event_lkg",0),
        "external_data_age_max_hours": round(report["external_live"].get("data_age_max_hours",0.0),3),
        "external_data_age_avg_hours": round(sum(report["external_live"].get("data_age_hours_values",[]))/max(1,len(report["external_live"].get("data_age_hours_values",[]))),3),
        "external_catalog_lkg_loaded": report["external_live"].get("catalog_lkg_loaded",0),
        "cache_bootstrap_files_copied": cache_bootstrap.get("files_copied",0),
        "external_match_rate_pct": round(
            100.0 * totals.get("external_live",0) / max(1, report["external_live"].get("events_found",0)), 1
        ),
        "live_audit_strong": live_audit_counts.get("strong",0),
        "live_audit_review": live_audit_counts.get("review",0),
        "live_audit_risky_kept": live_audit_counts.get("risky",0),
        "sportguide_catalog_entries": len(sportguide_catalog.get("entries",[])),
        "sportguide_catalog_cached_channels": len(sportguide_catalog.get("channel_map",{})),
        "external_unique_events_used": usage["unique_events_global"],
        "external_unique_channel_events_used": usage["unique_channel_events"],
        "external_same_channel_event_reuse": usage["same_channel_reuse"],
        "external_duplicate_event_matches": usage["same_channel_reuse"],
        "external_cross_channel_simulcast_events": usage["cross_channel_simulcast_events"],
        "external_cross_channel_simulcast_extra_matches": usage["cross_channel_simulcast_extra_matches"],
        "external_max_channels_per_event": usage["max_channels_per_event"],
        "external_one_to_one_enabled": bool(settings.get("external_live_one_to_one", True)),
        "external_one_to_one_scope": settings.get("external_live_one_to_one_scope", "channel"),
        "source_recommendation_auto_apply": bool(settings.get("source_recommendation_auto_apply", False)),
        "source_recommendation_schedule_verified": sum(
            1 for c in report["channels"] for r in c.get("cross_source_recommendations", [])
            if r.get("schedule_verified")
        ),
        "source_recommendation_schedule_strong": sum(
            1 for c in report["channels"] for r in c.get("cross_source_recommendations", [])
            if r.get("schedule_consensus_grade") == "strong"
        ),
        "source_recommendation_schedule_moderate": sum(
            1 for c in report["channels"] for r in c.get("cross_source_recommendations", [])
            if r.get("schedule_consensus_grade") == "moderate"
        ),
        "source_current_ok": sum(1 for x in report["sources"].values() if x.get("current_ok")),
        "source_cache_fallbacks": sum(1 for x in report["sources"].values() if x.get("used_cache")),
        "source_salvaged_feeds": sum(1 for x in report["sources"].values() if x.get("salvaged")),
        "source_unavailable": sum(1 for x in report["sources"].values() if not x.get("ok")),
        "source_fallback_url_uses": sum(1 for x in report["sources"].values() if x.get("fallback_url_used")),
        "source_cache_supplemented_channels": sum(len(x.get("cache_supplemented_channels",[])) for x in report["sources"].values()),
        "source_degraded": sum(1 for x in report["sources"].values() if x.get("degraded")),
        "source_coverage_warnings": sum(1 for x in report["sources"].values() if x.get("coverage_warning")),
        "verified_fallbacks_applied": sum(1 for c in report["channels"] if c.get("verified_fallback")),
        "channel_lkg_recoveries": sum(1 for c in report["channels"] if c.get("channel_lkg_recovered")),
        "fallback_promotion_candidates": len(promotion_candidates),
        "recommendation_history_keys": len(recommendation_history.get("items",{})),
        "schedule_repeat_matches": sum(int(r.get("schedule_consensus_repeat_matched",0)) for c in report["channels"] for r in c.get("cross_source_recommendations", [])),
    }

    health_report, health_history = build_health_evaluation(report, settings) if settings.get("health_monitor_enabled",True) else ({"status":"disabled","alerts":[],"source_regressions":[],"history_builds":0,"comparison":{}},{"builds":[]})
    report["health_monitor"] = health_report
    report["summary"]["health_status"] = health_report.get("status","disabled")
    report["summary"]["health_alerts_total"] = len(health_report.get("alerts",[]))
    report["summary"]["health_alerts_warning"] = sum(1 for a in health_report.get("alerts",[]) if a.get("severity")=="warning")
    report["summary"]["health_alerts_critical"] = sum(1 for a in health_report.get("alerts",[]) if a.get("severity")=="critical")
    report["summary"]["health_source_regressions"] = len(health_report.get("source_regressions",[]))
    report["summary"]["health_history_builds"] = health_report.get("history_builds",0)
    report["summary"]["health_external_live_drop_pct"] = (health_report.get("comparison",{}).get("external_live_drop_pct",0.0))
    report["summary"]["health_score"] = health_report.get("health_score")
    report["summary"]["health_score_single_anomaly_penalty"] = (health_report.get("health_score_components") or {}).get("single_anomaly_penalty",0)
    report["summary"]["health_trend_status"] = (health_report.get("trend") or {}).get("status","disabled")
    report["summary"]["health_trend_persistent_regressions"] = len((health_report.get("trend") or {}).get("persistent_regressions",[]))
    report["summary"]["health_trend_single_anomalies"] = len((health_report.get("trend") or {}).get("single_anomalies",[]))
    report["summary"]["health_trend_confidence"] = (health_report.get("trend") or {}).get("confidence","disabled")
    report["summary"]["health_trend_confidence_score"] = (health_report.get("trend") or {}).get("confidence_score",0)
    report["summary"]["health_unified_history_builds"] = health_report.get("history_builds",0)

    out_xml = BASE_DIR / settings["output_xml"]
    out_gz = BASE_DIR / settings["output_gz"]
    report_file = BASE_DIR / settings["report_file"]
    status_file = BASE_DIR / settings["status_file"]
    quality_file = BASE_DIR / settings.get("quality_report_file", "docs/quality_report.json")
    live_file = BASE_DIR / settings.get("live_matches_file", "docs/live_matches.json")
    empty_file = BASE_DIR / settings.get("empty_channels_file", "docs/empty_channels.json")
    audit_file = BASE_DIR / settings.get("live_audit_file", "docs/live_audit.json")
    recommendations_file = BASE_DIR / settings.get("source_recommendations_file", "docs/source_recommendations.json")
    catalog_file = BASE_DIR / settings.get("sportguide_catalog_file", "docs/sportguide_catalog.json")
    sofascore_file = BASE_DIR / settings.get("sofascore_report_file", "docs/sofascore_live.json")
    recovery_file = BASE_DIR / settings.get("source_recovery_file", "docs/source_recovery.json")
    verified_fallback_file = BASE_DIR / settings.get("verified_fallback_report_file", "docs/verified_fallbacks.json")
    channel_recovery_file = BASE_DIR / settings.get("channel_recovery_file", "docs/channel_recovery.json")
    promotion_file = BASE_DIR / settings.get("fallback_promotion_file", "docs/fallback_promotion_candidates.json")
    external_recovery_file = BASE_DIR / settings.get("external_live_recovery_file", "docs/external_live_recovery.json")
    health_file = BASE_DIR / settings.get("health_report_file", "docs/build_health.json")
    trend_file = BASE_DIR / settings.get("health_trend_report_file", "docs/build_trends.json")
    history_file = BASE_DIR / settings.get("health_history_report_file", "docs/build_history.json")
    polish_comparison_file = BASE_DIR / settings.get("polish_source_comparison_file", "docs/polish_source_comparison.json")
    plusx_autoimport_file = BASE_DIR / settings.get("plusx_autoimport_report_file", "docs/plusx_autoimport.json")
    out_xml.parent.mkdir(parents=True,exist_ok=True)

    tree = ET.ElementTree(out_root)
    try: ET.indent(tree, space="  ")
    except AttributeError: pass
    tree.write(out_xml,encoding="utf-8",xml_declaration=True)
    with out_xml.open("rb") as src, gzip.open(out_gz,"wb",compresslevel=9) as dst_gz:
        dst_gz.write(src.read())
    report_file.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    plusx_autoimport_file.write_text(json.dumps({
        "version":"3.18", "generated_at_utc":report["generated_at_utc"],
        **(report.get("plusx_autoimport") or {})
    },ensure_ascii=False,indent=2),encoding="utf-8")
    polish_rows = [
        {
            "name":c.get("name"), "id":c.get("id"),
            "configured_source":c.get("configured_source"),
            "chosen_source":c.get("source"), "chosen_source_id":c.get("source_id"),
            "resolution":c.get("source_resolution"),
            "discovery_score":c.get("source_discovery_score"),
            "programmes":c.get("programmes",0),
            "used_plusx":c.get("source")=="poland_plusx",
            "active":c.get("active"), "empty":c.get("empty")
        }
        for c in report["channels"] if str(c.get("name","")).startswith("PL ")
    ]
    polish_comparison_file.write_text(json.dumps({
        "version":"3.18", "generated_at_utc":report["generated_at_utc"],
        "priority_source":"poland_plusx",
        "priority_source_url":config.get("sources",{}).get("poland_plusx",{}).get("url"),
        "summary":{
            "polish_channels":len(polish_rows),
            "plusx_used":sum(1 for x in polish_rows if x.get("used_plusx")),
            "fallback_used":sum(1 for x in polish_rows if not x.get("used_plusx") and x.get("active")),
            "unmatched_or_empty":sum(1 for x in polish_rows if not x.get("active"))
        },
        "channels":polish_rows
    },ensure_ascii=False,indent=2),encoding="utf-8")
    quality_file.write_text(json.dumps({"version":"3.18","generated_at_utc":report["generated_at_utc"],"channels":quality_rows},ensure_ascii=False,indent=2),encoding="utf-8")
    live_file.write_text(json.dumps({"version":"3.18","generated_at_utc":report["generated_at_utc"],"matches":all_live_matches},ensure_ascii=False,indent=2),encoding="utf-8")
    empty_rows = [
        {
            "name": c["name"], "id": c["id"], "source": c.get("source"), "source_id": c.get("source_id"),
            "source_resolution": c.get("source_resolution"),
            "source_discovery_score": c.get("source_discovery_score"),
            "source_suggestions": c.get("source_suggestions",[]),
        }
        for c in report["channels"] if c.get("empty") or not c.get("matched")
    ]
    empty_file.write_text(json.dumps({
        "version":"3.18","generated_at_utc":report["generated_at_utc"],"channels":empty_rows
    },ensure_ascii=False,indent=2),encoding="utf-8")
    audit_rows = {
        "version":"3.18","generated_at_utc":report["generated_at_utc"],
        "summary":dict(live_audit_counts),
        "matches":all_live_matches,
        "review": [m for m in all_live_matches if (m.get("audit") or {}).get("grade") in ("review","risky")]
    }
    audit_file.write_text(json.dumps(audit_rows,ensure_ascii=False,indent=2),encoding="utf-8")
    reco_rows=[]
    for c in report["channels"]:
        if c.get("empty"):
            reco_rows.append({"name":c["name"],"id":c["id"],"configured_source":c.get("configured_source"),
                              "current_source_id":c.get("source_id"),
                              "same_source_suggestions":c.get("source_suggestions",[]),
                              "cross_source_recommendations":c.get("cross_source_recommendations",[])})
    recommendations_file.write_text(json.dumps({"version":"3.18","generated_at_utc":report["generated_at_utc"],
                                                "channels":reco_rows},ensure_ascii=False,indent=2),encoding="utf-8")
    catalog_file.write_text(json.dumps(sportguide_catalog,ensure_ascii=False,indent=2),encoding="utf-8")
    sofascore_file.write_text(json.dumps(report.get("sofascore", {}), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    recovery_file.write_text(json.dumps({"version":"3.18","generated_at_utc":report["generated_at_utc"],
        "sources":report["sources"],
        "degraded_sources":[{"source":name,**row} for name,row in report["sources"].items() if row.get("degraded")],
        "summary":{k:v for k,v in report["summary"].items() if k.startswith("source_")}},ensure_ascii=False,indent=2),encoding="utf-8")
    channel_recovery_file.write_text(json.dumps({"version":"3.18","generated_at_utc":report["generated_at_utc"],
        "recovered":[{"name":c.get("name"),"id":c.get("id"),"source":c.get("source"),"source_id":c.get("source_id"),
                      "meta":c.get("channel_lkg_meta")} for c in report["channels"] if c.get("channel_lkg_recovered")],
        "count":report["summary"].get("channel_lkg_recoveries",0)},ensure_ascii=False,indent=2),encoding="utf-8")
    promotion_file.write_text(json.dumps({"version":"3.18","generated_at_utc":report["generated_at_utc"],
        "required_builds":settings.get("recommendation_history_required_builds",3),
        "auto_apply":False,"candidates":promotion_candidates},ensure_ascii=False,indent=2),encoding="utf-8")
    verified_fallback_file.write_text(json.dumps({"version":"3.18","generated_at_utc":report["generated_at_utc"],
        "approved":config.get("verified_fallbacks",[]),
        "applied":[{"name":c.get("name"),"id":c.get("id"),"source":c.get("source"),"source_id":c.get("source_id"),
                    "reason":c.get("verified_fallback_reason"),"evidence":c.get("verified_fallback_evidence")}
                   for c in report["channels"] if c.get("verified_fallback")]},ensure_ascii=False,indent=2),encoding="utf-8")
    external_recovery_file.write_text(json.dumps({
        "version":"3.18","generated_at_utc":report["generated_at_utc"],
        "cache_bootstrap":cache_bootstrap,
        "summary":{
            "channels_current":report["external_live"].get("channels_current",0),
            "channels_cached":report["external_live"].get("channels_cached",0),
            "channels_fresh_cache":report["external_live"].get("channels_fresh_cache",0),
            "channels_stale_cache":report["external_live"].get("channels_stale_cache",0),
            "channels_event_lkg":report["external_live"].get("channels_event_lkg",0),
            "channels_unavailable":report["external_live"].get("channels_unavailable",0),
            "channels_with_events":report["external_live"].get("channels_with_events",0),
            "events_current":report["external_live"].get("events_found_current",0),
            "events_cached":report["external_live"].get("events_found_cached",0),
            "events_fresh_cache":report["external_live"].get("events_found_fresh_cache",0),
            "events_stale_cache":report["external_live"].get("events_found_stale_cache",0),
            "events_event_lkg":report["external_live"].get("events_found_event_lkg",0),
            "data_age_max_hours":round(report["external_live"].get("data_age_max_hours",0.0),3),
            "data_age_avg_hours":round(sum(report["external_live"].get("data_age_hours_values",[]))/max(1,len(report["external_live"].get("data_age_hours_values",[]))),3),
            "event_cache_hits":report["external_live"].get("event_cache_hits",0),
            "stale_page_cache_hits":report["external_live"].get("stale_page_cache_hits",0),
            "catalog_lkg_loaded":report["external_live"].get("catalog_lkg_loaded",0),
            "catalog_lkg_age_hours":report["external_live"].get("catalog_lkg_age_hours"),
            "network_failures":report["external_live"].get("network_failures",0),
        },
        "channels":report["external_live"].get("channel_status",{}),
        "catalog":{
            "entries":len(sportguide_catalog.get("entries",[])),
            "channel_map":len(sportguide_catalog.get("channel_map",{})),
            "cache_age_hours":sportguide_catalog.get("_cache_age_hours"),
            "cache_valid":sportguide_catalog.get("_cache_valid"),
        },
        "errors":report["external_live"].get("errors",[]),
    },ensure_ascii=False,indent=2),encoding="utf-8")
    health_file.write_text(json.dumps(health_report,ensure_ascii=False,indent=2),encoding="utf-8")
    trend_file.write_text(json.dumps({"version":"3.18","generated_at_utc":report["generated_at_utc"],
        "health_score":health_report.get("health_score"),"status":health_report.get("status"),
        "trend":health_report.get("trend",{}),"comparison":health_report.get("comparison",{})},ensure_ascii=False,indent=2),encoding="utf-8")
    history_file.write_text(json.dumps({"version":2,"generated_at_utc":report["generated_at_utc"],
        "builds":health_history.get("builds",[]),"count":len(health_history.get("builds",[])),
        "canonical_cache":settings.get("health_history_file",".cache/build_history.json")},ensure_ascii=False,indent=2),encoding="utf-8")
    write_status_html(status_file, report)

    print(json.dumps(report["summary"],ensure_ascii=False,indent=2))
    for p in [out_xml,out_gz,report_file,quality_file,live_file,empty_file,audit_file,recommendations_file,catalog_file,recovery_file,channel_recovery_file,promotion_file,verified_fallback_file,external_recovery_file,health_file,trend_file,history_file,status_file]: print(f"Created: {p}")
    if report["summary"]["channels_matched"] == 0: sys.exit(2)
    if settings.get("fail_on_missing_channels", False) and report["summary"]["channels_missing"] > 0: sys.exit(3)
    if settings.get("fail_on_empty_channels", False) and report["summary"].get("channels_empty",0) > 0: sys.exit(4)
    if settings.get("health_fail_on_critical", False) and report["summary"].get("health_status")=="critical": sys.exit(5)

if __name__ == "__main__":
    main()
