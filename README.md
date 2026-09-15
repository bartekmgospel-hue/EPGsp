# Sports EPG v3.18 — PlusX expanded SPORT/UK/US/DE/CZ/SK/CA

Ta wersja zachowuje wcześniejsze funkcje v3.18 i rozszerza integrację z `http://list.plusx.tv/pl10.gz`.

## Nowe
- automatyczne wykrywanie dodatkowych kanałów sportowych z PlusX
- zakres krajów: UK, US, DE, CZ, SK, CA
- dodatkowo globalny tryb SPORT: pewnie rozpoznane kanały sportowe mogą być dodane także spoza tych krajów
- kanały już istniejące w katalogu nie są duplikowane
- autoimport zachowuje oryginalny XMLTV `channel id`, co ułatwia automatyczne dopasowanie w TiviMate
- raport: `docs/plusx_autoimport.json`

## Ważne
XMLTV nie przechowuje typowej nazwy grupy IPTV typu `SPORT`, `UK`, `US` itd. Dlatego autoimport opiera się na kodzie kraju w `channel id` / nazwie kanału oraz konserwatywnym rozpoznawaniu sieci sportowych. Dzięki temu nie dodaje masowo kanałów ogólnych, np. BBC One.

## Nadal aktywne
- polskie PlusX jako dodatkowe źródło priorytetowe
- polskie tłumaczenia tytułów
- tylko wersja przetłumaczona, bez dodatkowego `Original/Oryginał`
- ikony sportów i LIVE
- wzbogacanie tytułów o drużyny/zawodników
- snapshot-aware External LIVE monitoring

## Canal+ Extra 1–7

Dodano ręcznie kanały `PL CANAL+ EXTRA 1` … `PL CANAL+ EXTRA 7` z priorytetowym źródłem `poland_plusx` (`http://list.plusx.tv/pl10.gz`). Każdy kanał ma kilka wariantów możliwego `source_id` oraz `autodiscover: true`, dzięki czemu generator może odnaleźć właściwy identyfikator nawet wtedy, gdy PlusX używa innego zapisu nazwy.

## Korekta źródeł Arena/Max Sport
- SR Arena Sport 6–10: tylko źródło `arena_rs`; usunięto błędny fallback do PlusX.
- HR Max Sport 1: tylko źródło `sportklub`; usunięto błędne odwołanie do PlusX.
- Jeżeli kanału nie ma w realnym feedzie źródłowym, generator pozostawi go jako brakujący zamiast sztucznie dopasowywać do PlusX.


## MAXSport 1 — nowe źródło

Dla kanału **HR Max Sport 1** głównym źródłem EPG jest teraz:

`https://iptv-org.github.io/epg/guides/hr/maxtv.hrvatskitelekom.hr.xml`

Źródło: MAXtv / Hrvatski Telekom (mirror iptv-org). Priorytetowy identyfikator XMLTV: `MaxSport1.hr`.
