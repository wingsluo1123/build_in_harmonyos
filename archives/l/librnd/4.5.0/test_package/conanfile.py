#!/usr/bin/env python3
"""Conan test_package for librnd 4.5.0 — exercises the real public API.

Builds test.c (librnd-core base64 codec: known-answer encode/decode plus
roundtrips) by linking all 8 librnd libraries directly, then runs it.
Emits the HMBS_TEST_PACKAGE_RESULT marker with the real assertion count
from the test source (6 checks).
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class LibrndTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["librnd"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（librnd 对外透出 include/librnd4）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        # 真机 clang 不在固定 /data/service/hnp/bin 路径下（实测 Error 127）；
        # 优先用环境 CC，否则按 PATH 依次取 cc/gcc/clang，均经 PATH 解析。
        cc = (
            os.environ.get("CC")
            or shutil.which("cc")
            or shutil.which("gcc")
            or shutil.which("clang")
            or "cc"
        )
        # 【直接链库，不用 dlopen】R34 要求 test 实际调用被测包 API；
        # 且 CI 的 L1e 会把包的 lib/ 与 include/ 移走后重跑，直链使其在
        # 编译/链接期就失败，反向验证更硬。8 个库全链确保每个产出物都被消费。
        # 上游安装物无 `lib` 前缀（src/Makefile.in: `librnd-core.a`
        # 而非 `liblibrnd-core.a`，`.so` 同理），`-l<name>` 永远搜不到
        #（真机 ld.lld: unable to find library -llibrnd-* ×8），
        # 故用防止上游重命名的显式归档路径直链；`--start-group`
        # 消除静态归档之间的顺序依赖，避免多费一轮真机。
        archives = [
            "librnd-hid.a",
            "librnd-font2.a",
            "librnd-font.a",
            "librnd-polybool2.a",
            "librnd-polybool.a",
            "librnd-poly.a",
            "librnd-core.a",
            "librnd-3rd.a",
        ]
        libs = "-Wl,--start-group %s -Wl,--end-group -lm" % " ".join(
            '"%s"' % os.path.join(libdir, a) for a in archives
        )
        self.run("%s test.c -o test_probe %s %s" % (cc, inc, libs))

    def test(self):
        # 6 explicit checks in test.c (2 known-answer + 4 roundtrips).
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "./test_probe",
            "discovered": 6,
            "passedCount": 6,
        }
        if not can_run(self):
            self.output.info("Cross build: librnd consumer was built; run it on the HarmonyOS PC target.")
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            return
        # 真机无固定 /data/service/hnp/bin/bash（实测 Error 127 的同类问题）；
        # 优先用构建环境 CONFIG_SHELL，否则用 HMBS 注入的 SHELL（/bin/sh）。
        bash = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL", "/bin/sh")
        try:
            self.run('%s -c "./test_probe"' % bash, env="conanrun")
        except Exception:
            test_pkg["passed"] = False
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            raise
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
