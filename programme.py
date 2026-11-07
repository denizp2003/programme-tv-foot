#!/usr/bin/env python3
"""Programme du jour : lives YouTube programmés des chaînes de foot.

Usage : YT_API_KEY=xxx python3 programme.py   (écrit index.html)
Clé API gratuite : console.cloud.google.com > YouTube Data API v3.
Coût en quota : environ 3 unités par chaîne et par exécution (quota gratuit : 10 000/jour).
"""
import html
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Modifier cette liste librement : handle YouTube, sans le @.
CHAINES = [
    {"nom": "CazéTV", "handle": "CazeTV", "pays": "Brésil"},
    {"nom": "GE TV", "handle": "getv", "pays": "Brésil"},
    {"nom": "ESPN Brasil", "handle": "ESPNBrasil", "pays": "Brésil"},
    {"nom": "Canal GOAL Brasil", "handle": "CanalGOAL", "pays": "Brésil"},
    {"nom": "SBT Sports", "handle": "SBTSports", "pays": "Brésil"},
    {"nom": "XSports", "handle": "xsports.brasil", "pays": "Brésil"},
    {"nom": "TNT Sports Brasil", "handle": "TNTSportsBR", "pays": "Brésil"},
]
# Si un handle est faux, le script cherche la chaîne par son nom et affiche son identifiant
# dans la console : le copier ici sous la forme {"id": "UC...", ...} pour fixer la chaîne.
# Mots-clés pour ne garder que le foot ; liste vide = tout garder.
MOTS_CLES = ["x ", " vs ", "ao vivo", "futebol", "campeonato", "copa", "liga", "brasileirão"]
FENETRE_HEURES = 96  # 4 jours : lives en cours + à venir sur cette durée
TZ = ZoneInfo("Europe/Paris")
API = "https://www.googleapis.com/youtube/v3/"


def appel(endpoint, **params):
    params["key"] = os.environ["YT_API_KEY"]
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def lives_de_la_chaine(chaine):
    """Retourne les lives en cours ou programmés d'une chaîne (liste de dicts)."""
    if chaine.get("id"):
        c = appel("channels", part="contentDetails", id=chaine["id"])
    else:
        c = appel("channels", part="contentDetails", forHandle=chaine.get("handle", ""))
    if not c.get("items"):  # repli : recherche par nom (100 unités de quota)
        s = appel("search", part="snippet", type="channel", q=chaine["nom"], maxResults=1)
        if not s.get("items"):
            raise RuntimeError("chaîne introuvable")
        cid = s["items"][0]["snippet"]["channelId"]
        print(f"[{chaine['nom']}] trouvée par recherche : {cid} "
              f"({s['items'][0]['snippet']['title']}), à vérifier et à fixer avec \"id\"")
        c = appel("channels", part="contentDetails", id=cid)
    uploads = c["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    items = appel("playlistItems", part="contentDetails", playlistId=uploads, maxResults=50)
    ids = [i["contentDetails"]["videoId"] for i in items.get("items", [])]
    if not ids:
        return []
    vids = appel("videos", part="snippet,liveStreamingDetails", id=",".join(ids))
    return extraire_lives(vids.get("items", []), chaine)


def extraire_lives(videos, chaine, maintenant=None):
    maintenant = maintenant or datetime.now(timezone.utc)
    limite = maintenant + timedelta(hours=FENETRE_HEURES)
    out = []
    for v in videos:
        d = v.get("liveStreamingDetails")
        if not d or d.get("actualEndTime"):
            continue  # pas un live, ou déjà terminé
        debut = d.get("actualStartTime") or d.get("scheduledStartTime")
        if not debut:
            continue
        debut = datetime.fromisoformat(debut.replace("Z", "+00:00"))
        en_cours = "actualStartTime" in d
        if not en_cours and not (maintenant - timedelta(hours=1) <= debut <= limite):
            continue
        titre = v["snippet"]["title"]
        if MOTS_CLES and not any(m in (titre.lower() + " ") for m in MOTS_CLES):
            continue
        out.append({
            "chaine": chaine["nom"], "pays": chaine["pays"], "titre": titre,
            "debut": debut, "en_cours": en_cours,
            "url": "https://www.youtube.com/watch?v=" + v["id"],
        })
    return out


def rendre_html(lives, erreurs):
    lives = sorted(lives, key=lambda x: x["debut"])
    maj = datetime.now(TZ).strftime("%d/%m %H:%M")
    lignes = []
    jour = None
    for l in lives:
        loc = l["debut"].astimezone(TZ)
        if loc.date() != jour:
            jour = loc.date()
            lignes.append(f"<h2>{loc.strftime('%A %d/%m')}</h2>")
        badge = ' <b class="live">EN DIRECT</b>' if l["en_cours"] else ""
        lignes.append(
            f'<div class="m"><span class="h">{loc.strftime("%H:%M")}</span> '
            f'<a href="{html.escape(l["url"])}">{html.escape(l["titre"])}</a>{badge}'
            f'<br><small>{html.escape(l["chaine"])} · {html.escape(l["pays"])}</small></div>'
        )
    if not lives:
        lignes.append("<p>Aucun match trouvé.</p>")
    err = "".join(f"<p class='err'>⚠ {html.escape(e)}</p>" for e in erreurs)
    return f"""<!doctype html><html lang="fr"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Matchs des 4 prochains jours</title>
<style>body{{font:16px system-ui;max-width:640px;margin:1rem auto;padding:0 1rem}}
.m{{padding:.5rem 0;border-bottom:1px solid #ddd}}.h{{font-weight:700;margin-right:.5rem}}
.live{{color:#fff;background:#d00;padding:0 .3rem;border-radius:3px;font-size:.75rem}}
.err{{color:#b00}}small{{color:#666}}</style>
<h1>Matchs des 4 prochains jours</h1><small>Mis à jour {maj} (heure de Paris)</small>
{"".join(lignes)}{err}</html>"""


def main():
    lives, erreurs = [], []
    if "YT_API_KEY" in os.environ:
        for c in CHAINES:
            try:
                lives += lives_de_la_chaine(c)
            except Exception as e:  # une chaîne en panne ne bloque pas les autres
                erreurs.append(f"{c['nom']} : {e}")
    else:
        erreurs.append("YouTube ignoré : variable YT_API_KEY manquante")
    import sources_tv
    maintenant = datetime.now(timezone.utc)
    for nom, f in (("TRT Spor", sources_tv.lives_trt), ("Match TV", sources_tv.lives_matchtv)):
        try:
            trouves = [x for x in f(maintenant)
                       if maintenant - timedelta(hours=2) <= x["debut"] <= maintenant + timedelta(hours=FENETRE_HEURES)]
            if not trouves:
                erreurs.append(f"{nom} : aucun match trouvé (page lue, mais rien de reconnu)")
            lives += trouves
        except Exception as e:
            erreurs.append(f"{nom} : {e}")
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(rendre_html(lives, erreurs))
    print(f"{len(lives)} matchs, {len(erreurs)} erreur(s)")


if __name__ == "__main__":
    main()
