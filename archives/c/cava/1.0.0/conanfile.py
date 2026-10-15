#!/usr/bin/env python3
"""Conan recipe for cava 1.0.0 — console audio visualizer (Autotools).

cava 把音频输入做 FFT 后在终端渲染频谱条。上游 tag 归档只有 configure.ac
（无 configure），故 build() 内 autoreconf 自举（适配检查清单 Autotools #1）。

【输入后端按本设备实物能力裁剪】
  上游 Makefile.am 把 input/fifo.c + input/shmem.c（file/FIFO 输入）与
  output/terminal_noncurses.c 无条件编入；alsa/pulse/pipewire/portaudio/
  sndio/oss/jack 全部由 configure 的 AC_CHECK_LIB/PKG_CHECK_MODULES 探测，
  失败仅 AC_MSG_NOTICE 降级（configure.ac:104-323）—— 是上游原生可裁剪项。
  本设备运行期无法打开音频采集节点（见 notes.md 能力面实测），故显式
  --disable-input-* 裁到 file/FIFO 输入，渲染保留 ncurses。
"""
import os
import re

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

# 裁到 file/FIFO 输入：上游支持的原生最小输入面（configure 不报错，仅 NOTICE 降级）
DISABLED_INPUTS = [
    "--disable-input-alsa",
    "--disable-input-pulse",
    "--disable-input-pipewire",
    "--disable-input-portaudio",
    "--disable-input-sndio",
    "--disable-input-oss",
    "--disable-input-jack",
    "--disable-input-coreaudio",
    "--disable-input-coreaudio-tap",
    # SDL/OpenGL 渲染在本平台无窗口环境，且避免误链系统同名库（R26）
    "--disable-output-sdl",
]

# 适配检查清单 Autotools #4：本设备 `uname -s = HarmonyOS`，config.guess(2024-07-27) 不认识，
# 且它在 HMDFS 上 `can't create <TMPDIR>/cgXXXX/dummy.c: Permission denied` 拿不到回退判据
# ⇒ `configure: error: cannot guess build type; you must specify one`（G2 实测第 2 轮）。
# 两侧都显式给：build 用 gnu 三元组、host 用 ohos（⛔ 两边都写 OHOS 会误判）。
# config.sub(2024-07-27) 实测接受 `aarch64-unknown-linux-ohos`。
CANONICAL_ARGS = [
    "--build=aarch64-unknown-linux-gnu",
    "--host=aarch64-unknown-linux-ohos",
]


