from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.machine.control_unit import ControlUnit
from src.machine.datapath import DataPath
from src.machine.memory import Memory
from src.machine.scalar_alu import ScalarALU
from src.machine.scalar_rf import ScalarRegisterFile
from src.machine.vector_alu import VectorALU
from src.machine.vector_rf import VectorRegisterFile

__all__ = [
    "ControlUnit",
    "DataPath",
    "Memory",
    "ScalarALU",
    "ScalarRegisterFile",
    "VectorALU",
    "VectorRegisterFile",
    "main",
    "run_simulation",
]


def run_simulation(
    code_image: bytes | bytearray, start_pc: int = 0x0000, stdin_text: str = "", limit: int = 100000
) -> tuple[str, int, int]:
    dp = DataPath()
    dp.mem.raw_mem[0 : len(code_image)] = code_image
    dp.pc = start_pc
    if stdin_text:
        dp.mem.io_input_buffer = [ord(c) for c in stdin_text]

    cu = ControlUnit(dp)
    while not cu.halted and cu.tick_count < limit:
        cu.step()

    output = "".join(chr(b) for b in dp.mem.io_output_buffer)
    return output, cu.instruction_count, cu.tick_count


def setup_logger(log_dest: str | None, debug: bool) -> logging.Handler | None:
    if not log_dest and not debug:
        logging.disable(logging.CRITICAL)
        return None

    logger = logging.getLogger("machine")
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    formatter = logging.Formatter("%(levelname)-7s %(name)s:%(funcName)-10s %(message)s")

    handler: logging.Handler
    if log_dest == "-" or (debug and not log_dest):
        handler = logging.StreamHandler(sys.stderr)
    else:
        assert log_dest is not None
        p = Path(log_dest)
        p.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(p, mode="w", encoding="utf-8")

    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return handler


def detect_entry(code_image: bytes) -> int:
    for address in range(0, len(code_image) - 3, 4):
        if code_image[address : address + 4] != b"\x00\x00\x00\x00":
            return address
    raise ValueError("Binary image does not contain an executable instruction")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="PowerPC/AltiVec RISC Microcoded Processor Simulator.")
    parser.add_argument("binary", help="Path to executable binary file (.bin)")
    parser.add_argument("--input", "-i", dest="input_file", help="Path to text file with input tokens (STDIN)")
    parser.add_argument(
        "--log",
        "-l",
        dest="log_dest",
        nargs="?",
        const="-",
        default=None,
        help="Log file path. If specified without argument, logs to console (stderr)",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable detailed tick-by-tick step trace of the processor",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100000,
        help="Maximum simulation tick limit (default: 100000)",
    )
    args = parser.parse_args(argv)

    bin_path = Path(args.binary)
    if not bin_path.is_file():
        print(f"Error: binary file '{bin_path}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(bin_path, "rb") as f_bin:
        bin_data = f_bin.read()

    stdin_text = ""
    if args.input_file:
        inp_path = Path(args.input_file)
        if not inp_path.is_file():
            print(f"Error: input file '{inp_path}' not found.", file=sys.stderr)
            sys.exit(1)
        with open(inp_path, "r", encoding="utf-8") as f_in:
            stdin_text = f_in.read()

    log_dest = args.log_dest
    if log_dest and log_dest != "-" and not Path(log_dest).is_absolute():
        log_dest = str(bin_path.parent / log_dest)

    handler = setup_logger(log_dest, args.debug)

    try:
        output_str, instr_cnt, ticks_cnt = run_simulation(
            code_image=bytearray(bin_data),
            start_pc=detect_entry(bin_data),
            stdin_text=stdin_text,
            limit=args.limit,
        )
    finally:
        if handler:
            logging.getLogger("machine").removeHandler(handler)

    print(output_str, end="" if output_str.endswith("\n") else "\n")
    print(f"Instructions executed: {instr_cnt}")
    print(f"Simulation ticks:      {ticks_cnt}")


if __name__ == "__main__":
    main()
