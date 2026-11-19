from __future__ import annotations

from src.microcode import AluOp


class ScalarALU:
    SALU_OP = "SALU_OP"
    SALU_OUT = "SALU_OUT"

    def compute(self, op: AluOp, a: int, b: int) -> tuple[int, int | None, int | None]:
        res = 0
        flag_z: int | None = None
        flag_n: int | None = None

        if op == AluOp.PASS_A:
            res = a
        elif op == AluOp.PASS_B:
            res = b
        elif op == AluOp.ADD:
            res = (a + b) & 0xFFFFFFFF
        elif op == AluOp.SUB:
            res = (a - b) & 0xFFFFFFFF
        elif op == AluOp.MUL:
            res = (a * b) & 0xFFFFFFFF
        elif op == AluOp.DIV:
            res = (a // b) & 0xFFFFFFFF if b != 0 else 0
        elif op == AluOp.MOD:
            res = (a % b) & 0xFFFFFFFF if b != 0 else 0
        elif op == AluOp.AND:
            res = (a & b) & 0xFFFFFFFF
        elif op == AluOp.OR:
            res = (a | b) & 0xFFFFFFFF
        elif op == AluOp.XOR:
            res = (a ^ b) & 0xFFFFFFFF
        elif op == AluOp.LSL:
            res = (a << (b & 0x1F)) & 0xFFFFFFFF
        elif op == AluOp.LSR:
            res = (a >> (b & 0x1F)) & 0xFFFFFFFF
        elif op == AluOp.ASR:
            sign = a & 0x80000000
            val = a
            for _ in range(b & 0x1F):
                val = (val >> 1) | sign
            res = val & 0xFFFFFFFF
        elif op == AluOp.ADDIS:
            res = (a + ((b & 0xFFFF) << 16)) & 0xFFFFFFFF
        elif op == AluOp.CMP:
            diff = (a - b) & 0xFFFFFFFF
            flag_z = 1 if diff == 0 else 0
            flag_n = 1 if (diff & 0x80000000) != 0 else 0
        elif op == AluOp.CMPL:
            u_a, u_b = a & 0xFFFFFFFF, b & 0xFFFFFFFF
            flag_z = 1 if u_a == u_b else 0
            flag_n = 1 if u_a < u_b else 0

        return res, flag_z, flag_n

    def execute(self, rs1: int, rs2: int, salu_op: AluOp) -> tuple[int, int | None, int | None]:
        return self.compute(salu_op, rs1, rs2)
