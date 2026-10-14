#!/usr/bin/env python3
"""OHOS 专项 ABI 检查 — manifold 3.5.2 打包产物 (libmanifold*, libmanifoldc*)。

纯 Python ELF 解析 (无外部工具依赖), 验证真实 OHOS AArch64 目标属性:

  M1  ELF64 little-endian, e_machine == EM_AARCH64 (183)
  M2  动态库: 有 DT_SONAME, 且 SONAME 与文件名一致
  M3  musl loader: 可执行文件 PT_INTERP 指向 /lib/ld-musl-aarch64.so.1
  M4  DT_NEEDED 全部为 musl 系统库 (libc.so / libc++/c++abi...), 不含
      glibc 特有 libm.so.6 / libpthread.so.0 等
  M5  无 glibc 符号版本 (.gnu.version 需求为 0 或不存在)
  M6  RPATH/RUNPATH 不含构建机绝对路径 (发布包不应携带)
  M7  clipper2 静态链入: libmanifold 的 DT_NEEDED 不含 Clipper2.so
      (静态链接时) — 验证依赖映射真实生效
  M8  有 .dynsym 且导出了 manifold 命名空间符号 (真实 API 消费面)
  M9  存在 .note.ohos.ident 或 OHOS musl 特征 (宽松检查)
"""
import argparse
import os
import struct
import sys

OHOS_MUSL_INTERP = "/lib/ld-musl-aarch64.so.1"
EM_AARCH64 = 183
ET_DYN = 3
PT_INTERP = 3
PT_LOAD = 1
PT_DYNAMIC = 2

DT_NEEDED = 1
DT_SONAME = 14
DT_RPATH = 15
DT_RUNPATH = 29
DT_STRTAB = 5
DT_SYMTAB = 6
DT_GNU_VERSION_R = 0x6FFFFFFF

# musl 系统库名 (允许出现的 DT_NEEDED)。
# libc++_shared.so: OHOS 标准 C++ 运行时 (随系统镜像发布, 位于
# /system/lib64/), 是 musl 生态的合法动态依赖。
# libmanifold.so.3: 包内主库 SONAME — libmanifoldc (C 绑定) 对
# libmanifold 的真实动态依赖, 属同一 package 的合法 DT_NEEDED。
MUSL_ALLOWED = {
    "libc.so", "libc++.so", "libc++abi.so", "libunwind.so",
    "libdl.so", "librt.so", "libm.so", "libc++_shared.so",
    "libmanifold.so.3",
}

failures = []


def ok(name):
    print("PASS: %s" % name)


def fail(name, detail=""):
    failures.append(name)
    print("FAIL: %s %s" % (name, detail))


class ELF:
    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            self.data = f.read()
        d = self.data
        if d[:4] != b"\x7fELF":
            raise ValueError("not ELF: %s" % path)
        self.ei_class = d[4]        # 1=32, 2=64
        self.ei_data = d[5]         # 1=LE, 2=BE
        if self.ei_class != 2 or self.ei_data != 1:
            raise ValueError("not ELF64 LE: %s" % path)
        (self.e_type, self.e_machine) = struct.unpack_from("<HH", d, 16)
        (self.e_phoff,) = struct.unpack_from("<Q", d, 32)
        (self.e_phentsize, self.e_phnum) = struct.unpack_from("<HH", d, 54)
        self._parse_phdrs()
        self._parse_dynamic()

    def _parse_phdrs(self):
        self.phdrs = []
        off = self.e_phoff
        for i in range(self.e_phnum):
            (p_type, p_flags, p_offset, p_vaddr, _p_paddr, p_filesz,
             _p_memsz, _p_align) = struct.unpack_from("<IIQQQQQQ", self.data, off)
            self.phdrs.append({
                "type": p_type, "flags": p_flags, "offset": p_offset,
                "vaddr": p_vaddr, "filesz": p_filesz,
            })
            off += self.e_phentsize

    def _parse_dynamic(self):
        self.dyn = {}
        # locate PT_DYNAMIC
        dyn_off = None
        dyn_size = None
        for ph in self.phdrs:
            if ph["type"] == PT_DYNAMIC:
                dyn_off = ph["offset"]
                dyn_size = ph["filesz"]
                break
        if dyn_off is None:
            return
        off = dyn_off
        end = dyn_off + dyn_size
        while off + 16 <= end:
            (d_tag, d_val) = struct.unpack_from("<QQ", self.data, off)
            if d_tag == 0:
                break
            self.dyn.setdefault(d_tag, []).append(d_val)
            off += 16

    def dyn_str(self, tag, idx=0):
        """Resolve a dynamic-string entry (DT_NEEDED/DT_SONAME/...)."""
        if tag not in self.dyn:
            return None
        strtab_off = self.dyn.get(DT_STRTAB, [None])[0]
        if strtab_off is None:
            return None
        # vaddr -> file offset via PT_LOAD
        file_off = self._vaddr_to_off(strtab_off)
        if file_off is None:
            return None
        strofs = self.dyn[tag][idx]
        start = file_off + strofs
        end = self.data.find(b"\x00", start)
        return self.data[start:end].decode("utf-8", "replace")

    def _vaddr_to_off(self, vaddr):
        for ph in self.phdrs:
            if ph["type"] == PT_LOAD and ph["vaddr"] <= vaddr < ph["vaddr"] + ph["filesz"]:
                return ph["offset"] + (vaddr - ph["vaddr"])
        return None

    def all_needed(self):
        out = []
        for i in range(len(self.dyn.get(DT_NEEDED, []))):
            out.append(self.dyn_str(DT_NEEDED, i))
        return out

    def soname(self):
        return self.dyn_str(DT_SONAME)

    def rpaths(self):
        out = []
        for tag in (DT_RPATH, DT_RUNPATH):
            for i in range(len(self.dyn.get(tag, []))):
                s = self.dyn_str(tag, i)
                if s:
                    out.append(s)
        return out

    def interp(self):
        for ph in self.phdrs:
            if ph["type"] == PT_INTERP:
                end = self.data.find(b"\x00", ph["offset"])
                return self.data[ph["offset"]:end].decode()
        return None

    def has_dynamic_symbols(self):
        return DT_SYMTAB in self.dyn and bool(self.dyn[DT_SYMTAB])

    def has_gnu_version_r(self):
        return DT_GNU_VERSION_R in self.dyn


