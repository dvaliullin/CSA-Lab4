from __future__ import annotations

import logging

from src.isa import DecodedInstruction, Opcode, decode_instruction
from src.machine.datapath import DataPath
from src.microcode import (
    ArSel,
    CondSel,
    MicroInstruction,
    SeqOp,
    WDataSelect,
    build_control_store,
)

logger = logging.getLogger("machine")


class MapROM:
    MAP_ADDR = "MAP_ADDR"

    def __init__(self, dispatch_table: dict[int, int]) -> None:
        self.dispatch_table = dispatch_table

    def lookup(self, opcode: Opcode) -> int:
        return self.dispatch_table.get(opcode.value, 0)


class InstructionDecoder:
    OPCODE = "Opcode"
    SR_ADDR = "SR_ADDR"
    VR_ADDR = "VR_ADDR"
    IR_IMM = "IR_IMM"

    @staticmethod
    def decode(instruction: int) -> DecodedInstruction:
        return decode_instruction(instruction)


class MicroProgramROM:
    M_ADDR = "M_ADDR"
    MICROCODE = "Microcode"

    def __init__(self, words: list[MicroInstruction]) -> None:
        self.words = words

    def read(self, address: int) -> MicroInstruction:
        return self.words[address & 0xFF]


class MPCIncrementer:
    @staticmethod
    def increment(mpc: int) -> int:
        return (mpc + 1) & 0xFF


class MuxMPC:
    def select(self, seq_op: SeqOp, next_maddr: int, mapped: int, mpc_inc: int, flag_status: bool) -> int:
        if seq_op is SeqOp.NEXT_MADDR:
            return next_maddr
        if seq_op is SeqOp.MPC_INC:
            return mpc_inc
        if seq_op is SeqOp.MAP_ADDR:
            return mapped
        if seq_op is SeqOp.FETCH0:
            return 0
        if seq_op is SeqOp.FLAG_STATUS:
            return next_maddr if flag_status else mpc_inc
        return mpc_inc


class MuxCond:
    COND_SEL = "COND_SEL"

    @staticmethod
    def select(cond_sel: CondSel, z: int, n: int, vcnt_done: bool) -> bool:
        if cond_sel is CondSel.UNCOND:
            return True
        if cond_sel is CondSel.VCNT_LOOP:
            return not vcnt_done
        if cond_sel is CondSel.EQ:
            return z == 1
        if cond_sel is CondSel.NE:
            return z == 0
        if cond_sel is CondSel.LT:
            return n == 1
        if cond_sel is CondSel.GE:
            return n == 0
        if cond_sel is CondSel.LE:
            return n == 1 or z == 1
        if cond_sel is CondSel.GT:
            return n == 0 and z == 0
        return False


