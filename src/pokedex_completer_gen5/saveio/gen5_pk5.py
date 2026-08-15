from __future__ import annotations

import struct
from dataclasses import dataclass

PK5_BOXED_SIZE = 136
PK5_PARTY_SIZE = 220
ENCRYPTED_SIZE = 128
BLOCK_SIZE = 32
BLOCKS = 4
MAX_SPECIES_GEN5 = 649

BLOCK_ORDERS = [
    (0, 1, 2, 3),
    (0, 1, 3, 2),
    (0, 2, 1, 3),
    (0, 3, 1, 2),
    (0, 2, 3, 1),
    (0, 3, 2, 1),
    (1, 0, 2, 3),
    (1, 0, 3, 2),
    (2, 0, 1, 3),
    (3, 0, 1, 2),
    (2, 0, 3, 1),
    (3, 0, 2, 1),
    (1, 2, 0, 3),
    (1, 3, 0, 2),
    (2, 1, 0, 3),
    (3, 1, 0, 2),
    (2, 3, 0, 1),
    (3, 2, 1, 0),
    (1, 2, 3, 0),
    (1, 3, 2, 0),
    (2, 1, 3, 0),
    (3, 1, 2, 0),
    (2, 3, 1, 0),
    (3, 2, 1, 0),
]


@dataclass(frozen=True)
class ParsedPK5:
    is_empty: bool
    checksum_valid: bool
    species_id: int
    pid: int
    checksum: int
    raw_size: int

    @property
    def plausible_species(self) -> bool:
        return 1 <= self.species_id <= MAX_SPECIES_GEN5

    @property
    def usable(self) -> bool:
        return self.is_empty or (self.checksum_valid and self.plausible_species)


def lcrng_step(seed: int) -> int:
    return (seed * 0x41C64E6D + 0x6073) & 0xFFFFFFFF


def decrypt_words(encrypted: bytes, seed: int) -> bytes:
    out = bytearray(len(encrypted))
    for i in range(0, len(encrypted), 2):
        seed = lcrng_step(seed)
        word = struct.unpack_from("<H", encrypted, i)[0]
        dec = word ^ ((seed >> 16) & 0xFFFF)
        struct.pack_into("<H", out, i, dec)
    return bytes(out)


def unshuffle_blocks(pid: int, payload: bytes) -> bytes:
    shuffle_value = (pid >> 13) & 31
    order = BLOCK_ORDERS[shuffle_value % 24]
    blocks = [payload[i * BLOCK_SIZE : (i + 1) * BLOCK_SIZE] for i in range(BLOCKS)]
    logical = [b"" for _ in range(BLOCKS)]
    for physical_index, logical_index in enumerate(order):
        logical[logical_index] = blocks[physical_index]
    return b"".join(logical)


def checksum_words(payload: bytes) -> int:
    total = 0
    for i in range(0, len(payload), 2):
        total = (total + struct.unpack_from("<H", payload, i)[0]) & 0xFFFF
    return total


def parse_pk5(raw: bytes) -> ParsedPK5:
    if len(raw) not in (PK5_BOXED_SIZE, PK5_PARTY_SIZE):
        raise ValueError(f"Expected 136 boxed or 220 party bytes, got {len(raw)}")

    boxed = raw[:PK5_BOXED_SIZE]
    if boxed == bytes(PK5_BOXED_SIZE):
        return ParsedPK5(True, True, 0, 0, 0, len(raw))

    pid = struct.unpack_from("<I", boxed, 0)[0]
    checksum = struct.unpack_from("<H", boxed, 6)[0]
    encrypted = boxed[8:136]
    decrypted = decrypt_words(encrypted, checksum)
    unshuffled = unshuffle_blocks(pid, decrypted)
    calc_checksum = checksum_words(unshuffled)
    species_id = struct.unpack_from("<H", unshuffled, 0)[0]
    is_empty = pid == 0 and checksum == 0 and species_id == 0
    return ParsedPK5(
        is_empty=is_empty,
        checksum_valid=calc_checksum == checksum,
        species_id=species_id,
        pid=pid,
        checksum=checksum,
        raw_size=len(raw),
    )
