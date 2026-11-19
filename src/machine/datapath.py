from __future__ import annotations

from src.isa import DEFAULT_BASE, STACK_TOP
from src.machine.memory import Memory, SparseMemory
from src.machine.scalar_alu import ScalarALU
from src.machine.scalar_rf import ScalarRegisterFile
from src.machine.vector_alu import VectorALU
from src.machine.vector_rf import VectorRegisterFile


class Mux:
    def __init__(self, name: str) -> None:
        self.name = name

    def select(self, value: object) -> object:
        return value


class PCIncrementer:
    PC_INC = "PC_INC"

    @staticmethod
    def add(pc: int) -> int:
        return (pc + 4) & 0xFFFF


class DataPath:
    def __init__(self) -> None:
        self.srf: ScalarRegisterFile = ScalarRegisterFile()
        self.srf.write(1, STACK_TOP)
        self.vrf: VectorRegisterFile = VectorRegisterFile()
        self.salu: ScalarALU = ScalarALU()
        self.valu: VectorALU = VectorALU()
        self.mem: Memory = Memory()

        self.pc: int = DEFAULT_BASE
        self.ar: int = 0
        self.ir: int = 0
        self.lr: int = 0
        self.vcnt: int = 0
        self.flag_z: int = 0
        self.flag_n: int = 0
        self.pc_inc = PCIncrementer()

        self.mux_srf = Mux("MUX_SRF")
        self.mux_salu = Mux("MUX_SALU")
        self.mux_vrf = Mux("MUX_VRF")
        self.mux_lr = Mux("MUX_LR")
        self.mux_pc = Mux("MUX_PC")
        self.mux_ar = Mux("MUX_AR")
        self.rdata = 0
        self.wdata = 0
        self.rs1 = 0
        self.rs2 = 0
        self.ir_imm = 0
        self.salu_out = 0
        self.valu_out: list[int] = [0, 0, 0, 0]
        self.data_addr = 0
        self.branch_target = 0

    @property
    def vcnt_done(self) -> bool:
        return self.vcnt == 3

    @property
    def PC(self) -> int:
        return self.pc

    @PC.setter
    def PC(self, value: int) -> None:
        self.pc = value & 0xFFFF

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
        self.lr = value & 0xFFFF

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
