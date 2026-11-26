from __future__ import annotations

import logging
from enum import Enum
from typing import overload

from src.isa import MEM_SIZE, STDIN_DATA, STDOUT_DATA
from src.microcode import MemSize, WDataSelect

logger = logging.getLogger("machine")


class SparseMemory:
    def __init__(self, size: int) -> None:
        self.size = size
        self._bytes: dict[int, int] = {}

    def __len__(self) -> int:
        return self.size

    @overload
    def __getitem__(self, key: int) -> int: ...

    @overload
    def __getitem__(self, key: slice) -> bytes: ...

    def __getitem__(self, key: int | slice) -> int | bytes:
        if isinstance(key, int):
            addr = key & 0xFFFFFFFF
            if addr < 0 or addr >= self.size:
                raise IndexError("memory address out of range")
            return self._bytes.get(addr, 0)

        start, stop, step = key.indices(self.size)
        if step != 1:
            return bytes(self._bytes.get(addr & 0xFFFFFFFF, 0) for addr in range(start, stop, step))
        stop = min(stop, self.size)
        return bytes(self._bytes.get(addr & 0xFFFFFFFF, 0) for addr in range(start, stop))

    @overload
    def __setitem__(self, key: int, value: int) -> None: ...

    @overload
    def __setitem__(self, key: slice, value: bytes | bytearray) -> None: ...

    def __setitem__(self, key: int | slice, value: int | bytes | bytearray) -> None:
        if isinstance(key, int):
            addr = key & 0xFFFFFFFF
            if addr < 0 or addr >= self.size:
                raise IndexError("memory address out of range")
            if not isinstance(value, int):
                raise TypeError("A byte value is required for integer addressing")
            self._bytes[addr] = value & 0xFF
            return

        if not isinstance(value, (bytes, bytearray)):
            raise TypeError("A bytes-like value is required for slice assignment")
        start, stop, step = key.indices(self.size)
        if step != 1:
            raise ValueError("Non-unit slice steps are not supported")
        for addr, byte in zip(range(start, min(stop, self.size)), value):
            if addr >= 0:
                self._bytes[addr & 0xFFFFFFFF] = byte


class MemoryTarget(Enum):
    RAM = "RAM"
    STDIN_DATA = "STDIN_DATA"
    STDOUT_DATA = "STDOUT_DATA"


class MemoryAddressDecoder:
    MEM_ADDR = "MEM_ADDR"
    MEM_READ = "MEM_READ"
    MEM_WRITE = "MEM_WRITE"
    MEM_SEL = "MEM_SEL"

    @staticmethod
    def decode(mem_addr: int) -> MemoryTarget:
        clean_addr = mem_addr & 0xFFFFFFFF
        if clean_addr == STDIN_DATA:
            return MemoryTarget.STDIN_DATA
        if clean_addr == STDOUT_DATA:
            return MemoryTarget.STDOUT_DATA
        return MemoryTarget.RAM


AddressDecoder = MemoryAddressDecoder


class ByteAligner:
    MEM_SIZE = "MEM_SIZE"

    @staticmethod
    def word_address(addr: int) -> int:
        return addr & 0xFFFFFFFC

    @staticmethod
    def byte_address(addr: int) -> int:
        return addr & 0xFFFFFFFF

    @staticmethod
    def align_read(raw_word: int, mem_size: MemSize) -> int:
        return (raw_word & 0xFF) if mem_size is MemSize.BYTE else (raw_word & 0xFFFFFFFF)

    @staticmethod
    def align_write_scalar(wdata: int, mem_size: MemSize) -> int:
        return (wdata & 0xFF) if mem_size is MemSize.BYTE else (wdata & 0xFFFFFFFF)


class MuxWData:
    WDATA_SEL = "WDATA_SEL"

    @staticmethod
    def select(stb_stw_data: int, splitted_data: int, wdata_sel: WDataSelect) -> int:
        return stb_stw_data if wdata_sel is WDataSelect.STB_STW_DATA else (splitted_data & 0xFFFFFFFF)


class Memory:
    raw_mem: SparseMemory
    io_input_buffer: list[int]
    io_output_buffer: list[int]

    def __init__(self, size: int = MEM_SIZE) -> None:
        self.raw_mem = SparseMemory(size)
        self.io_input_buffer = []
        self.io_output_buffer = []
        self.address_decoder = MemoryAddressDecoder()
        self.byte_aligner = ByteAligner()
        self.mux_wdata = MuxWData()
        self.addr = 0
        self.rdata = 0
        self.wdata = 0
        self.mem_sel: MemoryTarget = MemoryTarget.RAM

    def read(self, addr: int, byte: bool = False, mem_size: MemSize | None = None) -> int:
        size = mem_size if mem_size is not None else (MemSize.BYTE if byte else MemSize.WORD)
        self.addr = addr & 0xFFFFFFFF
        self.mem_sel = self.address_decoder.decode(self.addr)

        if self.mem_sel is MemoryTarget.STDIN_DATA:
            if self.io_input_buffer:
                val = self.io_input_buffer.pop(0)
                char_repr = chr(val) if 32 <= val <= 126 else f"\\x{val:02x}"
                logger.debug("INPUT:  '%s' (%d) from port 0x%08X", char_repr, val, self.addr)
                self.rdata = val
                return self.rdata
            logger.debug("INPUT:  EOF (-1) from port 0x%08X", self.addr)
            self.rdata = 0xFFFFFFFF
            return self.rdata

        if size is MemSize.BYTE:
            raw_val = self.raw_mem[self.byte_aligner.byte_address(self.addr)]
        else:
            aligned = self.byte_aligner.word_address(self.addr)
            raw_val = int.from_bytes(self.raw_mem[aligned : aligned + 4], "little", signed=False)
        self.rdata = self.byte_aligner.align_read(raw_val, size)
        return self.rdata

    def write(
        self,
        addr: int,
        val: int,
        byte: bool = False,
        mem_size: MemSize | None = None,
        wdata_sel: WDataSelect = WDataSelect.STB_STW_DATA,
        splitted_data: int = 0,
    ) -> None:
        size = mem_size if mem_size is not None else (MemSize.BYTE if byte else MemSize.WORD)
        self.addr = addr & 0xFFFFFFFF
        self.mem_sel = self.address_decoder.decode(self.addr)

        stb_stw_data = self.byte_aligner.align_write_scalar(val, size)
        src_split = splitted_data if wdata_sel is WDataSelect.SPLITTED_DATA else val
        self.wdata = self.mux_wdata.select(stb_stw_data, src_split, wdata_sel)

        if self.mem_sel is MemoryTarget.STDOUT_DATA:
            b_val = self.wdata & 0xFF
            self.io_output_buffer.append(b_val)
            char_repr = chr(b_val) if 32 <= b_val <= 126 else f"\\x{b_val:02x}"
            curr_out = "".join(chr(b) if 32 <= b <= 126 else "." for b in self.io_output_buffer)
            logger.debug("OUTPUT: '%s' (%d) to port 0x%08X | buffer: '%s'", char_repr, b_val, self.addr, curr_out)
            return

        if size is MemSize.BYTE:
            self.raw_mem[self.byte_aligner.byte_address(self.addr)] = self.wdata & 0xFF
        else:
            aligned = self.byte_aligner.word_address(self.addr)
            self.raw_mem[aligned : aligned + 4] = (self.wdata & 0xFFFFFFFF).to_bytes(4, "little")
