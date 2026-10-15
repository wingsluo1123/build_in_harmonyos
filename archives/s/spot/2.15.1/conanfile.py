#!/usr/bin/env python3
"""Conan recipe — spot 2.15.1 (autotools)"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SpotConan(ConanFile):
    name = "spot"
    version = "2.15.1"
    description = "Library and tools for manipulation of LTL/PSL formulas and omega-automata"
    license = "GPL-3.0-or-later"
    homepage = "https://spot.lre.epita.fr/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("spot is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8 (aarch64)")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _usable_shell():
        # profile [buildenv] 钉死的 /data/service/hnp/bin/bash 在部分 HMBS 主机缺失，
        # 导致 configure 以 Error 127 失败；优先取真实存在的 shell（先例 siscone）。
        for cand in ("/bin/sh", "/data/service/hnp/bin/bash", "/bin/bash"):
            if os.path.isfile(cand):
                return cand
        return "sh"

    def _usable_tmpdir(self):
        # OHOS /tmp 为只读挂载（E002），构建期内使用 build 目录下的可写 tmp。
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        return tmp

    def _restore_script_modes(self):
        # conan 解压不保留可执行位（E490）：configure/辅助脚本/测试脚本必须以
        # +x 落盘，否则 configure 或 make check 以 Error 126 (Permission denied) 失败。
        # 覆盖：三级 configure（顶层/buddy/ltdl）、autotools 辅助脚本（any depth）、
        # tests/**/*.test 与 tests/**/*.py（make check 直接执行）。
        script_names = ("configure", "config.guess", "config.sub", "install-sh",
                        "missing", "compile", "depcomp", "ylwrap", "test-driver",
                        "ar-lib", "ltmain.sh", "mkinstalldirs")
        paths = []
        for name in script_names:
            paths.extend(glob.glob(os.path.join(self.source_folder, "**", name),
                                   recursive=True))
        for pattern in (("tests", "**", "*.test"), ("tests", "**", "*.py")):
            paths.extend(glob.glob(os.path.join(self.source_folder, *pattern),
                                   recursive=True))
        for path in paths:
            if os.path.isfile(path):
                os.chmod(path, 0o755)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 关闭 SWIG/python 绑定：避免构建期 python 依赖（本包仅库与 CLI 工具）。
        tc.configure_args.append("--disable-python")
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
        if self.options.get_safe("fPIC"):
            tc.extra_cflags.append("-fPIC")
            tc.extra_cxxflags.append("-fPIC")
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-musl",
                "--host=aarch64-unknown-linux-musl",
            ])
        tc.generate()
        # save_script 生成的脚本在 [buildenv] 之后加载，会覆盖 profile 中不可用的 shell/TMPDIR。
        shell = self._usable_shell()
        env = Environment()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        env.define("TMPDIR", self._usable_tmpdir())
        env.vars(self, scope="build").save_script("spot_hmos_env")

    def build(self):
        self._restore_script_modes()
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            # OHOS 拒绝对带 #! 的脚本直接 execve（EACCES，sh 报 Permission
            # denied / Error 126）；真机实测：同权限位下 ELF 可执行、
            # `sh configure` 正常、全新 755 脚本同样被拒。此处复刻
            # Autotools.configure() 的调用并加显式 shell 前缀；参数串取自
            # helper 构造函数自 toolchain json 读入的 _configure_args，
            # 与原生路径逐字一致。
            configure_script = os.path.join(self.source_folder, "configure")
            self.run('{} "{}" {}'.format(self._usable_shell(), configure_script,
                                         autotools._configure_args or ""))
        else:
            autotools.configure()
        autotools.make(args=["-j4"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool *.la 包装文件对消费者无用，且上游 spot.spec 亦排除（%exclude）。
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)
        self._sign_package_elfs()
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def _sign_package_elfs(self):
        # OHOS 要求共享库/可执行文件带有效代码签名；构建或安装期被改写的 ELF
        # 链接期自签名失效，按 E077 流程重签：llvm-objcopy 去 .codesign 段 →
        # binary-sign-tool -selfSign 重签 → 恢复权限位（先例 libwebp 1.6.0.1）。
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        targets = []
        for sub in ("lib", "bin"):
            for path in sorted(glob.glob(os.path.join(self.package_folder, sub, "**", "*"),
                                         recursive=True)):
                if not os.path.isfile(path) or os.path.islink(path):
                    continue
                with open(path, "rb") as fh:
                    if fh.read(4) == b"\x7fELF":
                        targets.append(path)
        for path in targets:
            mode = os.stat(path).st_mode
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{path}" -outFile "{path}.signed" -selfSign 1')
            os.replace(f"{path}.signed", path)
            os.chmod(path, mode)

    def package_info(self):
        self.cpp_info.libs = ["spot", "bddx"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("pkg_config_name", "libspot")
