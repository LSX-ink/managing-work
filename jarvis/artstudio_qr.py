"""QR codes made on this PC in pure Python (ISO/IEC 18004): byte mode, versions 1 to 10, error correction level M.

The text is packed into codewords, Reed-Solomon error correction is added over GF(256), the blocks are interleaved
and placed in the zigzag, and the mask with the lowest penalty is chosen. The picture is saved as a PNG in a memory
folder (Ideas by default) and pops up. Nothing is sent anywhere.
"""

import re

from PIL import Image

import artstudio_common as ac
import screen
from config import Settings

# Error correction level M, per version: (EC codewords per block, [(blocks, data codewords per block), ...]).
BLOCKS_M = {
    1: (10, [(1, 16)]), 2: (16, [(1, 28)]), 3: (26, [(1, 44)]), 4: (18, [(2, 32)]), 5: (24, [(2, 43)]),
    6: (16, [(4, 27)]), 7: (18, [(4, 31)]), 8: (22, [(2, 38), (2, 39)]), 9: (22, [(3, 36), (2, 37)]),
    10: (26, [(4, 43), (1, 44)]),
}
ALIGNMENT = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42],
             9: [6, 26, 46], 10: [6, 28, 50]}
FORMAT_M = 0b00  # the level M bits in the format information
MAX_VERSION = 10

# GF(256) with the QR polynomial x^8 + x^4 + x^3 + x^2 + 1.
EXP = [0] * 512
LOG = [0] * 256
_x = 1
for _i in range(255):
    EXP[_i], LOG[_x] = _x, _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    EXP[_i] = EXP[_i - 255]


def gf_mul(a: int, b: int) -> int:
    return 0 if a == 0 or b == 0 else EXP[LOG[a] + LOG[b]]


def rs_generator(degree: int) -> list[int]:
    """Coefficients (highest power first, leading 1) of (x - a^0)(x - a^1)...(x - a^(degree-1))."""
    poly = [1]
    for i in range(degree):
        poly = [a ^ gf_mul(b, EXP[i]) for a, b in zip(poly + [0], [0] + poly)]
    return poly


def rs_remainder(data: list[int], degree: int) -> list[int]:
    """The error correction codewords for one block."""
    gen = rs_generator(degree)
    rem = [0] * degree
    for byte in data:
        factor = byte ^ rem[0]
        rem = rem[1:] + [0]
        for i in range(degree):
            rem[i] ^= gf_mul(gen[i + 1], factor)
    return rem


def capacity(version: int) -> int:
    return sum(n * size for n, size in BLOCKS_M[version][1])


def size_of(version: int) -> int:
    return 17 + 4 * version


def pick_version(length: int) -> int:
    for v in range(1, MAX_VERSION + 1):
        count_bits = 8 if v <= 9 else 16
        if 4 + count_bits + 8 * length <= capacity(v) * 8:
            return v
    raise ValueError(f"That's too long for a QR code; keep it under {capacity(MAX_VERSION) - 3} characters.")


def data_codewords(payload: bytes, version: int) -> list[int]:
    """Mode, length, the bytes, terminator and padding, as codewords."""
    bits = [0, 1, 0, 0]
    count_bits = 8 if version <= 9 else 16
    bits += [(len(payload) >> i) & 1 for i in range(count_bits - 1, -1, -1)]
    for byte in payload:
        bits += [(byte >> i) & 1 for i in range(7, -1, -1)]
    total = capacity(version) * 8
    bits += [0] * min(4, total - len(bits))
    bits += [0] * (-len(bits) % 8)
    words = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    pad = 0xEC
    while len(words) < capacity(version):
        words.append(pad)
        pad ^= 0xEC ^ 0x11
    return words


def interleave(words: list[int], version: int) -> list[int]:
    """Split into blocks, add error correction to each, and interleave them."""
    ec_len, groups = BLOCKS_M[version]
    blocks, i = [], 0
    for count, size in groups:
        for _ in range(count):
            blocks.append(words[i:i + size])
            i += size
    ecs = [rs_remainder(b, ec_len) for b in blocks]
    out = [b[n] for n in range(max(len(b) for b in blocks)) for b in blocks if n < len(b)]
    return out + [e[n] for n in range(ec_len) for e in ecs]


def format_bits(mask: int) -> int:
    data = FORMAT_M << 3 | mask
    rem = data
    for _ in range(10):
        rem = (rem << 1) ^ ((rem >> 9) * 0x537)
    return (data << 10 | rem) ^ 0x5412


def version_bits(version: int) -> int:
    rem = version
    for _ in range(12):
        rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
    return version << 12 | rem


