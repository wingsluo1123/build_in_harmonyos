#!/usr/bin/env python3
"""Conan recipe — rar 7.23 (makefile): RARLAB UnRAR CLI and libunrar library.

Source mapping: task version "7.23" == upstream display version 7.23 ==
unrarsrc-7.2.7.tar.gz (version.hpp: RARVER_MAJOR=7 RARVER_MINOR=23
RARVER_BETA=0, 2026-06-27; the CLI banner prints "UNRAR 7.23").
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RarConan(ConanFile):
    name = "rar"
    version = "7.23"
    description = "RARLAB UnRAR: unrar utility and libunrar library for extracting RAR archives"
    license = "unrar"
    homepage = "https://www.rarlab.com/rar_add.htm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # 工具链解析（R33：编译器来自 Conan profile，不裸用 shell 环境变量）

    def _tool(self, key, fallback):
        executables = self.conf.get("tools.build:compiler_executables")
        if executables and key in executables:
            return executables[key]
        return fallback

    def _make(self, target=None):
        cxx = self._tool("cpp", "clang++")
        ar = self._tool("ar", "llvm-ar")
        # llvm-strip 默认会删除 OHOS lld 链接期写入的 .codesign 段（本地
        # llvm-objcopy/llvm-strip 实验实锤），导致产物在 HarmonyOS 上无法
        # execve（EACCES）。用 --keep-section 保留签名段；无签名段时为空操作。
        def q(v):
            return "'" + v.replace("'", "'\\''") + "'"
        args = [f"CXX={q(cxx)}",
                f"STRIP={q('llvm-strip --keep-section=.codesign')}",
                f"AR={q(ar)}", "-j4"]
        cmd = "make " + (f"{target} " if target else "") + " ".join(args)
        self.run(cmd, cwd=self.source_folder)

    def build(self):
        apply_conandata_patches(self)

        # 上游 makefile 的 lib 目标用 -DRARDLL（含 dll.cpp 入口、无 main()），
        # unrar 目标用 -DUNRAR（含 main）。两套对象不能混用，必须 clean 分隔：
        # 先 lib（PIC 对象）→ 保存 libunrar.{a,so} → clean → 再 unrar。
        self._make("clean")
        self._make("lib")

        lib_dir = os.path.join(self.build_folder, "saved_libs")
        os.makedirs(lib_dir, exist_ok=True)
        for f in ["libunrar.a", "libunrar.so"]:
            src_file = os.path.join(self.source_folder, f)
            if os.path.exists(src_file):
                copy(self, f, self.source_folder, lib_dir)

        self._make("clean")
        self._make()

        bin_dir = os.path.join(self.build_folder, "saved_bin")
        os.makedirs(bin_dir, exist_ok=True)
        unrar_bin = os.path.join(self.source_folder, "unrar")
        if os.path.exists(unrar_bin):
            copy(self, "unrar", self.source_folder, bin_dir)

    # ── OHOS 代码签名（E452 强制重签协议）──
    # 链接期 lld 写入的 .codesign 在 strip/conan 打包改写后结构性存在但已失效，
    # 装载器照样拒绝 execve（EACCES）。唯一可靠形态：最终产物强制重签——
    # 去旧段 → 签到旁路文件 → 校验 → 原子替换 → 复原执行位。

    _OBJCOPY_CANDIDATES = ("/data/service/hnp/bin/llvm-objcopy", "llvm-objcopy")
    _SIGNTOOL_CANDIDATES = ("/data/service/hnp/bin/binary-sign-tool",
                            "binary-sign-tool")

    @staticmethod
    def _has_ohos_signature(path):
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return False
        return b"codesign" in data or b".note.ohos" in data

    @staticmethod
    def _find_tool(candidates):
        for candidate in candidates:
            resolved = shutil.which(candidate) or (
                candidate if os.path.isfile(candidate) else None)
            if resolved:
                return resolved
        return None

    def _sign_ohos_elf(self, path):
        """强制重签最终打包产物（E452）。工具缺失时留诊断日志并放行——
        CI test 阶段的 EACCES 会把问题显式暴露，不静默。"""
        if str(self.settings.os) != "OHOS":
            return
        name = os.path.basename(path)
        had = self._has_ohos_signature(path)
        self.output.info(f"{name}: link-time signature marker={had} "
                         "(structural only; force re-signing final artifact)")
        objcopy = self._find_tool(self._OBJCOPY_CANDIDATES)
        signer = self._find_tool(self._SIGNTOOL_CANDIDATES)
        self.output.info(f"{name}: objcopy={objcopy} signer={signer}")
        if not signer:
            self.output.warning(
                f"{name}: binary-sign-tool not found; cannot force re-sign")
            return
        unsigned = path + ".unsigned"
        signed = path + ".signed"
        for tmp in (unsigned, signed):
            if os.path.exists(tmp):
                os.remove(tmp)
        if had and objcopy:
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" '
                     f'"{unsigned}"', ignore_errors=True)
        if not os.path.isfile(unsigned):
            shutil.copy2(path, unsigned)
        result = self.run(
            f'"{signer}" sign -inFile "{unsigned}" -outFile "{signed}" '
            f'-selfSign 1', ignore_errors=True)
        if result != 0 or not os.path.isfile(signed) or os.path.getsize(signed) == 0:
            for tmp in (unsigned, signed):
                if os.path.exists(tmp):
                    os.remove(tmp)
            raise ConanInvalidConfiguration(
                f"binary-sign-tool failed (rc={result}) for {path}")
        os.replace(signed, path)
        os.remove(unsigned)
        # HMDFS 可能丢可执行位（E077），复原 owner x
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass
        ok = self._has_ohos_signature(path)
        self.output.info(f"{name}: re-signed, marker={ok}, "
                         f"mode={oct(os.stat(path).st_mode)}")
        if not ok:
            raise ConanInvalidConfiguration(
                f"signed artifact lost its .codesign section: {path}")

    def package(self):
        copy(self, "dll.hpp", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "license.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

        lib_dir = os.path.join(self.build_folder, "saved_libs")
        if self.options.shared:
            copy(self, "libunrar.so", lib_dir,
                 os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libunrar.a", lib_dir,
                 os.path.join(self.package_folder, "lib"))

        bin_dir = os.path.join(self.build_folder, "saved_bin")
        copy(self, "unrar", bin_dir, os.path.join(self.package_folder, "bin"))

        for elf in [os.path.join(self.package_folder, "bin", "unrar"),
                    os.path.join(self.package_folder, "lib", "libunrar.so")]:
            if os.path.isfile(elf):
                self._sign_ohos_elf(elf)

    def package_info(self):
        self.cpp_info.libs = ["unrar"]
        self.cpp_info.bindirs = ["bin"]
        if self.options.shared:
            self.cpp_info.defines.append("UNRAR_DLL")