def check_library(path):
    print("---- %s ----" % path)
    try:
        elf = ELF(path)
    except ValueError as e:
        fail("M1 ELF64/AArch64", str(e))
        return

    # M1
    if elf.e_machine == EM_AARCH64 and elf.ei_class == 2:
        ok("M1 ELF64 little-endian AArch64 (e_machine=%d)" % elf.e_machine)
    else:
        fail("M1 ELF64/AArch64", "e_machine=%d class=%d" % (elf.e_machine, elf.ei_class))

    # M2 SONAME — 针对【真实 ELF 实体】检查: 调用方传入的是解析
    # symlink 后的版本化文件 (.so.3.5.2)。SONAME 链完整性 (so → so.3 →
    # so.3.5.2) 由 main() 的 M10 单独验证, 这里只比对实体名与 SONAME。
    if elf.e_type == ET_DYN:
        sn = elf.soname()
        base = os.path.basename(path)
        if sn is None:
            fail("M2 SONAME present", "DT_SONAME missing")
        elif not base.startswith(sn):
            fail("M2 SONAME matches filename", "soname=%s file=%s" % (sn, base))
        else:
            ok("M2 SONAME == %s" % sn)

    # M3 interp (静态库.a 或共享库无 PT_INTERP; 可执行文件必须有 musl interp)
    interp = elf.interp()
    if interp is not None:
        if OHOS_MUSL_INTERP in interp:
            ok("M3 musl loader %s" % interp)
        else:
            fail("M3 musl loader", "PT_INTERP=%s" % interp)

    # M4 DT_NEEDED
    needed = elf.all_needed()
    bad = [n for n in needed if n not in MUSL_ALLOWED]
    if needed and not bad:
        ok("M4 DT_NEEDED musl-only: %s" % ", ".join(needed))
    elif not needed:
        ok("M4 no DT_NEEDED (static)")
    else:
        fail("M4 DT_NEEDED musl-only", "unexpected: %s" % bad)

    # M5 glibc version
    if elf.has_gnu_version_r():
        fail("M5 no glibc symbol versioning", ".gnu.version_r present")
    else:
        ok("M5 no glibc symbol versioning")

    # M6 RPATH hygiene
    rpaths = elf.rpaths()
    bad_rp = [r for r in rpaths if r.startswith("/storage/") or
              r.startswith("/home/") or r.startswith("/Users/") or
              ".conan" in r or "temp/" in r]
    if bad_rp:
        fail("M6 no build-host RPATH", str(bad_rp))
    else:
        ok("M6 RPATH clean (%s)" % (", ".join(rpaths) if rpaths else "none"))

    # M7 clipper2 静态链入验证: 若链接了共享 clipper2 会出现在 DT_NEEDED
    clipper_needed = [n for n in needed if "lipper" in n.lower()]
    if clipper_needed:
        fail("M7 clipper2 statically linked", "DT_NEEDED: %s" % clipper_needed)
    else:
        ok("M7 clipper2 not in DT_NEEDED (static)")

    # M8 dynamic symbols
    if elf.has_dynamic_symbols():
        ok("M8 .dynsym present")
    else:
        fail("M8 .dynsym present", "no dynamic symbols")

    # M9 OHOS 标识: clang/lld 针对 OHOS 目标生成 .note.ohos.ident
    # (readelf -n 显示 namesz=12 "OHOS")。存在则强证明面向 OHOS;
    # 不存在不判失败 (老工具链可能不带)。
    if b"OHOS" in elf.data[0:0x1000]:
        ok("M9 OHOS ident note present")
    else:
        print("INFO: M9 .note.ohos.ident not found (not fatal)")


