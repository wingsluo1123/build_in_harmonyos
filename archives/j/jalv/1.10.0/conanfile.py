#!/usr/bin/env python3
"""Conan recipe — jalv 1.10.0 (LV2 plugin host, meson).

jalv 是 LV2 生态的命令行插件宿主：用 lilv 发现/加载插件，经 JACK（或
PortAudio）驱动插件跑实时音频处理，并支持控制端口、状态保存、UI 承载
（suil）。上游构建系统为 meson，属 drobilla/lv2 全家桶的 meson 直驱
一族，交叉适配沿用本仓 meson 两步法（见 notes.md 与
skills/meson-cross-pkgconfig）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.0"


class JalvConan(ConanFile):
    name = "jalv"
    version = "1.10.0"
    description = "jalv: an LV2 plugin host for JACK (console) / GUI"
    license = "ISC"
    url = "https://download.drobilla.net/"
    homepage = "https://drobilla.net/software/jalv.html"
    topics = ("lv2", "audio", "plugin", "host", "jack")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # 补丁必须显式导出，cache 内构建时才能取到 patches/ 目录。
    exports_sources = "patches/*"

    # lv2 族的 .pc 只由显式 requires 的包生成（meson-cross-pkgconfig 坑④），
    # 因此这里把 jalv 直接消费头文件/库的包全部显式声明：lv2（宿主契约头）、
    # lilv（发现/加载/状态）、sratom+sord+serd（lilv 的 URD 栈，经 lilv 传递
    # 钉版，不重复显式钉以免版本冲突）、zix（语义/容器工具）、suil（UI 承载）、
    # jack（唯一有运行时意义的驱动后端，见 notes.md）。
    requires = (
        "lv2/1.18.11-git",
        "lilv/0.28.0",
        "sratom/0.6.22",
        "sord/0.16.22",
        "zix/0.8.1-git.1",
        "suil/0.10.26",
        "jack/1.9.22",
    )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jalv supports Linux/OHOS only, got {self.settings.os}")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"jalv recipe targets armv8 cross builds, got "
                f"{self.settings.arch}")

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

        tc = MesonToolchain(self)
        # CI worker 的 PATH 不含 llvm-ar/llvm-ranlib，meson 在 project()
        # 阶段探测链接器会失败：从 profile 的编译器绝对路径推导同目录
        # 工具写进 machine file 的 [binaries]（suil/c-rbtree 同款先例）。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") if compilers else None
        if cc:
            tool_dir = os.path.dirname(cc)
            tc.binaries["ar"] = os.path.join(tool_dir, "llvm-ar")
            tc.binaries["ranlib"] = os.path.join(tool_dir, "llvm-ranlib")
        tc.project_options.update({
            # 坑①：上游 meson_options.txt 无 shared 选项，库形态只能走
            # meson 内建 default_library（shared|static）。
            "default_library": "static",
            # OHOS PC 无 X11/GTK/Qt 窗口系统接入，GUI 前端全部关闭；
            # 控制台前端是 LV2 宿主的主用途，保留。
            "gtk3": "disabled",
            "qt5": "disabled",
            "qt6": "disabled",
            "man": "disabled",
            # 驱动后端：portaudio/19.7.0 在 OHOS 上按配方关闭了 ALSA/JACK/
            # OSS 全部 host API（见其 notes.md），无法真正出流；jack 有
            # 完整 libjack + jackd，因此选 jack 且显式关 portaudio。
            "jack": "enabled",
            "portaudio": "disabled",
            "tests": "enabled",
            "lint": False,
        })
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        # CI worker 资源紧张时 ninja 首个 spawn 即 EAGAIN（posix_spawn:
        # Resource temporarily unavailable），与源码无关；按 -j 4→2→1
        # 逐级限流重试缓解，最终仍失败则原样抛出最后一次错误。
        last_err = None
        for jobs in (4, 2, 1):
            try:
                self.run(f"meson compile -C {self.build_folder} -j {jobs}",
                         env="conanbuild")
                last_err = None
                break
            except Exception as exc:  # conan ConanException
                last_err = exc
                self.output.warning(
                    f"meson compile -j {jobs} failed; retrying with lower "
                    f"parallelism (worker spawn pressure): {exc}")
        if last_err is not None:
            raise last_err

        # 上游测试：meson 只提供 test/test_symap（symap 单元测试，纯计算
        # 无 IO）。构建机与目标同为 aarch64 OHOS，可直接执行——本机实测
        # 通过，失败即真失败，不做吞错。lint 目标（autoship/cppcheck/reuse/
        # clang-format）属开发者环境工具，-Dlint=false 关闭。
        test_bin = os.path.join(self.build_folder, "test", "test_symap")
        if os.path.exists(test_bin):
            self.run(test_bin, env="conanbuild")
        else:
            raise ConanInvalidConfiguration(
                "upstream test_symap missing: meson tests must be enabled")

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # OHOS 代码签名陷阱：meson install 会用 RPATH/文件布局重写已链接
        # 的 ELF，重写后原本的 codesign 段失效 —— 直接执行装好的
        # bin/jalv 报 EPERM "Operation not permitted"（构建目录里的同名
        # 产物可执行，实证见 notes.md）。修法：安装完成后对包内每个 ELF
        # 重新自签名，并用 llvm-readelf 复验 codesign 段确实存在。
        self._sign_ohos_elfs()

    def _sign_ohos_elfs(self):
        import glob
        import shutil
        import subprocess

        signer = shutil.which("binary-sign-tool") or \
            "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or \
            "/data/service/hnp/bin/llvm-readelf"
        if not (os.path.isfile(signer) and os.path.isfile(readelf)):
            raise ConanException(
                "OHOS signing tools (binary-sign-tool/llvm-readelf) missing: "
                "packaged ELFs would be non-executable")

        targets = []
        for pattern in ("bin/*", "lib/*.so*", "lib/jack/*.so*"):
            for path in glob.glob(os.path.join(self.package_folder, pattern)):
                if os.path.isfile(path) and not os.path.islink(path):
                    targets.append(path)
        if not targets:
            raise ConanException("no packaged ELF found to sign")

        for path in sorted(targets):
            signed = path + ".signed"
            subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", signed,
                 "-selfSign", "1"],
                check=True, capture_output=True, timeout=120)
            os.replace(signed, path)
            os.chmod(path, 0o755)
            sections = subprocess.run([readelf, "-SW", path],
                                      check=True, capture_output=True,
                                      text=True, timeout=60).stdout
            if ".codesign" not in sections:
                raise ConanException(
                    f"codesign section missing after signing: {path}")
            self.output.info(f"signed packaged ELF: {path}")

    def package_info(self):
        # application 类型无 cpp_info 语义，仅声明 bin 目录供 runenv 使用。
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