class ControlUnit:
    def __init__(self, datapath: DataPath) -> None:
        self.dp: DataPath = datapath
        self.control_store, self.dispatch_table = build_control_store()
        self.rom = MicroProgramROM(self.control_store)
        self.map_rom = MapROM(self.dispatch_table)
        self.instruction_decoder = InstructionDecoder()
        self.mpc_inc = MPCIncrementer()
        self.mux_mpc = MuxMPC()
        self.mux_cond = MuxCond()
        self.mpc: int = 0
        self.mir: MicroInstruction = MicroInstruction()
        self.tick_count: int = 0
        self.instruction_count: int = 0
        self.halted: bool = False

    @property
    def MPC(self) -> int:
        return self.mpc

    @property
    def MIR(self) -> MicroInstruction:
        return self.mir

    @property
    def ROM(self) -> MicroProgramROM:
        return self.rom

    @property
    def MAP_ROM(self) -> MapROM:
        return self.map_rom

    @property
    def MUX_MPC(self) -> MuxMPC:
        return self.mux_mpc

    @property
    def MUX_COND(self) -> MuxCond:
        return self.mux_cond

    def step(self) -> None:
        if self.halted:
            return

        # 1. Чтение микрокоманды из ROM в MIR
        self.mir = self.rom.read(self.mpc)
        mir = self.mir
        self.tick_count += 1

        if mir.HALT_EN:
            self.halted = True
            logger.info("HALT: instruction TRAP executed at PC=%08X (ticks: %d)", self.dp.pc, self.tick_count)
            final_str = "".join(chr(b) for b in self.dp.mem.io_output_buffer)
            logger.info("output_buffer: %r", final_str)
            return

        # 2. Декодирование IR и выборка из SRF
        decoded = self.instruction_decoder.decode(self.dp.IR)
        self.dp.ir_imm = decoded.imm
        flag_status = self.mux_cond.select(mir.COND_SEL, self.dp.flag_z, self.dp.flag_n, self.dp.VCNT_DONE)

        rs1_val = self.dp.srf.read_port_1(decoded.rs1)
        rs2_sel = decoded.rd if (mir.MEM_WRITE and mir.WDATA_SEL is WDataSelect.STB_STW_DATA) else decoded.rs2
        rs2_val = self.dp.srf.read_port_2(rs2_sel)

        # 3. SALU
        self.dp.rs1 = self.dp.select_salu_a(mir.SALU_A_SEL, rs1_val)
        self.dp.rs2 = self.dp.select_salu_b(mir.SALU_B_SEL, rs2_val)

        res, new_z, new_n = self.dp.salu.execute(self.dp.rs1, self.dp.rs2, mir.SALU_OP)
        self.dp.salu_out = res
        self.dp.data_addr = res
        self.dp.branch_target = res & 0xFFFFFFFF

        if mir.FLAGS_WE:
            if new_z is not None:
                self.dp.flag_z = new_z
            if new_n is not None:
                self.dp.flag_n = new_n

        # 4. AR (для LVX/STVX: на vcnt==0 -> DATA_ADDR, иначе -> AR + 4 от AR_INC) и чтение памяти
        if mir.AR_EN:
            ar_sel = mir.AR_SEL
            if mir.VALU_OP in ("VLD", "VST"):
                ar_sel = ArSel.DATA_ADDR if self.dp.vcnt == 0 else ArSel.AR_PLUS_4
            self.dp.AR = self.dp.select_ar_in(ar_sel)

        if mir.MEM_READ:
            self.dp.rdata = self.dp.mem.read(self.dp.ar, mem_size=mir.MEM_SIZE)
            if mir.IR_EN:
                self.dp.IR = self.dp.rdata

        # 5. Vector DataPath (VALU / Splitter / Packer) и запись памяти
        if mir.VALU_OP in ("VADD", "VSUB", "VMUL", "VDIV", "VCMP"):
            v1 = self.dp.vrf.read_port_1(decoded.vs1)
            v2 = self.dp.vrf.read_port_2(decoded.vs2)
            self.dp.valu_out = self.dp.valu.execute(v1, v2, mir.VALU_OP)
        elif mir.VALU_OP == "VLD":
            self.dp.packed_data = self.dp.packer.pack(self.dp.vcnt, self.dp.rdata)
        elif mir.VALU_OP == "VST":
            vrs1 = self.dp.vrf.read_port_1(decoded.vd)
            self.dp.splitted_data = self.dp.splitter.split(vrs1, self.dp.vcnt)

        if mir.VRF_WE:
            vrf_wb = self.dp.select_vrf_wb(mir.VRF_SEL)
            self.dp.vrf.write_back(decoded.vd, vrf_wb, True)

        if mir.MEM_WRITE:
            if mir.WDATA_SEL is WDataSelect.SPLITTED_DATA:
                self.dp.wdata = self.dp.splitted_data
                self.dp.mem.write(
                    self.dp.ar,
                    0,
                    mem_size=mir.MEM_SIZE,
                    wdata_sel=WDataSelect.SPLITTED_DATA,
                    splitted_data=self.dp.splitted_data,
                )
            else:
                self.dp.wdata = rs2_val
                self.dp.mem.write(
                    self.dp.ar,
                    rs2_val,
                    mem_size=mir.MEM_SIZE,
                    wdata_sel=WDataSelect.STB_STW_DATA,
                )

        # 6. Обновление регистров по фронту такта
        if mir.VCNT_RST:
            self.dp.vcnt = 0
            self.dp.packer.reset()
        elif mir.VCNT_EN:
            self.dp.vcnt = (self.dp.vcnt + 1) & 0x03

        if mir.SRF_WE:
            srf_wb = self.dp.select_srf_wb(mir.SRF_SEL)
            self.dp.srf.write_back(decoded.rd, srf_wb, True)

        if mir.LR_EN:
            self.dp.LR = self.dp.select_lr_in(mir.LR_SEL, rs1_val)

        if mir.PC_EN:
            self.dp.PC = self.dp.select_pc_in(mir.PC_SEL)

        # 7. Логирование состояния
        log_decoded = self.instruction_decoder.decode(self.dp.IR) if mir.IR_EN else decoded
        non_zero_regs = " ".join(f"r{idx}={val:X}" for idx, val in enumerate(self.dp.srf.get_all()) if val != 0)
        non_zero_vecs = " ".join(
            f"v{idx}=[{' '.join(f'{lane:X}' for lane in vec)}]"
            for idx, vec in enumerate(self.dp.vrf.get_all())
            if any(lane != 0 for lane in vec)
        )
        logger.debug(
            "TICK: %4d MPC: %02X PC: %08X IR: %08X AR: %08X LR: %08X %-10s Z: %d N: %d R: {%s} V: {%s}",
            self.tick_count,
            self.mpc,
            self.dp.pc,
            self.dp.ir,
            self.dp.ar,
            self.dp.lr,
            f"[{log_decoded.opcode.name}]",
            self.dp.flag_z,
            self.dp.flag_n,
            non_zero_regs,
            non_zero_vecs,
        )

        # 8. Выбор следующего адреса микропрограммы (MUX_MPC)
        mapped = self.map_rom.lookup(log_decoded.opcode)
        if mir.SEQ_OP is SeqOp.MAP_ADDR and log_decoded.opcode is not Opcode.TRAP:
            self.instruction_count += 1

        self.mpc = self.mux_mpc.select(
            mir.SEQ_OP,
            mir.NEXT_MADDR,
            mapped,
            self.mpc_inc.increment(self.mpc),
            flag_status,
        )
