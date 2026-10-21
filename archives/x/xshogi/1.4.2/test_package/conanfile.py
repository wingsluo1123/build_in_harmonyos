#!/usr/bin/env python3
"""Conan test_package — xshogi 1.4.2

xshogi 是纯可执行包（无库、无对外头文件），消费者视角唯一真实的用法就是执行
安装后的 bin/xshogi。test_xshogi.sh 做三件真事（不是空壳）：

  1. 裸环境执行 xshogi --version → 断言退出码 0 且输出含 "xshogi version 1.4.2"
     （版本与上游 configure.ac / 配方一致；同时复现 CI L2 smoke 的条件：
     LD_LIBRARY_PATH/LD_PRELOAD 清空，只依赖包自身的 DT_RPATH=$ORIGIN/../lib）
  2. xshogi -version（单横线形式）同样断言退出码 0 与版本串
  3. 无效 DISPLAY 下 xshogi -help → 断言非 0 退出且 stderr 是 Xt 的显示失败
     诊断：证明二进制真的加载 libXaw/libXmu/libXt/libXext/libX11 并调用
     XtAppInitialize，而不是只打印一行字符串。

第 1 条同时是自包含性断言：设备无系统 X11 动态库（实测 /lib、/lib64、
/usr/lib、/system/lib*、$HOME/usr/local/lib 均无 libX11*/libXaw*），配方
package() 把各依赖 .so 复制到 lib/ 并以 DT_RPATH=$ORIGIN/../lib 链接；若复制或
rpath 失效，裸环境执行会以 127（Error loading shared library ...）失败，
本断言立即暴露。

上游测试：xshogi 1.4.2 无自动化测试套件（源码包无 tests/ 目录，Makefile.am /
Makefile.in 无 TESTS / check_PROGRAMS / check-local），清点证据见
test_package/MANIFEST.yml 的 upstream_test_audit。
"""
import os
import shutil

from conan import ConanFile


class XshogiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["xshogi"]
        binary = os.path.join(dep.package_folder, "bin", "xshogi")

        # HMBS [shell_getcwd]：HNP bash 在 HMFS 工作目录 getcwd 不可用；
        # 用注入的 SHELL/CONFIG_SHELL（/bin/sh），脚本为 POSIX sh 兼容。
        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or shutil.which("bash") or "/bin/sh")
        script = os.path.join(self.source_folder, "test_xshogi.sh")
        # 显式裸环境：不走 conanrun 的 LD_LIBRARY_PATH，验证包自包含
        self.run(f'"{shell}" "{script}" "{binary}"')

        # 上游测试清点（R51）：见 test_package/MANIFEST.yml upstream_test_audit
        print('HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
              '"framework":"none",'
              '"command":"make -n check (no TESTS/check_PROGRAMS)",'
              '"discovered":0,"executed":0,"passed":0,"failed":0,'
              '"skipped":0,'
              '"reason":"xshogi 1.4.2 上游无测试套件：源码包无 tests/ 目录，'
              'Makefile.am/Makefile.in 无 TESTS、check_PROGRAMS、check-local"}')
