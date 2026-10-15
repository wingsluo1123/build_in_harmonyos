#!/usr/bin/env python3
"""Patch sandbox test.dtb: set /<node> status to "okay" for staging runs.

test.dts marks mmc4..mmc10 status="disabled"; the bootstd ut tests bind
them programmatically (lists_bind_fdt), but a plain u-boot shell run
cannot address them.

KEY QUIRK: u-boot's bundled dtc fork serialises string-valued props
INLINE (the property data holds the string itself, not a strings-block
offset), because u-boot's ofnode_read_string() returns fdt_getprop()
raw. Property NAMES are normal strings-block offsets; only VALUES are
inline. Hence the patch is an in-place overwrite: "okay\\0" replaces the
head of "disabled\\0" (value keeps its 9-byte length; the 4 stale tail
bytes are ignored by readers that stop at the NUL).

With --stick-name NAME the sandbox,filepath of every usb flash-stick
node is overwritten with NAME. sandbox_flash_bind() reads it through
dev_read_string(), so the stale tail after the new NUL is ignored. All
three sticks pointing at one file makes the usb storage device INDEX
irrelevant: sandbox enumerates the sticks in an order that is NOT stable
across runs (observed dev0 = flash1.img / testflash2.bin / testflash.bin
in different runs), so a fixed "usb read" device number is a coin flip.
NAME must be <= the shortest existing value ("flash1.img", 10 chars).

Usage: python3 patch-dtb.py <in.dtb> <out.dtb> [node ...]
                              [--stick-name NAME]
"""
import struct
import sys

FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9


def align4(n):
    return (n + 3) & ~3


def patch(in_path, out_path, nodes, stick_name=None):
    blob = bytearray(open(in_path, 'rb').read())
    (magic, total, off_struct, off_strings, off_memrsv, ver, lcv,
     bootcpuid, size_strings, size_struct) = struct.unpack('>10I',
                                                           blob[:40])
    assert magic == 0xd00dfeed, 'bad fdt magic'
    structb = bytearray(blob[off_struct:off_struct + size_struct])
    sb = blob[off_strings:off_strings + size_strings]

    def string_at(off):
        end = sb.index(b'\x00', off)
        return sb[off:end].decode('ascii')

    pos = 0
    path = []
    hits = {}
    stick_hits = []
    while pos < len(structb):
        tok = struct.unpack_from('>I', structb, pos)[0]
        pos += 4
        if tok == FDT_BEGIN_NODE:
            end = structb.index(b'\x00', pos)
            name = bytes(structb[pos:end]).decode('ascii')
            path.append(name)
            pos = align4(end + 1)
        elif tok == FDT_END_NODE:
            path.pop()
        elif tok == FDT_PROP:
            ln, nameoff = struct.unpack_from('>II', structb, pos)
            data = pos + 8
            pname = string_at(nameoff)
            if pname == 'status' and len(path) == 2 and \
                    path[0] == '' and path[1] in nodes:
                hits[path[1]] = data
            elif pname == 'sandbox,filepath' and path and \
                    path[-1].startswith('flash-stick'):
                stick_hits.append((path[-1], data, ln))
            pos = align4(data + ln)
        elif tok == FDT_NOP:
            pass
        elif tok == FDT_END:
            break
        else:
            raise ValueError(f'unknown token {tok:#x} at {pos - 4}')

    for node in nodes:
        assert node in hits, f'/{node}/status not found'
        hit = hits[node]
        old = bytes(structb[hit:hit + 9])
        assert old[:9] == b'disabled\x00', f'{node} status = {old!r}'
        structb[hit:hit + 5] = b'okay\x00'

    if stick_name:
        assert len(stick_hits) == 3, \
            f'expected 3 flash-stick filepaths, got {len(stick_hits)}'
        newval = stick_name.encode('ascii') + b'\x00'
        for name, data, ln in stick_hits:
            assert ln >= len(newval), \
                f'{name} filepath slot {ln}B < {len(newval)}B'
            old = bytes(structb[data:data + ln]).split(b'\x00')[0]
            structb[data:data + len(newval)] = newval
            print(f'patch-dtb: {name} sandbox,filepath '
                  f'{old.decode()} -> {stick_name}')

    blob[off_struct:off_struct + size_struct] = structb

    open(out_path, 'wb').write(bytes(blob))
    print(f'patch-dtb: {", ".join("/" + n for n in nodes)} '
          f'status disabled -> okay (in-place, {total} bytes)')


if __name__ == '__main__':
    args = sys.argv[3:]
    stick = None
    if '--stick-name' in args:
        i = args.index('--stick-name')
        stick = args[i + 1]
        del args[i:i + 2]
    nodes = args if args else ([] if stick else ['mmc4'])
    patch(sys.argv[1], sys.argv[2], nodes, stick)
