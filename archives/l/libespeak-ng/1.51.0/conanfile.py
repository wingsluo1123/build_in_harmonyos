#!/usr/bin/env python3
"""Conan recipe — libespeak-ng 1.51.0 (eSpeak NG Text-to-Speech, Autotools).

eSpeak NG 是开源语音合成引擎（共振峰合成），支持 100+ 语言/方言，
提供 libespeak-ng 库与 espeak-ng / speak-ng 命令行工具。

源码选择（R39 官方源）：
    使用 GitHub 官方 git archive tarball
    https://github.com/espeak-ng/espeak-ng/archive/refs/tags/1.51.tar.gz
    而非 releases/download/1.51/espeak-ng-1.51.tar.gz ——
    后者（上游 release 打包件）**缺少**：
      1. src/libespeak-ng/*.h 与 src/speechPlayer/src/*.h（28+6 个内部头文件）
      2. phsource/ dictsource/ espeak-ng-data/（全部字典/音素数据源）
    git archive tarball 内容完整，可正常构建库、工具与数据。

OHOS 适配要点：
- config.guess/config.sub：automake 1.16.5 自带版本（2023-08-22）已原生
  识别 HarmonyOS（config.guess → aarch64-unknown-linux-ohos），无需补丁。
- E114：configure/config.status 的 `umask 077 && mktemp -d` 临时目录在
  HMDFS 上权限被拒（Permission denied）→ 统一改写为 umask 022。
- git archive tarball 不含 configure（需 autogen.sh）：
  automake 严格要求 ChangeLog.md（上游只有 CHANGELOG.md）→ 复制生成
  ChangeLog.md / NEWS / README 后 `automake --foreign`（绕开 GNU 标准）。
- pcaudiolib（音频输出）：来自制品仓 pcaudiolib/1.3，autoconf 探测
  pcaudiolib/audio.h 自动启用，配置阶段通过 Conan 依赖注入 include/lib。
- 字典数据（phsource→phontab/phondata、dictsource→112 个 *_dict）由
  espeak-ng 自身 --compile-phonemes / --compile=<lang> 编译生成，
  构建期间自动完成并随 `make install` 安装到 share/espeak-ng-data。

settings.os 判断遵循 R32（in ("Linux", "OHOS")）；build() 全部依赖来自
Conan 依赖注入 / AutotoolsToolchain，不依赖未定义 shell 环境变量（R33）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibespeakngConan(ConanFile):
    name = "libespeak-ng"
    version = "1.51.0"
    description = ("eSpeak NG — open source text-to-speech synthesizer based on "
                   "formant synthesis, supporting 100+ languages/accents "
                   "(library + espeak-ng/speak-ng CLI)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/espeak-ng/espeak-ng"
    url = "https://github.com/espeak-ng/espeak-ng"

    # 库 + CLI 混合包：package_type 必须为 library（application 类型会让
    # CMakeDeps 生成空 INCLUDE_DIRS，下游 find_package 找不到头文件），
    # 命令行工具通过 cpp_info.bindirs + 软件级 commands.json 声明（R38）。
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "patches/*"

    def validate(self):
        # R32: OHOS 与 Linux 同样处理；os 判断必须用 in (...)
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libespeak-ng does not support os={self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # pcaudiolib：espeak-ng 的便携音频输出后端（制品仓已发布，含 OHOS binary）
        self.requires("pcaudiolib/1.3")

    def build_requirements(self):
        # autogen（libtoolize/aclocal/automake/autoconf）需要 GNU autotools 工具链；
        # CI worker（最小 OHOS 镜像）缺 automake/libtoolize（仅 /data/service/hnp/bin
        # 有 autoconf 套件），必须 tool_requires 拉入（与 abiword/pcaudiolib 同款，
        # 均已 CI 验证）。tool_requires 用 build profile 解析，conan create 需
        # -pr:h 与 -pr:b 同时传入（AutotoolsToolchain 惯例）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        # Autotools in-tree 构建：espeak-ng 由源码根生成 Makefile 并在同目录
        # configure/make/install（源码即构建目录）。basic_layout(src_folder=".")
        # 会将 build 设为 build-release，导致 Autotools.install() 的 make 在
        # build-release 执行（该目录无 Makefile → "No rule to make target
        # 'install'"）。强制 build 与 source 同目录（in-tree），确保
        # configure/make/install 三者在同一目录（generate 在 build/conan 下）。
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = os.path.join(self.folders.build, "conan")
        self.cpp.build.bindirs = ["."]
        self.cpp.build.libdirs = ["."]

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _autogen(self):
        """git archive tarball 不含 configure —— 生成 autotools 构建文件。

        1. automake 严格要求 GNU 标准文件（ChangeLog.md 等）；上游只提供
           CHANGELOG.md，缺失会报 `required file './ChangeLog.md' not found`
           → 从 CHANGELOG.md 复制生成 ChangeLog.md / NEWS / README。
        2. `automake --foreign` 绕开 GNU 标准校验（GNU 模式还要求
           install-sh 等 GNU 专有布局）。
        3. libtoolize --copy / autoheader / autoconf 生成 configure 与
           config.guess / config.sub（automake 1.16.5 版本已含 OHOS 支持）。
        """
        srcdir = self.source_folder
        changelog = os.path.join(srcdir, "CHANGELOG.md")
        for target in ("ChangeLog.md", "NEWS"):
            dst = os.path.join(srcdir, target)
            if os.path.exists(changelog) and not os.path.exists(dst):
                # HMDFS 上软链接不稳定（R3/E…），复制实际文件
                copy(self, "CHANGELOG.md", src=srcdir, dst=dst)
        readme = os.path.join(srcdir, "README.md")
        if os.path.exists(readme) and not os.path.exists(os.path.join(srcdir, "README")):
            copy(self, "README.md", src=srcdir, dst="README")
        if not os.path.exists(os.path.join(srcdir, "AUTHORS")):
            with open(os.path.join(srcdir, "AUTHORS"), "w", encoding="utf-8") as f:
                f.write("eSpeak NG contributors\n")

        os.chdir(srcdir)
        self.run("libtoolize --copy", shell=True)
        self.run("aclocal -I m4", shell=True)
        self.run("autoheader", shell=True)
        self.run("automake --add-missing --copy --foreign", shell=True)
        self.run("autoconf", shell=True)

    def _fix_umask(self):
        """E114：configure/config.status 用 `umask 077 && mktemp -d` 建临时目录，
        HMDFS（固定 660）拒绝写入 → Permission denied / config.status error。

        统一改写 umask 077 → umask 022（与 pcaudiolib / asterisk / speech-dispatcher
        同款；参考 SKILL archives/p/pcaudiolib/1.3/conanfile.py）。
        """
        for fname in ("configure", "config.status"):
            fpath = os.path.join(self.source_folder, fname)
            if not os.path.exists(fpath):
                continue
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if "umask 077" in content:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(content.replace("umask 077", "umask 022"))

    def _chmod_helpers(self):
        """E490：Autotools helper scripts 在 HMDFS（chmod 被忽略/权限固定）上
        可能丢失执行位，导致 `./configure: Permission denied` 或
        `automake: ...: cannot execute`。显式 chmod +x 恢复执行位（幂等）。

        覆盖 configure 及 autogen 生成的辅助脚本（config.guess/config.sub/
        install-sh/missing/compile/depcomp/ltmain.sh）与 configure 同级。
        """
        helpers = ("configure", "config.guess", "config.sub", "install-sh",
                   "missing", "compile", "depcomp", "ltmain.sh")
        for h in helpers:
            p = os.path.join(self.source_folder, h)
            if os.path.isfile(p):
                try:
                    os.chmod(p, 0o755)
                except OSError as exc:
                    self.output.info(f"chmod {h}: {exc} (ignored)")

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            # 沿用 pcaudiolib（同 espeak-ng 生态、CI 已验证）的三元组惯例：
            # CI worker 为 x86_64 Linux 交叉到 aarch64 OHOS（clang 交叉工具链）。
            tc.configure_args.extend([
                "--build=x86_64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
                # 交叉编译下 AC_FUNC_MALLOC/REALLOC 无法实测（musl 正常），
                # 显式置 yes（与 pcaudiolib 同款）。
                "ac_cv_func_malloc_0_nonnull=yes",
                "ac_cv_func_realloc_0_nonnull=yes",
            ])
            # E1031：AutotoolsToolchain 按 build_type=Release 自动注入
            # CFLAGS=-O3 / CXXFLAGS=-O3——OHOS 上 -O3 优化级触发 espeak-ng
            # `--compile=<lang>`（字典编译）在 FUTEX 上死锁（挂起 0 CPU、
            # --version 正常但 --compile 卡死）。实测验证：-O3+NDEBUG 二进制
            # --compile=af 挂起；追加 -O2/-UNDEBUG（覆盖 -O3/NDEBUG）后字典
            # 编译与合成均正常（112 字典 + 70KB WAV）。AutotoolsToolchain 的
            # cflags/cxxflags 只读，但 extra_cflags/extra_cxxflags 追加在
            # build_type_flags(-O3) 之后（尾者生效），extra_defines 追加在
            # ndebug(-DNDEBUG) 之后，故用 -O2/-UNDEBUG 完成覆盖。
            tc.extra_cflags.append("-O2")
            tc.extra_cxxflags.append("-O2")
            # NDEBUG 覆盖：extra_defines 元素会被自动加 -D 前缀（-D-UNDEBUG
            # 非法），因此 -UNDEBUG 通过 extra_cflags/CXXFLAGS 追加（-U 放在
            # -DNDEBUG 之后取消定义，实测有效）。
            tc.extra_cflags.append("-UNDEBUG")
            tc.extra_cxxflags.append("-UNDEBUG")
        # espeak-ng 1.51 autoconf 已能自动探测 pcaudiolib/sonic；
        # 显式关闭未适配的可选后端，保持构建确定性与最小依赖面。
        tc.configure_args.append("--without-sonic")
        tc.configure_args.append("--without-mbrola")
        # speechPlayer 是 NVDA speechPlayer 音频可视化/播放器模块（C++）：
        # ① 历史适配（archives/e/espeak-ng/1.51）与 OHOS clang 15 存在 C++
        #    歧义/优化问题（本机 conan 构建的 libespeak-ng.so 在
        #    espeak_Initialize 时挂起 procmgr_wait，去掉 speechPlayer 后正常）；
        # ② OHOS 无音频输出设备，speechPlayer 的波形播放功能无实际用途；
        # ③ Klatt 共振峰合成（核心 TTS 引擎）与 speechPlayer 独立，保留。
        # 关闭后 libespeak-ng 主库、espeak-ng/speak-ng CLI 与全部语言字典
        # 数据仍完整构建，espeak_Synth 通过 AUDIO_OUTPUT_RETRIEVAL 输出波形。
        tc.configure_args.append("--without-speechplayer")
        if self.settings.os == "OHOS" and not self.options.shared:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._chmod_helpers()
        self._autogen()
        self._chmod_helpers()
        self._fix_umask()
        autotools = Autotools(self)
        autotools.configure()
        # 字典/音素数据（phsource + 112 个语言字典）在 all-am 阶段由
        # espeak-ng 自身 --compile* 编译生成，单线程可预期完成。
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # E1031b：Autotools.install() 默认追加 -j<njobs>（本机 20），HMDFS 上
        # GNU make jobserver 用 mkfifo 创建管道被拒（Operation not permitted）
        # → 显式 -j1 单线程安装（build() 编译同理，见 _make 目标 -j1）。
        autotools.install(args=["-j1"])
        # libtool 安装的 .la 文件引用构建机绝对路径，剔除
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for f in os.listdir(lib_dir):
                if f.endswith(".la"):
                    os.remove(os.path.join(lib_dir, f))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["espeak-ng"]
        self.cpp_info.includedirs = ["include"]
        # 命令行工具：espeak-ng / espeak / speak-ng / speak
        self.cpp_info.bindirs = ["bin"]
        # espeak-ng-data（112 个语言字典 + 音素数据），运行期必需
        self.cpp_info.resdirs = ["bin", "share"]
        self.cpp_info.datadirs = ["share"]
        self.cpp_info.set_property("espeak_ng_data_dir",
                                   "share/espeak-ng-data")
