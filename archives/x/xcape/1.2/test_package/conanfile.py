#!/usr/bin/env python3
"""xcape 1.2 消费者测试（R34/L0c）——真实执行打包产物并据观测结果决定退出码。

xcape 需要 X server（XOpenDisplay + XTEST + XRecord/XKB 扩展）才能施展功能；
HarmonyOS PC 无 X server，因此不可能在此验证"Ctrl 单击生成 Escape"这一运行时
行为。本测试如实覆盖能在设备上证实的部分，不含任何伪装成运行时通过的成分：

  test_ohos.sh（鸿蒙特有，执行式）
    1) ELF 形态：AArch64 + ELF64
    2) E549 自签名：readelf -S 命中 .codesign
    3) X11 链接：DT_NEEDED 记录 libXtst.so.6 / libX11.so.6
    4) 真实执行：无 DISPLAY 跑 `xcape -d`，观测上游确定性诊断
       "Unable to connect to X11 display"（xcape.c L162-163）且 rc=1
    5) 打包完整性：bin/xcape 与 share/man/man1/xcape.1 均存在

运行时功能（按键映射、XTEST 合成、XRecord 事件拦截）在 HarmonyOS PC 上
不可执行——平台无 X server 与 X 扩展事件源，此限制在 notes.md 与
test_package/MANIFEST.yml 中同样如实记录。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class XcapeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _dep_cpp_info(self):
        for dep in self.dependencies.host.values():
            if dep.ref.name == "xcape":
                return dep
        return None

    def _locate_binary(self):
        dep = self._dep_cpp_info()
        if not dep:
            return None
        for bindir in (dep.cpp_info.bindirs or ["bin"]):
            if not os.path.isabs(bindir):
                bindir = os.path.join(dep.package_folder, bindir)
            cand = os.path.join(bindir, "xcape")
            if os.path.isfile(cand):
                return cand
        return None

    def test(self):
        dep = self._dep_cpp_info()
        if dep is None:
            raise Exception("xcape dependency not found in test graph")
        binary = self._locate_binary()
        if not binary:
            raise Exception("xcape binary not found in package bindirs")

        # 打包完整性：manpage 必须落位（与 conanfile.py package() 一一对应）
        manpage = os.path.join(dep.package_folder, "share", "man", "man1", "xcape.1")
        if not os.path.isfile(manpage):
            raise Exception(f"manpage missing: {manpage}")
        self.output.info("package layout OK: bin/xcape + share/man/man1/xcape.1")

        script = os.path.join(self.source_folder, "test_ohos.sh")
        if not os.path.isfile(script):
            raise Exception("test_ohos.sh missing in test_package")
        os.chmod(script, 0o755)
        out_file = os.path.join(self.build_folder, "xcape_ohos_out.txt")
        self.run(f'"{script}" "{binary}" "{out_file}"', env="conanrun")
        self.output.info(
            "xcape consumer test PASSED: signed aarch64/musl ELF executes on OHOS; "
            "DT_NEEDED resolves libXtst.so.6 + libX11.so.6; deterministic no-X path "
            "observed (rc=1 + \"Unable to connect to X11 display\"). "
            "运行时按键映射行为因平台无 X server 不可执行，未计入通过项。"
        )
