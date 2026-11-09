# SC Blueprint Tracker · Fabrication Kiosk

Neslužbeni tracker za crafting u Star Citizenu, napravljen od strane zajednice.
Statična web stranica bez servera i registracije: svaki posjetitelj ima svoj profil u svom pregledniku.

Ovaj paket je napravljen za **GitHub Pages**. Automatski zadatak (GitHub Action):
- svakih 6 sati provjeri koje verzije igre su trenutno na LIVE-u i PTU-u (RSI patch notes),
- povuče nove podatke iz datoteka igre kad ih Star Citizen Wiki objavi,
- ponovno sastavi stranicu i objavi je.

Ti ne moraš raditi ništa.

---

## 1. Postavljanje (jednom, ~10 minuta)

1. Napravi besplatni račun na https://github.com (ako ga nemaš).
2. Gore desno **+ → New repository**:
   - ime npr. `sc-blueprint-tracker`
   - **Public** (GitHub Pages je besplatan za javne repozitorije)
   - ostalo ostavi kako je → **Create repository**.
3. Na stranici novog repozitorija klikni **uploading an existing file**.
   Raspakiraj ovaj zip i povuci **sav sadržaj mape** (ne samu mapu) u prozor → **Commit changes**.
4. **Provjeri da je stigla mapa `.github`.** Neki preglednici kod povlačenja preskoče
   mape koje počinju točkom. Ako je nema:
   **Add file → Create new file**, za ime upiši `.github/workflows/update.yml`,
   zalijepi sadržaj iste datoteke iz zipa → **Commit changes**.
5. **Settings → Actions → General** → na dnu, u dijelu *Workflow permissions*, odaberi
   **Read and write permissions** → **Save**.
6. **Settings → Pages** → kod *Source* odaberi **GitHub Actions**.
7. **Actions** → lijevo **Update game data and publish** → **Run workflow**.
   Nakon 2–3 minute pojavi se zelena kvačica.
8. Stranica je na `https://TVOJE-IME.github.io/sc-blueprint-tracker/`
   (adresa piše i pod **Settings → Pages**).

Vlastita domena: **Settings → Pages → Custom domain**.

---

## 2. Što se događa automatski

Svakih 6 sati (i kad nešto promijeniš u repozitoriju) zadatak:

1. **Provjeri verzije igre** iz službenih RSI izvora (Spectrum patch notes, RSI Roadmap),
   a kao rezervu koristi patchbot.io. Rezultat ide u `data/status.json`.
