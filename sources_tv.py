"""Lecture des grilles TRT Spor (Turquie) et Match TV (Russie).

Les deux pages sont construites par JavaScript : on les ouvre avec Playwright
(navigateur sans écran) puis on lit le texte affiché. Les fonctions parse_* ne
dépendent que du texte et sont testables sans réseau.
"""
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TRT_URL = "https://www.trtspor.com.tr/yayin-akisi/trt-spor"

TZ_TR = ZoneInfo("Europe/Istanbul")
TZ_RU = ZoneInfo("Europe/Moscow")

def fetch_text(url, attente_ms=8000):
    from playwright.sync_api import sync_playwright  # import tardif : seulement en exécution réelle
    with sync_playwright() as p:
        nav = p.chromium.launch()
        page = nav.new_page(viewport={"width": 1280, "height": 900})
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
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


# ---------- Match TV (chaîne principale « Матч ТВ » uniquement) ----------
# Source : grille par chaîne de news.sportbox.ru. La journée TV commence à 04:00 (Moscou).
SPORTBOX_URL = "https://news.sportbox.ru/tv?date={d}"
_AUTRES_CHAINES = ("матч премьер", "матч страна", "матч арена", "футбол 1", "футбол 2", "футбол 3",
                   "матч! премьер", "матч! страна", "матч! арена", "матч! футбол", "sportbox.ru",
                   "матч! боец", "матч! игра", "матч! наш спорт")
_LIGNE = re.compile(r"^(\d{2}:\d{2})\s+(.+)$")
_PAS_FOOT = ("волейбол", "гандбол", "регби", "хоккей", "баскетбол", "бокс", "единоборств", "атлетик",
             "водное поло", "плаван", "гимнаст", "теннис", "биатлон", "автоспорт", "формул", "бильярд",
             "футзал", "пляжный", "падел", "прыжки", "гонки", "шахмат")


def parse_matchtv(texte, jour_tv):
    """jour_tv : date de la journée TV (04:00 de ce jour à 03:59 du lendemain, heure de Moscou)."""
    lignes = [l.strip() for l in texte.splitlines() if l.strip()]
    try:
        k = next(i for i, l in enumerate(lignes) if l.lower() == "матч тв")
    except StopIteration:
        return []
    out = []
    for l in lignes[k + 1:]:
        if not _LIGNE.match(l) and l.upper() == l and len(l) < 40:
            break  # titre de la chaîne suivante (en majuscules)
        m = _LIGNE.match(l)
        if not m:
            continue
        h, mi = map(int, m.group(1).split(":"))
        titre = m.group(2)
        d = jour_tv + timedelta(days=1) if (h, mi) < (4, 0) else jour_tv
        bas = titre.lower()
        direct = "прямая трансляция" in bas or bas.endswith("live")
        foot = "футбол" in bas or re.search(r"\S\s[-–]\s\S", titre)
        if direct and foot and not any(x in bas for x in _PAS_FOOT):
            debut = datetime(d.year, d.month, d.day, h, mi, tzinfo=TZ_RU)
            out.append({"chaine": "Матч ТВ", "pays": "Russie", "titre": titre[:140],
                        "debut": debut.astimezone(timezone.utc), "en_cours": False,
                        "url": SPORTBOX_URL.format(d=jour_tv.isoformat())})
    return out


def lives_trt(maintenant):
    texte = fetch_text(TRT_URL)
    r = parse_trt(texte, maintenant.astimezone(TZ_TR).date())
    if not r:
        debut = re.sub(r"\s+", " ", texte)[:100]
        raise RuntimeError(f"rien reconnu (texte de {len(texte)} caractères, début : {debut})")
    return r


def lives_matchtv(maintenant):
    aujourdhui = maintenant.astimezone(TZ_RU).date()
    vus, out, notes = set(), [], []
    for delta in (-1, 0, 1, 2, 3, 4):
        jour = aujourdhui + timedelta(days=delta)
        try:
            texte = fetch_text(SPORTBOX_URL.format(d=jour.isoformat()))
        except Exception as e:
            notes.append(f"{jour:%d/%m} : {str(e).splitlines()[0][:60]}")
            continue
        notes.append(f"{jour:%d/%m} : {len(texte)} car., entête {'Матч ТВ' in texte}")
        for x in parse_matchtv(texte, jour):
            if (x["debut"], x["titre"]) not in vus:
                vus.add((x["debut"], x["titre"]))
                out.append(x)
    if not out:
        raise RuntimeError("rien reconnu (" + " ; ".join(notes) + ")")
    return out
