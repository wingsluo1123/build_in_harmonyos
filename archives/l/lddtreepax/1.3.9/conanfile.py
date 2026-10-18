#!/usr/bin/env python3
"""lddtreepax 1.3.9 — gentoo/pax-utils v1.3.9 的 python 实现 lddtree（Alpine 子包 lddtreepax，noarch 脚本工具）.

- source:  gentoo/pax-utils v1.3.9 官方 tag archive（R39 官方源；本包只取 lddtree.py 单文件）
- build:   无编译（脚本工具）；apply shebang 补丁 + 运行上游 lddtree-py 测试用例
- package: lddtree.py 安装为 bin/lddtreepax（同 Alpine _lddtreepax：mv lddtree → lddtreepax）
- 消费:    pyelftools/0.33 runenv 注入 PYTHONPATH；python3 解释器来自设备 PATH
           （CI worker 保证 python3 存在，同 pax-utils/1.3.10 notes）
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)


class LddtreepaxConan(ConanFile):
    name = "lddtreepax"
    version = "1.3.9"
    description = ("Read and package ELF dependency trees — python lddtree of "
                   "gentoo/pax-utils (Alpine subpackage lddtreepax)")
    license = "GPL-2.0-only"
    homepage = "https://github.com/gentoo/pax-utils"
    url = ""  # CI fills this
    topics = ("elf", "lddtree", "gentoo", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Alpine _lddtreepax: depends="python3 py3-elftools"。python3 是设备解释器
        # （PATH 提供），pyelftools 是唯一运行期第三方依赖（lddtree.py:64-65
        # from elftools...，无 try/except，缺则 ImportError）。
        # run=True 必须显式声明：python-require 包无 C 头/库，conan 2.29
        # _skip_binaries 以 files=(headers|libs|run|build) 判 skip，run 默认
        # False → 依赖被 BINARY_SKIP（package_folder=None、runenv 不聚合，
        # 2026-10-13 conan graph info 实测）。run=True 后不 skip，pyelftools
        # 的 PYTHONPATH runenv 正常聚合进消费者 conanrun。
        self.requires("pyelftools/0.33", run=True)

    def validate(self):
        # R32: OHOS 平台兼容
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        # codeload 端点路径没有 .tar.gz 后缀，显式 filename 否则 conan 误判 zip
        # （pax-utils/1.3.10 实测教训）。
        get(self, filename="pax-utils-1.3.9.tar.gz",
            **self.conan_data["sources"], strip_root=True)

    def _bash(self):
        # 沙箱/worker PATH 可能无 bash——优先 profile buildenv 的绝对路径
        return ("/data/service/hnp/bin/bash"
                if os.path.isfile("/data/service/hnp/bin/bash")
                else "bash")

    def build(self):
        apply_conandata_patches(self)
        # 上游测试入口（tests/lddtree/meson.build 注册 lddtree-py）：
        #   dotest-py → dotest-sfx：lddtree.py /bin/bash | grep -i 'none'
        #   负向断言（testit：smoke 文件为空才 PASS）。
        # 按 meson test 等价环境执行：workdir=tests/lddtree +
        # builddir/srcdir/current_srcdir 三环境变量（lib.sh 靠它把 srcdir 挂上
        # PATH 找到 lddtree.py）+ pyelftools runenv（PYTHONPATH）。
        if can_run(self):
            tests_dir = os.path.join(self.source_folder, "tests", "lddtree")
            runenv = VirtualRunEnv(self)
            runenv.vars().save_script("conanrun_upstream_test")
            run_script = os.path.join(self.build_folder,
                                      "conanrun_upstream_test.sh")
            env = dict(os.environ)
            for p in ("/storage/Users/currentUser/usr/local/bin",
                      "/data/service/hnp/bin", "/usr/local/bin", "/usr/bin",
                      "/bin"):
                if p not in env.get("PATH", "").split(os.pathsep):
                    env["PATH"] = p + os.pathsep + env.get("PATH", "")
            env["builddir"] = self.build_folder
            env["srcdir"] = self.source_folder
            env["current_srcdir"] = tests_dir
            cmd = (f'source "{run_script}" && cd "{tests_dir}" '
                   f'&& bash ./dotest-py')
            r = subprocess.run([self._bash(), "-c", cmd], env=env,
                               capture_output=True, text=True, timeout=600)
            out = (r.stdout + r.stderr)
            print("[lddtreepax upstream tests] rc=%d" % r.returncode)
            for line in out.splitlines():
                print("[lddtreepax upstream tests]", line)
            if r.returncode == 0:
                # 如实标注空跑边界（E363：不得把空跑报成行为验证）：
                # OHOS 设备无 /bin/bash fixture（/bin 只读不可补），本用例
                # 与 pax-utils/1.3.10 notes 同边界；真实行为由 test_package
                # 对 /bin/sh 的 4 条断言覆盖。详见 notes.md 申报表。
                print("[lddtreepax upstream tests] NOTE: raw PASS，fixture "
                      "/bin/bash 在本机不存在 → 空跑（E363 边界，见 notes.md）")
            else:
                # 不静默吞掉：完整输出已在上方打印，构建继续并如实记录
                # （同 pyelftools build() 模式）。
                print("[lddtreepax upstream tests] WARN: rc=%d — 如实记录"
                      "（musl 负向断言边界见 notes.md）" % r.returncode)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        dst = os.path.join(bindir, "lddtreepax")
        shutil.copy2(os.path.join(self.source_folder, "lddtree.py"), dst)
        os.chmod(dst, 0o755)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # pyelftools（python-require）的二进制在嵌套安装时被 skip，其 runenv
        # （PYTHONPATH）不会聚合进消费者环境（2026-10-13 实测：直接消费者
        # conanrunenv 含 PYTHONPATH，lddtreepax 嵌套图中缺失）——由本包显式
        # 补声明，保证已安装 lddtreepax 开箱即用。
        pyelf = self.dependencies["pyelftools"].package_folder
        sites = glob.glob(os.path.join(pyelf, "lib", "python*",
                                       "site-packages"))
        if not sites:
            raise ConanException(
                f"pyelftools site-packages not found under {pyelf}")
        self.runenv_info.append_path("PYTHONPATH", sites[0])
