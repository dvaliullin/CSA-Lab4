from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.isa import DEFAULT_BASE, MEM_SIZE, decode_instruction
from src.machine.memory import SparseMemory
from src.translator.object_module import ObjectModule


class Linker:
    def __init__(self, modules: list[ObjectModule], default_base: int = DEFAULT_BASE):
        self.modules = sorted(
            modules,
            key=lambda m: 0 if m.base_org is not None else (0 if "_start" in m.symbols else 1),
        )
        self.default_base = default_base

    def link(self) -> tuple[SparseMemory, dict[str, int], list[str]]:
        global_symbols: dict[str, int] = {}
        module_bases: list[int] = []

        current_addr = self.default_base
        for mod in self.modules:
            if mod.base_org is not None:
                current_addr = mod.base_org
            module_bases.append(current_addr)
            for gsym in mod.globals:
                if gsym in mod.symbols:
                    global_symbols[gsym] = current_addr + mod.symbols[gsym]
            current_addr += len(mod.code_bytes)
            current_addr = (current_addr + 3) & ~3

        image = SparseMemory(MEM_SIZE)
        listing_lines: list[str] = []

        for idx, mod in enumerate(self.modules):
            base = module_bases[idx]
            image[base : base + len(mod.code_bytes)] = mod.code_bytes

            for reloc in mod.relocations:
                patch_addr = base + reloc.offset
                target_addr = 0
                if reloc.symbol in mod.symbols:
                    target_addr = base + mod.symbols[reloc.symbol]
                elif reloc.symbol in global_symbols:
                    target_addr = global_symbols[reloc.symbol]
                else:
                    raise KeyError(f"Undefined symbol: '{reloc.symbol}' in module {mod.name}")

                word = int.from_bytes(image[patch_addr : patch_addr + 4], "little")
                if reloc.rel_type in ("ABS16", "BRANCH16"):
                    word &= ~(0xFFFF << 2)
                    word |= ((target_addr & 0xFFFF) << 2)
                elif reloc.rel_type == "JUMP20":
                    word &= ~(0xFFFFF << 2)
                    word |= ((target_addr & 0xFFFFF) << 2)

                image[patch_addr : patch_addr + 4] = word.to_bytes(4, "little")

            for offset in range(0, len(mod.code_bytes), 4):
                addr = base + offset
                word = int.from_bytes(image[addr : addr + 4], "little")
                decoded = decode_instruction(word)
                listing_lines.append(f"{addr:04X} - {word:08X} - {decoded.opcode.name}")

        return image, global_symbols, listing_lines


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Link relocatable object files into a machine-code binary.")
    parser.add_argument("objects", nargs="+", help="Input .o object files")
    parser.add_argument("-o", "--output", required=True, help="Output .bin file")
    args = parser.parse_args(argv)

    object_paths = [Path(path) for path in args.objects]
    for object_path in object_paths:
        if not object_path.is_file():
            print(f"Error: object file '{object_path}' not found.", file=sys.stderr)
            sys.exit(1)

    try:
        modules = [ObjectModule.load(path) for path in object_paths]
        linker = Linker(modules)
        image, symbols, listing = linker.link()
    except (KeyError, ValueError, OSError) as exc:
        print(f"Linker Error: {exc}", file=sys.stderr)
        sys.exit(1)

    base_addr = linker.modules[0].base_org if linker.modules[0].base_org is not None else DEFAULT_BASE
    end_addr = base_addr
    for module in linker.modules:
        end_addr += len(module.code_bytes)
    end_addr = (end_addr + 3) & ~3

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(bytes(image[:end_addr]))

    dump_path = output_path.with_suffix(".dump")
    dump_lines = [
        f"Memory Dump for {output_path.name}",
        f"Base address: 0x{base_addr:04X}, End address: 0x{end_addr:04X}, Size: {end_addr} bytes",
        "",
        "Symbol Table:",
    ]
    for symbol, address in sorted(symbols.items(), key=lambda item: item[1]):
        dump_lines.append(f"  {symbol:<20}: 0x{address:04X} ({address})")
    dump_lines.append("\nDisassembly Listing (<address> - <HEXCODE> - <mnemonic>):")
    dump_lines.extend(listing)
    dump_path.write_text("\n".join(dump_lines) + "\n", encoding="utf-8")

    print("Linking successful:")
    print(f"  Binary: {output_path} ({end_addr} bytes)")
    print(f"  Dump:   {dump_path}")


if __name__ == "__main__":
    main()