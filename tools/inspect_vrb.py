"""Inspect .vrb archives: header, checksums, and the type/field names in the type table.

usage: python inspect_vrb.py <file.vrb>... [--names] [--extract DIR]
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from vrb import COMPRESSION, Archive, expand_path  # noqa: E402


def names(type_table: bytes) -> list[str]:
    # type names are stored as ASCII, field names as UTF-16
    found = {m.group().decode() for m in re.finditer(rb"[A-Za-z0-9_.:`]{3,}", type_table)}
    found |= {m.group().decode("utf-16-le") for m in re.finditer(rb"(?:[A-Za-z0-9_.:`]\x00){3,}", type_table)}
    return sorted(found)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=expand_path)
    ap.add_argument("--names", action="store_true", help="list type and field names")
    ap.add_argument("--extract", type=expand_path, help="write decompressed sections to this folder")
    args = ap.parse_args()

    for path in args.files:
        a = Archive.load(path)
        print(f"== {path.name}  v{a.version}  {len(a.data)} bytes")
        checks = a.verify()
        print(f"   header checksum {a.checksum:016x} {'OK' if checks['header'] else 'BAD'}")
        for e in a.entries():
            print(f"   {e.name:<10} @{e.offset:<9} {e.size:>9} -> {e.raw_size:>9} bytes  "
                  f"{COMPRESSION.get(e.compression, e.compression):<6} {'OK' if checks[e.name] else 'BAD'}")
        if args.names:
            for n in names(a.read("type")):
                print("     ", n)
        if args.extract:
            args.extract.mkdir(parents=True, exist_ok=True)
            for e in a.entries():
                (args.extract / f"{path.stem}.{e.name}.bin").write_bytes(a.read(e.name))


if __name__ == "__main__":
    main()
