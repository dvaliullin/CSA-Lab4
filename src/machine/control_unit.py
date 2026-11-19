from __future__ import annotations

import logging
from typing import cast

from src.isa import DecodedInstruction, Opcode, decode_instruction
from src.machine.datapath import DataPath
from src.microcode import (
    DestReg,
    MemReadDest,
    MicroCond,
    MicroInstruction,
    SrcA,
    SrcB,
    build_control_store,
)

logger = logging.getLogger("machine")


class InstructionDecoder:
    OPCODE = "Opcode"
    REG_ADDR = "REG_ADDR"
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
    def select(self, seq_op: MicroCond, next_maddr: int, mapped: int, mpc_inc: int, flag: int) -> int:
        if seq_op is MicroCond.NEXT:
            return next_maddr
        if seq_op is MicroCond.DISPATCH:
            return mapped
        if seq_op is MicroCond.COND_BRANCH:
            return flag
        if seq_op is MicroCond.FETCH:
            return 0
        return mpc_inc


class MuxCond:
    COND_SEL = "COND_SEL"

    @staticmethod
    def select(condition: int, z: int, n: int, vcnt_done: bool = False) -> bool:
        if condition == 0:
            return z == 1
        if condition == 1:
            return z == 0
        if condition == 2:
            return n == 1
        if condition == 3:
            return n == 0
        if condition == 4:
            return n == 1 or z == 1
        if condition == 5:
            return n == 0 and z == 0
        return vcnt_done


