#!/usr/bin/env python3
"""Conan test_package — xdu 3.0

L1 test: xdu 是 X11 图形工具（无库可链接），test_xdu.sh 真实执行被测包
二进制（R34 实质依赖被测包）。xdu 无 -version 选项，-help 在
XtAppInitialize（xsetup）之后才处理；无 DISPLAY 环境运行 xdu 会先走
XtAppInitialize，报 "Can't open display" 并 exit(1) —— 证明
libXaw7/libXt/libXext/libX11 完整动态链接并可加载（缺库时 loader 报
"Error loading shared library" + exit 127，测试脚本据此区分）。

真机运行时库（xeyes 第 4 轮根因同款）：libX11.so.6 的 DT_NEEDED 需要
libxcb.so.1/libXau.so.6，libxcb 传递依赖 libXdmcp.so.6。主配方已声明
libxcb/1.17.0 + libxau/1.0.11 run=True，conanrun 环境注入其 libdir 到
LD_LIBRARY_PATH；按 HMBS [stale_runtime_library] 诊断 loader 可能忽略
LD_LIBRARY_PATH，再从依赖包文件夹取绝对路径经 LD_PRELOAD 注入
（依赖序 libXau → libXdmcp → libxcb → libX11 → libXext）。
"""
import os
import shutil

from conan import ConanFile


class XduTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_so(self, dep, soname_prefix):
        """在依赖包里找 SONAME 前缀对应的 .so 文件（xeyes 同款）。

        conan 缓存中的库可能是 .so -> .so.1 -> .so.1.x.y 符号链接链，
        HMFS 对 symlink 物化不可靠（E050），LD_PRELOAD 优先指向实体文件
        （loader 按 SONAME 登记，效果等价）；仅当全是 symlink 时才退回
        符号链接路径。
        """
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
        """xdu 运行时共享库补齐（conan 依赖链 libX11/libXext/libXaw/libXt）。

        libX11.so.6 运行时需要 libxcb.so.1 + libXau.so.6（libxcb 自身又
        链接 libXau.so.6 / libXdmcp.so.6），libXext.so.6 链接 libX11.so.6，
        libXt/libXmu/libXpm/libXaw 按依赖序跟进。依赖序拼接 LD_PRELOAD：
        libXau → libXdmcp → libxcb → libX11 → libXext → libXmuu → libXmu
        → libXt → libXpm → libXaw。
        """
        found = []
        for name, prefix in (("libxau", "libXau.so.6"),
                             ("libxdmcp", "libXdmcp.so.6"),
                             ("libxcb", "libxcb.so.1"),
                             ("libx11", "libX11.so.6"),
                             ("libxext", "libXext.so.6"),
                             ("libxmu", "libXmu.so.6"),
                             ("libxt", "libXt.so.6"),
                             ("libxpm", "libXpm.so.4"),
                             ("libxaw", "libXaw7.so.7")):
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            so = self._find_so(dep, prefix)
            if so:
                found.append(so)
        return ":".join(found)

    def test(self):
        dep = self.dependencies["xdu"]
        xdu_bin = os.path.join(dep.package_folder, "bin", "xdu")

        # HMBS [shell_getcwd]：使用注入的 SHELL/CONFIG_SHELL（/bin/sh），
        # 不硬编码 /data/service/hnp/bin/bash。脚本为 POSIX sh（xidle 同款）。
        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or shutil.which("bash") or "/bin/sh")
        script = os.path.join(self.source_folder, "test_xdu.sh")
        # HMBS [stale_runtime_library]：loader 可能忽略 LD_LIBRARY_PATH，
        # 对测试命令用 LD_PRELOAD 指向依赖包中的本次构建共享库（绝对路径）。
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)
        cmd = f'"{shell}" "{script}" "{xdu_bin}" "{preload}"'
        self.run(cmd, env="conanrun")
        # HMBS_TEST_PACKAGE_RESULT 由 test_xdu.sh 在真实断言结束后打印。
        # 上游套件审计结论（详见 test_package/MANIFEST.yml）：xdu 3.0
        # 发布包无自动化测试——Imakefile 仅 ComplexProgramTarget/InstallAppDefaults
        # 目标，无 check/TESTS；源码树无 tests/ 目录；xdu.man 无测试章节。
        print('HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
              '"framework":"none",'
              '"command":"make check (no check target in Imakefile)",'
              '"discovered":0,"executed":0,"passed":0,"failed":0,'
              '"skipped":0,'
              '"reason":"xdu 3.0 上游无测试套件：Imakefile 仅有 '
              'ComplexProgramTarget(xdu)/InstallAppDefaults(XDu) 目标，'
              '无 check/TESTS 目标、无 tests/ 目录、xdu.man 无测试章节"}')
