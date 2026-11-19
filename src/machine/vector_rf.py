from __future__ import annotations


class VectorRegisterFile:
    VRF_WE = "VRF_WE"
    REG_ADDR = "REG_ADDR"
    VRF_WB = "VRF_WB"
    RS1_SEL = "RS1_SEL"
    RS2_SEL = "RS2_SEL"

    def __init__(self, num_regs: int = 32, num_lanes: int = 4) -> None:
        self._vregs: list[list[int]] = [[0] * num_lanes for _ in range(num_regs)]

    def read_vector(self, vreg_idx: int) -> list[int]:
        return list(self._vregs[vreg_idx & 0x1F])

    def read_port_1(self, rs1_sel: int) -> list[int]:
        return self.read_vector(rs1_sel)

    def read_port_2(self, rs2_sel: int) -> list[int]:
        return self.read_vector(rs2_sel)

    def write_vector(self, vreg_idx: int, vector: list[int]) -> None:
        self._vregs[vreg_idx & 0x1F] = [val & 0xFFFFFFFF for val in vector[:4]]

    def write_back(self, reg_addr: int, vrf_wb: list[int], vrf_we: bool) -> None:
        if vrf_we:
            self.write_vector(reg_addr, vrf_wb)

    def read_lane(self, vreg_idx: int, lane: int) -> int:
        return self._vregs[vreg_idx & 0x1F][lane & 0x03]

    def write_lane(self, vreg_idx: int, lane: int, val: int) -> None:
        self._vregs[vreg_idx & 0x1F][lane & 0x03] = val & 0xFFFFFFFF

    def get_all(self) -> list[list[int]]:
        return [list(vector) for vector in self._vregs]
