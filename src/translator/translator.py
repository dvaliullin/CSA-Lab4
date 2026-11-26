from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.translator.encoder import InstructionEncoder, _is_int_literal
from src.translator.object_module import ObjectModule, RelocationEntry, SectionItem
from src.translator.preprocessor import Preprocessor

__all__ = [
    "Assembler",
    "InstructionEncoder",
    "ObjectModule",
    "Preprocessor",
    "RelocationEntry",
    "SectionItem",
    "main",
]


class Assembler:
    def __init__(self, filename: str, source_code: str) -> None:
        self.filename = filename
        self.source_code = source_code
        self.preprocessor = Preprocessor()
        self.preprocessed_lines: list[str] = []

    def assemble(self) -> ObjectModule:
        self.preprocessed_lines = self.preprocessor.process(self.source_code)
        module = ObjectModule(name=self.filename)
        current_section = ".text"
        collected_items: list[SectionItem] = []

        for line in self.preprocessed_lines:
            if line.startswith("."):
                parts = line.split()
                directive = parts[0].lower()
                if directive in (".text", ".data", ".section"):
                    current_section = (
                        ".data" if directive == ".data" or (len(parts) > 1 and parts[1] == ".data") else ".text"
                    )
                    continue
                if directive == ".org":
                    module.base_org = int(parts[1], 0)
                    continue
                if directive in (".global", ".globl"):
                    module.globals.append(parts[1])
                    continue
                if directive == ".extern":
                    module.externs.append(parts[1])
                    continue
                if directive in (".word", ".byte", ".pstr", ".string"):
                    raw = line[len(directive) :].strip()
                    collected_items.append(SectionItem(None, directive, parts[1:], current_section, raw))
                    continue

            label = None
            if ":" in line:
                label_part, *rest = line.split(":")
                label = label_part.strip()
                line = ":".join(rest).strip()
                if not line:
                    collected_items.append(SectionItem(label, "", [], current_section, ""))
                    continue

            parts = line.replace(",", " ").split()
            mnemonic = parts[0].lower()
            args = parts[1:]

            if mnemonic == "li":
                mnemonic = "addi"
                args = [args[0], "r0", args[1]]
            elif mnemonic == "lis":
                mnemonic = "addis"
                args = [args[0], "r0", args[1]]
            elif mnemonic == "mr":
                mnemonic = "or"
                args = [args[0], args[1], args[1]]
            elif mnemonic == "nop":
                mnemonic = "ori"
                args = ["r0", "r0", "0"]
            elif len(args) == 3 and _is_int_literal(args[2]):
                shift_map = {"slw": "slwi", "srw": "srwi", "sraw": "srawi"}
                if mnemonic in shift_map:
                    mnemonic = shift_map[mnemonic]

            collected_items.append(SectionItem(label, mnemonic, args, current_section, line))

        text_items = [it for it in collected_items if it.section == ".text"]
        data_items = [it for it in collected_items if it.section == ".data"]
        ordered_items = text_items + data_items

        current_offset = 0
        for idx, it in enumerate(ordered_items):
            next_mnemonic = it.mnemonic
            if not next_mnemonic:
                for next_it in ordered_items[idx + 1 :]:
                    if next_it.mnemonic:
                        next_mnemonic = next_it.mnemonic
                        break
            if next_mnemonic == ".word":
                current_offset = (current_offset + 3) & ~3

            if it.label:
                module.symbols[it.label] = current_offset

            if it.mnemonic in (".word", ".byte", ".pstr", ".string"):
                if it.mnemonic == ".word":
                    cnt = len(" ".join(it.args).replace(",", " ").split())
                    current_offset += 4 * cnt
                elif it.mnemonic == ".byte":
                    cnt = len(" ".join(it.args).replace(",", " ").split())
                    current_offset += cnt
                elif it.mnemonic in (".pstr", ".string"):
                    raw_str = it.raw_content.strip()
                    if raw_str.lower().startswith(it.mnemonic):
                        raw_str = raw_str[len(it.mnemonic) :].strip()
                    raw_str = raw_str.strip('"')
                    try:
                        pstr_content = bytes(raw_str, "utf-8").decode("unicode_escape")
                    except (UnicodeDecodeError, ValueError):
                        pstr_content = raw_str
                    current_offset += 1 + len(pstr_content)
            elif it.mnemonic:
                current_offset += 4

        for it in ordered_items:
            if it.mnemonic == ".word":
                while len(module.code_bytes) % 4 != 0:
                    module.code_bytes.append(0)
                for val_s in " ".join(it.args).replace(",", " ").split():
                    val = int(val_s.strip(), 0)
                    module.code_bytes.extend((val & 0xFFFFFFFF).to_bytes(4, "little", signed=False))
            elif it.mnemonic == ".byte":
                for val_s in " ".join(it.args).replace(",", " ").split():
                    val = int(val_s.strip(), 0)
                    module.code_bytes.extend((val & 0xFF).to_bytes(1, "little", signed=False))
            elif it.mnemonic in (".pstr", ".string"):
                raw_str = it.raw_content.strip()
                if raw_str.lower().startswith(it.mnemonic):
                    raw_str = raw_str[len(it.mnemonic) :].strip()
                raw_str = raw_str.strip('"')
                try:
                    pstr_content = bytes(raw_str, "utf-8").decode("unicode_escape")
                except (UnicodeDecodeError, ValueError):
                    pstr_content = raw_str
                module.code_bytes.append(len(pstr_content) & 0xFF)
                module.code_bytes.extend(pstr_content.encode("ascii"))
            elif it.mnemonic:
                offset = module.symbols.get(it.label, 0) if it.label else len(module.code_bytes)
                word = InstructionEncoder.encode(it.mnemonic, it.args, offset, module)
                module.code_bytes.extend(word.to_bytes(4, "little", signed=False))

        return module


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Translate one assembly source file into a relocatable object file.")
    parser.add_argument("source", help="Source .asm file")
    parser.add_argument("-o", "--output", dest="output_opt", help="Output object file path")
    args = parser.parse_args(argv)

    source_path = Path(args.source)
    if not source_path.is_file():
        print(f"Error: source file '{source_path}' not found.", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output_opt) if args.output_opt else Path("out") / f"{source_path.stem}.o"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with source_path.open("r", encoding="utf-8") as source_file:
        assembler = Assembler(source_path.name, source_file.read())
        module = assembler.assemble()

    module.save(output_path)
    prep_path = output_path.with_suffix(".preprocessed")
    prep_path.write_text("\n".join(assembler.preprocessed_lines) + "\n", encoding="utf-8")

    print("Translation successful:")
    print(f"  Object:      {output_path}")
    print(f"  Preprocessed: {prep_path}")


if __name__ == "__main__":
    main()
