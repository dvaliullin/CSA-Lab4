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


class SaluASel(Enum):
    NONE = auto()
    RS1 = auto()
    PC_OUT = auto()


class SaluBSel(Enum):
    NONE = auto()
    RS2 = auto()
    IR_IMM = auto()


class SrfSel(Enum):
    SALU_OUT = 0  # 00
    RDATA = 1  # 01
    RET_ADDR = 2  # 10


class VrfSel(Enum):
    VALU_OUT = 0  # 0
    PACKED_DATA = 1  # 1


class LrSel(Enum):
    PC_OUT = 0  # 0
    RS1 = 1  # 1


class PcSel(Enum):
    PC_PLUS_4 = 0  # 00
    BRANCH_TARGET = 1  # 01
    BLR_TARGET = 2  # 10


class ArSel(Enum):
    PC_OUT = 0  # 00
    DATA_ADDR = 1  # 01
    AR_PLUS_4 = 2  # 10


class CondSel(Enum):
    NONE = auto()
    UNCOND = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    GE = auto()
    LE = auto()
    GT = auto()
    VCNT_LOOP = auto()


class MemSize(Enum):
    BYTE = "BYTE"  # 00
    WORD = "WORD"  # 10


class WDataSelect(Enum):
    STB_STW_DATA = "STB_STW_DATA"  # 0
    SPLITTED_DATA = "SPLITTED_DATA"  # 1


class SeqOp(Enum):
    NEXT_MADDR = "NEXT_MADDR"
    MPC_INC = "MPC_INC"
    MAP_ADDR = "MAP_ADDR"
    FLAG_STATUS = "FLAG_STATUS"
    FETCH0 = "FETCH0"


@dataclass(frozen=True)
class MicroInstruction:
    # Scalar DataPath
    alu_op: AluOp = AluOp.NOP
    salu_a_sel: SaluASel = SaluASel.NONE
    salu_b_sel: SaluBSel = SaluBSel.NONE
    srf_sel: SrfSel = SrfSel.SALU_OUT
    srf_we: bool = False
    flags_we: bool = False

    # Flow Control
    ir_en: bool = False
    pc_en: bool = False
    pc_sel: PcSel = PcSel.PC_PLUS_4
    lr_en: bool = False
    lr_sel: LrSel = LrSel.PC_OUT
    ar_en: bool = False
    ar_sel: ArSel = ArSel.PC_OUT
    halt_en: bool = False

    # Memory
    mem_read: bool = False
    mem_write: bool = False
    mem_size: MemSize = MemSize.WORD
    wdata_sel: WDataSelect = WDataSelect.STB_STW_DATA

    # Vector DataPath
    vec_op: str = "NONE"
    vrf_we: bool = False
    vrf_sel: VrfSel = VrfSel.VALU_OUT
    vcnt_reset: bool = False
    vcnt_enable: bool = False

    # Control Unit Sequencer
    cond_sel: CondSel = CondSel.NONE
    seq_op: SeqOp = SeqOp.MPC_INC
    next_maddr: int = 0

    @property
    def SALU_OP(self) -> AluOp:
        return self.alu_op

    @property
    def SALU_A_SEL(self) -> SaluASel:
        return self.salu_a_sel

    @property
    def SALU_B_SEL(self) -> SaluBSel:
        return self.salu_b_sel

    @property
    def SRF_SEL(self) -> SrfSel:
        return self.srf_sel

    @property
    def SRF_WE(self) -> bool:
        return self.srf_we

    @property
    def FLAGS_WE(self) -> bool:
        return self.flags_we

    @property
    def IR_EN(self) -> bool:
        return self.ir_en

    @property
    def PC_EN(self) -> bool:
        return self.pc_en

    @property
    def PC_SEL(self) -> PcSel:
        return self.pc_sel

    @property
    def LR_EN(self) -> bool:
        return self.lr_en

    @property
    def LR_SEL(self) -> LrSel:
        return self.lr_sel

    @property
    def AR_EN(self) -> bool:
        return self.ar_en

    @property
    def AR_SEL(self) -> ArSel:
        return self.ar_sel

    @property
    def HALT_EN(self) -> bool:
        return self.halt_en

    @property
    def VRF_WE(self) -> bool:
        return self.vrf_we

    @property
    def VRF_SEL(self) -> VrfSel:
        return self.vrf_sel

    @property
    def MEM_READ(self) -> bool:
        return self.mem_read

    @property
    def MEM_WRITE(self) -> bool:
        return self.mem_write

    @property
    def MEM_SIZE(self) -> MemSize:
        return self.mem_size

    @property
    def WDATA_SEL(self) -> WDataSelect:
        return self.wdata_sel

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
    def COND_SEL(self) -> CondSel:
        return self.cond_sel

    @property
    def SEQ_OP(self) -> SeqOp:
        return self.seq_op

    @property
    def NEXT_MADDR(self) -> int:
        return self.next_maddr


