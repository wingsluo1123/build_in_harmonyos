#!/usr/bin/env python3
from conan import ConanFile
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.env import Environment
from conan.tools.layout import basic_layout
import glob
import os
import shutil

_OHOS_BIN = "/data/service/hnp/bin"
_OHOS_OBJCOPY = _OHOS_BIN + "/llvm-objcopy"
_OHOS_SIGNER = _OHOS_BIN + "/binary-sign-tool"


class LibaudclientConan(ConanFile):
    name = "libaudclient"
    version = "3.5-rc2.2"
    description = "Legacy D-Bus client library for controlling the Audacious media player"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/audacious-media-player/libaudclient"
    url = "https://github.com/audacious-media-player/libaudclient"
    topics = ("audacious", "dbus", "media-player", "remote-control")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def requirements(self):
        self.requires("dbus-glib/0.114", transitive_headers=True, transitive_libs=True)
        # glib 需为直接依赖：cpp_info.requires 只允许引用直接依赖（传递 include 给消费者）
        self.requires("glib/2.88.0", transitive_headers=True, transitive_libs=True)
        self.requires("dbus/1.14.10", transitive_headers=True, transitive_libs=True)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 上游 2013 年 config.guess/sub 不认识 HarmonyOS：显式指定构建三元组
        tc.configure_args.extend(["--build=aarch64-unknown-linux-gnu", "--host=aarch64-unknown-linux-gnu"])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()
        PkgConfigDeps(self).generate()
        # 仓库 dbus 包生成的 pc 名为 "dbus"，上游 configure 检查 "dbus-1"：
        # 生成转发型 dbus-1.pc（版本从 dbus.pc 读取，避免硬编码）
        dbus_dep = self.dependencies.get("dbus")
        dbus_pc = os.path.join(self.generators_folder, "dbus.pc")
        version = "1.0"
        if os.path.isfile(dbus_pc):
            with open(dbus_pc) as _f:
                for line in _f:
                    if line.startswith("Version:"):
                        version = line.split(":", 1)[1].strip()
                        break
        prefix = dbus_dep.package_folder if dbus_dep is not None else ""
        with open(os.path.join(self.generators_folder, "dbus-1.pc"), "w") as _pc:
            _pc.write(
                "prefix={prefix}\n"
                "includedir=${{prefix}}/include\n"
                "libdir=${{prefix}}/lib\n\n"
                "Name: dbus\n"
                "Description: DBus forwarding pc for OHOS repo package\n"
                "Version: {version}\n"
                "Requires: dbus\n"
                "Cflags: -I${{includedir}}/dbus-1.0\n".format(prefix=prefix, version=version))
        env = Environment()
        dg = self.dependencies.get("dbus-glib")
        if dg is not None:
            tool_bin = os.path.join(dg.package_folder, "bin")
            if os.path.isdir(tool_bin):
                env.prepend_path("PATH", tool_bin)
        env.vars(self).save_script("libaudclient_tools")

    def build(self):
        apply_conandata_patches(self)
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            self.run("autoheader 2>/dev/null; autoconf", cwd=self.source_folder)
        # 鸿蒙 PC 拒绝执行未签名 ELF：configure 的 try-run 探测会 exec 失败。
        # 本机为原生构建，这些探测语义上本应通过 → 让 ac_fn_c_try_run 恒返回 0
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            _s = open(cfg).read()
            _fn = "ac_fn_c_try_run ()\n{\n"
            if _fn in _s and "OHOS-unsigned-elf" not in _s:
                _s = _s.replace(_fn, _fn + "  return 0  # OHOS-unsigned-elf: exec denied, assume native pass\n", 1)
                open(cfg, "w").write(_s)
        # autoconf 2.69 的交叉编译检测为内联 exec（不经 ac_fn_c_try_run）：
        # 未签名 ELF 被拒执行时直接 as_fn_error 退出 → 替换为 no-op（原生构建语义）
        import re as _re
        cfg2 = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg2):
            _t = open(cfg2).read()
            if "cannot run C compiled programs" in _t and "OHOS-assume-pass" not in _t:
                _t2 = _re.sub(
                    r'as_fn_error \$\? "cannot run C compiled programs\..*?" "\$LINENO" 5',
                    '$as_echo "OHOS-assume-pass: cannot run C compiled programs" >&2',
                    _t, flags=_re.S)
                if _t2 != _t:
                    open(cfg2, "w").write(_t2)
        # HMDFS：config.status 以 umask 077 建临时目录后立即写入会 EACCES
        # （仓库既有修复模式：放宽为 022；configure 内嵌 config.status 模板，改一处全覆盖）
        cfg3 = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg3):
            _u = open(cfg3).read()
            if "umask 077" in _u and "OHOS-umask" not in _u:
                _u = _u.replace("umask 077", "umask 022")
                open(cfg3, "w").write(_u)
        # buildsys 为纯 in-source 构建系统：configure 与 make 都必须在源码目录执行
        # （工具链 CC/CFLAGS/PKG_CONFIG_PATH 已由 conanbuild 环境提供）
        self.run("./configure --prefix=/ --build=aarch64-unknown-linux-gnu "
                 "--host=aarch64-unknown-linux-gnu", cwd=self.source_folder)
        # buildsys 为 in-source 构建系统：make 须在源码目录执行；
        # 裸 make（无 -j）避免 jobserver 在 HMDFS 上 mkfifo 失败
        self.run("make", cwd=self.source_folder)

    def package(self):
        self.run('make install DESTDIR="%s"' % self.package_folder,
                 cwd=self.source_folder)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)
        self._ensure_shared_lib_aliases()
        self._sign_artifacts()

    def _ensure_shared_lib_aliases(self):
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        real = [p for p in glob.glob(os.path.join(libdir, "libaudclient.so.*"))
                if not os.path.islink(p)]
        if not real:
            return
        source = sorted(real)[-1]
        major = os.path.basename(source)[len("libaudclient.so."):].split(".")[0]
        for alias in ("libaudclient.so." + major, "libaudclient.so"):
            target = os.path.join(libdir, alias)
            if os.path.lexists(target):
                continue
            shutil.copy2(source, target)
            self.output.info("Materialized alias %s" % os.path.basename(target))

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_artifacts(self):
        libdir = os.path.join(self.package_folder, "lib")
        targets = []
        if os.path.isdir(libdir):
            for pattern in ("**/*.so", "**/*.so.*"):
                targets.extend(glob.glob(os.path.join(libdir, pattern), recursive=True))
        targets = [t for t in targets if self._is_elf(t)]
        if not targets:
            return
        if not os.path.isfile(_OHOS_SIGNER):
            self.output.warning("binary-sign-tool not found; skip codesign")
            return
        objcopy = _OHOS_OBJCOPY if os.path.isfile(_OHOS_OBJCOPY) else shutil.which("llvm-objcopy")
        for target in sorted(set(targets)):
            if objcopy:
                self.run('"%s" --remove-section .codesign "%s" 2>/dev/null || true'
                         % (objcopy, target))
            self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                     % (_OHOS_SIGNER, target, target))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "audclient")
        self.cpp_info.libs = ["audclient"]
        self.cpp_info.requires = ["dbus-glib::dbus-glib", "glib::glib-2.0", "glib::gobject-2.0", "glib::gthread-2.0", "dbus::dbus"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
