#!/usr/bin/env python3
"""Conan recipe for xroar 1.11 — Dragon 32/64 & Tandy CoCo emulator.

XRoar (Ciaran Anscomb) emulates the Dragon 32/64, Tandy Color Computer
(CoCo 1/2/3) and Tandy MC-10. Upstream 1.11 release tarball:
http://www.6809.org.uk/xroar/download/1.11/xroar-1.11.tar.gz

Build system: autotools; the release tarball ships a pre-generated
`configure`/`Makefile.in` (no autoreconf needed) and pre-generated font
tables (mc6847/font-*.c/.h, tcc1014/font-gime.c/.h).

OHOS 适配要点（headless / null-UI 构建）
----------------------------------------
1. **零必需依赖**：所有 GUI/音频/存储后端（GTK2/3、SDL2/3、X11、OpenGL、
   ALSA/OSS/Pulse/CoreAudio/JACK、sndfile、TRE、zlib、libpng、evdev、
   joydev）都是可选集成，configure 检测失败即优雅降级（PKG_CHECK_MODULES
   的 `:,:` fallback）。src/null/ui_null.c 与 null 音频驱动始终编译，
   因此显式 --without-* 全部禁用，得到确定性的无界面 xroar 可执行文件，
   不引入任何依赖库适配任务。
2. **E007 config.guess/config.sub**：tarball 自带的 GNU config.guess 没有
   HarmonyOS 分支（uname -s = "HarmonyOS"），configure 第一阶段即报
   "cannot guess build type"。build() 内补 `*:HarmonyOS:*:*)` 分支与
   __OHOS__ libc 探测（R1：不用 --build/--host 伪造三元组）。
3. **E114 configure umask**：生成的 configure 里
   `(umask 077 && mktemp -d ...)` 在 HMDFS 上产出 drwx--S--- 目录，
   config.status 写 subs1.awk 报 Permission denied；去掉 umask 077。
4. **font2c 陷阱**：src/Makefile.am 把预生成字体表列为 BUILT_SOURCES，
   其规则需要为构建宿主编译 tools/font2c，而 font2c 链接 SDL +
   SDL2_image（tools/Makefile.am font2c_LDADD）。tarball 已带全部生成物，
   build() 在 make 前 touch 这 6 个文件使规则永不触发，避免引入 SDL。
5. 无上游自动化测试套件（无 tests/、无 make check 目标）；验证方式为
   完整构建 xroar + test_package 消费者冒烟测试（--version / --help）。

运行时注意：模拟 ROM 镜像不在源码包内，真机交互运行需用户提供 ROM；
本包的 test_package 只验证 CLI 行为（版本打印、无 ROM 时的明确报错）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, load, replace_in_file
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

_SOURCE_URL = "http://www.6809.org.uk/xroar/download/1.11/xroar-1.11.tar.gz"
_SOURCE_SHA256 = "70270805ebd52c0b62237cc2f28b32b5c7df9764d10a7c7190de584cfc6e95af"

# 预生成字体表（BUILT_SOURCES），touch 使 make 不再尝试用 font2c 重新生成
_FONT_TABLES = (
    "src/mc6847/font-6847.c",
    "src/mc6847/font-6847.h",
    "src/mc6847/font-6847t1.c",
    "src/mc6847/font-6847t1.h",
    "src/tcc1014/font-gime.c",
    "src/tcc1014/font-gime.h",
)

# 显式禁用的可选集成后端（全部有 null/无实现降级）
_CONFIGURE_DISABLE = (
    "gtk2", "gtk3", "gtkgl", "sdl2", "sdl3", "cocoa",
    "alsa", "oss", "pulse", "coreaudio", "jack",
    "evdev", "joydev", "sndfile", "tre", "zlib", "libpng",
    "pthreads",
)


class XroarConan(ConanFile):
    name = "xroar"
    version = "1.11"
    description = (
        "XRoar 1.11: Dragon 32/64, Tandy CoCo 1/2/3 and MC-10 emulator "
        "(headless null-UI build)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.6809.org.uk/xroar/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "xroar/1.11 in this recipe targets HarmonyOS PC (OHOS)/Linux only"
            )

    def source(self):
        # URL/SHA256 直接放在配方内，避免 CI conandata.yml 预下载路径的
        # BUILD_DIR 缺陷（见 notes.md / 仓库知识草稿）。
        get(self, url=_SOURCE_URL, sha256=_SOURCE_SHA256, strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        self._fix_config_guess()
        self._fix_config_sub()
        self._fix_configure_umask()
        self._protect_prebuilt_font_tables()

        args = ["--without-" + name for name in _CONFIGURE_DISABLE]
        args += [
            "--disable-wasm",
            "--disable-gdb-target",
            "--enable-ao-null",
            "--enable-filereq-cli",
        ]
        # knowledge/DRAFT-libfec-...-configshell-bash-getcwd-hmdfs：设备 profile
        # buildenv 的 CONFIG_SHELL/SHELL 指向 hnp bash，在 HMDFS 上 getcwd()
        # 失败，configure 前奏按 $CONFIG_SHELL 重 exec 后死于
        # "working directory cannot be determined"。命令行前缀压过导出值，
        # 强制 /bin/sh(mksh)。
        prefix = self.package_folder.replace("\\", "/")
        self.run(
            'CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh ../configure '
            '--prefix="%s" %s' % (prefix, " ".join(args)),
            env="conanbuild",
        )
        # 上游 configure 在未找到桌面 GL 时把 GL_LIBS 替换为字面量 "no"，
        # 但 vo_opengl.c 仍无条件编译并引用 GL 3.0 符号（上游假定 X11 必有
        # libGL）。OHOS 设备无 libGL，只有 libEGL/libGLESv3；GLESv3 提供全部
        # 所需符号（glGenTextures/glTexImage2D/glGenFramebuffers 等），
        # make 侧以系统 libGLESv3 注入。
        self.run(
            'CONFIG_SHELL=/bin/sh SHELL=/bin/sh make -j1 GL_LIBS=-lGLESv3',
            env="conanbuild",
        )

    def package(self):
        # 手动安装 bin/xroar：make install 还会装 man/info 与机器配置目录，
        # 对 headless 包只需可执行文件与许可证。
        src_dir = os.path.join(self.build_folder, "src")
        src = os.path.join(src_dir, "xroar")
        if not os.path.isfile(src):
            raise ConanException("xroar binary missing after build")
        dst = os.path.join(self.package_folder, "bin")
        os.makedirs(dst, exist_ok=True)
        copy(self, "xroar", src=src_dir, dst=dst, keep_path=False)
        copy(self, "COPYING.GPL", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.LGPL", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

    # ---------------------------------------------------------------- helpers
    def _fix_config_guess(self):
        """E007：让 config.guess 认识 HarmonyOS（uname -s = "HarmonyOS"）。

        新 case 分支必须插在 case 的第一条（分支按顺序匹配）。
        """
        path = os.path.join(self.source_folder, "config.guess")
        if "HarmonyOS" in load(self, path):
            return

        libc_android = "\t#if defined(__ANDROID__)\n\tLIBC=android"
        if libc_android in load(self, path):
            replace_in_file(self, path, libc_android,
                            libc_android + "\n#elif defined(__OHOS__)\n    LIBC=ohos")

        case_head = ("case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:"
                     "$UNAME_VERSION in\n")
        replace_in_file(self, path, case_head, case_head + (
            "    *:HarmonyOS:*:*)\n"
            "\tcase \"$UNAME_MACHINE\" in\n"
            "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
            "\t    armv7*|armv8*) MACHINE=arm ;;\n"
            "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
            "\t    i?86)         MACHINE=i686 ;;\n"
            "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
            "\tesac\n"
            "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
            "\t;;\n\n"
        ))

    def _fix_config_sub(self):
        """E007：让 config.sub 接受 ohos-linux 三元组。"""
        path = os.path.join(self.source_folder, "config.sub")
        if "ohos-linux" in load(self, path):
            return
        android_case = ("\t\t\t\tbasic_machine=$field1-unknown\n"
                        "\t\t\t\tbasic_os=linux-android\n"
                        "\t\t\t\t;;\n")
        replace_in_file(self, path, android_case, android_case + (
            "\tohos-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tbasic_os=linux-ohos\n"
            "\t\t\t\t;;\n"
        ))

    def _fix_configure_umask(self):
        """E114：HMDFS 上 config.status 临时目录必须可写（去掉 umask 077）。"""
        path = os.path.join(self.source_folder, "configure")
        if "umask 077" not in load(self, path):
            return
        replace_in_file(self, path, "umask 077 && mktemp", "mktemp")
        replace_in_file(self, path, "umask 077 && mkdir", "mkdir")

    def _protect_prebuilt_font_tables(self):
        """touch 预生成字体表，阻止 make 触发 font2c（需要 SDL+SDL2_image）。"""
        for rel in _FONT_TABLES:
            path = os.path.join(self.source_folder, rel)
            if not os.path.isfile(path):
                raise ConanException("prebuilt font table missing: %s" % rel)
            os.utime(path, None)
