from __future__ import annotations

import logging
from enum import Enum
from typing import overload

from src.isa import MEM_SIZE, STDIN_DATA, STDOUT_DATA

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


class AddressDecoder:
    ADDR = "ADDR"
    MEM_READ = "MEM_READ"
    MEM_WRITE = "MEM_WRITE"

    @staticmethod
    def decode(addr: int) -> MemoryTarget:
        clean_addr = addr & 0xFFFFFFFF
        if clean_addr == STDIN_DATA:
            return MemoryTarget.STDIN_DATA
        if clean_addr == STDOUT_DATA:
            return MemoryTarget.STDOUT_DATA
        return MemoryTarget.RAM


class ByteAligner:
    MEM_SIZE = "MEM_SIZE"

    @staticmethod
    def word_address(addr: int) -> int:
        return addr & 0xFFFFFFFC

    @staticmethod
    def byte_address(addr: int) -> int:
        return addr & 0xFFFFFFFF


class MuxWData:
    WDATA_SEL = "WDATA_SEL"

    @staticmethod
    def select(stb_stw_data: int, split_data: int, byte: bool) -> int:
        return stb_stw_data if byte else split_data


class Memory:
    raw_mem: SparseMemory
    io_input_buffer: list[int]
    io_output_buffer: list[int]

    def __init__(self, size: int = MEM_SIZE) -> None:
        self.raw_mem = SparseMemory(size)
        self.io_input_buffer = []
        self.io_output_buffer = []
        self.address_decoder = AddressDecoder()
        self.byte_aligner = ByteAligner()
        self.mux_wdata = MuxWData()
        self.addr = 0
        self.rdata = 0
        self.wdata = 0

    def read(self, addr: int, byte: bool = False) -> int:
        self.addr = addr & 0xFFFFFFFF
        clean_addr = addr & 0xFFFFFFFF
        target = self.address_decoder.decode(clean_addr)
        if target is MemoryTarget.STDIN_DATA:
            if self.io_input_buffer:
                val = self.io_input_buffer.pop(0)
                char_repr = chr(val) if 32 <= val <= 126 else f"\\x{val:02x}"
                logger.debug("INPUT:  '%s' (%d) from port 0x%08X", char_repr, val, clean_addr)
                self.rdata = val
                return self.rdata
            logger.debug("INPUT:  EOF (-1) from port 0x%08X", clean_addr)
            self.rdata = 0xFFFFFFFF
            return self.rdata

        ram_addr = self.byte_aligner.byte_address(clean_addr)
        if byte:
            self.rdata = self.raw_mem[ram_addr]
            return self.rdata
        aligned = self.byte_aligner.word_address(ram_addr)
        self.rdata = int.from_bytes(self.raw_mem[aligned : aligned + 4], "little", signed=False)
        return self.rdata

    def write(self, addr: int, val: int, byte: bool = False) -> None:
        self.addr = addr & 0xFFFFFFFF
        self.wdata = self.mux_wdata.select(val & 0xFF, val, byte)
        clean_addr = addr & 0xFFFFFFFF
        target = self.address_decoder.decode(clean_addr)
        if target is MemoryTarget.STDOUT_DATA:
            b_val = val & 0xFF
            self.io_output_buffer.append(b_val)
            char_repr = chr(b_val) if 32 <= b_val <= 126 else f"\\x{b_val:02x}"
            curr_out = "".join(chr(b) if 32 <= b <= 126 else "." for b in self.io_output_buffer)
            logger.debug("OUTPUT: '%s' (%d) to port 0x%08X | buffer: '%s'", char_repr, b_val, clean_addr, curr_out)
            return

        ram_addr = self.byte_aligner.byte_address(clean_addr)
        if byte:
            self.raw_mem[ram_addr] = self.wdata
        else:
            aligned = self.byte_aligner.word_address(ram_addr)
            self.raw_mem[aligned : aligned + 4] = (self.wdata & 0xFFFFFFFF).to_bytes(4, "little")
