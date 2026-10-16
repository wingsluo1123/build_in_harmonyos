#!/usr/bin/env python3
"""Conan recipe — ir-keytable 1.32.0（红外遥控器 keytable 工具）

ir-keytable 是 v4l-utils 的红外（IR）遥控配置工具：列出 IR 协议、
加载/测试 rc_keymap、调整 IR 接收器选项。
（C，Meson 构建，源出 v4l-utils-1.32.0 的 utils/keytable 子目录）

OHOS 适配要点：
- argp（musl/OHOS 无 glibc argp）→ 依赖 argp-standalone/1.5.0（提供 argp.h + libargp）
- intl（NLS，OHOS 无 libintl dev）→ meson 探测改为 required:false，ENABLE_NLS 不定义即不编译 NLS 代码
- bpf（eBPF 解码器）→ 关闭（-Dbpf=disabled，OHOS 无 bpf-gcc）
- 只配置/编译 utils/keytable（不构建 libv4l 与其他工具），最小化构建面
- OHOS ELF 签名（llvm-objcopy + binary-sign-tool）
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class IrKeytableConan(ConanFile):
    name = "ir_keytable"
    version = "1.32.0"
    description = "ir-keytable — IR remote controller keymap tool (v4l-utils)"
    license = "LGPL-2.1-or-later"
    homepage = "https://linuxtv.org/wiki/index.php/V4l-utils"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ir_keytable requires Linux/OHOS V4L2/IR kernel headers and ioctl support"
            )

    def requirements(self):
        # argp：OHOS(musl) 无 glibc argp → 用 argp-standalone（提供 argp.h + libargp）
        self.requires("argp-standalone/1.5.0")
        # NLS：common_arguments 的 -DENABLE_NLS 在 build() 中移除（见下），
        # 使源码 #else 分支 _()=string 兜底 → 无需 libintl（其 .so 为薄桩含未定义符号，不可用）

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # 关闭所有与 ir-keytable 无关的可选组件，最小化构建面
        tc.project_options["bpf"] = "disabled"
        tc.project_options["gconv"] = "disabled"
        tc.project_options["jpeg"] = "disabled"
        tc.project_options["libdvbv5"] = "disabled"
        tc.project_options["qv4l2"] = "disabled"
        tc.project_options["qvidcap"] = "disabled"
        tc.project_options["v4l2-tracer"] = "disabled"
        tc.project_options["v4l-plugins"] = False
        tc.project_options["v4l-utils"] = True
        tc.project_options["v4l-wrappers"] = False
        tc.project_options["v4l2-compliance-libv4l"] = False
        tc.project_options["v4l2-ctl-libv4l"] = False
        tc.project_options["v4l2-ctl-stream-to"] = False
        tc.project_options["doxygen-doc"] = "disabled"
        tc.project_options["doxygen-html"] = False
        tc.project_options["doxygen-man"] = False
        # 显式注入 argp-standalone 头/库路径：meson 的 cc.find_library('argp')
        # 与 #include <argp.h> 需要 -L/-I 进入 native 文件（MesonToolchain 默认
        # 未必把 host 依赖 libdir 透传给 find_library 搜索路径）。
        # 注意：self.dependencies 的 cpp_info.includedirs/libdirs 已是绝对路径，
        # 不可再拼 package_folder（否则路径翻倍 → 链接器找不到 -largp）。
        argp = self.dependencies["argp-standalone"]
        for inc in argp.cpp_info.includedirs:
            tc.c_args.append("-I{}".format(inc.replace("\\", "/")))
        for libd in argp.cpp_info.libdirs:
            tc.c_link_args.append("-L{}".format(libd.replace("\\", "/")))
        for libn in argp.cpp_info.libs:
            tc.c_link_args.append("-l{}".format(libn))
        tc.generate()
        self._patch_meson_machine_files()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            src = self.source_folder
            meson_main = os.path.join(src, "meson.build")
            # perl 可选（OHOS 无 perl；cec 族工具依赖 perl）
            replace_in_file(self, meson_main,
                            "prog_perl = find_program('perl')",
                            "prog_perl = find_program('perl', required : false)")
            # intl 可选（OHOS 无可用 libintl；其 .so 为薄桩含未定义符号）
            replace_in_file(self, meson_main,
                            "dep_intl = dependency('intl')",
                            "dep_intl = dependency('intl', required : false)")
            # 移除无条件 -DENABLE_NLS：源码 #else 分支 _()=string 兜底，去掉对 gettext 的依赖
            replace_in_file(self, meson_main,
                            "    '-DENABLE_NLS',",
                            "    # '-DENABLE_NLS',  # ir_keytable: OHOS 无 libintl，禁用 NLS")
            # v4l2 incdir 补 'include'（对齐 OHOS sysroot 头文件布局）
            replace_in_file(self, meson_main,
                            "v4l2_utils_incdir_arr = [\n    'lib' / 'include',\n]",
                            "v4l2_utils_incdir_arr = [\n    'lib' / 'include',\n    'include',\n]")
            # 跳过 contrib（其 decode_tm6000 引用 dep_libv4l2util，已被下方注释掉）
            replace_in_file(self, meson_main,
                            "    subdir('contrib')",
                            "    # subdir('contrib')  # ir_keytable: skipped")
            # libv4lconvert：OHOS 内核头缺 V4L2_PIX_FMT_NV12_16L16（仅配置 libv4l，不构建）
            replace_in_file(self, os.path.join(src, "lib", "libv4lconvert", "libv4lconvert.c"),
                            '#include "libv4lsyscall-priv.h"\n',
                            '#include "libv4lsyscall-priv.h"\n\n'
                            "#ifndef V4L2_PIX_FMT_NV12_16L16\n"
                            "#define V4L2_PIX_FMT_NV12_16L16 v4l2_fourcc('H', 'M', '1', '2')\n"
                            "#endif\n")
            # keytable/meson.build：dep_intl 非可选时会因 not-found 进入 deps 报错 → 条件加入
            keytable_meson = os.path.join(src, "utils", "keytable", "meson.build")
            replace_in_file(self, keytable_meson,
                            "ir_keytable_deps = [\n    dep_argp,\n    dep_intl,\n]",
                            "ir_keytable_deps = [\n    dep_argp,\n]\n"
                            "if dep_intl.found()\n    ir_keytable_deps += [dep_intl]\nendif")
            # utils/meson.build：cec 族按 perl 探测门控（perl 缺失时跳过）
            utils_meson = os.path.join(src, "utils", "meson.build")
            for s in ("libcecutil", "cec-ctl", "cec-follower", "cec-compliance"):
                replace_in_file(self, utils_meson,
                                "subdir('{}')".format(s),
                                "if prog_perl.found()\n    subdir('{}')\nendif".format(s))
            # 其余工具子目录跳过（ir_keytable 包只配置/构建 keytable）
            for s in ("libmedia_dev", "libv4l2util", "cx18-ctl", "edid-decode",
                      "ir-ctl", "ivtv-ctl", "media-ctl", "rds-ctl",
                      "v4l2-ctl", "v4l2-dbg", "v4l2-sysfs-path"):
                replace_in_file(self, utils_meson,
                                "subdir('{}')".format(s),
                                "# subdir('{}')  # ir_keytable: skipped".format(s))
        meson = Meson(self)
        meson.configure()
        # 只构建 ir-keytable 目标（不构建 libv4l 与其他工具，最小化构建面）
        self.run("meson compile -C {} ir-keytable".format(self.build_folder))

    def package(self):
        # 手动收集产物（避免 meson install 触发全部目标安装）
        src = self.source_folder
        keytable_src = os.path.join(src, "utils", "keytable")
        pkg = self.package_folder
        # 定位已构建的 ir-keytable 可执行文件
        exe = None
        for root, _dirs, files in os.walk(self.build_folder):
            for f in files:
                if f == "ir-keytable" and os.path.isfile(os.path.join(root, f)):
                    candidate = os.path.join(root, f)
                    if not os.path.islink(candidate) and self._is_elf(candidate):
                        exe = candidate
                        break
            if exe:
                break
        if not exe:
            raise ConanInvalidConfiguration("ir-keytable executable not found in build dir")
        bin_dir = os.path.join(pkg, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(exe, os.path.join(bin_dir, "ir-keytable"))
        # 数据文件（keytable/meson.build 安装布局）：
        #   rc_maps.cfg → sysconfdir(etc)；rc_keymaps/ → udevdir/rc_keymaps(lib/udev)
        #   70-infrared.rules → udevdir/rules.d(lib/udev/rules.d)
        etc_dir = os.path.join(pkg, "etc")
        udev_dir = os.path.join(pkg, "lib", "udev")
        os.makedirs(etc_dir, exist_ok=True)
        os.makedirs(os.path.join(udev_dir, "rc_keymaps"), exist_ok=True)
        os.makedirs(os.path.join(udev_dir, "rules.d"), exist_ok=True)
        copy(self, "rc_maps.cfg", src=keytable_src, dst=etc_dir)
        copy(self, "*", src=os.path.join(keytable_src, "rc_keymaps"),
             dst=os.path.join(udev_dir, "rc_keymaps"))
        copy(self, "70-infrared.rules", src=keytable_src, dst=os.path.join(udev_dir, "rules.d"))
        # 许可证
        copy(self, "COPYING", src=src, dst=os.path.join(pkg, "licenses"))
        # OHOS ELF 签名
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_package_elfs()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # 数据文件路径（keymap / udev 规则），供下游引用
        self.cpp_info.set_property("ir_keytable:system_dir", "lib/udev/rc_keymaps")
        self.cpp_info.set_property("ir_keytable:user_dir", "etc/rc_keymaps")
        # CLI 工具：追加 PATH 到 run/build 环境
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.runenv_info.append_path("PATH", "bin")
            self.buildenv_info.append_path("PATH", "bin")

    def _patch_meson_machine_files(self):
        """OHOS：向 conan_meson_{native,cross}.ini 注入 ar/ranlib，
        并将 shell 脚本形式的编译器包成 [shell, script] 二元组（Meson 要求）。"""
        compiler_exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        wrapper_binaries = {}
        if str(self.settings.os) == "OHOS":
            for key in ("c", "cpp"):
                compiler = compiler_exes.get(key)
                if compiler and self._is_shell_script(compiler):
                    wrapper_binaries[key] = "[{}, {}]".format(
                        self._meson_quote(shell),
                        self._meson_quote(compiler),
                    )

        ar = compiler_exes.get("ar")
        ranlib = compiler_exes.get("ranlib")
        if not ar:
            cc = compiler_exes.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate
        if not ar:
            return

        for name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, name)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            if "\nar =" not in content:
                insertion = "[binaries]\nar = '{}'\n".format(ar.replace("\\", "/"))
                if ranlib:
                    insertion += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))
                content = content.replace("[binaries]\n", insertion, 1)
            for key, value in wrapper_binaries.items():
                content = self._replace_meson_binary(content, key, value)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)

    @staticmethod
    def _is_shell_script(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(32).startswith(b"#!")
        except OSError:
            return False

    @staticmethod
    def _meson_quote(value):
        return "'{}'".format(value.replace("\\", "/").replace("'", "\\'"))

    @staticmethod
    def _replace_meson_binary(content, key, value):
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("{} = ".format(key)):
                lines[index] = "{} = {}".format(key, value)
                break
        trailing_newline = "\n" if content.endswith("\n") else ""
        return "\n".join(lines) + trailing_newline

    def _sign_ohos_package_elfs(self):
        elf_paths = []
        for root_dir in ("lib", "bin"):
            scan_root = os.path.join(self.package_folder, root_dir)
            if os.path.isdir(scan_root):
                elf_paths.extend(self._collect_ohos_elfs(scan_root))
        if not elf_paths:
            return

        objcopy = self._resolve_tool("llvm-objcopy")
        signer = self._resolve_tool("binary-sign-tool")
        missing = []
        if not objcopy:
            missing.append("llvm-objcopy")
        if not signer:
            missing.append("binary-sign-tool")
        if missing:
            raise ConanInvalidConfiguration(
                "OHOS ELF signing requires {}".format(", ".join(missing))
            )

        for path in elf_paths:
            self._sign_ohos_elf(path, objcopy, signer)

    def _collect_ohos_elfs(self, scan_root):
        elf_paths = []
        for root, _, filenames in os.walk(scan_root):
            for filename in sorted(filenames):
                path = os.path.join(root, filename)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                elf_paths.append(path)
        return elf_paths

    def _sign_ohos_elf(self, path, objcopy, signer):
        mode = os.stat(path).st_mode
        signed_path = path + ".signed"
        if os.path.exists(signed_path):
            os.remove(signed_path)
        self.run(shlex.join([objcopy, "--remove-section", ".codesign", path]))
        self.run(shlex.join([
            signer,
            "sign",
            "-inFile",
            path,
            "-outFile",
            signed_path,
            "-selfSign",
            "1",
        ]))
        os.replace(signed_path, path)
        os.chmod(path, mode)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _resolve_tool(self, name):
        compiler_exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compiler_exes.get("c") or ""
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path) if compiler_path else ""
        candidates = [
            os.environ.get(name.upper().replace("-", "_")),
            shutil.which(name),
            os.path.join(compiler_dir, name) if compiler_dir else None,
            os.path.join(os.path.expanduser("~"), "usr", "local", "bin", name),
            os.path.join("/data/service/hnp/bin", name),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""
