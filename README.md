# Bartosz Sports EPG v3.19 — Sofascore LIVE verification

Ta wersja rozwija v3.18 LIVE Accuracy 2 i dodaje drugą, niezależną warstwę weryfikacji transmisji LIVE na podstawie terminarza Sofascore.

## Najważniejsza zmiana

Sofascore nie zastępuje EPG. Generator używa go jako zegara referencyjnego dla realnego wydarzenia sportowego:

1. rozpoznaje dyscyplinę i uczestników w tytule EPG,
2. pobiera wydarzenia Sofascore dla dnia poprzedniego, bieżącego i następnego,
3. dopasowuje obie drużyny/zawodników oraz godzinę,
4. zgodność wydarzenia i czasu -> `🔴 LIVE`,
5. ten sam mecz znaleziony kilka godzin wcześniej/później -> emisja traktowana jako powtórka i LIVE jest blokowane.

To ma szczególnie poprawić Eleven Sports, Canal+ Sport/Extra, Polsat Sport i inne kanały, gdzie dostawca EPG nie podaje wiarygodnego znacznika LIVE.

## Priorytet decyzji v3.19

`Sofascore potwierdzony czas wydarzenia` → `Sport TV Guide` → `jawne LIVE w EPG` → `heurystyka`.

Jeżeli Sofascore znajdzie ten sam mecz o innej godzinie (domyślnie różnica >= 180 min i <= 36 h), działa **replay veto** — taki program nie będzie oznaczony jako LIVE nawet wtedy, gdy provider pozostawił w tytule słowo LIVE.

## Bezpieczeństwo i fallback

Integracja jest opcjonalna i awaria Sofascore nie zatrzymuje buildu. Dane są cache'owane w `.cache/sofascore`:
- świeży cache: 6 h,
- awaryjny stale cache: do 48 h,
- po braku danych generator wraca do Sport TV Guide i dotychczasowych reguł.

Endpoint Sofascore używany przez stronę nie jest tu traktowany jako gwarantowane publiczne API, dlatego integracja jest odseparowana i ma cache/fallback.

## Diagnostyka

Nowy raport: `docs/sofascore_live.json`.

Status pokazuje dodatkowo:
- `Sofascore LIVE` — transmisje potwierdzone przez godzinę wydarzenia,
- `Sofascore replay veto` — emisje rozpoznane jako powtórki tego samego wydarzenia,
- liczbę udanych/nieudanych zapytań i wydarzeń w cache.

## Testy

Dodany `v319_sofascore_test.py`, który sprawdza m.in.:
- `PKO BP Ekstraklasa: Widzew Łódź - Wieczysta Kraków` o właściwej godzinie -> LIVE,
- ten sam mecz następnego ranka -> powtórka, nawet jeśli provider wpisze LIVE,
- typowy mecz Eleven Sports `SS Lazio - AC Milan` -> LIVE po zgodności obu drużyn i godziny.

Workflow GitHub Actions został też poprawiony: testy v3.18/v3.19 są osobnymi poprawnymi krokami YAML.
