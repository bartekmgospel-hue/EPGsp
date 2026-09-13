# Sports EPG v3.17 — Confidence-aware Health Score Edition

V3.17 zachowuje wszystkie mechanizmy v3.16 i sprawia, że Health Score reaguje również na pojedyncze anomalie wykryte przez trend monitor.

## Najważniejsze zmiany

- `single_anomaly` nadal **nie zmienia automatycznie statusu na warning**
- Health Score dostaje małą karę zależną od confidence:
  - `low` → -1 pkt
  - `medium` → -4 pkt
  - `high` → -7 pkt
- łączna kara za pojedyncze anomalie jest ograniczona do **12 pkt**
- persistent regression nadal ma osobną, mocniejszą ścieżkę karania
- nowy komponent: `health_score_components.single_anomaly_penalty`
- raport summary dodaje `health_score_single_anomaly_penalty`
- unified history seed zawiera realne buildy **v3.13–v3.16**, więc pierwszy build v3.17 ma 5-punktową historię

## Oczekiwane zachowanie dla realnego wyniku v3.16

Przy `external_live: 101 → 83`, `single_anomaly`, `medium confidence`:

```json
{
  "health_status": "healthy",
  "health_score": 96,
  "health_score_single_anomaly_penalty": 4,
  "health_trend_status": "single_anomaly",
  "health_trend_confidence": "medium"
}
```

Jeśli v3.17 wróci do ~101 External LIVE, trend powinien się ustabilizować/poprawić, a Health Score może wrócić do 100. Jeśli spadek utrzyma się w kolejnym buildzie, trend może zostać sklasyfikowany jako `persistent_regression` i dostać mocniejszą karę.

## Uruchomienie

```bash
cd ~/Downloads/sports-epg-v3.17
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python verify_config.py
python smoke_test.py
python quality_test.py
python integration_test.py
python regression_test.py
python v34_test.py
python v35_test.py
python v36_test.py
python v37_test.py
python v38_test.py
python v39_test.py
python v310_test.py
python v311_test.py
python v312_test.py
python v313_test.py
python v314_test.py
python v315_test.py
python v316_test.py
python v317_test.py
python epg_generator.py
```

Po buildzie najlepiej przesłać `report.json`, `build_health.json`, `build_trends.json`, `build_history.json` i `external_live_recovery.json`.