class Grid:
    """The module grid (grid[y][x], True is dark) and which modules belong to the fixed patterns."""

    def __init__(self, version: int):
        self.version, self.size = version, size_of(version)
        self.dark = [[False] * self.size for _ in range(self.size)]
        self.fixed = [[False] * self.size for _ in range(self.size)]
        self.draw_patterns()

    def set(self, x: int, y: int, dark: bool) -> None:
        self.dark[y][x] = dark
        self.fixed[y][x] = True

    def draw_patterns(self) -> None:
        n = self.size
        for i in range(n):
            self.set(6, i, i % 2 == 0)
            self.set(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (n - 4, 3), (3, n - 4)):
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < n and 0 <= y < n:
                        ring = max(abs(dx), abs(dy))
                        self.set(x, y, ring not in (2, 4))
        spots = ALIGNMENT[self.version]
        for a in spots:
            for b in spots:
                if (a, b) in ((6, 6), (6, spots[-1]), (spots[-1], 6)):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self.set(a + dx, b + dy, max(abs(dx), abs(dy)) != 1)
        self.draw_format(0)
        self.draw_version()

    def draw_format(self, mask: int) -> None:
        n, bits = self.size, format_bits(mask)
        bit = lambda i: (bits >> i) & 1 == 1  # noqa: E731
        for i in range(6):
            self.set(8, i, bit(i))
        self.set(8, 7, bit(6))
        self.set(8, 8, bit(7))
        self.set(7, 8, bit(8))
        for i in range(9, 15):
            self.set(14 - i, 8, bit(i))
        for i in range(8):
            self.set(n - 1 - i, 8, bit(i))
        for i in range(8, 15):
            self.set(8, n - 15 + i, bit(i))
        self.set(8, n - 8, True)  # the dark module

    def draw_version(self) -> None:
        if self.version < 7:
            return
        bits = version_bits(self.version)
        for i in range(18):
            dark = (bits >> i) & 1 == 1
            a, b = self.size - 11 + i % 3, i // 3
            self.set(a, b, dark)
            self.set(b, a, dark)

    def place(self, codewords: list[int]) -> None:
        n, i, total = self.size, 0, len(codewords) * 8
        right = n - 1
        while right >= 1:
            if right == 6:
                right = 5
            upward = (right + 1) & 2 == 0
            for vert in range(n):
                y = n - 1 - vert if upward else vert
                for x in (right, right - 1):
                    if not self.fixed[y][x] and i < total:
                        self.dark[y][x] = (codewords[i >> 3] >> (7 - (i & 7))) & 1 == 1
                        i += 1
            right -= 2

    def apply_mask(self, mask: int) -> None:
        rule = MASKS[mask]
        for y in range(self.size):
            for x in range(self.size):
                if not self.fixed[y][x] and rule(y, x):
                    self.dark[y][x] = not self.dark[y][x]


MASKS = [
    lambda i, j: (i + j) % 2 == 0,
    lambda i, j: i % 2 == 0,
    lambda i, j: j % 3 == 0,
    lambda i, j: (i + j) % 3 == 0,
    lambda i, j: (i // 2 + j // 3) % 2 == 0,
    lambda i, j: (i * j) % 2 + (i * j) % 3 == 0,
    lambda i, j: ((i * j) % 2 + (i * j) % 3) % 2 == 0,
    lambda i, j: ((i + j) % 2 + (i * j) % 3) % 2 == 0,
]
FINDER_LIKE = ([1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0], [0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1])


def penalty(dark: list[list[bool]]) -> int:
    """The four penalty rules of the standard (lower is easier to scan)."""
    n = len(dark)
    lines = [row for row in dark] + [[dark[y][x] for y in range(n)] for x in range(n)]
    score = 0
    for line in lines:
        run = 1
        for a, b in zip(line, line[1:]):
            if a == b:
                run += 1
            else:
                score += run - 2 if run >= 5 else 0
                run = 1
        score += run - 2 if run >= 5 else 0
        ints = [int(v) for v in line]
        score += 40 * sum(ints[k:k + 11] in FINDER_LIKE for k in range(n - 10))
    score += 3 * sum(dark[y][x] == dark[y][x + 1] == dark[y + 1][x] == dark[y + 1][x + 1]
                     for y in range(n - 1) for x in range(n - 1))
    percent = sum(map(sum, dark)) * 100 / (n * n)
    score += 10 * int(abs(percent - 50) // 5)
    return score


def encode(text: str, mask: int | None = None) -> list[list[bool]]:
    """The QR code for text as rows of modules (True is dark), without the quiet zone."""
    payload = str(text).encode("utf-8")
    if not payload:
        raise ValueError("What should the QR code say?")
    version = pick_version(len(payload))
    codewords = interleave(data_codewords(payload, version), version)
    best = None
    for m in ([mask] if mask is not None else range(8)):
        grid = Grid(version)
        grid.place(codewords)
        grid.apply_mask(m)
        grid.draw_format(m)
        score = penalty(grid.dark)
        if best is None or score < best[0]:
            best = (score, grid)
    return best[1].dark


def image(matrix: list[list[bool]], scale: int = 10, border: int = 4) -> Image.Image:
    n = len(matrix)
    im = Image.new("1", (n + 2 * border, n + 2 * border), 1)
    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            if dark:
                im.putpixel((x + border, y + border), 0)
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST).convert("RGB")


def make(settings: Settings, text: str, save_to: str = "", name: str = "") -> screen.Shown:
    matrix = encode(text)
    target = ac.save_new(settings, image(matrix), save_to, name or "QR " + re.sub(r"[^\w.-]+", " ", text)[:30].strip())
    return screen.Shown(f"Here's the QR code, saved as {target.name}.", screen.file_card(settings, target))


def tool_definitions() -> list[dict]:
    return [{
        "name": "art_qr_code",
        "description": "Make a QR code picture for a link, Wi-Fi details or any text (up to about 200 characters), "
                       "made on this PC. It's saved as a PNG in a memory folder (Ideas by default) and pops up.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "What the QR code says, e.g. a web link."},
                "save_to": {"type": "string", "description": "Memory folder to save into (default Ideas)."},
                "name": {"type": "string", "description": "File name for the picture."},
            },
            "required": ["text"],
            "additionalProperties": False,
        },
    }]


NAMES = {"art_qr_code"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> screen.Shown:
    return make(settings, str(args.get("text") or "").strip(), args.get("save_to") or "", args.get("name") or "")
