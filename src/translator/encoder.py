from __future__ import annotations

import re

from src.isa import ALTIVEC_REGISTERS, PPC_REGISTERS, Opcode
from src.translator.object_module import ObjectModule, RelocationEntry


def _is_int_literal(text: str) -> bool:
    try:
        int(text, 0)
        return True
    except ValueError:
        return False


class InstructionEncoder:
    @staticmethod
    def encode(mnemonic: str, args: list[str], offset: int, module: ObjectModule) -> int:
        op = Opcode[mnemonic.rstrip(".").upper()]

        def reg(name: str) -> int:
            return PPC_REGISTERS[name.lower()] & 0x1F

        def vreg(name: str) -> int:
            return ALTIVEC_REGISTERS[name.lower()] & 0x1F

        # R-type скалярные операции АЛУ
        if op in (
            Opcode.ADD,
            Opcode.SUB,
            Opcode.MULLW,
            Opcode.DIVW,
            Opcode.MODW,
            Opcode.AND,
            Opcode.OR,
            Opcode.XOR,
            Opcode.SLW,
            Opcode.SRW,
            Opcode.SRAW,
        ):
            return ((op.value & 0x3F) << 26) | (reg(args[0]) << 21) | (reg(args[1]) << 16) | (reg(args[2]) << 11)

        if op in (Opcode.CMPW, Opcode.CMPLW):
            return ((op.value & 0x3F) << 26) | (reg(args[0]) << 16) | (reg(args[1]) << 11)

        if op in (Opcode.NOP, Opcode.TRAP, Opcode.BLR):
            return (op.value & 0x3F) << 26

        if op == Opcode.MFLR:
            return ((op.value & 0x3F) << 26) | (reg(args[0]) << 21)

        if op == Opcode.MTLR:
            return ((op.value & 0x3F) << 26) | (reg(args[0]) << 16)

        # I-type операции с константой (Immediate)
        if op in (
            Opcode.ADDI,
            Opcode.SUBI,
            Opcode.ANDI,
            Opcode.ORI,
            Opcode.SLWI,
            Opcode.SRWI,
            Opcode.SRAWI,
            Opcode.ADDIS,
        ):
            imm_str = args[2]
            imm = 0
            if _is_int_literal(imm_str):
                imm = int(imm_str, 0)
            else:
                module.relocations.append(RelocationEntry(offset, imm_str, "ABS16"))
            return ((op.value & 0x3F) << 26) | (reg(args[0]) << 21) | (reg(args[1]) << 16) | (imm & 0xFFFF)

        if op == Opcode.CMPWI:
            imm_str = args[1]
            if _is_int_literal(imm_str):
                imm = int(imm_str, 0)
            else:
                imm = 0
                module.relocations.append(RelocationEntry(offset, imm_str, "ABS16"))
            return ((op.value & 0x3F) << 26) | (reg(args[0]) << 16) | (imm & 0xFFFF)

        # I-type Load / Store (d(rA))
        if op in (Opcode.LWZ, Opcode.LBZ, Opcode.STW, Opcode.STB):
            target_reg = reg(args[0])
            m = re.match(r"([-\w\d]*)\((r\d+|sp)\)", args[1])
            assert m, f"Invalid PowerPC memory operand: {args[1]}"
            d_str, ra_str = m.groups()
            d_imm = 0
            if d_str:
                if _is_int_literal(d_str):
                    d_imm = int(d_str, 0)
                else:
                    module.relocations.append(RelocationEntry(offset, d_str, "ABS16"))
            return ((op.value & 0x3F) << 26) | (target_reg << 21) | (reg(ra_str) << 16) | (d_imm & 0xFFFF)

        # J/B-type условные и безусловные переходы (PC-relative 26-bit word offset)
        if op in (Opcode.BEQ, Opcode.BNE, Opcode.BLT, Opcode.BGE, Opcode.BLE, Opcode.BGT, Opcode.B, Opcode.BL):
            if len(args) != 1:
                raise ValueError(f"{mnemonic} expects a single label operand")
            module.relocations.append(RelocationEntry(offset, args[0], "REL26"))
            return (op.value & 0x3F) << 26

        # V-type векторные SIMD-операции AltiVec
        if op in (Opcode.VADDUWM, Opcode.VSUBUWM, Opcode.VMULUWM, Opcode.VDIVUWM, Opcode.VCMPEQUW):
            return ((op.value & 0x3F) << 26) | (vreg(args[0]) << 21) | (vreg(args[1]) << 16) | (vreg(args[2]) << 11)

        # VL-type векторный доступ к памяти (LVX / STVX)
        if op in (Opcode.LVX, Opcode.STVX):
            target_vreg = vreg(args[0])
            m = re.match(r"([-\w\d]*)\((r\d+|sp)\)", args[1])
            assert m, f"Invalid AltiVec memory operand: {args[1]}"
            d_str, ra_str = m.groups()
            d_imm = 0
            if d_str:
                if _is_int_literal(d_str):
                    d_imm = int(d_str, 0)
                else:
                    module.relocations.append(RelocationEntry(offset, d_str, "ABS16"))
            return ((op.value & 0x3F) << 26) | (target_vreg << 21) | (reg(ra_str) << 16) | (d_imm & 0xFFFF)

        raise ValueError(f"Unknown PowerPC instruction: {mnemonic}")