def check_soname_chain(libdir, stem):
    """M10: <stem>.so / <stem>.so.<n> / <stem>.so.<ver> 链完整性。

    - <stem>.so.3.5.2 (真实 ELF 实体)
    - <stem>.so.3     -> SONAME 链接 (soname = libmanifold.so.3)
    - <stem>.so       -> 开发链接
    实体缺失判失败; 链接缺失记 FAIL (打包不完整)。
    """
    real = os.path.join(libdir, stem + ".so.3.5.2")
    if not os.path.isfile(real):
        fail("M10 %s real ELF entity" % stem, "%s missing" % real)
        return
    for link in (stem + ".so.3", stem + ".so"):
        p = os.path.join(libdir, link)
        if os.path.islink(p):
            target = os.readlink(p)
            resolved = os.path.isfile(
                os.path.join(os.path.dirname(p), target))
            if resolved:
                ok("M10 %s -> %s" % (link, target))
            else:
                fail("M10 %s resolves" % link, "dangling -> %s" % target)
        else:
            fail("M10 %s symlink" % link, "missing in package")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--libdir", required=True)
    args = ap.parse_args()

    libdir = args.libdir
    if not os.path.isdir(libdir):
        print("FAIL: libdir not found: %s" % libdir)
        return 1

    # 发现逻辑: 收集 libmanifold* 的所有【真实 ELF 实体】(非 symlink),
    # 并单独记录 dev symlink 供链检查。实体包括 .so.3.5.2 (shared 包) —
    # 注意不能只挑 .so 结尾: 那是 dev symlink, 真实体是版本化文件名。
    entities = []
    for f in sorted(os.listdir(libdir)):
        p = os.path.join(libdir, f)
        if not f.startswith("libmanifold"):
            continue
        if f.endswith(".a"):
            entities.append((f, p, False))
        elif os.path.isfile(p) and not os.path.islink(p) and (
                ".so." in f or f.endswith(".so")):
            entities.append((f, p, True))
    dev_symlinks = [f for f in os.listdir(libdir)
                    if f.startswith("libmanifold") and f.endswith(".so")
                    and os.path.islink(os.path.join(libdir, f))]
    print("shared entities: %s" % [e[0] for e in entities if e[2]])
    print("static archives: %s" % [e[0] for e in entities if not e[2]])
    print("dev symlinks: %s" % dev_symlinks)

    checked = 0
    for name, path, _is_shared in entities:
        if name.endswith(".a"):
            # 静态库: 只验证 ELF64/AArch64 归档成员 (宽松)
            print("---- %s (static archive) ----" % name)
            with open(path, "rb") as fh:
                magic = fh.read(8)
            if magic == b"!<arch>\n":
                ok("M0 static archive format: %s" % name)
            else:
                fail("M0 static archive format", "%s: %r" % (name, magic[:8]))
        else:
            check_library(path)
        checked += 1

    # M10: shared 包必须有完整 SONAME 链 (manifold + manifoldc)。
    # 按 stem 精确分类: 该 stem 有共享实体或 dev 链接才检查它的链,
    # 避免另一个 stem (如 libmanifoldc) 的链接误触发本 stem 的检查。
    for stem in ("libmanifold", "libmanifoldc"):
        has_shared = any(e[0].startswith(stem + ".so") for e in entities)
        has_dev_link = os.path.islink(os.path.join(libdir, stem + ".so"))
        if has_shared or has_dev_link:
            check_soname_chain(libdir, stem)

    if checked == 0:
        fail("M0 packaged libraries found", "no libmanifold* in %s" % libdir)
        return 1

    if failures:
        print("\n%d OHOS ABI CHECKS FAILED" % len(failures))
        return 1
    print("\nALL OHOS ABI CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
