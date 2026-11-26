from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import TypedDict

import pytest
import yaml

from src.isa import DEFAULT_BASE
from src.linker import Linker
from src.machine.machine import run_simulation
from src.translator.translator import Assembler

GOLDEN_DIR = Path("golden")

_TICK_RE = re.compile(r"TICK:\s+\d+\s+MPC:\s+([0-9A-Fa-f]+)\s+PC:\s+([0-9A-Fa-f]+)")
_TICK_STATE_RE = re.compile(r"TICK:\s+\d+\s+MPC:\s+[0-9A-Fa-f]+\s+(PC:\s+[0-9A-Fa-f]+.*)$")


class GoldenResult(TypedDict):
    out_code: bytes
    out_code_hex: str
    out_stdout: str
    out_log: str


def str_presenter(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


GoldenDumper = yaml.SafeDumper
GoldenDumper.add_representer(str, str_presenter)


def clean_multiline(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    return normalized + "\n" if normalized else ""


def deduplicate_unchanged_ticks(lines: list[str]) -> list[str]:
    result: list[str] = []
    prev_state: str | None = None

    for line in lines:
        match = _TICK_STATE_RE.search(line)
        if not match:
            result.append(line)
            continue

        state = match.group(1)
        if state == prev_state:
            continue

        prev_state = state
        result.append(line)

    return result


def _collapse_chunks(chunks: list[tuple[str, list[str]]], max_loop_len: int = 300) -> list[str]:
    pcs = [pc for pc, _ in chunks]
    out: list[str] = []
    i = 0
    n = len(chunks)

    while i < n:
        if not pcs[i]:
            out.extend(chunks[i][1])
            i += 1
            continue

        matched_len = 0
        max_l = min(max_loop_len, (n - i) // 2)
        for length in range(1, max_l + 1):
            window = pcs[i : i + length]
            if all(window) and window == pcs[i + length : i + 2 * length]:
                matched_len = length
                break

        if matched_len > 0:
            pattern = pcs[i : i + matched_len]
            reps = 2
            while (
                i + (reps + 1) * matched_len <= n
                and pcs[i + reps * matched_len : i + (reps + 1) * matched_len] == pattern
            ):
                reps += 1

            out.extend(_collapse_chunks(chunks[i : i + matched_len], max_loop_len))
            omitted_lines = sum(len(lines) for _, lines in chunks[i + matched_len : i + reps * matched_len])
            out.append(
                f"... [loop of {matched_len} instructions repeated {reps - 1} more times "
                f"({omitted_lines} log lines omitted)] ..."
            )
            i += reps * matched_len
        else:
            out.extend(chunks[i][1])
            i += 1

    return out


def truncate_log_lines(lines: list[str], head_lines: int = 80, tail_lines: int = 80) -> list[str]:
    if len(lines) <= head_lines + tail_lines:
        return lines
    omitted = len(lines) - head_lines - tail_lines
    return lines[:head_lines] + [f"... ({omitted} lines truncated) ..."] + lines[-tail_lines:]


def collapse_loops(log_text: str) -> str:
    raw_lines = clean_multiline(log_text).splitlines()
    if not raw_lines:
        return ""

    lines = deduplicate_unchanged_ticks(raw_lines)

    chunks: list[tuple[str, list[str]]] = []
    current_pc = ""
    current_lines: list[str] = []

    for line in lines:
        match = _TICK_RE.search(line)
        if match:
            mpc_hex, pc_hex = match.groups()
            if int(mpc_hex, 16) == 0:
                if current_lines:
                    chunks.append((current_pc, current_lines))
                current_pc = pc_hex
                current_lines = [line]
                continue
        elif "HALT:" in line:
            if current_lines:
                chunks.append((current_pc, current_lines))
            chunks.append(("", [line]))
            current_pc = ""
            current_lines = []
            continue

        current_lines.append(line)

    if current_lines:
        chunks.append((current_pc, current_lines))

    collapsed = _collapse_chunks(chunks, max_loop_len=300)
    capped = truncate_log_lines(collapsed)
    return "\n".join(capped) + "\n"


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


def run_pipeline(golden_data: dict[str, object]) -> GoldenResult:
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

        current_addr = base_addr
        end_addr = base_addr
        for mod in linker.modules:
            if mod.base_org is not None:
                current_addr = mod.base_org
            current_addr += len(mod.code_bytes)
            current_addr = (current_addr + 3) & ~3
            end_addr = max(end_addr, current_addr)
        executable_bin = bytes(full_image[:end_addr])

        stdin_input = str(golden_data.get("in_stdin", "")).replace("\r\n", "\n")
        stdout_text, instr_cnt, ticks_cnt = run_simulation(executable_bin, start_pc, stdin_input)

        stdout_body = stdout_text if (not stdout_text or stdout_text.endswith("\n")) else stdout_text + "\n"
        formatted_stdout = (
            f"source LoC: {total_loc} code instr: {len(listing)}\n{stdout_body}instr: {instr_cnt} ticks: {ticks_cnt}\n"
        )

        return {
            "out_code": executable_bin,
            "out_code_hex": clean_multiline("\n".join(listing)),
            "out_stdout": clean_multiline(formatted_stdout),
            "out_log": collapse_loops(log_stream.getvalue()),
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
    assert results["out_code_hex"].strip() == str(golden_data.get("out_code_hex", "")).strip(), (
        f"Hex listing mismatch in {golden_path.name}"
    )
    assert results["out_stdout"].strip() == str(golden_data.get("out_stdout", "")).strip(), (
        f"Stdout mismatch in {golden_path.name}"
    )
    assert results["out_log"].strip() == str(golden_data.get("out_log", "")).strip(), (
        f"Log mismatch in {golden_path.name}"
    )
