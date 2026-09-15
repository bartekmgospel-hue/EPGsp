import epg_generator as e

samples = {
    "Piłka nożna: Liga hiszpańska": "football",
    "Żużel: PGE Ekstraliga": "speedway",
    "Żużel: Metalkas 2. Ekstraliga": "speedway",
    "Toruń - Lublin: Półfinał Ekstraligi": "speedway",
    "Liga włoska: mecz: SS Lazio - AC Milan": "football",
    "Liga niemiecka: mecz: RB Lipsk - Haburger SV": "football",
    "Formuła 1: Grand Prix Hiszpanii": "motorsport",
    "Liga portugalska: mecz: FC Familicao - Sporting CP": "football",
    "Siatkówka mężczyzn: Mistrzostwa Europy 2026": "volleyball",
    "Liga portugal Betclic 2026-27": "football",
    "Serie A 2026-27": "football",
    "Kolarstwo: Giro d'Abruzzo": "cycling",
    "Motocross World": "motocross",
}

for title, expected in samples.items():
    sport = e.sport_from_text(title)
    assert sport is not None, title
    assert sport["key"] == expected, (title, sport["key"], expected)

print("v3.18 sport icon tests OK")
