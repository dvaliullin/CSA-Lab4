from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class AluOp(Enum):
    NOP = auto()
    PASS_A = auto()
    PASS_B = auto()
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    AND = auto()
    OR = auto()
    XOR = auto()
    LSL = auto()
    LSR = auto()
    ASR = auto()
    CMP = auto()
    CMPL = auto()
    ADDIS = auto()


class SrcA(Enum):
    NONE = auto()
    PC = auto()
    RS1 = auto()
    MAR = auto()
    SP = auto()
    IMM = auto()
    LR = auto()
    RD = auto()


class SrcB(Enum):
    NONE = auto()
    RS2 = auto()
    IMM = auto()
    CONST_4 = auto()


class DestReg(Enum):
    NONE = auto()
    RD = auto()
    MAR = auto()
    IR = auto()
    PC = auto()
    LR = auto()
    FLAGS = auto()


class MicroCond(Enum):
    NEXT = auto()
    DISPATCH = auto()
    FETCH = auto()
    COND_BRANCH = auto()


class MemReadDest(Enum):
    NONE = auto()
    IR = auto()
    RD = auto()


class MemSize(Enum):
    WORD = "WORD"
    BYTE = "BYTE"


class WDataSelect(Enum):
    SPLIT_DATA = "SPLIT_DATA"
    STB_STW_DATA = "STB_STW_DATA"


class SeqOp(Enum):
    NEXT_MADDR = "NEXT_MADDR"
    MPC_INC = "MPC_INC"
    MAP_ADDR = "MAP_ADDR"
    FLAG_STATUS = "FLAG_STATUS"


@dataclass(frozen=True)
class MicroInstruction:
    alu_op: AluOp = AluOp.NOP
    src_a: SrcA = SrcA.NONE
    src_b: SrcB = SrcB.NONE
    dest: DestReg = DestReg.NONE
    mem_read: bool = False
    mem_read_dest: MemReadDest = MemReadDest.NONE
    mem_write: bool = False
    mem_write_src: SrcA = SrcA.NONE
    mem_byte: bool = False
    vec_op: str = "NONE"
    vcnt_reset: bool = False
    vcnt_enable: bool = False
    ucond: MicroCond = MicroCond.NEXT
    next_uaddr: int = 0

    @property
    def SALU_OP(self) -> AluOp:
        return self.alu_op

    @property
    def SRF_WE(self) -> bool:
        return self.dest is DestReg.RD

    @property
    def VRF_WE(self) -> bool:
        return self.vec_op in ("VADD", "VSUB", "VMUL", "VDIV", "VCMP", "VLD")

    @property
    def MEM_READ(self) -> bool:
        return self.mem_read

    @property
    def MEM_WRITE(self) -> bool:
        return self.mem_write

    @property
    def MEM_SIZE(self) -> MemSize:
        return MemSize.BYTE if self.mem_byte else MemSize.WORD

    @property
    def WDATA_SEL(self) -> WDataSelect:
        return WDataSelect.STB_STW_DATA if self.mem_byte else WDataSelect.SPLIT_DATA

    @property
    def VALU_OP(self) -> str:
        return self.vec_op

    @property
    def VCNT_EN(self) -> bool:
        return self.vcnt_enable

    @property
    def VCNT_RST(self) -> bool:
        return self.vcnt_reset

    @property
    def SEQ_OP(self) -> MicroCond:
        return self.ucond

    @property
    def NEXT_MADDR(self) -> int:
        return self.next_uaddr


