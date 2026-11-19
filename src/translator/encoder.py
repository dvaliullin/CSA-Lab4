from __future__ import annotations

import re

from src.isa import ALTIVEC_REGISTERS, PPC_REGISTERS, Opcode
from src.translator.object_module import ObjectModule, RelocationEntry


class InstructionEncoder:
    @staticmethod
    def encode(mnemonic: str, args: list[str], offset: int, module: ObjectModule) -> int:
        op = Opcode[mnemonic.upper()]

        def reg(name: str) -> int:
            return PPC_REGISTERS[name.lower()]

        def vreg(name: str) -> int:
            return ALTIVEC_REGISTERS[name.lower()]

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
            return ((op.value & 0x3F) << 26) | (reg(args[0]) << 22) | (reg(args[1]) << 18) | (reg(args[2]) << 14)

        if op in (Opcode.CMPW, Opcode.CMPLW):
            return ((op.value & 0x3F) << 26) | (reg(args[0]) << 18) | (reg(args[1]) << 14)

        if op in (Opcode.NOP, Opcode.TRAP, Opcode.BLR):
            return (op.value & 0x3F) << 26

        if op == Opcode.MFLR:
            return ((op.value & 0x3F) << 26) | (reg(args[0]) << 22)

        if op == Opcode.MTLR:
            return ((op.value & 0x3F) << 26) | (reg(args[0]) << 18)

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
            if imm_str.lstrip("-").isdigit() or imm_str.startswith("0x"):
                imm = int(imm_str, 0)
            else:
                module.relocations.append(RelocationEntry(offset, imm_str, "ABS16"))
            return ((op.value & 0x3F) << 26) | (reg(args[0]) << 22) | (reg(args[1]) << 18) | ((imm & 0xFFFF) << 2)

        if op == Opcode.CMPWI:
            imm_str = args[1]
            imm = int(imm_str, 0) if (imm_str.lstrip("-").isdigit() or imm_str.startswith("0x")) else 0
            if not (imm_str.lstrip("-").isdigit() or imm_str.startswith("0x")):
                module.relocations.append(RelocationEntry(offset, imm_str, "ABS16"))
            return ((op.value & 0x3F) << 26) | (reg(args[0]) << 18) | ((imm & 0xFFFF) << 2)

        # I-type Load / Store (d(rA))
        if op in (Opcode.LWZ, Opcode.LBZ, Opcode.STW, Opcode.STB):
            target_reg = reg(args[0])
            m = re.match(r"([-\w\d]*)\((r\d+|sp|rtoc)\)", args[1])
            assert m, f"Invalid PowerPC memory operand: {args[1]}"
            d_str, ra_str = m.groups()
            d_imm = 0
            if d_str:
                if d_str.lstrip("-").isdigit() or d_str.startswith("0x"):
                    d_imm = int(d_str, 0)
                else:
                    module.relocations.append(RelocationEntry(offset, d_str, "ABS16"))
            return ((op.value & 0x3F) << 26) | (target_reg << 22) | (reg(ra_str) << 18) | ((d_imm & 0xFFFF) << 2)

        # B-type условные переходы
        if op in (Opcode.BEQ, Opcode.BNE, Opcode.BLT, Opcode.BGE, Opcode.BLE, Opcode.BGT):
            cond_map = {Opcode.BEQ: 0, Opcode.BNE: 1, Opcode.BLT: 2, Opcode.BGE: 3, Opcode.BLE: 4, Opcode.BGT: 5}
            if len(args) != 1:
                raise ValueError(f"{mnemonic} expects a single label operand")
            module.relocations.append(RelocationEntry(offset, args[0], "BRANCH16"))
            return ((op.value & 0x3F) << 26) | (cond_map[op] << 22)

        # J-type безусловные прыжки и вызовы
        if op in (Opcode.B, Opcode.BL):
            target = args[0]
            module.relocations.append(RelocationEntry(offset, target, "JUMP20"))
            rd = 15 if op == Opcode.BL else 0
            return ((op.value & 0x3F) << 26) | (rd << 22)

        # V-type векторные SIMD-операции AltiVec
        if op in (Opcode.VADDUWM, Opcode.VSUBUWM, Opcode.VMULUWM, Opcode.VDIVUWM, Opcode.VCMPEQUW):
            return ((op.value & 0x3F) << 26) | (vreg(args[0]) << 23) | (vreg(args[1]) << 20) | (vreg(args[2]) << 17)

        # VL-type векторный доступ к памяти (LVX / STVX)
        if op in (Opcode.LVX, Opcode.STVX):
            target_vreg = vreg(args[0])
            m = re.match(r"([-\w\d]*)\((r\d+|sp|rtoc)\)", args[1])
            assert m, f"Invalid AltiVec memory operand: {args[1]}"
            d_str, ra_str = m.groups()
            d_imm = 0
            if d_str:
                if d_str.lstrip("-").isdigit() or d_str.startswith("0x"):
                    d_imm = int(d_str, 0)
                else:
                    module.relocations.append(RelocationEntry(offset, d_str, "ABS16"))
            return ((op.value & 0x3F) << 26) | (target_vreg << 23) | (reg(ra_str) << 18) | ((d_imm & 0xFFFF) << 2)

        raise ValueError(f"Unknown PowerPC instruction: {mnemonic}")