def build_control_store() -> tuple[list[MicroInstruction], dict[int, int]]:
    store: list[MicroInstruction] = [MicroInstruction() for _ in range(256)]
    dispatch: dict[int, int] = {}

    # Часть A: Общие циклы (0x00..0x03)
    store[0x00] = MicroInstruction(
        ar_sel=ArSel.PC_OUT,
        ar_en=True,
        mem_read=True,
        mem_size=MemSize.WORD,
        ir_en=True,
        pc_sel=PcSel.PC_PLUS_4,
        pc_en=True,
        seq_op=SeqOp.MPC_INC,
    )
    store[0x01] = MicroInstruction(vcnt_reset=True, seq_op=SeqOp.MAP_ADDR)
    store[0x02] = MicroInstruction(seq_op=SeqOp.FETCH0)
    dispatch[0x00] = 0x02  # NOP (3 такта)

    store[0x03] = MicroInstruction(halt_en=True, cond_sel=CondSel.UNCOND, seq_op=SeqOp.FLAG_STATUS, next_maddr=0x03)
    dispatch[0x3F] = 0x03  # TRAP (3 такта)

    # Часть B: Скалярные команды R-типа (4 такта)
    r_alu = [
        (0x01, 0x04, AluOp.ADD),
        (0x02, 0x06, AluOp.SUB),
        (0x03, 0x08, AluOp.MUL),
        (0x04, 0x0A, AluOp.DIV),
        (0x05, 0x0C, AluOp.MOD),
        (0x06, 0x0E, AluOp.AND),
        (0x07, 0x10, AluOp.OR),
        (0x08, 0x12, AluOp.XOR),
        (0x09, 0x14, AluOp.LSL),
        (0x0A, 0x16, AluOp.LSR),
        (0x0B, 0x18, AluOp.ASR),
    ]
    for opcode, base_addr, alu_op in r_alu:
        store[base_addr] = MicroInstruction(
            alu_op=alu_op, salu_a_sel=SaluASel.RS1, salu_b_sel=SaluBSel.RS2, seq_op=SeqOp.MPC_INC
        )
        store[base_addr + 1] = MicroInstruction(
            alu_op=alu_op,
            salu_a_sel=SaluASel.RS1,
            salu_b_sel=SaluBSel.RS2,
            srf_sel=SrfSel.SALU_OUT,
            srf_we=True,
            seq_op=SeqOp.FETCH0,
        )
        dispatch[opcode] = base_addr

    # CMPW (0x1A..0x1B) и CMPLW (0x1C..0x1D)
    store[0x1A] = MicroInstruction(
        alu_op=AluOp.CMP, salu_a_sel=SaluASel.RS1, salu_b_sel=SaluBSel.RS2, seq_op=SeqOp.MPC_INC
    )
    store[0x1B] = MicroInstruction(
        alu_op=AluOp.CMP, salu_a_sel=SaluASel.RS1, salu_b_sel=SaluBSel.RS2, flags_we=True, seq_op=SeqOp.FETCH0
    )
    dispatch[0x0C] = 0x1A

    store[0x1C] = MicroInstruction(
        alu_op=AluOp.CMPL, salu_a_sel=SaluASel.RS1, salu_b_sel=SaluBSel.RS2, seq_op=SeqOp.MPC_INC
    )
    store[0x1D] = MicroInstruction(
        alu_op=AluOp.CMPL, salu_a_sel=SaluASel.RS1, salu_b_sel=SaluBSel.RS2, flags_we=True, seq_op=SeqOp.FETCH0
    )
    dispatch[0x0D] = 0x1C

    # ADDIS / LIS (0x0E) на 0x1E..0x1F
    store[0x1E] = MicroInstruction(
        alu_op=AluOp.ADDIS, salu_a_sel=SaluASel.RS1, salu_b_sel=SaluBSel.IR_IMM, seq_op=SeqOp.MPC_INC
    )
    store[0x1F] = MicroInstruction(
        alu_op=AluOp.ADDIS,
        salu_a_sel=SaluASel.RS1,
        salu_b_sel=SaluBSel.IR_IMM,
        srf_sel=SrfSel.SALU_OUT,
        srf_we=True,
        seq_op=SeqOp.FETCH0,
    )
    dispatch[0x0E] = 0x1E

    # Часть C: Скалярные команды I-типа (4 такта, 0x20..0x2F)
    i_alu = [
        (0x10, 0x20, AluOp.ADD),
        (0x11, 0x22, AluOp.SUB),
        (0x12, 0x24, AluOp.AND),
        (0x13, 0x26, AluOp.OR),
        (0x15, 0x2A, AluOp.LSL),
        (0x16, 0x2C, AluOp.LSR),
        (0x17, 0x2E, AluOp.ASR),
    ]
    for opcode, base_addr, alu_op in i_alu:
        store[base_addr] = MicroInstruction(
            alu_op=alu_op, salu_a_sel=SaluASel.RS1, salu_b_sel=SaluBSel.IR_IMM, seq_op=SeqOp.MPC_INC
        )
        store[base_addr + 1] = MicroInstruction(
            alu_op=alu_op,
            salu_a_sel=SaluASel.RS1,
            salu_b_sel=SaluBSel.IR_IMM,
            srf_sel=SrfSel.SALU_OUT,
            srf_we=True,
            seq_op=SeqOp.FETCH0,
        )
        dispatch[opcode] = base_addr

    # CMPWI (0x28..0x29)
    store[0x28] = MicroInstruction(
        alu_op=AluOp.CMP, salu_a_sel=SaluASel.RS1, salu_b_sel=SaluBSel.IR_IMM, seq_op=SeqOp.MPC_INC
    )
    store[0x29] = MicroInstruction(
        alu_op=AluOp.CMP, salu_a_sel=SaluASel.RS1, salu_b_sel=SaluBSel.IR_IMM, flags_we=True, seq_op=SeqOp.FETCH0
    )
    dispatch[0x14] = 0x28

    # Часть D: Скалярный доступ к памяти / MMIO (5 тактов, 0x30..0x3B)
    # LWZ
    store[0x30] = MicroInstruction(
        alu_op=AluOp.ADD,
        salu_a_sel=SaluASel.RS1,
        salu_b_sel=SaluBSel.IR_IMM,
        ar_sel=ArSel.DATA_ADDR,
        ar_en=True,
        seq_op=SeqOp.MPC_INC,
    )
    store[0x31] = MicroInstruction(mem_read=True, mem_size=MemSize.WORD, seq_op=SeqOp.MPC_INC)
    store[0x32] = MicroInstruction(srf_sel=SrfSel.RDATA, srf_we=True, seq_op=SeqOp.FETCH0)
    dispatch[0x18] = 0x30

    # LBZ
    store[0x33] = MicroInstruction(
        alu_op=AluOp.ADD,
        salu_a_sel=SaluASel.RS1,
        salu_b_sel=SaluBSel.IR_IMM,
        ar_sel=ArSel.DATA_ADDR,
        ar_en=True,
        seq_op=SeqOp.MPC_INC,
    )
    store[0x34] = MicroInstruction(mem_read=True, mem_size=MemSize.BYTE, seq_op=SeqOp.MPC_INC)
    store[0x35] = MicroInstruction(srf_sel=SrfSel.RDATA, srf_we=True, seq_op=SeqOp.FETCH0)
    dispatch[0x19] = 0x33

    # STW
    store[0x36] = MicroInstruction(
        alu_op=AluOp.ADD,
        salu_a_sel=SaluASel.RS1,
        salu_b_sel=SaluBSel.IR_IMM,
        ar_sel=ArSel.DATA_ADDR,
        ar_en=True,
        seq_op=SeqOp.MPC_INC,
    )
    store[0x37] = MicroInstruction(
        mem_write=True, mem_size=MemSize.WORD, wdata_sel=WDataSelect.STB_STW_DATA, seq_op=SeqOp.MPC_INC
    )
    store[0x38] = MicroInstruction(seq_op=SeqOp.FETCH0)
    dispatch[0x20] = 0x36

    # STB
    store[0x39] = MicroInstruction(
        alu_op=AluOp.ADD,
        salu_a_sel=SaluASel.RS1,
        salu_b_sel=SaluBSel.IR_IMM,
        ar_sel=ArSel.DATA_ADDR,
        ar_en=True,
        seq_op=SeqOp.MPC_INC,
    )
    store[0x3A] = MicroInstruction(
        mem_write=True, mem_size=MemSize.BYTE, wdata_sel=WDataSelect.STB_STW_DATA, seq_op=SeqOp.MPC_INC
    )
    store[0x3B] = MicroInstruction(seq_op=SeqOp.FETCH0)
    dispatch[0x21] = 0x39

    # Часть E: Ветвления, переходы и работа с LR (4-5 тактов, 0x40..0x58)
    branch_conds = [
        (0x28, CondSel.EQ),
        (0x29, CondSel.NE),
        (0x2A, CondSel.LT),
        (0x2B, CondSel.GE),
        (0x2C, CondSel.LE),
        (0x2D, CondSel.GT),
    ]
    for idx, (b_op, cond_sel) in enumerate(branch_conds):
        chk_addr = 0x40 + idx * 2
        no_addr = chk_addr + 1
        store[chk_addr] = MicroInstruction(cond_sel=cond_sel, seq_op=SeqOp.FLAG_STATUS, next_maddr=0x4C)
        store[no_addr] = MicroInstruction(seq_op=SeqOp.FETCH0)
        dispatch[b_op] = chk_addr

    store[0x4C] = MicroInstruction(
        alu_op=AluOp.ADD,
        salu_a_sel=SaluASel.PC_OUT,
        salu_b_sel=SaluBSel.IR_IMM,
        pc_sel=PcSel.BRANCH_TARGET,
        pc_en=True,
        seq_op=SeqOp.FETCH0,
    )

    # B (4 такта)
    store[0x4E] = MicroInstruction(
        alu_op=AluOp.ADD, salu_a_sel=SaluASel.PC_OUT, salu_b_sel=SaluBSel.IR_IMM, seq_op=SeqOp.MPC_INC
    )
    store[0x4F] = MicroInstruction(
        alu_op=AluOp.ADD,
        salu_a_sel=SaluASel.PC_OUT,
        salu_b_sel=SaluBSel.IR_IMM,
        pc_sel=PcSel.BRANCH_TARGET,
        pc_en=True,
        seq_op=SeqOp.FETCH0,
    )
    dispatch[0x30] = 0x4E

    # BL (5 тактов)
    store[0x50] = MicroInstruction(lr_sel=LrSel.PC_OUT, lr_en=True, seq_op=SeqOp.MPC_INC)
    store[0x51] = MicroInstruction(
        alu_op=AluOp.ADD, salu_a_sel=SaluASel.PC_OUT, salu_b_sel=SaluBSel.IR_IMM, seq_op=SeqOp.MPC_INC
    )
    store[0x52] = MicroInstruction(
        alu_op=AluOp.ADD,
        salu_a_sel=SaluASel.PC_OUT,
        salu_b_sel=SaluBSel.IR_IMM,
        pc_sel=PcSel.BRANCH_TARGET,
        pc_en=True,
        seq_op=SeqOp.FETCH0,
    )
    dispatch[0x31] = 0x50

    # BLR (4 такта)
    store[0x53] = MicroInstruction(pc_sel=PcSel.BLR_TARGET, seq_op=SeqOp.MPC_INC)
    store[0x54] = MicroInstruction(pc_sel=PcSel.BLR_TARGET, pc_en=True, seq_op=SeqOp.FETCH0)
    dispatch[0x32] = 0x53

    # MFLR (4 такта)
    store[0x55] = MicroInstruction(srf_sel=SrfSel.RET_ADDR, seq_op=SeqOp.MPC_INC)
    store[0x56] = MicroInstruction(srf_sel=SrfSel.RET_ADDR, srf_we=True, seq_op=SeqOp.FETCH0)
    dispatch[0x33] = 0x55

    # MTLR (4 такта)
    store[0x57] = MicroInstruction(lr_sel=LrSel.RS1, seq_op=SeqOp.MPC_INC)
    store[0x58] = MicroInstruction(lr_sel=LrSel.RS1, lr_en=True, seq_op=SeqOp.FETCH0)
    dispatch[0x3B] = 0x57

    # Часть F: Векторная SIMD-арифметика (4 такта, 0x60..0x69)
    for opcode, base_addr, vec_op in [
        (0x34, 0x60, "VADD"),
        (0x35, 0x62, "VSUB"),
        (0x36, 0x64, "VMUL"),
        (0x37, 0x66, "VDIV"),
        (0x38, 0x68, "VCMP"),
    ]:
        store[base_addr] = MicroInstruction(vec_op=vec_op, seq_op=SeqOp.MPC_INC)
        store[base_addr + 1] = MicroInstruction(
            vec_op=vec_op, vrf_sel=VrfSel.VALU_OUT, vrf_we=True, seq_op=SeqOp.FETCH0
        )
        dispatch[opcode] = base_addr

    # Часть J: Векторная память (7 тактов)
    # LVX (0x70..0x71)
    store[0x70] = MicroInstruction(
        alu_op=AluOp.ADD,
        salu_a_sel=SaluASel.RS1,
        salu_b_sel=SaluBSel.IR_IMM,
        ar_sel=ArSel.DATA_ADDR,
        ar_en=True,
        mem_read=True,
        mem_size=MemSize.WORD,
        vec_op="VLD",
        vcnt_enable=True,
        cond_sel=CondSel.VCNT_LOOP,
        seq_op=SeqOp.FLAG_STATUS,
        next_maddr=0x70,
    )
    store[0x71] = MicroInstruction(vrf_sel=VrfSel.PACKED_DATA, vrf_we=True, seq_op=SeqOp.FETCH0)
    dispatch[0x39] = 0x70

    # STVX (0x72..0x73)
    store[0x72] = MicroInstruction(
        alu_op=AluOp.ADD,
        salu_a_sel=SaluASel.RS1,
        salu_b_sel=SaluBSel.IR_IMM,
        ar_sel=ArSel.DATA_ADDR,
        ar_en=True,
        vec_op="VST",
        mem_write=True,
        mem_size=MemSize.WORD,
        wdata_sel=WDataSelect.SPLITTED_DATA,
        vcnt_enable=True,
        cond_sel=CondSel.VCNT_LOOP,
        seq_op=SeqOp.FLAG_STATUS,
        next_maddr=0x72,
    )
    store[0x73] = MicroInstruction(seq_op=SeqOp.FETCH0)
    dispatch[0x3A] = 0x72

    return store, dispatch
