# se2-vrb-tools
Offline tools for Space Engineers 2 save files. Read, inspect and repair saves without the game running.

Right now it can:
- parse and verify `.vrb` archives (the SE2 save container format)
- remove the "altered with Debug Menu" mark from a save
- list the type and field names stored in a save

## Setup
Python 3.11+.
```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Usage
Close Space Engineers 2 first. Saves live in `%AppData%\SpaceEngineers2\AppData\SaveGames`.

Remove the debug menu mark:
```
.venv\Scripts\python tools\unflag.py "%AppData%\SpaceEngineers2\AppData\SaveGames\<save>" --dry-run
.venv\Scripts\python tools\unflag.py "%AppData%\SpaceEngineers2\AppData\SaveGames\<save>"
```
It backs up the touched files to `%LocalAppData%\se2-vrb-tools\backups` before writing. Don't open the debug menu (Ctrl+F12) in that save again, or the mark comes back.

Inspect archives:
```
.venv\Scripts\python tools\inspect_vrb.py "<save>\sessioncomponents.vrb" --names
```

## How it works
See [docs/vrb-format.md](docs/vrb-format.md) for the file format and checksum details.

## Disclaimer
Editing saves can break them. Keep backups. Not affiliated with Keen Software House.

## License
AGPL-3.0, see [LICENSE](LICENSE).