def build_control_store() -> tuple[list[MicroInstruction], dict[int, int]]:
    store: list[MicroInstruction] = [MicroInstruction() for _ in range(256)]
    dispatch: dict[int, int] = {}

    store[0] = MicroInstruction(
        alu_op=AluOp.PASS_A, src_a=SrcA.PC, dest=DestReg.MAR, ucond=MicroCond.NEXT, next_uaddr=1
    )
    store[1] = MicroInstruction(
        alu_op=AluOp.ADD,
        src_a=SrcA.PC,
        src_b=SrcB.CONST_4,
        dest=DestReg.PC,
        mem_read=True,
        mem_read_dest=MemReadDest.IR,
        ucond=MicroCond.NEXT,
        next_uaddr=2,
    )
    store[2] = MicroInstruction(alu_op=AluOp.NOP, ucond=MicroCond.DISPATCH)

    # Integer ALU
    store[10] = MicroInstruction(
        alu_op=AluOp.ADD, src_a=SrcA.RS1, src_b=SrcB.RS2, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x01] = 10
    store[11] = MicroInstruction(
        alu_op=AluOp.SUB, src_a=SrcA.RS1, src_b=SrcB.RS2, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x02] = 11
    store[12] = MicroInstruction(
        alu_op=AluOp.MUL, src_a=SrcA.RS1, src_b=SrcB.RS2, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x03] = 12
    store[13] = MicroInstruction(
        alu_op=AluOp.DIV, src_a=SrcA.RS1, src_b=SrcB.RS2, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x04] = 13
    store[14] = MicroInstruction(
        alu_op=AluOp.MOD, src_a=SrcA.RS1, src_b=SrcB.RS2, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x05] = 14
    store[15] = MicroInstruction(
        alu_op=AluOp.AND, src_a=SrcA.RS1, src_b=SrcB.RS2, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x06] = 15
    store[16] = MicroInstruction(
        alu_op=AluOp.OR, src_a=SrcA.RS1, src_b=SrcB.RS2, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x07] = 16
    store[17] = MicroInstruction(
        alu_op=AluOp.XOR, src_a=SrcA.RS1, src_b=SrcB.RS2, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x08] = 17
    store[18] = MicroInstruction(
        alu_op=AluOp.LSL, src_a=SrcA.RS1, src_b=SrcB.RS2, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x09] = 18
    store[19] = MicroInstruction(
        alu_op=AluOp.LSR, src_a=SrcA.RS1, src_b=SrcB.RS2, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x0A] = 19
    store[20] = MicroInstruction(
        alu_op=AluOp.ASR, src_a=SrcA.RS1, src_b=SrcB.RS2, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x0B] = 20
    store[21] = MicroInstruction(
        alu_op=AluOp.CMP, src_a=SrcA.RS1, src_b=SrcB.RS2, dest=DestReg.FLAGS, ucond=MicroCond.FETCH
    )
    dispatch[0x0C] = 21
    store[95] = MicroInstruction(
        alu_op=AluOp.CMPL, src_a=SrcA.RS1, src_b=SrcB.RS2, dest=DestReg.FLAGS, ucond=MicroCond.FETCH
    )
    dispatch[0x0D] = 95

    # Immediate ALU
    store[22] = MicroInstruction(
        alu_op=AluOp.ADD, src_a=SrcA.RS1, src_b=SrcB.IMM, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x10] = 22
    store[23] = MicroInstruction(
        alu_op=AluOp.SUB, src_a=SrcA.RS1, src_b=SrcB.IMM, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x11] = 23
    store[24] = MicroInstruction(
        alu_op=AluOp.AND, src_a=SrcA.RS1, src_b=SrcB.IMM, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x12] = 24
    store[25] = MicroInstruction(
        alu_op=AluOp.OR, src_a=SrcA.RS1, src_b=SrcB.IMM, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x13] = 25
    store[26] = MicroInstruction(
        alu_op=AluOp.CMP, src_a=SrcA.RS1, src_b=SrcB.IMM, dest=DestReg.FLAGS, ucond=MicroCond.FETCH
    )
    dispatch[0x14] = 26
    # Immediate Shifts: SLWI, SRWI, SRAWI
    store[27] = MicroInstruction(
        alu_op=AluOp.LSL, src_a=SrcA.RS1, src_b=SrcB.IMM, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x15] = 27
    store[28] = MicroInstruction(
        alu_op=AluOp.LSR, src_a=SrcA.RS1, src_b=SrcB.IMM, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x16] = 28
    store[29] = MicroInstruction(
        alu_op=AluOp.ASR, src_a=SrcA.RS1, src_b=SrcB.IMM, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x17] = 29

    # LWZ
    store[30] = MicroInstruction(
        alu_op=AluOp.ADD, src_a=SrcA.RS1, src_b=SrcB.IMM, dest=DestReg.MAR, ucond=MicroCond.NEXT, next_uaddr=31
    )
    store[31] = MicroInstruction(mem_read=True, mem_read_dest=MemReadDest.RD, ucond=MicroCond.FETCH)
    dispatch[0x18] = 30

    # LBZ
    store[32] = MicroInstruction(
        alu_op=AluOp.ADD, src_a=SrcA.RS1, src_b=SrcB.IMM, dest=DestReg.MAR, ucond=MicroCond.NEXT, next_uaddr=33
    )
    store[33] = MicroInstruction(mem_read=True, mem_read_dest=MemReadDest.RD, mem_byte=True, ucond=MicroCond.FETCH)
    dispatch[0x19] = 32

    # STW: MAR <- RS1 + IMM; затем запись RD через шину WDATA
    store[35] = MicroInstruction(
        alu_op=AluOp.ADD, src_a=SrcA.RS1, src_b=SrcB.IMM, dest=DestReg.MAR, ucond=MicroCond.NEXT, next_uaddr=36
    )
    store[36] = MicroInstruction(src_a=SrcA.RD, mem_write=True, mem_write_src=SrcA.RD, ucond=MicroCond.FETCH)
    dispatch[0x20] = 35

    # STB: MAR <- RS1 + IMM; затем запись RD через шину WDATA
    store[37] = MicroInstruction(
        alu_op=AluOp.ADD, src_a=SrcA.RS1, src_b=SrcB.IMM, dest=DestReg.MAR, ucond=MicroCond.NEXT, next_uaddr=38
    )
    store[38] = MicroInstruction(
        src_a=SrcA.RD, mem_write=True, mem_write_src=SrcA.RD, mem_byte=True, ucond=MicroCond.FETCH
    )
    dispatch[0x21] = 37

    # Условные переходы
    store[40] = MicroInstruction(alu_op=AluOp.PASS_A, src_a=SrcA.IMM, dest=DestReg.NONE, ucond=MicroCond.COND_BRANCH)
    for b_op in (0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D):
        dispatch[b_op] = 40

    # B
    store[50] = MicroInstruction(alu_op=AluOp.PASS_A, src_a=SrcA.IMM, dest=DestReg.PC, ucond=MicroCond.FETCH)
    dispatch[0x30] = 50

    # BL
    store[51] = MicroInstruction(
        alu_op=AluOp.PASS_A, src_a=SrcA.PC, dest=DestReg.LR, ucond=MicroCond.NEXT, next_uaddr=52
    )
    store[52] = MicroInstruction(alu_op=AluOp.PASS_A, src_a=SrcA.IMM, dest=DestReg.PC, ucond=MicroCond.FETCH)
    dispatch[0x31] = 51

    # BLR
    store[53] = MicroInstruction(alu_op=AluOp.PASS_A, src_a=SrcA.LR, dest=DestReg.PC, ucond=MicroCond.FETCH)
    dispatch[0x32] = 53

    # MFLR / MTLR
    store[54] = MicroInstruction(alu_op=AluOp.PASS_A, src_a=SrcA.LR, dest=DestReg.RD, ucond=MicroCond.FETCH)
    dispatch[0x33] = 54
    store[55] = MicroInstruction(alu_op=AluOp.PASS_A, src_a=SrcA.RS1, dest=DestReg.LR, ucond=MicroCond.FETCH)
    dispatch[0x3B] = 55

    # AltiVec
    store[60] = MicroInstruction(vec_op="VADD", ucond=MicroCond.FETCH)
    dispatch[0x34] = 60
    store[61] = MicroInstruction(vec_op="VSUB", ucond=MicroCond.FETCH)
    dispatch[0x35] = 61
    store[62] = MicroInstruction(vec_op="VMUL", ucond=MicroCond.FETCH)
    dispatch[0x36] = 62
    store[63] = MicroInstruction(vec_op="VDIV", ucond=MicroCond.FETCH)
    dispatch[0x37] = 63
    store[64] = MicroInstruction(vec_op="VCMP", ucond=MicroCond.FETCH)
    dispatch[0x38] = 64

    # LVX
    store[70] = MicroInstruction(
        alu_op=AluOp.ADD,
        src_a=SrcA.RS1,
        src_b=SrcB.IMM,
        dest=DestReg.MAR,
        vec_op="VLD",
        vcnt_reset=True,
        vcnt_enable=True,
        ucond=MicroCond.NEXT,
        next_uaddr=71,
    )
    store[71] = MicroInstruction(
        alu_op=AluOp.ADD,
        src_a=SrcA.MAR,
        src_b=SrcB.CONST_4,
        dest=DestReg.MAR,
        vec_op="VLD",
        vcnt_enable=True,
        ucond=MicroCond.NEXT,
        next_uaddr=72,
    )
    store[72] = MicroInstruction(
        alu_op=AluOp.ADD,
        src_a=SrcA.MAR,
        src_b=SrcB.CONST_4,
        dest=DestReg.MAR,
        vec_op="VLD",
        vcnt_enable=True,
        ucond=MicroCond.NEXT,
        next_uaddr=73,
    )
    store[73] = MicroInstruction(
        alu_op=AluOp.ADD,
        src_a=SrcA.MAR,
        src_b=SrcB.CONST_4,
        dest=DestReg.MAR,
        vec_op="VLD",
        vcnt_enable=True,
        ucond=MicroCond.FETCH,
    )
    dispatch[0x39] = 70

    # STVX
    store[80] = MicroInstruction(
        alu_op=AluOp.ADD,
        src_a=SrcA.RS1,
        src_b=SrcB.IMM,
        dest=DestReg.MAR,
        vec_op="VST",
        vcnt_reset=True,
        vcnt_enable=True,
        ucond=MicroCond.NEXT,
        next_uaddr=81,
    )
    store[81] = MicroInstruction(
        alu_op=AluOp.ADD,
        src_a=SrcA.MAR,
        src_b=SrcB.CONST_4,
        dest=DestReg.MAR,
        vec_op="VST",
        vcnt_enable=True,
        ucond=MicroCond.NEXT,
        next_uaddr=82,
    )
    store[82] = MicroInstruction(
        alu_op=AluOp.ADD,
        src_a=SrcA.MAR,
        src_b=SrcB.CONST_4,
        dest=DestReg.MAR,
        vec_op="VST",
        vcnt_enable=True,
        ucond=MicroCond.NEXT,
        next_uaddr=83,
    )
    store[83] = MicroInstruction(
        alu_op=AluOp.ADD,
        src_a=SrcA.MAR,
        src_b=SrcB.CONST_4,
        dest=DestReg.MAR,
        vec_op="VST",
        vcnt_enable=True,
        ucond=MicroCond.FETCH,
    )
    dispatch[0x3A] = 80

    # ADDIS / LIS (Opcode 0x0E)
    store[96] = MicroInstruction(
        alu_op=AluOp.ADDIS, src_a=SrcA.RS1, src_b=SrcB.IMM, dest=DestReg.RD, ucond=MicroCond.FETCH
    )
    dispatch[0x0E] = 96

    # TRAP
    store[90] = MicroInstruction(alu_op=AluOp.NOP, ucond=MicroCond.NEXT, next_uaddr=90)
    dispatch[0x3F] = 90

    return store, dispatch
