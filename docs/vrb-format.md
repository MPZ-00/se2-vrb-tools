# VRB format notes
Space Engineers 2 (build 4.0.0.3169) stores saves as "VRage Binary Archives", `.vrb`. These notes come from inspecting real saves and the game's `VRage.Library.dll` (`Keen.VRage.Library.Serialization.Binary.Archive`).

## Save folder
```
SaveGames/<name>/
  .container-info        JSON metadata for the save list (name, PCU, UsedDebugMenu, ...)
  savegame.vrb           world entities
  sessioncomponents.vrb  session state, including the world info record
  snapshots.vrb, assetjournal.vrb, modlist.vrb
  Blobs/<guid>           more VR3B archives (grids, voxel data, ...)
  .autosaves/, .backups/ game-managed copies
```

## Header (192 bytes, little endian)
| Offset | Type | Field |
|---|---|---|
| 0 | u32 | Magic `VR3B` |
| 4 | u32 | Version (1) |
| 8 | u64 | Header checksum |
| 16 | Entry | Bundle table |
| 52 | Entry | Type table |
| 88 | Entry | Chunk table (offset 0 when absent) |
| 124 | i32 | Bundle count |
| 128 | i32 | Chunk count |
| 132 | Entry+ | Main chunk (an Entry followed by chunk-specific fields such as root type) |

Entry, 36 bytes, packed:
| Offset | Type | Field |
|---|---|---|
| 0 | i64 | Offset in file |
| 8 | u64 | Checksum of the on-disk (compressed) bytes |
| 16 | i64 | Size on disk |
| 24 | i64 | Uncompressed size |
| 32 | u8 | Compression: 0 none, 1 zlib, 2 brotli |
| 33 | u8[3] | Padding |

In practice the file is laid out as header, main chunk at 0xC0, bundle table, type table.

## Checksums
All checksums are XxHash64 with seed `0x42335256` (the magic `VR3B` read as a little-endian u32).
- Entry checksum: hash of the entry's bytes as stored on disk, after compression.
- Header checksum: hash of the 192 header bytes with the checksum field zeroed.

The game rejects a mismatch on load with `invalid binary archive: ChecksumMismatch`.

## Tables
- Bundle table: UTF-16 assembly names with versions (`Game2`, `VRage`, `System.Runtime`).
- Type table: fully qualified type names as ASCII (`Game2:Keen.Game2....ObjectBuilder`), field names as length-prefixed UTF-16. The main chunk refers to types and fields by index, so it contains almost no readable names.

## Debug menu flag
The "save was altered with the Debug Menu" mark lives in two places:
1. `sessioncomponents.vrb`, in the world info record: `SaveName` (string), `WorldType` (string), `PersistentID` (Guid, 16 bytes), `UsedDebugMenu` (bool, 1 byte). This is the source of truth.
2. `.container-info`, `$Value.Meta.UsedDebugMenu`. A cached copy for the save list, rewritten from session state on every save.

Behavior observed in game logs:
- Loading a world flagged `true` adds a process-wide `DebugMenu` crash-handler tag right after spawn.
- Once a process has that tag, every save it writes is flagged `true`, including other worlds.
- So clearing the flag only sticks if it's done with the game closed, and the debug menu is not opened afterwards.

`tools/unflag.py` does both edits and recomputes the checksums.
