from datetime import datetime, timedelta, timezone
import programme as p

now = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
ch = {"nom": "CazéTV", "pays": "Brésil", "handle": "x"}
vids = [
    {"id": "a", "snippet": {"title": "Bodø/Glimt x Viking | AO VIVO"},
     "liveStreamingDetails": {"scheduledStartTime": iso(now + timedelta(hours=7))}},
    {"id": "b", "snippet": {"title": "Flamengo x Palmeiras | AO VIVO"},
     "liveStreamingDetails": {"actualStartTime": iso(now - timedelta(minutes=30)),
                              "scheduledStartTime": iso(now - timedelta(minutes=40))}},
    {"id": "c", "snippet": {"title": "Vieux match x Rien"},
     "liveStreamingDetails": {"actualStartTime": iso(now - timedelta(days=2)),
                              "actualEndTime": iso(now - timedelta(days=2, hours=-2))}},
    {"id": "d", "snippet": {"title": "Vidéo normale"}},
    {"id": "e", "snippet": {"title": "Match dans 5 jours x Équipe"},
     "liveStreamingDetails": {"scheduledStartTime": iso(now + timedelta(days=5))}},
    {"id": "f", "snippet": {"title": "Podcast sans rapport"},
     "liveStreamingDetails": {"scheduledStartTime": iso(now + timedelta(hours=3))}},
]
r = p.extraire_lives(vids, ch, now)
titres = [x["titre"] for x in r]
assert titres == ["Bodø/Glimt x Viking | AO VIVO", "Flamengo x Palmeiras | AO VIVO"] or \
       sorted(titres) == sorted(["Bodø/Glimt x Viking | AO VIVO", "Flamengo x Palmeiras | AO VIVO"]), titres
assert [x["en_cours"] for x in r if "Flamengo" in x["titre"]] == [True]
page = p.rendre_html(r, ["Test erreur"])
assert "EN DIRECT" in page and "Bodø/Glimt" in page and "08:00" not in page
print("OK", titres)
open("/tmp/apercu.html", "w").write(page)
