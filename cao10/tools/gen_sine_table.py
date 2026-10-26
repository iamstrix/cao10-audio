"""Generate exactly the same binary32 sine constants for NASM and C."""
import math
import struct
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
bits = [struct.unpack('<I', struct.pack('<f', math.sin(2*math.pi*i/256)))[0] for i in range(256)]
(ROOT/'engine/sine_table.inc').write_text('\n'.join(f'    dd 0x{x:08x}' for x in bits)+'\n')
(ROOT/'ref/sine_table.h').write_text('static const uint32_t sine_bits[256] = {\n'+','.join(f'0x{x:08x}u' for x in bits)+'\n};\n')
