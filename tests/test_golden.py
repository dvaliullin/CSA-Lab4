from __future__ import annotations

import io
import logging
from pathlib import Path

import pytest
import yaml

from src.isa import DEFAULT_BASE
from src.linker import Linker
from src.machine.machine import run_simulation
from src.translator.translator import Assembler

GOLDEN_DIR = Path("golden")


class GoldenDumper(yaml.SafeDumper):
    pass


def str_presenter(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


GoldenDumper.add_representer(str, str_presenter)
yaml.SafeDumper.add_representer(str, str_presenter)


def clean_multiline(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    return normalized + "\n" if normalized else ""


def dump_golden_yaml(data: dict[str, object], path: Path) -> None:
    clean_data: dict[str, object] = {}
    for k, v in data.items():
        if isinstance(v, str) and "\n" in v:
            clean_data[k] = clean_multiline(v)
        else:
            clean_data[k] = v

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(clean_data, f, Dumper=GoldenDumper, sort_keys=False, width=10000, allow_unicode=True)


def count_loc(source: str) -> int:
    return sum(1 for line in source.splitlines() if line.split("#")[0].split(";")[0].strip())


def run_pipeline(golden_data: dict[str, object]) -> dict[str, object]:
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    formatter = logging.Formatter("%(levelname)-7s %(name)s:%(funcName)-10s %(message)s")
    handler.setFormatter(formatter)

    logger = logging.getLogger("machine")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    modules = []
    total_loc = 0

    try:
        if golden_data.get("in_source_lib"):
            lib_src = clean_multiline(str(golden_data["in_source_lib"]))
            total_loc += count_loc(lib_src)
            modules.append(Assembler("lib_io.asm", lib_src).assemble())

        main_src = clean_multiline(str(golden_data["in_source"]))
        total_loc += count_loc(main_src)
        modules.append(Assembler("main.asm", main_src).assemble())

        linker = Linker(modules)
        full_image, symbols, listing = linker.link()

        base_addr = linker.modules[0].base_org if linker.modules[0].base_org is not None else DEFAULT_BASE
        start_pc = symbols.get("_start", base_addr)

        end_addr = base_addr
        for mod in linker.modules:
            end_addr += len(mod.code_bytes)
        end_addr = (end_addr + 3) & ~3
        executable_bin = bytes(full_image[:end_addr])

        stdin_input = str(golden_data.get("in_stdin", "")).replace("\r\n", "\n")
        stdout_text, instr_cnt, ticks_cnt = run_simulation(executable_bin, start_pc, stdin_input)

        stdout_body = stdout_text if (not stdout_text or stdout_text.endswith("\n")) else stdout_text + "\n"
        formatted_stdout = (
            f"source LoC: {total_loc} code instr: {len(listing)}\n"
            f"{stdout_body}"
            f"instr: {instr_cnt} ticks: {ticks_cnt}\n"
        )

        return {
            "out_code": executable_bin,
            "out_code_hex": clean_multiline("\n".join(listing)),
            "out_stdout": clean_multiline(formatted_stdout),
            "out_log": clean_multiline(log_stream.getvalue()),
        }
    finally:
        logger.removeHandler(handler)


@pytest.mark.parametrize("golden_path", sorted(GOLDEN_DIR.glob("*.yml")), ids=lambda p: p.name)
def test_golden(golden_path: Path, request: pytest.FixtureRequest) -> None:
    with open(golden_path, "r", encoding="utf-8") as f:
        golden_data = yaml.safe_load(f)

    assert "in_source" in golden_data, f"Missing 'in_source' in {golden_path.name}"

    results = run_pipeline(golden_data)

    if request.config.getoption("--update-goldens", default=False):
        golden_data.update(results)
        dump_golden_yaml(golden_data, golden_path)
        return

    assert results["out_code"] == golden_data.get("out_code"), f"Machine code mismatch in {golden_path.name}"
    assert results["out_code_hex"].strip() == str(golden_data.get("out_code_hex", "")).strip(), f"Hex listing mismatch in {golden_path.name}"
    assert results["out_stdout"].strip() == str(golden_data.get("out_stdout", "")).strip(), f"Stdout mismatch in {golden_path.name}"
    assert results["out_log"].strip() == str(golden_data.get("out_log", "")).strip(), f"Log mismatch in {golden_path.name}"