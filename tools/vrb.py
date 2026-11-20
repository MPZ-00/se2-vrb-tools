"""Reader/writer for VRage 3 binary archives (.vrb), the container format of Space Engineers 2 saves.

Layout mirrors Keen.VRage.Library.Serialization.Binary.Archive.ArchiveHeader. See docs/vrb-format.md.
"""
import os
import struct
from dataclasses import dataclass
from pathlib import Path

import brotli
import xxhash

MAGIC = b"VR3B"
SEED = struct.unpack("<I", MAGIC)[0]
HEADER_SIZE = 192
ENTRY_OFFSETS = {"bundle": 16, "type": 52, "chunktable": 88, "main": 132}
COMPRESSION = {0: "none", 1: "zlib", 2: "brotli"}


def expand_path(arg: str) -> Path:
    """argparse type: expand %VAR%/$VAR and ~, since only cmd does that itself."""
    return Path(os.path.expanduser(os.path.expandvars(arg)))


def xxh64(data: bytes) -> int:
    return xxhash.xxh64_intdigest(data, seed=SEED)


@dataclass
class Entry:
    name: str
    offset: int
    checksum: int
    size: int
    raw_size: int
    compression: int


class Archive:
    def __init__(self, data: bytes):
        if data[:4] != MAGIC:
            raise ValueError(f"not a VR3B archive (magic {data[:4]!r})")
        self.data = bytes(data)

    @classmethod
    def load(cls, path) -> "Archive":
        with open(path, "rb") as f:
            return cls(f.read())

    @property
    def version(self) -> int:
        return struct.unpack_from("<I", self.data, 4)[0]

    @property
    def checksum(self) -> int:
        return struct.unpack_from("<Q", self.data, 8)[0]

    def entry(self, name: str) -> Entry:
        at = ENTRY_OFFSETS[name]
        off, chk, size, raw = struct.unpack_from("<QQqq", self.data, at)
        return Entry(name, off, chk, size, raw, self.data[at + 32])

    def entries(self):
        return [e for e in map(self.entry, ENTRY_OFFSETS) if e.offset]

    def raw(self, name: str) -> bytes:
        return self.data[self.entry(name).offset:][:self.entry(name).size]

    def read(self, name: str) -> bytes:
        e = self.entry(name)
        blob = self.raw(name)
        if e.compression == 0:
            return blob
        if e.compression == 2:
            out = brotli.decompress(blob)
        elif e.compression == 1:
            import zlib
            out = zlib.decompress(blob)
        else:
            raise ValueError(f"unknown compression {e.compression}")
        if len(out) != e.raw_size:
            raise ValueError(f"{name}: decompressed {len(out)} bytes, header says {e.raw_size}")
        return out

    def header_checksum(self, data: bytes | None = None) -> int:
        hdr = bytearray((data or self.data)[:HEADER_SIZE])
        hdr[8:16] = bytes(8)
        return xxh64(bytes(hdr))

    def verify(self) -> dict:
        result = {"header": self.checksum == self.header_checksum()}
        for e in self.entries():
            result[e.name] = xxh64(self.raw(e.name)) == e.checksum
        return result

    def with_main(self, payload: bytes) -> "Archive":
        """Return a new archive with the main chunk replaced (uncompressed bytes), recompressed and re-checksummed."""
        main = self.entry("main")
        if main.offset != HEADER_SIZE:
            raise ValueError("main chunk is not directly after the header, layout unsupported")
        if main.compression == 2:
            comp = brotli.compress(payload, quality=11, lgwin=22)
        elif main.compression == 0:
            comp = payload
        else:
            raise ValueError(f"writing compression {main.compression} not supported")

        old_end = main.offset + main.size
        delta = len(comp) - main.size
        out = bytearray(self.data[:HEADER_SIZE] + comp + self.data[old_end:])
        for e in self.entries():
            if e.name != "main" and e.offset >= old_end:
                struct.pack_into("<Q", out, ENTRY_OFFSETS[e.name], e.offset + delta)
        struct.pack_into("<Qqq", out, ENTRY_OFFSETS["main"] + 8, xxh64(comp), len(comp), len(payload))
        struct.pack_into("<Q", out, 8, self.header_checksum(bytes(out)))
        new = Archive(bytes(out))
        if not all(new.verify().values()):
            raise AssertionError(f"rewritten archive fails verification: {new.verify()}")
        return new

    def save(self, path):
        with open(path, "wb") as f:
            f.write(self.data)
