#!/usr/bin/env python3
"""直接读 ELF 程序头里的 PT_INTERP，打印其路径（没有则打印 NONE）。

给 test_t_coffee.sh 的 T1 断言用：比在 4.8 MB 产物上 grep 加载器名字更硬——
它读的是 ELF 程序头本身，而不是"文件里是否恰好出现某个字符串"。
用法: elf_interp_of.py <elf> ; 输出一行: <interpreter> 或 NONE 或 ERR:<原因>
"""
import struct
import sys

try:
    data = open(sys.argv[1], "rb").read()
except Exception as exc:  # noqa: BLE001
    print("ERR:%s" % exc)
    raise SystemExit(0)

if data[:4] != b"\x7fELF":
    print("NONE")
    raise SystemExit(0)
if data[4] != 2 or data[5] != 1:
    # 只处理 64 位小端 ELF；其它形态交由调用方的 grep 兜底
    print("ERR:not-elf64-le")
    raise SystemExit(0)

try:
    e_phoff, = struct.unpack_from("<Q", data, 32)
    e_phentsize, e_phnum = struct.unpack_from("<HH", data, 54)
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        (p_type,) = struct.unpack_from("<I", data, off)
        if p_type != 3:  # PT_INTERP
            continue
        p_offset, _vaddr, _paddr, p_filesz = struct.unpack_from("<QQQQ", data, off + 8)
        raw = data[p_offset:p_offset + p_filesz].split(b"\0", 1)[0]
        print(raw.decode("utf-8", "replace") or "NONE")
        raise SystemExit(0)
    print("NONE")
except Exception as exc:  # noqa: BLE001
    print("ERR:%s" % exc)
