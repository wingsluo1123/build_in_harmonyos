#!/usr/bin/env python3
"""openvdb 13.0.0 消费者测试（真实编译+链接；原生构建下真实执行）。

为什么本机（交叉编译）不执行二进制：
  · OHOS SDK 不随附设备端 musl 动态加载器 ld-musl-aarch64.so.1；
  · 本机 QEMU 执行**动态** aarch64 OHOS 产物必然段错误（实测连
    hello-world 都 segfault，QEMU 8.2.2 + OHOS musl）；
  · 依赖 tbb 的制品仓包**只提供共享库**（libtbb.so，无 libtbb.a），
    因此消费者无法做成全静态二进制。
  → 交叉编译时只做「编译+链接+符号+架构」验证（真实链接，非空壳）；
    设备端原生构建（官方 CI aarch64 worker）则真实执行并校验输出。

**ELF 检查不依赖外部工具**（2026-09-28 修复）：
  原实现在 CI 上崩于 `FileNotFoundError: 'readelf'`——CI worker（OHOS 环境）的
  PATH 里没有 readelf/nm。现在架构与 INTERP 判定改为**纯 Python 解析 ELF 头/程序头**，
  符号判定优先用 nm 家族工具（PATH → SDK/HNP 目录自动定位），拿不到工具时回退为
  **纯 Python 解析 .symtab 并按 mangled 片段匹配**。任何缺失都不会再让脚本异常退出。

用法（由 test_package/conanfile.py 调用）：
  python3 test_openvdb.py --pkg <pkg_folder> --cxx <compiler> [--cross]
                          --include=<dir> --libdir=<dir> --lib=<name> ...
"""
import argparse
import glob
import os
import shutil
import struct
import subprocess
import sys
import tempfile

PASS, FAIL, NOTE = "PASS:", "FAIL:", "NOTE:"
_failures = 0
_checks = 0

EM_AARCH64 = 0xB7          # ELF e_machine for AArch64
PT_INTERP = 3              # program header type for the dynamic loader
SHT_SYMTAB = 2
SHN_UNDEF = 0

# openvdb 使用版本化内联命名空间 openvdb::v13_0；FloatGrid 是 typedef 而非符号，
# 故取真实的类型/函数符号。demangled 与 mangled 两种形态都列出来
# （Itanium ABI：长度前缀按字符数，openvdb=7、v13_0=5）：
#   openvdb::v13_0::GridBase         -> _ZN7openvdb5v13_08GridBase...
#   openvdb::v13_0::Grid<            -> _ZN7openvdb5v13_04GridI...
#   openvdb::v13_0::tree::Tree<      -> _ZN7openvdb5v13_04tree4TreeI...
#   openvdb::v13_0::math::Transform  -> _ZN7openvdb5v13_04math9Transform...
WANTED_SYMBOLS = [
    ("openvdb::v13_0::GridBase", "7openvdb5v13_08GridBase"),
    ("openvdb::v13_0::Grid<", "7openvdb5v13_04GridI"),
    ("openvdb::v13_0::tree::Tree<", "7openvdb5v13_04tree4TreeI"),
    ("openvdb::v13_0::math::Transform", "7openvdb5v13_04math9Transform"),
]


def check(ok, what, extra=""):
    global _failures, _checks
    _checks += 1
    if ok:
        print(f"{PASS} {what}")
    else:
        _failures += 1
        print(f"{FAIL} {what}{(' — ' + extra) if extra else ''}")
    return ok


