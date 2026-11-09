# PTU podaci (neobavezno)

PTU podaci o blueprintima ne objavljuju se nigdje redovito, pa ih ovdje dodaješ ručno
kad želiš pokazati nadolazeće promjene.

1. Instaliraj PTU u RSI Launcheru.
2. Izvuci podatke alatom ScDataDumper (https://github.com/octfx/ScDataDumper) iz
   `...\StarCitizen\PTU\Data.p4k`. To je isti alat kojim Star Citizen Wiki radi LIVE podatke.
3. Datoteku `blueprints.json` stavi u ovu mapu (`tools/ptu/blueprints.json`).
4. U `tools/ptu/version.txt` upiši točnu verziju iz launchera ili Game.loga, npr.
   `4.10.3-PTU.13132336`
5. Commitaj obje datoteke na GitHub. Automatski zadatak usporedi PTU s LIVE podacima
   i na stranici označi nove, promijenjene i uklonjene blueprinte kao **PTU**.

Kad taj patch izađe na LIVE, PTU oznake nestaju same. Datoteke možeš i obrisati.
