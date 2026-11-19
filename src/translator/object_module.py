from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RelocationEntry:
    offset: int
    symbol: str
    rel_type: str


@dataclass
class SectionItem:
    label: str | None
    mnemonic: str
    args: list[str]
    section: str
    raw_content: str


@dataclass
class ObjectModule:
    name: str
    code_bytes: bytearray = field(default_factory=bytearray)
    symbols: dict[str, int] = field(default_factory=dict)
    globals: list[str] = field(default_factory=list)
    externs: list[str] = field(default_factory=list)
    relocations: list[RelocationEntry] = field(default_factory=list)
    base_org: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "code_bytes": self.code_bytes.hex(),
            "symbols": self.symbols,
            "globals": self.globals,
            "externs": self.externs,
            "relocations": [
                {"offset": reloc.offset, "symbol": reloc.symbol, "rel_type": reloc.rel_type}
                for reloc in self.relocations
            ],
            "base_org": self.base_org,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ObjectModule:
        return cls(
            name=str(data["name"]),
            code_bytes=bytearray.fromhex(str(data["code_bytes"])),
            symbols={str(key): int(value) for key, value in dict(data["symbols"]).items()},
            globals=[str(value) for value in data["globals"]],
            externs=[str(value) for value in data["externs"]],
            relocations=[
                RelocationEntry(int(reloc["offset"]), str(reloc["symbol"]), str(reloc["rel_type"]))
                for reloc in data["relocations"]
            ],
            base_org=None if data["base_org"] is None else int(data["base_org"]),
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> ObjectModule:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
