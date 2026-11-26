from __future__ import annotations

from enum import IntEnum
from typing import NamedTuple

MEM_SIZE: int = 4294967296  # 4 GiB
STACK_TOP: int = 0xFFFFFFFF

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
PPC_REGISTERS.update({"sp": 1})

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


_JUMP_BRANCH_OPCODES = (
    Opcode.BEQ,
    Opcode.BNE,
    Opcode.BLT,
    Opcode.BGE,
    Opcode.BLE,
    Opcode.BGT,
    Opcode.B,
    Opcode.BL,
)


def decode_instruction(word: int) -> DecodedInstruction:
    op_val = (word >> 26) & 0x3F
    opcode = Opcode(op_val) if op_val in Opcode._value2member_map_ else Opcode.NOP

    rd = (word >> 21) & 0x1F
    rs1 = (word >> 16) & 0x1F
    rs2 = (word >> 11) & 0x1F

    raw_imm16 = word & 0xFFFF
    imm16 = raw_imm16 - 0x10000 if raw_imm16 & 0x8000 else raw_imm16

    raw_off26 = word & 0x3FFFFFF
    off26 = raw_off26 - 0x4000000 if raw_off26 & 0x2000000 else raw_off26

    vd = (word >> 21) & 0x1F
    vs1 = (word >> 16) & 0x1F
    vs2 = (word >> 11) & 0x1F

    final_imm = (off26 << 2) if opcode in _JUMP_BRANCH_OPCODES else imm16
    return DecodedInstruction(opcode, rd, rs1, rs2, final_imm, 0, vd, vs1, vs2)
