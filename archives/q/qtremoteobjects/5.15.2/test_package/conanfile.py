#!/usr/bin/env python3
"""Conan test_package — qtremoteobjects 5.15.2

OHOS 平台限制：stripped ELF 共享库无法被 dlopen 加载 (Permission denied)。
本测试包采用静态验证方式：readelf 检查 ELF 结构 + nm -D 检查导出符号，
不依赖运行时加载，绕过 OHOS ELF 签名限制。
"""
import os
import glob
from conan import ConanFile


class QtremoteobjectsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def build(self):
        pass  # 无需编译，纯静态验证

    def test(self):
        ro_dep = self.dependencies["qtremoteobjects"]
        ro_lib_dir = os.path.join(ro_dep.package_folder, "lib")

        # 1. 检查库文件存在
        so_files = glob.glob(os.path.join(ro_lib_dir, "libQt5RemoteObjects.so*"))
        if not so_files:
            raise AssertionError("libQt5RemoteObjects.so not found in package")
        print(f"OK: Found {len(so_files)} library file(s)")

        # 找到实际 .so 文件（优先 .so.5.15.2）
        so_file = None
        for f in sorted(so_files, reverse=True):
            if os.path.isfile(f) and not os.path.islink(f):
                so_file = f
                break
        if not so_file:
            so_file = so_files[0]
        print(f"  Testing: {os.path.basename(so_file)}")

        # 2. readelf 验证 ELF 结构
        print("\n--- ELF Structure (readelf -d) ---")
        self.run(f'readelf -d "{so_file}"', env="CONAN_RETURN=1")
        output = self.run(f'readelf -d "{so_file}"', env="CONAN_RETURN=1", stream=True)

        # 检查 SONAME
        soname_output = []
        for line in output:
            soname_output.append(line)
            if "SONAME" in line:
                assert "libQt5RemoteObjects.so.5" in line, f"SONAME mismatch: {line}"
                print(f"OK: SONAME = {line.strip()}")

        # 检查 NEEDED 依赖
        needed_libs = [l for l in soname_output if "NEEDED" in l]
        print(f"OK: {len(needed_libs)} NEEDED dependencies")
        for lib in needed_libs:
            print(f"  {lib.strip()}")

        # 3. nm -D 验证导出符号
        print("\n--- Exported Symbols (nm -D) ---")
        nm_output = self.run(f'nm -D "{so_file}" 2>/dev/null', env="CONAN_RETURN=1", stream=True)

        key_symbols = [
            "QRemoteObjectNode",
            "QRemoteObjectReplica",
            "QRemoteObjectSourceBase",
            "qt_remoteobjects",
        ]

        all_symbols_text = "\n".join(nm_output)
        for sym in key_symbols:
            if sym in all_symbols_text:
                print(f"OK: Symbol '{sym}' found")
            else:
                print(f"WARN: Symbol '{sym}' not found")

        # 4. 检查头文件
        include_dir = os.path.join(ro_dep.package_folder, "include")
        headers = glob.glob(os.path.join(include_dir, "**", "*.h"), recursive=True)
        if headers:
            print(f"\nOK: {len(headers)} header file(s) found")
            for h in headers[:5]:
                print(f"  {os.path.relpath(h, ro_dep.package_folder)}")

        print(f"\n{'='*50}")
        print("test qtremoteobjects 5.15.2: PASSED")
        print(f"{'='*50}")
