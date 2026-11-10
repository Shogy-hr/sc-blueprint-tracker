# Ikone iz igre / In-game icons

`src/` holds UI icons copied from the Star Citizen `Data.p4k` (© Cloud Imperium):
- `Inv_Icon_*.svg`: inventory icons of resources (`Data/UI/Textures/Vector/General/Items`)
- `Mineral_256.png`, `Metal_256.png`: generic commodity icons (`Data/UI/SharedAssets/commodityLogos`, converted from DDS)
- `Engineering_Icon_Item*.svg`, `mining.svg`, `salvage.svg` …: component and tool icons (`Data/UI/Textures/Vector/...`)

`make.py` turns them into small tinted WebP images (`out/mats.json`, `out/subs.json`); needs `rsvg-convert` and Pillow, so it is run by hand, not by the bot.
`tools/sclib.py:add_game_icons()` puts them into `imgdata.json` on every image build: a material icon from the game wins over a wiki photo, and items without a picture show the in-game icon of their category.
New ores that have no icon of their own get the generic in-game mineral icon.
