from __future__ import annotations


class ScalarAddressDecoder:
    def __init__(self, size: int = 32) -> None:
        self.size = size

    @staticmethod
    def decode_rs1(rs1_sel: int) -> int:
        return rs1_sel & 0x1F

    @staticmethod
    def decode_rs2(rs2_sel: int) -> int:
        return rs2_sel & 0x1F

    def decode_write_enables(self, sr_addr: int, srf_we: bool) -> list[bool]:
        addr = sr_addr & 0x1F
        return [srf_we and i != 0 and i == addr for i in range(self.size)]


class ScalarRegisterFile:
    SRF_WE = "SRF_WE"
    SR_ADDR = "SR_ADDR"
    SRF_WB = "SRF_WB"
    RS1_SEL = "RS1_SEL"
    RS2_SEL = "RS2_SEL"

    def __init__(self, size: int = 32) -> None:
        self._regs: list[int] = [0] * size
        self.address_decoder = ScalarAddressDecoder(size)

    def read(self, reg_idx: int) -> int:
        idx = reg_idx & 0x1F
        if idx == 0:
            return 0
        return self._regs[idx]

    def read_port_1(self, rs1_sel: int) -> int:
        return self.read(self.address_decoder.decode_rs1(rs1_sel))

    def read_port_2(self, rs2_sel: int) -> int:
        return self.read(self.address_decoder.decode_rs2(rs2_sel))

    def write(self, reg_idx: int, val: int) -> None:
        self.write_back(reg_idx, val, True)

    def write_back(self, sr_addr: int, srf_wb: int, srf_we: bool) -> None:
        enables = self.address_decoder.decode_write_enables(sr_addr, srf_we)
        masked = srf_wb & 0xFFFFFFFF
        for idx, en in enumerate(enables):
            if en:
                self._regs[idx] = masked

    def get_all(self) -> list[int]:
        return list(self._regs)