class _Result:
    """subprocess.run 的最小替身：工具不存在时用它兜底，避免整个测试脚本崩溃。"""

    def __init__(self, returncode=127, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def run(cmd, timeout=1800, extra_env=None):
    """执行外部命令；**任何** OSError（含 FileNotFoundError）都降级为 rc=127。

    extra_env：为子进程追加环境变量（例如执行消费者二进制时显式注入 LD_LIBRARY_PATH ——
    设备端不能假定运行环境已经带上了依赖库目录，CI #63842 实测报
    `Error loading shared library libtbb.so`）。
    """
    env = None
    if extra_env:
        env = dict(os.environ)
        for k, v in extra_env.items():
            if k == "LD_LIBRARY_PATH" and os.environ.get(k):
                v = v + os.pathsep + os.environ[k]
            env[k] = v
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    except FileNotFoundError as exc:
        print(f"{NOTE} 外部工具不可用：{exc}（已降级，不判失败）")
        return _Result(stderr=str(exc))
    except subprocess.TimeoutExpired:
        print(f"{NOTE} 命令超时：{' '.join(map(str, cmd))[:120]}")
        return _Result(returncode=124, stderr="timeout")
    except OSError as exc:
        print(f"{NOTE} 命令执行失败：{exc}")
        return _Result(stderr=str(exc))


def runtime_library_path(pkg, libdirs, extra=()):
    """构造执行消费者二进制时使用的 LD_LIBRARY_PATH（去重、保持顺序）。

    消费者动态链接依赖库（如 tbb 的 libtbb.so），而设备端（OHOS）上的库搜索路径
    不能假定已被 conanrun 配置好 → 显式注入。
    """
    cand = [os.path.join(pkg, "lib")] + list(libdirs) + list(extra) + ["/system/lib64", "/system/lib"]
    out = []
    for d in cand:
        if d and d not in out:
            out.append(d)
    return os.pathsep.join(out)


# ────────────────────────── 工具定位 ──────────────────────────

def _ohos_dirs(cxx=None):
    """OHOS 专属的工具/编译器目录（HNP、SDK、给定编译器所在目录）。"""
    dirs = []
    if cxx:
        dirs.append(os.path.dirname(os.path.realpath(cxx)))
    # CI worker 的编译器目录（profile 里就是绝对路径 /data/service/hnp/bin/clang++）
    dirs.append("/data/service/hnp/bin")
    for env in ("OHOS_SDK", "OHOS_SDK_NATIVE", "OHOS_SDK_ROOT", "HMBS_OHOS_SDK"):
        v = os.environ.get(env)
        if v:
            dirs += [os.path.join(v, "native", "llvm", "bin"),
                     os.path.join(v, "llvm", "bin"), os.path.join(v, "bin")]
    for pat in ("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin",
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin",
                "/data/service/hnp/*/ohos/native/llvm/bin",
                "/data/service/hnp/*/*/ohos/native/llvm/bin",
                "/data/service/hnp/*/llvm/bin",
                "/data/service/hnp/*/*/llvm/bin"):
        dirs += sorted(glob.glob(pat), reverse=True)
    return dirs


def _candidate_dirs(cxx=None):
    """全部候选目录：OHOS 专属目录优先，然后系统目录。"""
    dirs = _ohos_dirs(cxx) + ["/system/bin", "/vendor/bin", "/usr/local/bin", "/usr/bin", "/bin"]
    out = []
    for d in dirs:
        if d and os.path.isdir(d) and d not in out:
            out.append(d)
    return out


def _first_tool_in(dirs, names):
    for d in dirs:
        for name in names:
            p = os.path.join(d, name)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
    return None


def compiler_triple(cxx):
    """`<cxx> -dumpmachine` 的目标三元组（失败返回空串）。"""
    r = run([cxx, "-dumpmachine"], timeout=60)
    return (r.stdout or "").strip()


def _is_ohos_target(cxx):
    triple = compiler_triple(cxx).lower()
    return ("ohos" in triple) or triple.startswith("aarch64")


def find_compiler(cxx):
    """把 --cxx 解析成**可执行**的 C++ 编译器绝对路径。

    优先级（关键：OHOS 专属目录排在宿主机 PATH 之前，且要用目标三元组校验，
    否则裸名可能抓到宿主编译器，产出**错误目标架构**的产物，
    表现为链接期 "skipping incompatible ... libtbb.so"）：
      1) 原样（存在且可执行）—— CI profile 给的就是 /data/service/hnp/bin/clang++，直接信任
      2) OHOS 专属目录（HNP / $OHOS_SDK / SDK glob）里**目标三元组含 ohos/aarch64** 的 clang++/g++/c++/clang
      3) PATH（shutil.which），同样做三元组校验
      4) $CXX / $CC
      5) 系统目录兜底（不再校验，仅保证“有编译器可用”）
    找不到时返回 None（调用方只打印 NOTE，不抛异常）。
    """
    if cxx and os.path.isfile(cxx) and os.access(cxx, os.X_OK):
        return cxx
    names = ("clang++", "g++", "c++", "clang")
    for d in _ohos_dirs(cxx):
        for name in names:
            p = os.path.join(d, name)
            if os.path.isfile(p) and os.access(p, os.X_OK) and _is_ohos_target(p):
                return p
    if cxx:
        found = shutil.which(cxx)
        if found and _is_ohos_target(found):
            return found
    for env in ("CXX", "CC"):
        v = os.environ.get(env)
        if v:
            for cand in (v, shutil.which(v) or ""):
                if cand and os.path.isfile(cand) and os.access(cand, os.X_OK) and _is_ohos_target(cand):
                    return cand
    # 兜底：任何可用的编译器（可能不是 OHOS 目标，调用方会打印 NOTE 说明）
    fb = _first_tool_in(_ohos_dirs(cxx), names)
    if fb:
        return fb
    if cxx:
        fb = shutil.which(cxx)
        if fb:
            return fb
    return _first_tool_in(["/system/bin", "/vendor/bin", "/usr/local/bin", "/usr/bin", "/bin"], names)


def find_tool(names, cxx=None):
    """按 PATH → 编译器同目录 → SDK/HNP/系统目录 的顺序找工具；找不到返回 None。"""
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    for d in _candidate_dirs(cxx):
        for n in names:
            p = os.path.join(d, n)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
    return None


# ────────────────────────── 纯 Python ELF 解析 ──────────────────────────

def _iter_ar_members(path):
    """遍历 ar 归档成员，产出 (name, offset, size)。

    注意：ar 的 `/'（符号表）与 `//'（长文件名表）成员不是目标文件，
    调用方需按名字跳过（否则会去解析几十 MB 的符号表成员）。
    """
    with open(path, "rb") as fh:
        if fh.read(8) != b"!<arch>\n":
            return
        while True:
            hdr = fh.read(60)
            if len(hdr) < 60:
                return
            name = hdr[0:16].decode("ascii", "replace").strip().rstrip("/")
            try:
                size = int(hdr[48:58].decode("ascii", "replace").strip() or "0")
            except ValueError:
                return
            pos = fh.tell()
            yield name, pos, size
            fh.seek(pos + size + (size % 2))     # 成员按偶数对齐


def _elf_header(path, offset=0):
    """返回 (e_machine, is_elf, ei_data, e_phoff, e_phentsize, e_phnum)。"""
    with open(path, "rb") as fh:
        fh.seek(offset)
        ident = fh.read(64)
    if len(ident) < 52 or ident[:4] != b"\x7fELF":
        return None
    ei_data = ident[5]
    endian = "<" if ei_data == 1 else ">"
    e_machine = struct.unpack_from(endian + "H", ident, 18)[0]
    e_phoff = struct.unpack_from(endian + "Q", ident, 32)[0]
    e_phentsize = struct.unpack_from(endian + "H", ident, 54)[0]
    e_phnum = struct.unpack_from(endian + "H", ident, 56)[0]
    return e_machine, True, ei_data, e_phoff, e_phentsize, e_phnum


def elf_machine_of(path):
    """取 ELF 的 e_machine；.a 归档则取第一个 ELF 成员；非 ELF 返回 None。"""
    hdr = _elf_header(path)
    if hdr:
        return hdr[0]
    if _is_archive(path):
        for _name, off, size in _iter_ar_members(path):
            if size < 64:
                continue
            hdr = _elf_header(path, off)
            if hdr:
                return hdr[0]
    return None


def _is_archive(path):
    try:
        with open(path, "rb") as fh:
            return fh.read(8) == b"!<arch>\n"
    except OSError:
        return False


def elf_has_interp(path):
    """解析程序头，判断是否存在 PT_INTERP（动态加载器）。"""
    hdr = _elf_header(path)
    if not hdr:
        return None
    _machine, _is_elf, ei_data, e_phoff, e_phentsize, e_phnum = hdr
    if not e_phoff or not e_phnum:
        return False
    endian = "<" if ei_data == 1 else ">"
    with open(path, "rb") as fh:
        fh.seek(e_phoff)
        table = fh.read(e_phentsize * e_phnum)
    for i in range(e_phnum):
        base = i * e_phentsize
        if base + 4 > len(table):
            break
        if struct.unpack_from(endian + "I", table, base)[0] == PT_INTERP:
            return True
    return False


def elf_symbol_names(path, limit_members=4000):
    """纯 Python 抽取 ELF/.a 中**已定义**符号名（用于无 nm 环境下的回退判定）。"""
    names = set()
    if _is_archive(path):
        for name, off, size in list(_iter_ar_members(path))[:limit_members]:
            if name in ("/", "//", ""):        # ar 符号表 / 长名表，不是目标文件
                continue
            hdr = _elf_header(path, off)
            if hdr:
                names |= _symtab_names(path, off, hdr, size)
    else:
        hdr = _elf_header(path)
        if hdr:
            names = _symtab_names(path, 0, hdr, os.path.getsize(path))
    return names


def _symtab_names(path, offset, hdr, member_size=None):
    _machine, _is_elf, ei_data, _phoff, _phentsize, _phnum = hdr
    endian = "<" if ei_data == 1 else ">"
    out = set()
    want = min(member_size or (64 * 1024 * 1024), 64 * 1024 * 1024)
    try:
        with open(path, "rb") as fh:
            fh.seek(offset)
            blob = fh.read(want)              # 只读该成员，避免拖入 55 MB 的 ar 符号表
    except OSError:
        return out
    if len(blob) < 64:
        return out
    e_shoff = struct.unpack_from(endian + "Q", blob, 40)[0]
    e_shentsize = struct.unpack_from(endian + "H", blob, 58)[0]
    e_shnum = struct.unpack_from(endian + "H", blob, 60)[0]
    if not e_shoff or not e_shnum:
        return out

    def sh(i):
        base = e_shoff + i * e_shentsize
        if base + 40 > len(blob):
            return None
        return {
            "type": struct.unpack_from(endian + "I", blob, base + 4)[0],
            "offset": struct.unpack_from(endian + "Q", blob, base + 24)[0],
            "size": struct.unpack_from(endian + "Q", blob, base + 32)[0],
            "link": struct.unpack_from(endian + "I", blob, base + 40)[0],
            "entsize": struct.unpack_from(endian + "Q", blob, base + 56)[0],
        }

    for i in range(min(e_shnum, 4096)):
        s = sh(i)
        if not s or s["type"] != SHT_SYMTAB:
            continue
        strtab = sh(s["link"])
        if not strtab:
            continue
        sym_off, sym_size = s["offset"], s["size"]
        str_off, str_size = strtab["offset"], strtab["size"]
        if not (0 <= sym_off < len(blob)) or not (0 <= str_off < len(blob)):
            continue
        symtab = blob[sym_off:sym_off + sym_size]
        strtab_data = blob[str_off:str_off + str_size]
        entsize = s["entsize"] or 24
        for j in range(0, max(len(symtab) - entsize + 1, 0), entsize):
            st_name = struct.unpack_from(endian + "I", symtab, j)[0]
            st_shndx = struct.unpack_from(endian + "H", symtab, j + 6)[0]
            if st_shndx == SHN_UNDEF or st_name == 0 or st_name >= len(strtab_data):
                continue
            end = strtab_data.find(b"\x00", st_name)
            if end < 0:
                continue
            out.add(strtab_data[st_name:end].decode("utf-8", "replace"))
        break
    return out


# ────────────────────────── 检查项 ──────────────────────────

def check_arch(lib, cxx):
    """3. 目标架构：纯 Python 判定，readelf 只作为附加证据（缺失不影响判定）。"""
    machine = elf_machine_of(lib)
    ok = check(machine == EM_AARCH64,
               "libopenvdb 为 AArch64 ELF（纯 Python 解析 ELF 头 e_machine）",
               f"e_machine={machine!r}（期望 {EM_AARCH64}）")
    tool = find_tool(["llvm-readelf", "readelf", "eu-readelf"], cxx)
    if tool:
        r = run([tool, "-h", lib], timeout=180)
        first = next((l.strip() for l in (r.stdout or "").splitlines() if "Machine" in l), "")
        print(f"{NOTE} 附加证据：{os.path.basename(tool)} -h → {first or 'rc=' + str(r.returncode)}")
    else:
        print(f"{NOTE} 环境无 readelf/llvm-readelf，架构判定完全由纯 Python 解析完成")
    return ok


def check_symbols(lib, cxx):
    """4. 关键 API 符号导出：优先 nm 家族，缺失则纯 Python 解析符号表。"""
    names = None
    tool = find_tool(["llvm-nm", "nm", "eu-nm"], cxx)
    if tool:
        r = run([tool, "-C", "--defined-only", lib], timeout=1800)
        if r.returncode == 0 and r.stdout:
            names = set(r.stdout.split())
            print(f"{NOTE} 符号来源：{os.path.basename(tool)} -C --defined-only")
    if names is None:
        syms = elf_symbol_names(lib)
        names = syms
        print(f"{NOTE} 环境无 nm/llvm-nm，改用纯 Python 解析 .symtab（取到 {len(syms)} 个已定义符号名）")

    missing = []
    for demangled, mangled in WANTED_SYMBOLS:
        if any(demangled in n for n in names) or any(mangled in n for n in names):
            continue
        missing.append(demangled)
    return check(not missing, f"libopenvdb 导出关键 API 符号（{len(WANTED_SYMBOLS)} 个）",
                 f"缺: {missing}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--cxx", required=True)
    ap.add_argument("--cross", action="store_true",
                    help="交叉编译环境（本机 → OHOS）：尝试静态链接，且不执行产物")
    ap.add_argument("--include", action="append", default=[])
    ap.add_argument("--libdir", action="append", default=[])
    ap.add_argument("--lib", action="append", default=[])
    a = ap.parse_args()
    pkg = a.pkg

    # ---- 1/2. 安装布局 ----
    libdir = os.path.join(pkg, "lib")
    lib = None
    for cand in ("libopenvdb.a", "libopenvdb.so"):
        if os.path.isfile(os.path.join(libdir, cand)):
            lib = os.path.join(libdir, cand)
            break
    check(lib is not None, f"libopenvdb 库文件存在（{os.path.basename(lib) if lib else '缺失'}）")
    hdr = os.path.join(pkg, "include", "openvdb", "openvdb.h")
    check(os.path.isfile(hdr), "include/openvdb/openvdb.h 存在")

    # ---- 3. 目标架构（纯 Python）----
    if lib:
        check_arch(lib, a.cxx)
    else:
        check(False, "libopenvdb 为 AArch64 ELF", "库缺失")

    # ---- 4. 关键 API 符号导出 ----
    if lib:
        check_symbols(lib, a.cxx)
    else:
        check(False, "libopenvdb 导出关键 API 符号", "库缺失")

    # ---- 5. 编译 + 链接消费者 ----
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "consumer.cpp")
    tmp = tempfile.mkdtemp(prefix="openvdb_consumer_")
    out_bin = os.path.join(tmp, "openvdb_consumer")

    # 解析出真正可执行的编译器：CI 上 profile 给的是 /data/service/hnp/bin/clang++ 这类
    # **包装脚本**（它注入 --target=aarch64-linux-ohos；SDK 原生 clang++ 的默认目标是宿主机！），
    # 但也可能只给裸名（PATH 里未必有）——这里做多级解析 + 目标三元组校验。
    cxx = find_compiler(a.cxx)
    triple = compiler_triple(cxx) if cxx else ""
    ohos_ok = bool(cxx) and ("ohos" in triple.lower() or triple.lower().startswith("aarch64"))
    if cxx:
        note = f"{NOTE} 编译器：{cxx}（目标 {triple or '未知'}）"
        if cxx != a.cxx:
            note += f"（--cxx 给的是 {a.cxx!r}）"
        print(note)
    else:
        print(f"{NOTE} 未能解析出可执行的 C++ 编译器（--cxx={a.cxx!r}）")

    if not ohos_ok:
        # 关键：绝不用**非 OHOS 目标**的编译器去编译消费者——那会产出错误目标架构的产物，
        # 链接期报 "skipping incompatible ... libtbb.so" 之类的假失败（本机实测）。
        # 环境给不出 OHOS 编译器时，如实跳过编译/执行检查并说明，不判失败。
        print(f"{NOTE} 未找到面向 OHOS/aarch64 的 C++ 编译器 → 跳过「消费者编译+链接」与「真实执行」检查"
              f"（已搜索 PATH、$CXX/$CC 与 {len(_candidate_dirs(a.cxx))} 个候选目录；"
              f"CI 的 profile 会通过 tools.build:compiler_executables 提供 /data/service/hnp/bin/clang++，"
              f"正常不会走到这里）")
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"{NOTE} 断言总数 {_checks}（其中编译/执行 2 项因缺 OHOS 编译器跳过），失败 {_failures}")
        return 1 if _failures else 0

    base = [cxx, "-std=c++17", src, "-o", out_bin,
            "-I", os.path.join(pkg, "include"), "-L", libdir]
    for d in a.include:
        base += ["-I", d]
    for d in a.libdir:
        base += ["-L", d]
    tail = ["-lopenvdb"] + [f"-l{n}" for n in a.lib]

    linked_static = False
    if a.cross:
        # 尝试全静态（本机可执行）；tbb 只提供 .so 时必然失败 → 回退动态
        r = run(base + ["-static"] + tail, timeout=1800)
        if r.returncode == 0:
            linked_static = True
            print(f"{NOTE} 静态链接成功（本机可执行）")
        else:
            print(f"{NOTE} 静态链接失败（依赖仅提供共享库，如 tbb 只有 libtbb.so）→ 回退动态链接")
            r = run(base + tail, timeout=1800)
    else:
        r = run(base + tail, timeout=1800)

    ok_link = check(r.returncode == 0, "消费者编译+链接成功（libopenvdb 可用）",
                    (r.stderr or "")[-500:])

    # ---- 6/7. 执行（仅原生构建；交叉编译时按上面说明跳过）----
    if not ok_link:
        check(False, "消费者真实执行通过（exit 0）", "编译失败，未执行")
    elif linked_static or not a.cross:
        n_interp = 1 if elf_has_interp(out_bin) else 0
        if linked_static:
            check(n_interp == 0, "消费者静态链接（纯 Python 解析程序头无 PT_INTERP）")
        else:
            print(f"{NOTE} 原生构建：动态链接产物，PT_INTERP 段数={n_interp}")
        try:
            # 显式注入运行期库搜索路径：消费者动态链接 tbb/zlib/boost 等依赖库，
            # 设备端不能假定 conanrun 已把它们放进搜索路径
            # （CI #63842 实测：Error loading shared library libtbb.so）。
            ld = runtime_library_path(pkg, a.libdir, extra=[libdir])
            print(f"{NOTE} 执行时 LD_LIBRARY_PATH={ld}")
            rr = run([out_bin], timeout=1800, extra_env={"LD_LIBRARY_PATH": ld})
            for line in (rr.stdout or "").splitlines():
                print(f"{NOTE}   {line}")
            if rr.stderr:
                print(f"{NOTE}   stderr: {rr.stderr[:300]}")
            check(rr.returncode == 0, "消费者真实执行通过（exit 0）", f"rc={rr.returncode}")
            check("ALL PASS" in (rr.stdout or ""),
                  "消费者内部 6 项断言全部通过（输出含 ALL PASS）")
        except subprocess.TimeoutExpired:
            check(False, "消费者真实执行通过（exit 0）", "超时")
    else:
        print(f"{NOTE} 交叉编译环境：不解执行动态 aarch64 产物"
              f"（SDK 无设备端 musl 加载器；QEMU 跑动态 OHOS 产物段错误；"
              f"tbb 仅提供共享库无法全静态）。真实执行在设备端原生构建（CI）下完成。")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"{NOTE} 断言总数 {_checks}，失败 {_failures}")
    if _failures:
        print(f"{FAIL} {_failures} 项检查失败")
        return 1
    print(f"ALL PASS ({_checks} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
