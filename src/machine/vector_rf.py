from __future__ import annotations


class VectorAddressDecoder:
    def __init__(self, num_regs: int = 32) -> None:
        self.num_regs = num_regs

    @staticmethod
    def decode_vrs1(vrs1_sel: int) -> int:
        return vrs1_sel & 0x1F

    @staticmethod
    def decode_vrs2(vrs2_sel: int) -> int:
        return vrs2_sel & 0x1F

    def decode_write_enables(self, vr_addr: int, vrf_we: bool) -> list[bool]:
        addr = vr_addr & 0x1F
        return [vrf_we and i == addr for i in range(self.num_regs)]


class VectorLaneBank:
    def __init__(self, num_regs: int = 32) -> None:
        self._regs: list[int] = [0] * num_regs

    def read_mux_1(self, idx: int) -> int:
        return self._regs[idx]

    def read_mux_2(self, idx: int) -> int:
        return self._regs[idx]

    def write(self, idx: int, val: int) -> None:
        self._regs[idx] = val & 0xFFFFFFFF


class VectorRegisterFile:
    VRF_WE = "VRF_WE"
    VR_ADDR = "VR_ADDR"
    VRF_WB = "VRF_WB"
    VRS1_SEL = "VRS1_SEL"
    VRS2_SEL = "VRS2_SEL"

    def __init__(self, num_regs: int = 32, num_lanes: int = 4) -> None:
        self.num_lanes = num_lanes
        self.address_decoder = VectorAddressDecoder(num_regs)
        self._lanes: list[VectorLaneBank] = [VectorLaneBank(num_regs) for _ in range(num_lanes)]

    def read_vector(self, vreg_idx: int) -> list[int]:
        idx = self.address_decoder.decode_vrs1(vreg_idx)
        return [lane.read_mux_1(idx) for lane in self._lanes]

    def read_port_1(self, vrs1_sel: int) -> list[int]:
        idx = self.address_decoder.decode_vrs1(vrs1_sel)
        return [lane.read_mux_1(idx) for lane in self._lanes]

    def read_port_2(self, vrs2_sel: int) -> list[int]:
        idx = self.address_decoder.decode_vrs2(vrs2_sel)
        return [lane.read_mux_2(idx) for lane in self._lanes]

    def write_vector(self, vreg_idx: int, vector: list[int]) -> None:
        self.write_back(vreg_idx, vector, True)

    def write_back(self, vr_addr: int, vrf_wb: list[int], vrf_we: bool) -> None:
        enables = self.address_decoder.decode_write_enables(vr_addr, vrf_we)
        for idx, en in enumerate(enables):
            if en:
                for lane_idx, lane in enumerate(self._lanes):
                    lane.write(idx, vrf_wb[lane_idx])

    def read_lane(self, vreg_idx: int, lane: int) -> int:
        return self._lanes[lane & 0x03].read_mux_1(vreg_idx & 0x1F)

    def write_lane(self, vreg_idx: int, lane: int, val: int) -> None:
        self._lanes[lane & 0x03].write(vreg_idx & 0x1F, val)

    def get_all(self) -> list[list[int]]:
        return [[lane.read_mux_1(idx) for lane in self._lanes] for idx in range(self.address_decoder.num_regs)]