class CavaConan(ConanFile):
    name = "cava"
    version = "1.0.0"
    description = "cava — console audio visualizer (terminal spectrum analyzer)"
    license = "MIT"
    homepage = "https://github.com/karlstav/cava"
    url = "https://github.com/karlstav/cava"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 只声明本配方真正编入并链接的依赖（R36：声明与实物一致）
        self.requires("fftw/3.3.11")      # configure.ac:341 硬依赖（AC_MSG_ERROR）
        self.requires("iniparser/4.2.6")  # configure.ac:518 硬依赖（AC_MSG_ERROR）
        self.requires("ncurses/6.6")      # 终端渲染（output_ncurses 默认开）

    def build_requirements(self):
        # tag 归档无 configure → 自举需要 automake/libtoolize；
        # configure.ac 用 PKG_CHECK_MODULES → aclocal 需要 pkg.m4
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("pkg-config/0.29.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(DISABLED_INPUTS)
        tc.configure_args.extend(CANONICAL_ARGS)
        tc.generate()

        AutotoolsDeps(self).generate()

    def _patch_generated_env(self):
        """构建期环境两处修补（都在 generate() 之后、任何命令之前做）。

        ① 适配检查清单 Autotools #11：profile 把 SHELL/CONFIG_SHELL 绝对钉到 hnp bash，
           它在 HMDFS 构建目录下 getcwd 必挂（E386 家族）⇒ 对生成的聚合 env 脚本做
           文本替换为 /bin/sh。⛔ 不用二次 save_script 打补丁（聚合器会自 source 递归）。
        ② fftw 以共享库交付（libfftw3.so.3），而 configure 阶段 autoconf 要**真跑**
           conftest 做 "cross compiling" 探测 ⇒ 必须让动态加载器找得到依赖 .so，
           否则 `Error loading shared library libfftw3.so.3` → `cannot run C compiled
           programs`（G2 实测）。conanbuildenv 的 `LD_LIBRARY_PATH=...${VAR:+:$VAR}`
           是追加形态，故只需在进程环境里预置（先例 4ti2/1.6.10、acedb/4.9.62）。
        """
        folder = self.generators_folder or self.build_folder
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".sh"):
                continue
            path = os.path.join(folder, name)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            if "/data/service/hnp/bin/bash" in text:
                save(self, path, text.replace("/data/service/hnp/bin/bash", "/bin/sh"))

        runtime_libdirs = []
        for dep in self.dependencies.values():
            pkg = dep.package_folder
            if not pkg:
                continue
            for libdir in dep.cpp_info.libdirs:
                full = os.path.normpath(os.path.join(pkg, libdir))
                if os.path.isdir(full) and any(
                    f.endswith(".so") or ".so." in f for f in os.listdir(full)
                ):
                    runtime_libdirs.append(full)
        if runtime_libdirs:
            prev = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                runtime_libdirs + ([prev] if prev else [])
            )
            self.output.info(f"[build-env] LD_LIBRARY_PATH += {os.pathsep.join(runtime_libdirs)}")

    @staticmethod
    def _make_var(makefile, key):
        """从 automake 生成的 Makefile 取 `KEY = value`（构建系统自身真相，非 shell 环境变量）。"""
        pat = re.compile(r"^%s\s*=\s*(.*)$" % re.escape(key))
        try:
            with open(makefile, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    m = pat.match(line)
                    if m:
                        return m.group(1).strip()
        except OSError:
            pass
        return ""

    def _run_cavacore_test(self):
        """上游独立测试 cavacore_test（.github/workflows/build-and-test.yml 同款）。

        仿真模式（不定义 AUDIO_INPUT）下自产正弦波、跑 300 次 cava_execute，
        把左右声道输出与 blueprint 比对（±2%），不符即 exit 1 —— 真实断言。
        编译/链接参数全部取自本构建生成的 Makefile（构建系统真相）。
        """
        makefile = os.path.join(self.build_folder, "Makefile")
        src = self.source_folder
        cc = self._make_var(makefile, "CC") or "clang"
        cppflags = self._make_var(makefile, "CPPFLAGS")
        cflags = self._make_var(makefile, "CFLAGS")
        ldflags = self._make_var(makefile, "LDFLAGS")
        libs = self._make_var(makefile, "LIBS")
        for k, v in (("CC", cc), ("CPPFLAGS", cppflags), ("CFLAGS", cflags),
                     ("LDFLAGS", ldflags), ("LIBS", libs)):
            self.output.info(f"[cavacore_test] {k}={v}")

        # 优先复用 automake 已编好的 cavacore 对象（与 cava 二进制同一套 flags）
        obj = os.path.join(self.build_folder, "cava-cavacore.o")
        if not os.path.exists(obj):
            obj = ""

        self.run(
            '%s %s %s -I"%s" -c "%s" -o cavacore_test.o'
            % (cc, cppflags, cflags, src, os.path.join(src, "cavacore_test.c")),
            cwd=self.build_folder,
            env="conanbuild",
        )
        if obj:
            self.output.info("[cavacore_test] 复用 automake 对象 cava-cavacore.o")
        else:
            self.output.info("[cavacore_test] automake 对象未找到，用同套 flags 重编 cavacore.c")
            self.run(
                '%s %s %s -I"%s" -c "%s" -o cavacore-built.o'
                % (cc, cppflags, cflags, src, os.path.join(src, "cavacore.c")),
                cwd=self.build_folder,
                env="conanbuild",
            )
            obj = os.path.join(self.build_folder, "cavacore-built.o")

        self.run(
            '%s -o cavacore_test cavacore_test.o "%s" %s %s -lm'
            % (cc, obj, ldflags, libs),
            cwd=self.build_folder,
            env="conanbuild",
        )
        self.run("./cavacore_test", cwd=self.build_folder, env="conanrun")

    def _fix_hmdfs_umask(self):
        """E011/E114 受控方案（`手册/07 §12.1`、`14-最终防错清单:114` 配方落点）。

        HMDFS 的 UID 映射让 `(umask 077 && mktemp -d "./confXXXXXX")` 得到
        `drwx--S---`，当前进程（uid=20020084）写不进 ⇒
        `./config.status[1013]: can't create ./confXXXXXX/subs1.awk: Permission denied`
        → `config.status: error: could not setup config files machinery`（G2 实测第 3 轮）。
        本机对照探针：`umask 077 → drwx--S--- → touch 拒`；`umask 022 → drwxr-s--x → OK`。

        ⚠ 只把权限位 `077` 改成 `022`，**保留真实临时目录创建**，不换环境、不改上游源文件、
        不进 `patches/`（这是对 autoreconf **生成物** `configure` 的构建期受控改写）。
        须在 `autoreconf -fi` **之后**执行（否则被重新生成覆盖）。
        """
        target = os.path.join(self.source_folder, "configure")
        if os.path.isfile(target) and replace_in_file(
            self, target, "umask 077", "umask 022", strict=False
        ):
            self.output.info("[E011] configure: umask 077 → umask 022（受控方案，保留临时目录创建）")
        # config.guess 自带的三处同款 `umask 077`（经验库/05 §5.3 已记）；本包虽已用
        # --build/--host 绕开 config.guess，仍一并受控改写防回退。
        guess = os.path.join(self.source_folder, "config.guess")
        if os.path.isfile(guess) and replace_in_file(
            self, guess, "umask 077", "umask 022", strict=False
        ):
            self.output.info("[E011] config.guess: umask 077 → umask 022")

    def build(self):
        self._patch_generated_env()

        apply_conandata_patches(self)

        # tag 归档无 `version` 文件（autogen.sh 里 `echo 1.0.0 >version` 才生成），
        # 而 configure.ac 用 m4_esyscmd_s([cat version]) 取 PACKAGE_VERSION ⇒ 先补文件，
        # 否则 `cava -v` 打出空版本号。
        save(self, os.path.join(self.source_folder, "version"), "1.0.0\n")

        # tag 归档无 configure → 自举（适配检查清单 Autotools #1/#8）。
        # 不直接跑 ./autogen.sh（shebang 脚本在 CI worker 被拒，清单 #8），
        # 改为 autoreconf -fi 等价自举；libtoolize/aclocal 由 tool_requires 提供。
        self.run(
            "env -u CONFIG_SHELL SHELL=/bin/sh autoreconf -fi",
            cwd=self.source_folder,
            env="conanbuild",
        )

        # E011/E114 受控方案：必须在 autoreconf 之后（否则被重新生成覆盖）
        self._fix_hmdfs_umask()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

        # R51：上游测试必须在 build() 内真实执行
        # 1) automake 注册口径（Makefile.am 无 TESTS ⇒ 注册 0 项，target 存在且执行）
        #    ⚠ conan 2.29 的 Autotools.make 签名是 `target=`（str），不是 `targets=`
        autotools.make(target="check")
        # 2) 上游独立测试 cavacore_test（blueprint ±2% 断言）
        self._run_cavacore_test()
        # 3) 上游运行期配置测试：file/FIFO 输入 + raw 输出，draw_and_quit=60 帧后
        #    以 zero_test/non_zero_test 断言退出码（cava.c:1721-1731）
        test_cfg = os.path.join(self.source_folder, "example_files", "test_configs")
        for cfg in ("fifo_zero_test", "non_zero_test"):
            self.run(
                './cava -p "%s" > /dev/null' % os.path.join(test_cfg, cfg),
                cwd=self.build_folder,
                env="conanrun",
            )
            self.output.info(f"[cava] 上游配置测试 {cfg}: PASS（退出码 0）")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 上游无 libtool 库，按适配检查清单 Autotools #6 兜底清理 .la
        for root, _dirs, files in os.walk(self.package_folder):
            for f in files:
                if f.endswith(".la"):
                    os.remove(os.path.join(root, f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
