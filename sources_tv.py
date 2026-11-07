"""Lecture des grilles TRT Spor (Turquie) et Match TV (Russie).

Les deux pages sont construites par JavaScript : on les ouvre avec Playwright
(navigateur sans écran) puis on lit le texte affiché. Les fonctions parse_* ne
dépendent que du texte et sont testables sans réseau.
"""
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TRT_URL = "https://www.trtspor.com.tr/yayin-akisi/trt-spor"
MATCHTV_URL = "https://matchtv.ru/tvguide"
TZ_TR = ZoneInfo("Europe/Istanbul")
TZ_RU = ZoneInfo("Europe/Moscow")

MOIS_RU = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
           "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}


def fetch_text(url, attente_ms=4000):
    from playwright.sync_api import sync_playwright  # import tardif : seulement en exécution réelle
    with sync_playwright() as p:
        nav = p.chromium.launch()
        page = nav.new_page(viewport={"width": 1280, "height": 900})
        page.goto(url, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(attente_ms)
        texte = page.inner_text("body")
        nav.close()
    return texte


# ---------- TRT Spor ----------
_TRT_ENTREE = re.compile(r"(\d{2}:\d{2})\s+(.*?)(?=\s\d{2}:\d{2}\s|$)")


def parse_trt(texte, aujourdhui):
    """aujourdhui : date locale turque. La grille commence à la première heure listée
    et passe au jour suivant quand l'heure redescend (ex. 23:00 puis 01:00)."""
    t = re.sub(r"\s+", " ", texte)
    k = t.rfind("Yayın Akışı")
    if k != -1:
        t = t[k + len("Yayın Akışı"):]
    out, jour, precedent = [], aujourdhui, None
    for hhmm, titre in _TRT_ENTREE.findall(t):
        h, m = map(int, hhmm.split(":"))
        if precedent is not None and (h, m) < precedent:
            jour += timedelta(days=1)
        precedent = (h, m)
        up = titre.upper()
        if "KARŞILAŞMASI" in up or up.startswith("CANLI"):
            if up.startswith("TEKRAR"):
                continue
            debut = datetime(jour.year, jour.month, jour.day, h, m, tzinfo=TZ_TR)
            out.append({"chaine": "TRT Spor", "pays": "Turquie", "titre": titre.strip()[:140],
                        "debut": debut.astimezone(timezone.utc), "en_cours": False, "url": TRT_URL})
    return out


# ---------- Match TV (bloc « Главное на неделе ») ----------
_MTV_JOUR = r"(?:Сегодня|Завтра|\d{1,2}\s+[а-я]+)"
_MTV_ENTREE = re.compile(rf"({_MTV_JOUR}),\s*(\d{{2}}:\d{{2}})\s+(.*?)(?=\s{_MTV_JOUR},\s*\d{{2}}:\d{{2}}\s|$)")
_COTES = re.compile(r"\d\.\d{2}\s\d\.\d{2}\s\d\.\d{2}\s18\+\sРеклама")
_FOOT = ("футбол", "лига", "чемпионат", "кубок", "тур ")
_PAS_FOOT = ("единоборств", "хоккей", "биатлон", "теннис", "баскетбол", "формула")


def parse_matchtv(texte, aujourdhui):
    """aujourdhui : date locale à Moscou. Ne lit que les entrées datées explicitement."""
    t = re.sub(r"\s+", " ", texte)
    k = t.find("Сегодня,")
    t = t[k:] if k != -1 else t
    out = []
    for jour_txt, hhmm, reste in _MTV_ENTREE.findall(t):
        if jour_txt == "Сегодня":
            d = aujourdhui
        elif jour_txt == "Завтра":
            d = aujourdhui + timedelta(days=1)
        else:
            n, mois = jour_txt.split()
            if mois not in MOIS_RU:
                continue
            d = aujourdhui.replace(month=MOIS_RU[mois], day=int(n))
            if d < aujourdhui - timedelta(days=30):
                d = d.replace(year=d.year + 1)
        reste = _COTES.sub("", reste).strip()
        titre = reste[:140]
        bas = titre.lower()
        if any(x in bas for x in _PAS_FOOT) or not any(x in bas for x in _FOOT):
            continue
        h, m = map(int, hhmm.split(":"))
        debut = datetime(d.year, d.month, d.day, h, m, tzinfo=TZ_RU)
        out.append({"chaine": "Матч ТВ", "pays": "Russie", "titre": titre,
                    "debut": debut.astimezone(timezone.utc), "en_cours": False, "url": MATCHTV_URL})
    return out


def lives_trt(maintenant):
    return parse_trt(fetch_text(TRT_URL), maintenant.astimezone(TZ_TR).date())


def lives_matchtv(maintenant):
    return parse_matchtv(fetch_text(MATCHTV_URL), maintenant.astimezone(TZ_RU).date())
