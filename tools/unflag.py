"""Clear the "Used Debug Menu" mark from a Space Engineers 2 save.

usage: python unflag.py "<save folder>" [--dry-run]

Patches the flag in sessioncomponents.vrb (what the game actually reads) and in
.container-info (the cached copy shown in the save list). Backs up both first.
"""
import argparse
import datetime
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from vrb import Archive  # noqa: E402

# start of the world info record in the session components main chunk; fields follow in order:
# SaveName (string), WorldType (string), PersistentID (Guid), UsedDebugMenu (bool)
WORLD_INFO_MARKER = b"\x00\x3f\x02\x00\x00\x10\x02\x00\x00\x00"
BACKUP_ROOT = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "se2-vrb-tools" / "backups"


def find_flag(body: bytes):
    i = body.find(WORLD_INFO_MARKER)
    if i == -1 or body.find(WORLD_INFO_MARKER, i + 1) != -1:
        raise ValueError("world info record not found exactly once, save layout may have changed")
    p = i + len(WORLD_INFO_MARKER)
    name_len = struct.unpack_from("<I", body, p)[0]
    save_name = body[p + 4:p + 4 + name_len].decode("utf-16-le")
    p += 4 + name_len + 1
    type_len = struct.unpack_from("<I", body, p)[0]
    world_type = body[p + 4:p + 4 + type_len].decode("utf-16-le")
    flag_at = p + 4 + type_len + 16
    if body[flag_at] not in (0, 1) or body[flag_at + 1:flag_at + 6] != b"\x00\x01\x00\x00\x00":
        raise ValueError("unexpected bytes around the flag, refusing to patch")
    return save_name, world_type, flag_at


def game_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq SpaceEngineers2.exe"], capture_output=True, text=True).stdout
    return "SpaceEngineers2.exe" in out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("save", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    vrb_path = args.save / "sessioncomponents.vrb"
    info_path = args.save / ".container-info"
    archive = Archive.load(vrb_path)
    if not all(archive.verify().values()):
        sys.exit(f"{vrb_path} fails checksum verification, not touching it: {archive.verify()}")

    body = bytearray(archive.read("main"))
    save_name, world_type, flag_at = find_flag(body)
    info = json.loads(info_path.read_text(encoding="utf-8-sig"))
    meta_flag = info["$Value"]["Meta"].get("UsedDebugMenu")
    print(f"save:      {save_name} ({world_type})")
    print(f"session:   UsedDebugMenu = {bool(body[flag_at])}")
    print(f"metadata:  UsedDebugMenu = {meta_flag}")

    if not body[flag_at] and not meta_flag:
        print("already clean")
        return
    if args.dry_run:
        print("dry run")
        return
    # the running game re-stamps the flag on its next save and caches the save list
    if game_running():
        sys.exit("Space Engineers 2 is running. Quit it completely, then run this again.")

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = BACKUP_ROOT / f"{args.save.name}-{stamp}"
    backup.mkdir(parents=True)
    shutil.copy2(vrb_path, backup)
    shutil.copy2(info_path, backup)
    print(f"backup:    {backup}")

    if body[flag_at]:
        body[flag_at] = 0
        archive.with_main(bytes(body)).save(vrb_path)
    if meta_flag:
        info["$Value"]["Meta"]["UsedDebugMenu"] = False
        info_path.write_text(json.dumps(info, indent=2), encoding="utf-8", newline="\r\n")
    print("done. Load the save without opening the debug menu (Ctrl+F12), or it gets marked again.")


if __name__ == "__main__":
    main()
