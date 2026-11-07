from datetime import date
import sources_tv as s

# Extraits réels relevés le 07/11/2026 dans le navigateur
TRT = ("Yayın Akışı 06:00 TEKRAR UEFA AVRUPA LİGİ ÖZETLER Özetler. "
       "19:00 TRENDYOL 1.LİG FUTBOL KARŞILAŞMASI 14.HAFTA ORFA YAPI PENDİKSPOR FUTBOL A.Ş. - İSTANBULSPOR A.Ş. "
       "21:00 STADYUM Süper Lig heyecanı, Türkiye’nin ekran klasiği Stadyum’da yaşanıyor. "
       "23:00 TEKNİK ANALİZ Süper Lig maçlarının heyecanı. "
       "01:00 FUTBOL GECESİ Süper Lig heyecanı TRT Spor'da. "
       "02:00 TEKRAR UEFA ŞAMPİYONLAR LİGİ KARŞILAŞMASI Tekrar. "
       "03:00 CANLI SÜPER LİG KARŞILAŞMASI Gece maçı.")
r = s.parse_trt(TRT, date(2026, 11, 7))
assert len(r) == 2, r
assert r[0]["debut"].isoformat().startswith("2026-11-07T16:00"), r[0]["debut"]   # 19:00 Istanbul = 16:00 UTC
assert r[1]["debut"].isoformat().startswith("2026-11-08T00:00"), r[1]["debut"]   # 03:00 le lendemain

MTV = ("Эфир Телепрограмма Сегодня, 13:45 Факел - Динамо Москва Альфа-Банк Российская Премьер-Лига. Тур 14 "
       "Сегодня, 16:05 Ахмат - Родина Альфа-Банк Российская Премьер-Лига. Тур 14 2.21 3.55 3.15 18+ Реклама "
       "Сегодня, 22:50 Валенсия - Реал Футбол. Чемпионат Испании. Тур 12 "
       "Завтра, 01:00 UFC Fight Night Смешанные единоборства. Валдо Кортес-Акоста против Джонни Уокера "
       "Завтра, 19:50 Интер - Комо Чемпионат Италии. Тур 11 "
       "9 ноября, 20:35 Балтика - Урал Футбол. Тур 15")
m = s.parse_matchtv(MTV, date(2026, 11, 7))
titres = [x["titre"] for x in m]
assert len(m) == 5, titres
assert not any("UFC" in t for t in titres)
assert "Реклама" not in titres[1], titres[1]
assert m[0]["debut"].isoformat().startswith("2026-11-07T10:45"), m[0]["debut"]   # 13:45 Moscou = 10:45 UTC
assert m[-1]["debut"].day == 9
print("OK", len(r), len(m))
