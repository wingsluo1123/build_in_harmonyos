#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""samarium 1.0.0 交付形态自检（M）—— 与上游测试用例、业务用例互补的第三层证据。

检查对象是 **conan 打包后的安装态目录**（不是源码树、不是构建树），所以每一条都
能在"交付物是否真的可被下游消费"这个层面上失败。纯 Python 解析 ELF（不依赖
readelf/objdump/nm —— OHOS worker 上不保证有），pkg-config 真调用在有该工具的
平台上执行、否则显式标注跳过（不静默放过）。

用法：
  test_layout.py --package-folder=<pkg> --generators-dir=<gen> --consumer=<bin> \
                 --version=1.0.0 --expect-machine=AArch64 [--expect-ohos]
"""
import argparse
import glob
import os
import re
import shutil
import struct
import subprocess
import sys

PASS = 0
FAIL = 0
SKIP = 0

# 未交付模块（app/gui 硬依赖 SFML Window/Graphics）
DISABLED_HEADERS = ("app.hpp", "gui.hpp")
DISABLED_DIRS = ("app", "gui")

# 必须存在的关键公共头（交付范围断言：math/physics/geometry/graphics/util）
REQUIRED_HEADERS = (
    "samarium.hpp",
    "core.hpp",
    "core/types.hpp",
    "math.hpp",
    "math/Vector2.hpp",
    "math/math.hpp",
    "math/shapes.hpp",
    "math/vector_math.hpp",
    "physics.hpp",
    "physics/Particle.hpp",
    "physics/ParticleSystem.hpp",
    "physics/Spring.hpp",
    "physics/collision.hpp",
    "geometry/Mesh.hpp",
    "graphics/Trail.hpp",
    "graphics/Grid.hpp",
    "util/RandomGenerator.hpp",
    "util/ThreadPool.hpp",
)

# 交付无关/构建中间产物（禁止出现在包里）
FORBIDDEN_SUFFIXES = (
    ".cpp", ".c", ".cc", ".cxx", ".o", ".a", ".la", ".lo", ".obj", ".pyc", ".orig", ".rej",
)
FORBIDDEN_DIRS = ("test", "tests", "examples", "CMakeFiles", "__pycache__", ".git", "build")
FORBIDDEN_FILES = ("CMakeCache.txt", "CMakeLists.txt", "conanfile.py", ".gitignore", ".clang-format")

# 第三方头前缀：由 conan 依赖（fmt / range-v3）提供，不参与"本包头闭包"判定
EXTERNAL_INCLUDE_PREFIXES = ("range/", "fmt/", "SFML/", "boost/", "catch2/", "gtest/")

ELF_MACHINES = {40: "ARM", 62: "x86-64", 183: "AArch64"}
ELF_ETYPES = {1: "REL", 2: "EXEC", 3: "DYN", 4: "CORE"}


def check(condition, label):
    global PASS, FAIL
    if condition:
        PASS += 1
        print("[ok]   %s" % label)
    else:
        FAIL += 1
        print("[FAIL] %s" % label)
    return bool(condition)


def skip(label, reason):
    global SKIP
    SKIP += 1
    print("[skip] %s —— %s" % (label, reason))


# ─────────────────────────── 极简 ELF64 解析 ───────────────────────────
class Elf64:
    """只解析交付形态自检需要的字段：类型/架构/段名/SONAME/NEEDED/RUNPATH。"""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as handle:
            self.data = handle.read()
        self.valid = self.data[:4] == b"\x7fELF"
        self.is64 = self.valid and self.data[4] == 2
        self.little_endian = self.valid and self.data[5] == 1
        self._endian = "<" if self.little_endian else ">"
        self.etype = self.machine = None
        self.sections = []            # [(name, offset, size, addr)]
        self.dynamic = {}             # tag -> [values]
        self.dynstr = b""
        if self.valid and self.is64:
            self._parse()

    def _u(self, fmt, offset):
        return struct.unpack_from(self._endian + fmt, self.data, offset)[0]

    def _parse(self):
        self.etype = self._u("H", 16)
        self.machine = self._u("H", 18)
        shoff = self._u("Q", 40)
        shentsize = self._u("H", 58)
        shnum = self._u("H", 60)
        shstrndx = self._u("H", 62)
        raw = []
        for i in range(shnum):
            base = shoff + i * shentsize
            raw.append({
                "name": self._u("I", base),
                "type": self._u("I", base + 4),
                "offset": self._u("Q", base + 24),
                "size": self._u("Q", base + 32),
                "addr": self._u("Q", base + 16),
            })
        strtab = None
        if shstrndx < len(raw):
            strtab = self.data[raw[shstrndx]["offset"]:raw[shstrndx]["offset"] + raw[shstrndx]["size"]]
        for section in raw:
            name = b""
            if strtab and section["name"] < len(strtab):
                end = strtab.find(b"\0", section["name"])
                name = strtab[section["name"]:end if end != -1 else len(strtab)]
            section["sname"] = name.decode("utf-8", "replace")
            self.sections.append(section)
            if section["sname"] == ".dynstr":
                self.dynstr = self.data[section["offset"]:section["offset"] + section["size"]]
        dynamic = next((s for s in self.sections if s["sname"] == ".dynamic"), None)
        if dynamic is None:
            return
        for offset in range(dynamic["offset"], dynamic["offset"] + dynamic["size"], 16):
            tag = self._u("q", offset)
            value = self._u("Q", offset + 8)
            if tag == 0:
                break
            self.dynamic.setdefault(tag, []).append(value)

    def section_names(self):
        return [s["sname"] for s in self.sections]

    def string_at(self, offset):
        if offset >= len(self.dynstr):
            return ""
        end = self.dynstr.find(b"\0", offset)
        return self.dynstr[offset:end if end != -1 else len(self.dynstr)].decode("utf-8", "replace")

    def soname(self):
        values = self.dynamic.get(14)          # DT_SONAME
        return self.string_at(values[0]) if values else ""

    def needed(self):
        return [self.string_at(v) for v in self.dynamic.get(1, [])]   # DT_NEEDED

    def runpaths(self):
        out = []
        for tag in (15, 29):                   # DT_RPATH / DT_RUNPATH
            out.extend(self.string_at(v) for v in self.dynamic.get(tag, []))
        return out


# ─────────────────────────── 主流程 ───────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-folder", required=True)
    parser.add_argument("--generators-dir", required=True)
    parser.add_argument("--consumer", required=True)
    parser.add_argument("--version", default="")
    parser.add_argument("--expect-machine", default="")
    parser.add_argument("--expect-ohos", action="store_true")
    args = parser.parse_args()

    pkg = args.package_folder
    gen = args.generators_dir
    include_dir = os.path.join(pkg, "include")
    lib_dir = os.path.join(pkg, "lib")
    print("== samarium 交付形态自检 ==")
    print("包目录: %s" % pkg)

    # ── 1. 交付库本体 ────────────────────────────────────────────────
    libs = sorted(glob.glob(os.path.join(lib_dir, "*")))
    check(libs == [os.path.join(lib_dir, "libsamarium.so")],
          "lib/ 下恰好只有 libsamarium.so（CMAKE_PLATFORM_NO_VERSIONED_SONAME：无版本化符号链接残留），实际 %s"
          % [os.path.basename(x) for x in libs])

    lib = os.path.join(lib_dir, "libsamarium.so")
    if not os.path.isfile(lib):
        print("!! 交付库缺失，后续 ELF 检查无法进行")
    elf = Elf64(lib) if os.path.isfile(lib) else None
    check(bool(elf and elf.valid), "libsamarium.so 是合法 ELF")
    if elf and elf.valid and elf.is64:
        check(ELF_ETYPES.get(elf.etype) == "DYN",
              "libsamarium.so 是共享对象（ET_DYN），实际 %s" % ELF_ETYPES.get(elf.etype))
        machine = ELF_MACHINES.get(elf.machine, "unknown(%d)" % (elf.machine or 0))
        if args.expect_machine:
            check(machine == args.expect_machine,
                  "libsamarium.so 架构 == %s（conan settings.arch 对应），实际 %s"
                  % (args.expect_machine, machine))
        else:
            skip("libsamarium.so 架构检查", "调用方未给出期望架构")
        check(elf.soname() == "libsamarium.so",
              "DT_SONAME == libsamarium.so（OHOS 未知平台下 CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG 兜底），实际 %r"
              % elf.soname())
        check(not elf.runpaths(),
              "安装态 libsamarium.so 无 DT_RPATH/DT_RUNPATH（不带构建机路径，可重定位），实际 %s"
              % elf.runpaths())
        needed = elf.needed()
        check(needed and any(n.startswith(("libc.so", "libc++_shared.so", "libstdc++.so", "libc.musl"))
                             for n in needed),
              "DT_NEEDED 含 C/C++ 运行时（动态链接的共享库），实际 %s" % needed)
        if args.expect_ohos:
            check(".codesign" in elf.section_names(),
                  "安装态 libsamarium.so 带 .codesign 段（OHOS 加载器拒载未签名 .so）")
        else:
            skip("libsamarium.so .codesign 段检查",
                 "当前不是 OHOS 构建（无 binary-sign-tool/llvm-objcopy）")

    # ── 2. 公共头契约 ────────────────────────────────────────────────
    missing_headers = [h for h in REQUIRED_HEADERS
                       if not os.path.isfile(os.path.join(include_dir, "samarium", h))]
    check(not missing_headers, "交付头清单齐全（math/physics/geometry/graphics/util 关键公共头），缺失 %s"
          % missing_headers)

    headers = sorted(glob.glob(os.path.join(include_dir, "samarium", "**", "*.hpp"), recursive=True))
    check(len(headers) >= 40, "公共头数量 >= 40（实测 %d 个 .hpp）" % len(headers))

    unresolved = []
    for header in headers:
        for line in open(header, encoding="utf-8", errors="replace"):
            matched = re.match(r'\s*#\s*include\s+"([^"]+)"', line)
            if not matched:
                continue
            target = matched.group(1)
            # 第三方头由 conan 依赖（fmt/range-v3）提供，不属于本包头闭包；
            # 本包头闭包 = 包内 "samarium/..." 与相对路径 include（裁模块时最容易断的地方）
            if target.startswith(EXTERNAL_INCLUDE_PREFIXES):
                continue
            base = os.path.dirname(header)
            candidates = [os.path.join(base, target), os.path.join(include_dir, target)]
            if not any(os.path.isfile(c) for c in candidates):
                unresolved.append("%s -> %s" % (os.path.relpath(header, include_dir), target))
    check(not unresolved, "头文件包含闭包自洽（包内 samarium/... 与相对 include 均可解析；第三方头交给 conan 依赖），"
          "未解析 %s" % unresolved[:5])

    umbrella = os.path.join(include_dir, "samarium", "samarium.hpp")
    umbrella_text = open(umbrella, encoding="utf-8").read() if os.path.isfile(umbrella) else ""
    check('include "app.hpp"' not in umbrella_text and 'include "gui.hpp"' not in umbrella_text,
          "umbrella samarium.hpp 不再引用未交付模块（app.hpp / gui.hpp）")

    leftover = [name for name in DISABLED_HEADERS
                if os.path.exists(os.path.join(include_dir, "samarium", name))]
    leftover += [name for name in DISABLED_DIRS
                 if os.path.isdir(os.path.join(include_dir, "samarium", name))]
    check(not leftover,
          "未交付模块（app/gui，硬依赖 SFML Window/Graphics）的头已被裁净，残留 %s" % leftover)

    # ── 3. 包内纯净性 ────────────────────────────────────────────────
    junk = []
    hidden = []
    top_level = []
    for root, dirs, files in os.walk(pkg):
        rel = os.path.relpath(root, pkg)
        if rel == ".":
            top_level = sorted(dirs + files)
        for name in list(dirs) + files:
            if name.startswith("."):
                hidden.append(os.path.join(rel, name))
        for name in dirs:
            if name in FORBIDDEN_DIRS:
                junk.append(os.path.join(rel, name))
        for name in files:
            if name.lower().endswith(FORBIDDEN_SUFFIXES) or name in FORBIDDEN_FILES:
                junk.append(os.path.join(rel, name))
    check(not junk, "包内无测试源/示例/构建中间产物（test/、examples/、*.cpp、*.o、CMakeCache.txt…），命中 %s"
          % junk[:5])
    check(not hidden, "包内无隐藏文件/目录（JC5），命中 %s" % hidden[:5])
    expected_top = {"include", "lib", "licenses", "conaninfo.txt", "conanmanifest.txt"}
    check(set(top_level) <= expected_top,
          "包目录顶层条目仅 include/lib/licenses（+conan 元数据），实际 %s" % top_level)
    check(os.path.isfile(os.path.join(pkg, "conanmanifest.txt")),
          "conanmanifest.txt 存在（conan 包完整性清单）")

    # ── 4. 许可原文 ──────────────────────────────────────────────────
    license_path = os.path.join(pkg, "licenses", "LICENSE.md")
    license_text = open(license_path, encoding="utf-8").read() if os.path.isfile(license_path) else ""
    check(os.path.isfile(license_path), "licenses/LICENSE.md 存在（上游许可原文随包交付）")
    check("MIT License" in license_text
          and "Permission is hereby granted, free of charge" in license_text
          and "strangeQuark1041" in license_text,
          "LICENSE.md 正文是 MIT 全文且含上游版权人 strangeQuark1041")

    # ── 5. CMake 契约（CMakeDeps 生成，消费者实际使用的接口）────────────
    config = os.path.join(gen, "samarium-config.cmake")
    config_text = open(config, encoding="utf-8").read() if os.path.isfile(config) else ""
    check(os.path.isfile(config) and "samarium::samarium" in
          open(os.path.join(gen, "samariumTargets.cmake"), encoding="utf-8").read(),
          "CMakeDeps 生成 samarium 包配置并声明 samarium::samarium 目标")
    datas = glob.glob(os.path.join(gen, "samarium-*-data.cmake"))
    data_text = "".join(open(f, encoding="utf-8").read() for f in datas)
    check("find_dependency" in config_text
          and re.search(r"FIND_DEPENDENCY_NAMES[^\n]*fmt range-v3", data_text) is not None,
          "samarium-config.cmake 声明对 fmt / range-v3 的 find_dependency（公共头传递依赖）")
    check("fmt::fmt" in data_text and "range-v3::range-v3" in data_text,
          "组件依赖表含 fmt::fmt 与 range-v3::range-v3（cpp_info.components[...].requires 生效）")
    check("-std=c++20" in data_text,
          "包把 -std=c++20 传给消费者（公共头是 C++20：concepts / std::span / std::numbers）")
    check('set(samarium_PACKAGE_FOLDER_RELEASE "%s")' % pkg in data_text
          and '${samarium_PACKAGE_FOLDER_RELEASE}/include' in data_text,
          "生成配置的 include 以 ${PACKAGE_FOLDER}/include 形式派生（指向本包、可重定位）")

    # ── 6. pkg-config 契约 ───────────────────────────────────────────
    component_pc = os.path.join(gen, "samarium-samarium.pc")
    pc_text = open(component_pc, encoding="utf-8").read() if os.path.isfile(component_pc) else ""
    check("-lsamarium" in pc_text and 'includedir=${prefix}/include' in pc_text
          and "Requires: fmt range-v3" in pc_text,
          "生成的 samarium-samarium.pc：Libs 含 -lsamarium、includedir 由 ${prefix} 派生、Requires 链含 fmt/range-v3")
    check(os.path.isfile(os.path.join(gen, "samarium.pc")),
          "聚合 samarium.pc 存在（pkg-config 消费入口）")
    pkg_config = shutil.which("pkg-config")
    if pkg_config:
        env = dict(os.environ, PKG_CONFIG_PATH=gen)
        proc = subprocess.run([pkg_config, "--cflags", "--libs", "samarium"], env=env,
                              capture_output=True, text=True, check=False)
        check(proc.returncode == 0 and "-lsamarium" in proc.stdout
              and os.path.join(pkg, "include") in proc.stdout,
              "pkg-config --cflags --libs samarium 可解析并指向包内 include/lib，输出 %r" % proc.stdout.strip())
    else:
        skip("pkg-config 真调用", "本平台没有 pkg-config 可执行文件（文本契约已在上面单独检查）")

    # ── 7. 消费者二进制真的链接了交付库 ───────────────────────────────
    consumer = Elf64(args.consumer) if os.path.isfile(args.consumer) else None
    check(bool(consumer and consumer.valid and consumer.is64), "消费者可执行文件是合法 ELF64")
    if consumer and consumer.valid and consumer.is64:
        needed = consumer.needed()
        check(any(n.startswith("libsamarium") for n in needed),
              "消费者可执行文件的 DT_NEEDED 含 libsamarium（真实链接交付库，非头文件内联），实际 %s" % needed)

    # ── 8. 版本一致性 ────────────────────────────────────────────────
    version_hpp = os.path.join(include_dir, "samarium", "core", "version.hpp")
    version_text = open(version_hpp, encoding="utf-8").read() if os.path.isfile(version_hpp) else ""
    if args.version:
        check(re.search(r"major\{%s\}" % args.version.split(".")[0], version_text) is not None
              and re.search(r"minor\{%s\}" % args.version.split(".")[1], version_text) is not None,
              "包内 core/version.hpp 的主/次版本与包版本 %s 一致" % args.version)
    else:
        skip("version.hpp 版本一致性", "调用方未给出包版本")

    print("\n自检结果：%d 项通过，%d 项失败，%d 项跳过" % (PASS, FAIL, SKIP))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
