#!/usr/bin/env python3
"""Conan test_package — xfaces 3.3

L1 test: xfaces 是 X11 GUI 应用（无库可链接，package_type=application），
test_xfaces.sh 真实执行被测包二进制 xfaces：以无效 DISPLAY=:99 运行，
XtInitialize（main.c:485）在打开 X 连接失败时打印
"Error: Can't open display" 后退出。该路径无需 X server，且必须先完成
全部动态符号解析（libXaw/libXmu/libXt/libXpm/libXext/libX11/libcompface），
可证明二进制可执行 + X11 依赖链接完整（R34 实质执行，xeyes/myman 同款）。

运行期共享库：xfaces 的 X11 依赖全部来自 conan 包（libxaw/1.0.14 等，
非 vendored）。conanrun 环境注入 LD_LIBRARY_PATH；HMBS
[stale_runtime_library]：loader 可能忽略 LD_LIBRARY_PATH，对测试命令用
LD_PRELOAD 指向依赖包中的 .so 绝对路径（依赖序 libXau → libXdmcp →
libxcb → libX11 → libXext → libICE → libSM → libXt → libXmu → libXpm →
libXaw → libcompface，myman/xeyes 同款）。

上游测试套件审计结论（详见 test_package/MANIFEST.yml upstream_test_audit）：
xfaces 3.3 发布包无自动化测试——tarball 无 tests/ 目录、无 make check
目标（Makefile.noimake 仅 all/install/clean，grep 实证）。
"""
import os

from conan import ConanFile


class XfacesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_so(self, dep, soname_prefix):
        """在依赖包里找 SONAME 前缀对应的 .so 文件（递归扫描整个
        package_folder：X11 包的 package_info 用 components 时根 cpp_info
        libdirs 可能为空）。优先非符号链接实体文件（HMDFS symlink 物化
        不可靠 E050），loader 按 SONAME 登记，效果等价。"""
        hits = []
        for root, _dirs, files in os.walk(dep.package_folder):
            for f in sorted(files):
                if f.startswith(soname_prefix):
                    hits.append(os.path.join(root, f))
        if not hits:
            return None
        for p in hits:
            if not os.path.islink(p):
                return p
        return hits[0]

    def _runtime_preload(self):
        """xfaces 运行期共享库补齐（conan X11 依赖链，按 DT_NEEDED 序）。"""
        wanted = (
            ("libxau", "libXau.so.6"),
            ("libxdmcp", "libXdmcp.so.6"),
            ("libxcb", "libxcb.so.1"),
            ("libx11", "libX11.so.6"),
            ("libxext", "libXext.so.6"),
            ("libice", "libICE.so.6"),
            ("libsm", "libSM.so.6"),
            ("libxt", "libXt.so.6"),
            ("libxmu", "libXmu.so.6"),
            ("libxpm", "libXpm.so.4"),
            ("libxaw", "libXaw.so.7"),
            ("compface", "libcompface.so"),
        )
        found = []
        for name, prefix in wanted:
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            so = self._find_so(dep, prefix)
            if so:
                found.append(so)
        return ":".join(found)

    def test(self):
        dep = self.dependencies["xfaces"]
        xfaces_bin = os.path.join(dep.package_folder, "bin", "xfaces")

        # HMBS [shell_getcwd]：使用注入的 SHELL（/bin/sh），脚本为 POSIX sh
        import shutil
        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or shutil.which("bash") or "/bin/sh")
        script = os.path.join(self.source_folder, "test_xfaces.sh")
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)
        cmd = f'"{shell}" "{script}" "{xfaces_bin}" "{preload}"'
        self.run(cmd, env="conanrun")
        # 上游无测试套件（审计见 MANIFEST.yml），如实上报口径
        print('HMBS_TEST_PACKAGE_RESULT={"status":"no_tests",'
              '"framework":"none",'
              '"command":"upstream tarball has no test/check target",'
              '"discovered":1,"executed":1,"passed":1,"failed":0,'
              '"skipped":0,'
              '"reason":"xfaces 3.3 上游无测试套件：tarball 无 tests/ 目录、'
              'Makefile.noimake 仅 all/install/clean；L1 以无效 DISPLAY 真实'
              '执行被测二进制验证动态链接完整性"}')
