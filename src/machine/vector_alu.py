from __future__ import annotations


class VectorALU:
    VALU_OP = "VALU_OP"
    VALU_OUT = "VALU_OUT"

    def compute(self, op: str, v1: list[int], v2: list[int]) -> list[int]:
        res = [0] * 4
        for lane in range(4):
            a = v1[lane]
            b = v2[lane]
            if op == "VADD":
                res[lane] = (a + b) & 0xFFFFFFFF
            elif op == "VSUB":
                res[lane] = (a - b) & 0xFFFFFFFF
            elif op == "VMUL":
                res[lane] = (a * b) & 0xFFFFFFFF
            elif op == "VDIV":
                res[lane] = (a // b) & 0xFFFFFFFF if b != 0 else 0
            elif op == "VCMP":
                res[lane] = 0xFFFFFFFF if a == b else 0
        return res

    def execute(self, vrs1: list[int], vrs2: list[int], valu_op: str) -> list[int]:
        return self.compute(valu_op, vrs1, vrs2)
