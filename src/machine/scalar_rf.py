from __future__ import annotations


class ScalarRegisterFile:
    SRF_WE = "SRF_WE"
    REG_ADDR = "REG_ADDR"
    SRF_WB = "SRF_WB"
    RS1_SEL = "RS1_SEL"
    RS2_SEL = "RS2_SEL"

    def __init__(self, size: int = 32) -> None:
        self._regs: list[int] = [0] * size

    def read(self, reg_idx: int) -> int:
        if reg_idx == 0:
            return 0
        return self._regs[reg_idx & 0x1F]

    def read_port_1(self, rs1_sel: int) -> int:
        return self.read(rs1_sel)

    def read_port_2(self, rs2_sel: int) -> int:
        return self.read(rs2_sel)

    def write(self, reg_idx: int, val: int) -> None:
        if reg_idx != 0:
            self._regs[reg_idx & 0x1F] = val & 0xFFFFFFFF

    def write_back(self, reg_addr: int, srf_wb: int, srf_we: bool) -> None:
        if srf_we:
            self.write(reg_addr, srf_wb)

    def get_all(self) -> list[int]:
        return list(self._regs)
