"""Town map: dirt-only (letters a–d = Buch path variants, different clump salts)."""
from __future__ import annotations

MAP_W = 24
MAP_H = 20

# a = base dirt, b/c/d = other path tones (same tile pool, different regional variation)
_BASE_ROWS = [
    "aaaaaaaaaaaaaaaaaaaaaaaa",
    "aaaaaaaaaaaaaaaaaaaaaaaa",
    "aaaabbbbbbbbbbbaaaaaaaaa",
    "aaaabaaaaaaaabaaaaaaaaaa",
    "aaaabaaaaaaaabaaaaaaaaaa",
    "aaaabacccccaabaaaaaaaaaa",
    "aaaabacaaacaabaaaaaaaaaa",
    "aaaabacaaacaabaaaaaaaaaa",
    "aaaabacaaacaabaaaaaaaaaa",
    "aaaabaaccccaabaaaaaaaaaa",
    "aaaabaaaaaaaaaddddddddda",
    "aaaabbbbbbbbbbadddddddda",
    "aaaaaaaaaaaaaaadddddddda",
    "aaaaaaaaaaaaaaadddddddda",
    "aaaaaaaaaaaaaaadddddddda",
    "aaaaaaaaaaaaaaadddddddda",
    "aaaaaaaaaaaaaaadddddddda",
    "aaaaaaaaaaaaaaadddddddda",
    "aaaaaaaaaaaaaaaaaaaaaaaa",
    "aaaaaaaaaaaaaaaaaaaaaaaa",
]


def parse_world() -> list[list[str]]:
    return [list(row) for row in _BASE_ROWS]


def dirt_variant(ch: str) -> int:
    if "a" <= ch <= "d":
        return ord(ch) - ord("a")
    return 0


def blocks_movement(bx: int, by: int) -> bool:
    if bx < 0 or by < 0 or bx >= MAP_W or by >= MAP_H:
        return True
    return False
