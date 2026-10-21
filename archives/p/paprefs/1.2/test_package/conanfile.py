#!/usr/bin/env python3
"""Conan test_package for paprefs 1.2.

Two real-consumer behaviours are exercised on OHOS PC:

1. The consumer program (test_paprefs) is built against the packaged
   gtkmm-3.0 / giomm-2.4 / sigc++-2.0 / libpulse pkg-config chain — the exact
   dependency set paprefs' own meson.build consumes.  It drives Gtkmm through
   real GUI objects (Gtk::Main init, Gtk::Window, Gtk::Builder loading the
   packaged paprefs.glade, PulseAudio client API) and prints TAP.

2. The packaged `paprefs` binary itself is launched headless on the broadway
   GDK backend served by broadwayd from the gtk package (same technique as
   gspell/1.14.4): the process must come up, register its main loop and stay
   alive (a crash inside MainWindow construction or glade loading would exit
   early).
"""
import os
import re
import shutil
import subprocess
import time

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment

BROADWAY_DISPLAY = ":6"


class PaprefsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # PkgConfigDeps 不能用：atkmm/2.28.4（rev 2026-10-14）平铺 cpp_info
        # 与 gtkmm/3.24.11 组件引用 atkmm::atkmm-1.6 断裂（同主配方根因）。
        # 与主配方同款：把整张依赖图摊平成聚合 -I/-L/-l，写出
        # gtkmm-3.0/giomm-2.4/sigc++-2.0/libpulse 四个 .pc 供
        # pkg_check_modules 消费。
        incs, libdirs, libs = [], [], []
        for dep in self.dependencies.values():
            cpp_info = getattr(dep, "cpp_info", None)
            pkg_root = getattr(dep, "package_folder", None)
            if not cpp_info or not pkg_root:
                continue
            for node in [cpp_info] + list((cpp_info.components or {}).values()):
                for d in (node.includedirs or []):
                    full = d if os.path.isabs(d) else os.path.join(pkg_root, d)
                    if full not in incs:
                        incs.append(full)
                for d in (node.libdirs or []):
                    full = d if os.path.isabs(d) else os.path.join(pkg_root, d)
                    if full not in libdirs:
                        libdirs.append(full)
                for lib in (node.libs or []):
                    if lib not in libs:
                        libs.append(lib)
        cflags = " ".join("-I%s" % d for d in incs)
        # 只链接实际存在的库，并丢弃 gettext 特判集（asprintf 包内不存在；
        # gettextpo/textstyle 引用未解析的 libintl_*；intl 被 glib 的坏
        # libintl.so 抢先）——与主配方 _write_flat_pcs 同款逻辑。
        libs = [lib for lib in libs
                if lib not in ("gettextpo", "textstyle", "asprintf", "intl") and
                any(os.path.isfile(os.path.join(d, "lib%s.so" % lib)) or
                    os.path.isfile(os.path.join(d, "lib%s.a" % lib))
                    for d in libdirs)]
        gettext_dep = self.dependencies.get("paprefs")
        extra_link = ""
        # gettext 是 paprefs 的传递依赖，从图中直接取 libintl.a
        for dep in self.dependencies.values():
            ref = getattr(dep, "ref", None)
            if ref is not None and ref.name == "gettext" and \
                    getattr(dep, "package_folder", None):
                intl_a = os.path.join(dep.package_folder, "lib", "libintl.a")
                if os.path.isfile(intl_a):
                    extra_link = " " + intl_a
                break
        libs_args = " ".join(["-L%s" % d for d in libdirs] +
                             ["-l%s" % lib for lib in libs]) + extra_link
        for name in ("gtkmm-3.0", "giomm-2.4", "sigc++-2.0", "libpulse"):
            pc = os.path.join(self.generators_folder, "%s.pc" % name)
            with open(pc, "w", encoding="utf-8") as f:
                f.write(
                    "Name: %s\n"
                    "Description: flattened conan graph (%s)\n"
                    "Version: 1.0\n"
                    "Cflags: %s\n"
                    "Libs: %s\n" % (name, name, cflags, libs_args))
        # CMake pkg_check_modules 走 PATH 上的 pkg-config，进程内注入搜索路径
        # （测试端代码，不影响主配方）。
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(
            [self.generators_folder,
             os.environ.get("PKG_CONFIG_PATH", "")]).strip(os.pathsep)

    def _resolved_lib_dirs(self):
        dirs = []
        for dependency in self.dependencies.values():
            if not getattr(dependency, "package_folder", None):
                continue
            for libdir in dependency.cpp_info.libdirs or []:
                if not libdir:
                    continue
                full = libdir if os.path.isabs(libdir) else os.path.join(
                    dependency.package_folder, libdir)
                if full not in dirs:
                    dirs.append(full)
        for pattern in ("libpcre2-8.so*", "libffi.so*", "libexpat.so*",
                        "libintl.so*", "libpulsecommon*.so*"):
            for match in __import__("glob").glob(
                    "/data/service/hnp/*/*/lib/{}".format(pattern)):
                libdir = os.path.dirname(match)
                if libdir not in dirs:
                    dirs.append(libdir)
        return dirs

    def _collect_paths(self):
        """Return (pkg_config_paths, ld_library_paths) incl. component libdirs
        (pulsecommon lives in <pulseaudio>/lib/pulseaudio, a component libdir)."""
        pkg_paths = [self.generators_folder]
        ld_paths = []
        for dependency in self.dependencies.values():
            if not getattr(dependency, "package_folder", None):
                continue
            nodes = [dependency.cpp_info] + \
                list((getattr(dependency.cpp_info, "components", None) or {}).values())
            for node in nodes:
                for libdir in (node.libdirs or []):
                    if not libdir:
                        continue
                    full = libdir if os.path.isabs(libdir) else os.path.join(
                        dependency.package_folder, libdir)
                    ld_paths.append(full)
                    pkg_paths.append(os.path.join(full, "pkgconfig"))
        ld_paths.extend(self._resolved_lib_dirs())
        return pkg_paths, ld_paths

    def _env(self):
        env = Environment()
        pkg_paths, ld_paths = self._collect_paths()
        for p in pkg_paths:
            env.prepend_path("PKG_CONFIG_PATH", p)
        for p in ld_paths:
            env.prepend_path("LD_LIBRARY_PATH", p)
        return env

    def _ensure_signed_libs(self, ld_paths):
        """Copy dependency libs lacking .codesign into a temp dir and sign
        them there (E135: OHOS rejects unsigned .so at load time — observed
        with pulseaudio/17.0's libpulse*).  Never mutates other packages'
        cache files; returns the dir to prepend to LD_LIBRARY_PATH or None.
        """
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            return None
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(readelf):
            return None
        sign_dir = os.path.join(self.build_folder, "signedlib")
        os.makedirs(sign_dir, exist_ok=True)
        for d in ld_paths:
            if not os.path.isdir(d):
                continue
            for name in sorted(os.listdir(d)):
                if ".so" not in name:
                    continue
                src = os.path.join(d, name)
                if not os.path.isfile(src):
                    continue
                # 符号链接也要按链接名拷入（解引用）：loader 按 DT_NEEDED
                # 的 libpulse.so.0 找文件，只签真身 libpulse.so.0.24.3 不够。
                dst = os.path.join(sign_dir, name)
                if os.path.isfile(dst):
                    continue
                try:
                    secs = subprocess.run([readelf, "-S", src],
                                          capture_output=True, text=True,
                                          timeout=30).stdout
                except Exception:
                    continue
                if ".codesign" in secs:
                    continue
                import shutil as _sh
                _sh.copy2(src, dst, follow_symlinks=True)
                if os.path.isfile(objcopy):
                    subprocess.run([objcopy, "--remove-section", ".codesign", dst],
                                   capture_output=True, timeout=30)
                subprocess.run([signer, "sign", "-inFile", dst, "-outFile", dst,
                                "-selfSign", "1"], capture_output=True, timeout=30)
        return sign_dir

    def _gsettings_schema_dir(self):
        """paprefs 启动即读 org.freedesktop.pulseaudio.module-group schema
        （OHOS 的 pulseaudio 包不带 gschema），缺失时 GLib-GIO-ERROR 直接
        abort。这里生成最小 schema（enabled/name0-9/args0-9，与 paprefs.cc
        的读写一致）并编译，供 GSETTINGS_SCHEMA_DIR 使用。
        """
        compiler = "/data/service/hnp/bin/glib-compile-schemas"
        if not os.path.isfile(compiler):
            compiler = shutil.which("glib-compile-schemas") or ""
        if not compiler:
            return None
        schemas = os.path.join(self.build_folder, "gschemas")
        os.makedirs(schemas, exist_ok=True)
        xml = os.path.join(schemas, "org.freedesktop.pulseaudio.module-group.gschema.xml")
        if not os.path.isfile(xml):
            keys = ['<key name="enabled" type="b"><default>false</default></key>']
            for i in range(10):
                keys.append('<key name="name%d" type="s"><default>""</default></key>' % i)
                keys.append('<key name="args%d" type="s"><default>""</default></key>' % i)
            with open(xml, "w", encoding="utf-8") as f:
                f.write(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<schemalist>\n'
                    # 不带固定 path：paprefs 用 Gio::Settings::create(schema,
                    # path) 按模块传不同 path，schema 钉死 path 会导致
                    # "settings object created with schema ... and path ..."。
                    '  <schema id="org.freedesktop.pulseaudio.module-group">\n    '
                    + "\n    ".join(keys) + "\n  </schema>\n"
                    "</schemalist>\n")
        r = subprocess.run([compiler, schemas], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            self.output.warning("glib-compile-schemas failed: %s" % r.stderr)
            return None
        return schemas

    def _broadway_display(self):
        # 动态 display 号（端口 8080+N）：残留的上一轮 broadwayd 可能占着
        # 固定 :6（8086 Address in use → rc=1），按 PID 错开。
        return ":%d" % (os.getpid() % 200 + 10)

    def _broadway_env(self):
        """Start broadwayd; return (env, process)."""
        env = self._env()
        display = self._broadway_display()
        proc = None
        gtk_pkg = self.dependencies.get("gtk")
        if gtk_pkg is not None and gtk_pkg.package_folder:
            broadwayd = os.path.join(gtk_pkg.package_folder, "bin", "broadwayd")
            if os.path.isfile(broadwayd):
                run_env = dict(os.environ)
                # 与 test() 同源：_collect_paths 含组件 libdirs（pulsecommon
                # 等），否则 broadwayd 起不来（此前 rc=1 的根因）。
                _, ld_paths = self._collect_paths()
                run_env["LD_LIBRARY_PATH"] = os.pathsep.join(
                    ld_paths + [run_env.get("LD_LIBRARY_PATH", "")]).strip(os.pathsep)
                proc = subprocess.Popen([broadwayd, display],
                                        env=run_env,
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)
                for _ in range(20):
                    if proc.poll() is not None:
                        break
                    time.sleep(0.5)
                if proc.poll() is None:
                    env.define("GDK_BACKEND", "broadway")
                    env.define("BROADWAY_DISPLAY", display)
                else:
                    self.output.warning(
                        "broadwayd exited early (rc=%s); running consumer "
                        "test without a display backend" % proc.returncode)
                    proc = None
        return env, proc

    def build(self):
        envvars = self._env().vars(self)
        with envvars.apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise RuntimeError("test_paprefs executable directory was not produced")
        exe = os.path.join(bindirs[0], "test_paprefs")
        if not os.path.isfile(exe):
            raise RuntimeError("test_paprefs binary missing: {}".format(exe))

        # Locate the packaged paprefs binary + glade data inside the
        # tested package folder (real consumer layout).
        paprefs_pkg = self.dependencies.get("paprefs")
        if not paprefs_pkg or not paprefs_pkg.package_folder:
            raise RuntimeError("paprefs package not found in dependency graph")
        paprefs_bin = os.path.join(paprefs_pkg.package_folder, "bin", "paprefs")
        glade_file = os.path.join(paprefs_pkg.package_folder, "share", "paprefs",
                                  "paprefs.glade")
        for path, what in ((paprefs_bin, "packaged paprefs binary"),
                           (glade_file, "packaged paprefs.glade")):
            if not os.path.isfile(path):
                raise RuntimeError("{} missing: {}".format(what, path))

        env, broadwayd_proc = self._broadway_env()
        # 不用 env="conanrun"（重算 LD_LIBRARY_PATH 丢组件 libdir），也不依赖
        # self.run(env=list)——实测该路径下变量未传到 loader。直接写进程
        # 环境再 run（与 generate() 里 PKG_CONFIG_PATH 同款做法）。
        pkg_paths, ld_paths = self._collect_paths()
        # E135：把缺 .codesign 的依赖库（pulseaudio 系）拷到临时目录签名，
        # 前置到 LD_LIBRARY_PATH（不改动其他包的缓存文件）。
        sign_dir = self._ensure_signed_libs(ld_paths)
        if sign_dir:
            ld_paths = [sign_dir] + ld_paths
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            ld_paths + [os.environ.get("LD_LIBRARY_PATH", "")]).strip(os.pathsep)
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(
            pkg_paths + [os.environ.get("PKG_CONFIG_PATH", "")]).strip(os.pathsep)
        run_env = dict(os.environ)
        if broadwayd_proc is not None and broadwayd_proc.poll() is None:
            run_env["GDK_BACKEND"] = "broadway"
            run_env["BROADWAY_DISPLAY"] = self._broadway_display()
        # paprefs 启动即读 module-group schema：OHOS 无系统 schemas，
        # 注入测试生成的最小 schema 目录（缺失则 GLib-GIO-ERROR abort）。
        schema_dir = self._gsettings_schema_dir()
        if schema_dir:
            run_env["GSETTINGS_SCHEMA_DIR"] = schema_dir
        log = os.path.join(self.build_folder, "test_paprefs.tap")
        run_error = None
        try:
            with open(log, "w") as log_fh:
                log_fh.write("# LD_LIBRARY_PATH=%s\n" %
                             os.environ.get("LD_LIBRARY_PATH", ""))
                log_fh.flush()
                subprocess.run(
                    [exe, paprefs_bin, glade_file],
                    stdout=log_fh, stderr=subprocess.STDOUT,
                    env=run_env, timeout=120, check=False)
        except Exception as exc:      # re-raised below, after TAP is shown
            run_error = exc
        finally:
            if broadwayd_proc is not None and broadwayd_proc.poll() is None:
                broadwayd_proc.terminate()

        try:
            with open(log, encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        self.output.info("----- test_paprefs TAP -----\n{}".format(out))

        ok = len(re.findall(r"^ok\b", out, re.M))
        not_ok = len(re.findall(r"^not ok\b", out, re.M))
        plan = re.search(r"^1\.\.(\d+)\s*$", out, re.M)
        expected = int(plan.group(1)) if plan else 0
        if run_error is not None or expected < 1 or ok != expected or not_ok != 0:
            raise RuntimeError(
                "consumer assertions did not all pass ({}): plan={} ok={} "
                "not_ok={}\n{}".format(run_error, expected, ok, not_ok, out))
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT={{\"status\": \"passed\", \"assertions\": {}}}"
            .format(ok))