2. **Provjeri ima li novih podataka igre** u
   [StarCitizenWiki/scunpacked-data](https://github.com/StarCitizenWiki/scunpacked-data).
   To nisu ručno pisani članci nego podaci izvučeni izravno iz datoteka igre (`Data.p4k`).
   Ako je verzija nova, povuče blueprinte i slike, sastavi stranicu, spremi promjene
   u repozitorij i podigne verziju u `sw.js`.
3. **Traži slike sa Star Citizen Wikija** za blueprinte koji nemaju pravu sliku u Datapadu
   (varijante, spremnici i ostalo) i za sve **materijale** (rude i minerale). Kod materijala pazi
   na razlike u nazivima, npr. „Aluminum” u igri je „Aluminium” na Wikiju. Svaki predmet pita samo jednom, a one bez slike ponovno provjeri
   nakon 14 dana. Slike se spremaju u `tools/wiki/`. Redoslijed je: prava slika iz Datapada,
   zatim slika s Wikija, a tek onda slika osnovnog modela s oznakom „privremena slika”
   (samo za prave varijante iste kategorije, nikad npr. puška za spremnik).
4. **Objavi stranicu.**

Na stranici, u **⚙ Postavke → Status podataka** i na gumbu s verzijom u gornjoj traci, korisnici vide:
- 🟢 **Usklađeno s igrom**: podaci odgovaraju buildu na LIVE-u.
- 🟠 **Sinkroniziramo**: na LIVE-u je noviji build, a podaci iz igre još nisu objavljeni.
  Obično traje dan-dva. Kod malih hotfixeva podaci su često isti.
- ⚪ **Nije moguće provjeriti**: nijedan izvor trenutno ne odgovara.
- **PTU verzija** i, ako postoje PTU podaci, broj novih, promijenjenih i uklonjenih blueprinta,
  s prekidačem „Prikaži PTU promjene”.
- **Tvoja igra**: kad korisnik učita Game.log, vidi svoj build i je li usklađen s podacima.

Profili korisnika se pri svakoj promjeni podataka **automatski prilagode**:
preimenovani blueprinti zadrže oznaku „imam”, novi dobiju oznaku **NEW**, a uklonjeni ostaju sačuvani.

> GitHub gasi zakazane zadatke u repozitoriju bez ikakve aktivnosti 60 dana.
> Novi podaci obično stižu svaki mjesec pa se to ne bi trebalo dogoditi.
> Ako se dogodi, u **Actions** klikni **Enable workflow**.

---

## 3. PTU (nadolazeće promjene), neobavezno

Verziju PTU-a zadatak prati sam. **PTU podaci o blueprintima** se nigdje ne objavljuju redovito,
pa ih dodaješ ručno kad želiš. Upute su u `tools/ptu/README.md`, ukratko:
1. iz PTU instalacije izvuci `blueprints.json` alatom ScDataDumper,
2. stavi ga u `tools/ptu/` zajedno s `version.txt` (npr. `4.10.3-PTU.13132336`),
3. commitaj. Stranica tada označi PTU promjene oznakom **PTU** (ljubičasto).

Kad taj patch izađe na LIVE, PTU oznake nestaju same.

---

## 4. Ručno ažuriranje i izmjene (za napredne)

Treba Python 3.10+ i git.

```
cd tools
python3 update.py            # isto što radi GitHub zadatak
python3 update.py --force    # ponovno sastavi sve, i bez novih podataka
```

- Izgled i tekstovi: `tools/kiosk_src.html` (prijevodi su u objektu `TR`), zatim `python3 build.py`.
- `build_catalog.py`: blueprinti, recepti i misije.
- `build_imgs.py`: odabir slike za svaki blueprint (Datapad, Wiki, varijante).
- `fetch_wiki_images.py`: dohvat slika sa Star Citizen Wikija.
- `build_ptu.py`: usporedba PTU s LIVE.
- `check_versions.py`: provjera verzija i `data/status.json`.

---

## 5. Kasnije promjene – pravilo koje treba zapamtiti

U repozitoriju su dvije vrste datoteka:

| Mijenjaš ti (ili Claude) | Mijenja ih samo automatski zadatak – **ne diraj ih** |
|---|---|
| `tools/kiosk_src.html` (izgled, tekstovi, prijevodi, funkcije) | `index.html` |
| `tools/*.py` (alati) | `img/` (slike) |
| `tools/ptu/` (PTU podaci) | `tools/catalog.json`, `tools/imgdata.json` |
| `README.md`, `THIRD-PARTY.md`, `favicon.svg`, ikone | `tools/wiki/` (slike s Wikija) |
| `.github/workflows/update.yml` | `sw.js` (broj verzije), `data/` |

Svaka promjena se ubaci na GitHub i **zadatak se sam pokrene**. Za 2–3 minute iz `tools/kiosk_src.html`
ponovno sastavi `index.html`, s već skinutim slikama s Wikija, i objavi stranicu.
Zato se promjene i slike nikad ne sudaraju: ti mijenjaš izvor, a zadatak slaže gotovu stranicu.

Ako greškom ubaciš stari `index.html`, ništa se ne kvari jer ga zadatak pri sljedećem pokretanju
ponovno složi. Mapu `img/` i datoteke iz `tools/` koje mijenja zadatak nemoj zamjenjivati starima. Ako baš treba, u **Actions → Run workflow** pokreneš ga ručno.

---

## Nazivi

Nazivi su iz datoteka igre, uz tri ispravka:
- **Posebni razmaci** (nevidljivi znak koji CIG ponekad koristi) zamijenjeni su običnim, da pretraga radi.
- **Predmeti bez naziva u igri** (5 komponenti za Idris, Polaris, Javelin, Pioneer i Lephari) dobili su
  ime iz podataka, npr. „Radar S4 (Polaris)”, i to piše uz njih.
- **Različiti predmeti s istim imenom** (npr. dva „Serac” hladnjaka, „Antium Core Jet” koji je i oklop i kaciga)
  dobili su dodatak u zagradi, npr. „Serac (Polaris)”. Uz njih piše pravi naziv iz igre. Kad Game.log
  javi takav naziv, označe se svi predmeti s tim imenom, jer se iz loga ne može znati koji je.

## Privatnost

Stranica ne učitava ništa s drugih servera (ni font s Googlea) i nema kolačića, analitike ni praćenja.
Profil svakog posjetitelja ostaje u njegovom pregledniku, a Game.log se čita lokalno i nikamo se ne šalje.
Jedino hosting (GitHub Pages) vodi uobičajene zapise o posjetima. Detalji i licence su u `THIRD-PARTY.md`.

## Izvori i napomene

- Podaci o blueprintima: datoteke igre, preko [scunpacked-data](https://github.com/StarCitizenWiki/scunpacked-data) (Star Citizen Wiki, ScDataDumper).
- Slike predmeta: [Datapad](https://github.com/jpcoombes-byte/Datapad) (jpcoombes-byte).
- Verzije igre: RSI Spectrum patch notes i RSI Roadmap, uz patchbot.io kao rezervu.
- Ovo je neslužbena stranica zajednice i nije povezana s tvrtkama Cloud Imperium grupe.
  Star Citizen® je zaštićeni znak Cloud Imperiuma. Stranica nikad ne dira igru,
  a Game.log samo čita kao tekst. Prema pravilima RSI-ja za stranice zajednice
  mora ostati besplatna i jasno označena kao neslužbena (napomena je u podnožju stranice).
