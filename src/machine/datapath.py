from __future__ import annotations

from typing import Generic, TypeVar

from src.isa import DEFAULT_BASE, STACK_TOP
from src.machine.memory import Memory, SparseMemory
from src.machine.scalar_alu import ScalarALU
from src.machine.scalar_rf import ScalarRegisterFile
from src.machine.vector_alu import VectorALU
from src.machine.vector_rf import VectorRegisterFile
from src.microcode import ArSel, LrSel, PcSel, SaluASel, SaluBSel, SrfSel, VrfSel

T = TypeVar("T")


class Mux(Generic[T]):
    def __init__(self, name: str) -> None:
        self.name = name

    def select(self, sel: object, mapping: dict[object, T], default: T) -> T:
        return mapping.get(sel, default)


class PCIncrementer:
    PC_INC = "PC_INC"

    @staticmethod
    def add(pc_out: int) -> int:
        return (pc_out + 4) & 0xFFFFFFFF


class ARIncrementer:
    AR_INC = "AR_INC"

    @staticmethod
    def add(ar: int) -> int:
        return (ar + 4) & 0xFFFFFFFF


class Splitter:
    """Блок Splitter (stvx) на схеме Vector DataPath."""

    @staticmethod
    def split(vrs1: list[int], word_sel: int) -> int:
        return vrs1[word_sel & 0x03] & 0xFFFFFFFF


class Packer:
    """Блок Packer (lvx) на схеме Vector DataPath."""

    def __init__(self) -> None:
        self._buffer: list[int] = [0, 0, 0, 0]

    def reset(self) -> None:
        self._buffer = [0, 0, 0, 0]

    def pack(self, word_sel: int, rdata: int) -> list[int]:
        self._buffer[word_sel & 0x03] = rdata & 0xFFFFFFFF
        return list(self._buffer)


class DataPath:
    def __init__(self) -> None:
        self.srf: ScalarRegisterFile = ScalarRegisterFile()
        self.srf.write(1, STACK_TOP)
        self.vrf: VectorRegisterFile = VectorRegisterFile()
        self.salu: ScalarALU = ScalarALU()
        self.valu: VectorALU = VectorALU()
        self.mem: Memory = Memory()
        self.splitter: Splitter = Splitter()
        self.packer: Packer = Packer()

        self.pc: int = DEFAULT_BASE
        self.ar: int = 0
        self.ir: int = 0
        self.lr: int = 0
        self.vcnt: int = 0
        self.flag_z: int = 0
        self.flag_n: int = 0
        self.pc_inc = PCIncrementer()
        self.ar_inc = ARIncrementer()

        self.mux_srf: Mux[int] = Mux("MUX_SRF")
        self.mux_salu_a: Mux[int] = Mux("MUX_SALU_A")
        self.mux_salu_b: Mux[int] = Mux("MUX_SALU_B")
        self.mux_vrf: Mux[list[int]] = Mux("MUX_VRF")
        self.mux_lr: Mux[int] = Mux("MUX_LR")
        self.mux_pc: Mux[int] = Mux("MUX_PC")
        self.mux_ar: Mux[int] = Mux("MUX_AR")

        self.rdata = 0
        self.wdata = 0
        self.rs1 = 0
        self.rs2 = 0
        self.ir_imm = 0
        self.salu_out = 0
        self.valu_out: list[int] = [0, 0, 0, 0]
        self.packed_data: list[int] = [0, 0, 0, 0]
        self.splitted_data = 0
        self.data_addr = 0
        self.branch_target = 0

    def select_salu_a(self, sel: SaluASel, rs1_val: int) -> int:
        return self.mux_salu_a.select(
            sel,
            {
                SaluASel.NONE: 0,
                SaluASel.RS1: rs1_val,
                SaluASel.PC_OUT: self.pc,
            },
            0,
        )

    def select_salu_b(self, sel: SaluBSel, rs2_val: int) -> int:
        return self.mux_salu_b.select(
            sel,
            {
                SaluBSel.NONE: 0,
                SaluBSel.RS2: rs2_val,
                SaluBSel.IR_IMM: self.ir_imm,
            },
            0,
        )

    def select_srf_wb(self, sel: SrfSel) -> int:
        return self.mux_srf.select(
            sel,
            {
                SrfSel.SALU_OUT: self.salu_out,
                SrfSel.RDATA: self.rdata,
                SrfSel.RET_ADDR: self.lr,
            },
            self.salu_out,
        )

    def select_vrf_wb(self, sel: VrfSel) -> list[int]:
        return self.mux_vrf.select(
            sel,
            {
                VrfSel.VALU_OUT: self.valu_out,
                VrfSel.PACKED_DATA: self.packed_data,
            },
            self.valu_out,
        )

    def select_lr_in(self, sel: LrSel, rs1_val: int) -> int:
        return self.mux_lr.select(
            sel,
            {
                LrSel.PC_OUT: self.pc,
                LrSel.RS1: rs1_val,
            },
            self.pc,
        )

    def select_ar_in(self, sel: ArSel) -> int:
        return self.mux_ar.select(
            sel,
            {
                ArSel.PC_OUT: self.pc,
                ArSel.DATA_ADDR: self.data_addr,
                ArSel.AR_PLUS_4: self.ar_inc.add(self.ar),
            },
            self.pc,
        )

    def select_pc_in(self, sel: PcSel) -> int:
        return self.mux_pc.select(
            sel,
            {
                PcSel.PC_PLUS_4: self.pc_inc.add(self.pc),
                PcSel.BRANCH_TARGET: self.branch_target,
                PcSel.BLR_TARGET: self.lr,
            },
            self.pc,
        )

    @property
    def vcnt_done(self) -> bool:
        return self.vcnt == 3

    @property
    def PC(self) -> int:
        return self.pc

    @PC.setter
    def PC(self, value: int) -> None:
        self.pc = value & 0xFFFFFFFF

    @property
    def AR(self) -> int:
        return self.ar

    @AR.setter
    def AR(self, value: int) -> None:
        self.ar = value & 0xFFFFFFFF

    @property
    def IR(self) -> int:
        return self.ir

    @IR.setter
    def IR(self, value: int) -> None:
        self.ir = value & 0xFFFFFFFF

    @property
    def LR(self) -> int:
        return self.lr

    @LR.setter
    def LR(self, value: int) -> None:
        self.lr = value & 0xFFFFFFFF

    @property
    def VCNT(self) -> int:
        return self.vcnt

    @property
    def VCNT_DONE(self) -> bool:
        return self.vcnt_done

    @property
    def FLAGS_Z(self) -> int:
        return self.flag_z

    @property
    def FLAGS_N(self) -> int:
        return self.flag_n

    @property
    def RS1(self) -> int:
        return self.rs1

    @property
    def RS2(self) -> int:
        return self.rs2

    @property
    def IR_IMM(self) -> int:
        return self.ir_imm

    @property
    def RDATA(self) -> int:
        return self.rdata

    @property
    def WDATA(self) -> int:
        return self.wdata

    @property
    def SALU_OUT(self) -> int:
        return self.salu_out

    @property
    def VALU_OUT(self) -> list[int]:
        return list(self.valu_out)

    @property
    def DATA_ADDR(self) -> int:
        return self.data_addr

    @property
    def BRANCH_TARGET(self) -> int:
        return self.branch_target

    @property
    def regs(self) -> list[int]:
        return list(self.srf.get_all())

    @property
    def memory(self) -> SparseMemory:
        return self.mem.raw_mem
