"""Instruction Set Architecture with MMIO at 0xFFFF0000-0xFFFF0007."""

from __future__ import annotations

from enum import IntEnum
from typing import NamedTuple

MEM_SIZE: int = 4294967296  # 4 GiB
STACK_TOP: int = 0xFFFFFFFF

# Адреса портов ввода-вывода в диапазоне FFFF_0000 - FFFF_0007
STDIN_DATA: int = 0xFFFF0000
STDOUT_DATA: int = 0xFFFF0004
DEFAULT_BASE: int = 0x0000


class Opcode(IntEnum):
    NOP = 0x00

    ADD = 0x01
    SUB = 0x02
    MULLW = 0x03
    DIVW = 0x04
    MODW = 0x05
    AND = 0x06
    OR = 0x07
    XOR = 0x08
    SLW = 0x09
    SRW = 0x0A
    SRAW = 0x0B
    CMPW = 0x0C
    CMPLW = 0x0D
    ADDIS = 0x0E

    ADDI = 0x10
    SUBI = 0x11
    ANDI = 0x12
    ORI = 0x13
    CMPWI = 0x14
    SLWI = 0x15
    SRWI = 0x16
    SRAWI = 0x17

    LWZ = 0x18
    LBZ = 0x19
    STW = 0x20
    STB = 0x21

    BEQ = 0x28
    BNE = 0x29
    BLT = 0x2A
    BGE = 0x2B
    BLE = 0x2C
    BGT = 0x2D

    B = 0x30
    BL = 0x31
    BLR = 0x32
    MFLR = 0x33

    VADDUWM = 0x34
    VSUBUWM = 0x35
    VMULUWM = 0x36
    VDIVUWM = 0x37
    VCMPEQUW = 0x38
    LVX = 0x39
    STVX = 0x3A
    MTLR = 0x3B

    TRAP = 0x3F


PPC_REGISTERS: dict[str, int] = {f"r{i}": i for i in range(32)}
PPC_REGISTERS.update({"sp": 1, "rtoc": 2})

ALTIVEC_REGISTERS: dict[str, int] = {f"v{i}": i for i in range(32)}


class DecodedInstruction(NamedTuple):
    opcode: Opcode
    rd: int
    rs1: int
    rs2: int
    imm: int
    cond: int
    vd: int
    vs1: int
    vs2: int


def decode_instruction(word: int) -> DecodedInstruction:
    op_val = (word >> 26) & 0x3F
    opcode = Opcode(op_val) if op_val in Opcode._value2member_map_ else Opcode.NOP

    rd = (word >> 22) & 0x0F
    rs1 = (word >> 18) & 0x0F
    rs2 = (word >> 14) & 0x0F

    raw_imm16 = (word >> 2) & 0xFFFF
    imm16 = raw_imm16 - 0x10000 if raw_imm16 & 0x8000 else raw_imm16
    target20 = (word >> 2) & 0xFFFFF
    cond = (word >> 22) & 0x0F

    vd = (word >> 23) & 0x07
    vs1 = (word >> 20) & 0x07
    vs2 = (word >> 17) & 0x07

    final_imm = target20 if opcode in (Opcode.B, Opcode.BL) else imm16
    return DecodedInstruction(opcode, rd, rs1, rs2, final_imm, cond, vd, vs1, vs2)