class ControlUnit:
    def __init__(self, datapath: DataPath) -> None:
        self.dp: DataPath = datapath
        self.control_store, self.dispatch_table = build_control_store()
        self.rom = MicroProgramROM(self.control_store)
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
    def MUX_MPC(self) -> MuxMPC:
        return self.mux_mpc

    @property
    def MUX_COND(self) -> MuxCond:
        return self.mux_cond

    def step(self) -> None:
        if self.halted:
            return

        # Чтение микрокоманды в MIR (Microinstruction Register)
        self.mir = self.rom.read(self.mpc)
        mir = self.mir
        self.tick_count += 1
        decoded = self.instruction_decoder.decode(self.dp.IR)
        self.dp.ir_imm = decoded.imm

        op_a = 0
        if mir.src_a == SrcA.PC:
            op_a = self.dp.pc
        elif mir.src_a == SrcA.RS1:
            op_a = self.dp.srf.read_port_1(decoded.rs1)
        elif mir.src_a == SrcA.MAR:
            op_a = self.dp.ar
        elif mir.src_a == SrcA.IMM:
            op_a = decoded.imm
        elif mir.src_a == SrcA.SP:
            op_a = self.dp.srf.read_port_1(1)
        elif mir.src_a == SrcA.LR:
            op_a = self.dp.lr
        elif mir.src_a == SrcA.RD:
            op_a = self.dp.srf.read_port_1(decoded.rd)

        op_b = 0
        if mir.src_b == SrcB.RS2:
            op_b = self.dp.srf.read_port_2(decoded.rs2)
        elif mir.src_b == SrcB.IMM:
            op_b = decoded.imm
        elif mir.src_b == SrcB.CONST_4:
            op_b = 4

        self.dp.rs1 = cast(int, self.dp.mux_salu.select(op_a))
        self.dp.rs2 = cast(int, self.dp.mux_salu.select(op_b))

        res, new_z, new_n = self.dp.salu.execute(self.dp.rs1, self.dp.rs2, mir.SALU_OP)
        if mir.src_a == SrcA.PC and mir.src_b == SrcB.CONST_4:
            res = self.dp.pc_inc.add(self.dp.PC)
        self.dp.salu_out = res
        if new_z is not None:
            self.dp.flag_z = new_z
        if new_n is not None:
            self.dp.flag_n = new_n

        if mir.vcnt_reset:
            self.dp.vcnt = 0

        # Запись в регистры
        if mir.dest == DestReg.MAR:
            self.dp.data_addr = cast(int, self.dp.mux_ar.select(res))
            self.dp.AR = self.dp.data_addr
        elif mir.dest == DestReg.PC:
            self.dp.branch_target = cast(int, self.dp.mux_pc.select(res))
            self.dp.PC = self.dp.branch_target
        elif mir.dest == DestReg.LR:
            self.dp.lr = cast(int, self.dp.mux_lr.select(res)) & 0xFFFF
        elif mir.dest == DestReg.RD:
            srf_wb = cast(int, self.dp.mux_srf.select(res))
            self.dp.srf.write_back(decoded.rd, srf_wb, decoded.rd != 0)

        # Векторные операции (VALU и Splitter/Packer)
        if mir.vec_op in ("VADD", "VSUB", "VMUL", "VDIV", "VCMP"):
            v1 = self.dp.vrf.read_port_1(decoded.vs1)
            v2 = self.dp.vrf.read_port_2(decoded.vs2)
            v_res = self.dp.valu.execute(v1, v2, mir.VALU_OP)
            self.dp.valu_out = v_res
            self.dp.vrf.write_back(decoded.vd, cast(list[int], self.dp.mux_vrf.select(v_res)), True)
        elif mir.vec_op == "VLD":
            lane = self.dp.vcnt
            self.dp.rdata = self.dp.mem.read(self.dp.ar, byte=False)
            self.dp.vrf.write_lane(decoded.vd, lane, self.dp.rdata)
        elif mir.vec_op == "VST":
            lane = self.dp.vcnt
            self.dp.wdata = self.dp.vrf.read_lane(decoded.vd, lane)
            self.dp.mem.write(self.dp.ar, self.dp.wdata, byte=False)

        if mir.vcnt_enable:
            self.dp.vcnt = (self.dp.vcnt + 1) & 0x03

        # Обращение к памяти
        if mir.mem_read:
            read_data = self.dp.mem.read(self.dp.ar, byte=mir.mem_byte)
            if mir.mem_read_dest == MemReadDest.IR:
                self.dp.IR = read_data
            elif mir.mem_read_dest == MemReadDest.RD:
                self.dp.rdata = read_data
                self.dp.srf.write_back(decoded.rd, cast(int, self.dp.mux_srf.select(self.dp.rdata)), decoded.rd != 0)

        if mir.mem_write and mir.mem_write_src == SrcA.RD:
            self.dp.wdata = self.dp.srf.read_port_1(decoded.rd)
            self.dp.mem.write(self.dp.ar, self.dp.wdata, byte=mir.mem_byte)

        # Логирование текущего состояния процессора
        register_values = f"[{' '.join(str(value) for value in self.dp.srf.get_all())}]"
        vector_values = (
            "["
            + " ".join("[" + " ".join(str(value) for value in vector) + "]" for vector in self.dp.vrf.get_all())
            + "]"
        )
        logger.debug(
            "TICK: %4d MPC: %3d PC: %04X IR: %08X AR: %08X LR: %04X %-10s Z: %d N: %d R: %s V: %s",
            self.tick_count,
            self.mpc,
            self.dp.pc,
            self.dp.ir,
            self.dp.ar,
            self.dp.lr,
            f"[{decoded.opcode.name}]",
            self.dp.flag_z,
            self.dp.flag_n,
            register_values,
            vector_values,
        )

        # Мультиплексор следующего адреса микрокоманды (MUX_MPC / MUX_COND)
        if mir.ucond == MicroCond.NEXT:
            self.mpc = mir.next_uaddr
        elif mir.ucond == MicroCond.DISPATCH:
            if decoded.opcode == Opcode.TRAP:
                self.halted = True
                logger.info("HALT: instruction TRAP executed at PC=%04X (ticks: %d)", self.dp.pc, self.tick_count)
                final_str = "".join(chr(b) for b in self.dp.mem.io_output_buffer)
                logger.info("output_buffer: %r", final_str)
                return
            self.mpc = self.mux_mpc.select(
                MicroCond.DISPATCH,
                mir.next_uaddr,
                self.dispatch_table.get(decoded.opcode.value, 0),
                self.mpc_inc.increment(self.mpc),
                0,
            )
            self.instruction_count += 1
        elif mir.ucond == MicroCond.COND_BRANCH:
            take = self.mux_cond.select(decoded.cond, self.dp.flag_z, self.dp.flag_n, self.dp.VCNT_DONE)

            if take:
                self.dp.branch_target = res & 0xFFFF
                self.dp.pc = cast(int, self.dp.mux_pc.select(self.dp.branch_target))
            self.mpc = self.mux_mpc.select(
                MicroCond.COND_BRANCH, mir.next_uaddr, 0, self.mpc_inc.increment(self.mpc), 0
            )
        elif mir.ucond == MicroCond.FETCH:
            self.mpc = self.mux_mpc.select(MicroCond.FETCH, mir.next_uaddr, 0, self.mpc_inc.increment(self.mpc), 0)
