#!/usr/bin/env python3
"""libgfbgraph 0.2.5（GObject Facebook Graph API 封装）.

上游 tag 归档没有 configure，构建时执行 autoreconf。
制品仓 librest 0.10.2 的 pkg-config 名是 rest-1.0，并且按 libsoup-3.0 编译。
rest-0.7 用到的 RestProxy 调用在 rest-1.0 中签名一致；libsoup 2.4 的
SoupURI / SoupRequester 已不存在，由补丁改写成 libsoup 3 的等价调用。
"""
import errno
import os
import re
import shlex
import shutil
import subprocess
import sys
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# gnome-online-accounts/3.56.5 已在 origin/main 和制品仓（SEA-111，PR #8769）。
# 本 PR 改不了那份已发布配方。它的 build() 把 PKG_CONFIG_PATH 只设成
# generators + dbus + glib，并用系统 pkg-config。根配方把 glib 从 2.88.0
# override 到 2.84.0.1.1 后 package_id 对不上，CI 会从源码重编 GOA。
# 这时 glib-2.0.pc 的 Requires.private 要 libpcre2-8，gio-2.0.pc 要 zlib，
# gobject-2.0.pc 要 libffi，而这三份 .pc 不在 GOA 写死的搜索路径里。
# conan create 在同一进程里调依赖的 build()，这里在 meson setup 前把这几份
# .pc（prefix 改成包目录）补进 --pkg-config-path / PKG_CONFIG_PATH。
_GFG_TRANSITIVE_PC = ("libpcre2-8.pc", "libffi.pc", "zlib.pc", "expat.pc")


def _gfg_conan_home():
    return os.environ.get("CONAN_HOME") or os.path.expanduser("~/.conan2")


def _gfg_perl_executable():
    """Prefer Harmonybrew Perl; never pair the system Perl with Conan's PERL5LIB."""
    candidates = (
        os.path.expanduser("~/.harmonybrew/bin/perl"),
        "/data/service/hnp/bin/perl",
        "/usr/bin/perl",
        "/bin/perl",
    )
    for path in candidates:
        if os.path.isfile(path):
            return path
    return shutil.which("perl") or "perl"


def _gfg_tool_executable(name):
    """Use a concrete Harmonybrew/HNP autotools path when it is installed."""
    for directory in (
        os.path.expanduser("~/.harmonybrew/bin"),
        "/data/service/hnp/bin",
    ):
        path = os.path.join(directory, name)
        if os.path.isfile(path):
            return path
    return shutil.which(name)


def _gfg_stage_transitive_pcs():
    """把 glib/gio/gobject 的 Requires.private 指向的 .pc 收进一个目录。"""
    stage = os.path.join(_gfg_conan_home(), "pc-transitive-gfg13934")
    os.makedirs(stage, exist_ok=True)
    root = os.path.join(_gfg_conan_home(), "p")
    if not os.path.isdir(root):
        return stage
    for entry in os.listdir(root):
        pkg_folder = os.path.join(root, entry, "p")
        pc_dir = os.path.join(pkg_folder, "lib", "pkgconfig")
        if not os.path.isdir(pc_dir):
            continue
        for name in _GFG_TRANSITIVE_PC:
            src = os.path.join(pc_dir, name)
            if not os.path.isfile(src):
                continue
            with open(src, "r", encoding="utf-8", errors="replace") as handle:
                lines = handle.read().splitlines()
            rewritten = []
            for line in lines:
                if line.startswith("prefix="):
                    rewritten.append("prefix=%s" % pkg_folder)
                else:
                    rewritten.append(line)
            dest = os.path.join(stage, name)
            with open(dest, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("\n".join(rewritten) + "\n")
    return stage


def _gfg_write_pkgconfig_wrapper(stage):
    """meson 会按 PATH 找到的 pkg-config 再查 Requires.private。包装一层把 stage 加上。"""
    wrap_dir = os.path.join(_gfg_conan_home(), "pkgconfig-wrap-gfg13934")
    os.makedirs(wrap_dir, exist_ok=True)
    script = os.path.join(wrap_dir, "pkg-config")
    body = (
        "#!/bin/sh\n"
        "stage=\"%s\"\n"
        "if [ -d \"$stage\" ]; then\n"
        "  case \":${PKG_CONFIG_PATH:-}:\" in\n"
        "    *\":$stage:\"*) ;;\n"
        "    *) PKG_CONFIG_PATH=\"$stage${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}\"; export PKG_CONFIG_PATH ;;\n"
        "  esac\n"
        "fi\n"
        "real=\n"
        "oldifs=$IFS\n"
        "IFS=:\n"
        "for d in $PATH; do\n"
        "  cand=\"$d/pkg-config\"\n"
        "  case \"$cand\" in\n"
        "    \"$0\"|*/pkgconfig-wrap-gfg13934/pkg-config) continue ;;\n"
        "  esac\n"
        "  if [ -x \"$cand\" ]; then real=$cand; break; fi\n"
        "done\n"
        "IFS=$oldifs\n"
        "if [ -z \"$real\" ]; then\n"
        "  for cand in /data/service/hnp/bin/pkg-config /usr/bin/pkg-config \"$HOME/.harmonybrew/bin/pkg-config\"; do\n"
        "    if [ -x \"$cand\" ]; then real=$cand; break; fi\n"
        "  done\n"
        "fi\n"
        "[ -n \"$real\" ] || { echo \"gfg13934: pkg-config not found\" >&2; exit 127; }\n"
        "exec \"$real\" \"$@\"\n"
    ) % stage
    with open(script, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(body)
    os.chmod(script, 0o755)
    return wrap_dir


def _gfg_append_pkg_config_arg(cmd, stage):
    def repl(match):
        current = match.group(1)
        if stage in current.split(":"):
            return match.group(0)
        return "--pkg-config-path %s:%s" % (stage, current)

    return re.sub(r"--pkg-config-path\s+(\S+)", repl, cmd, count=1)


def _gfg_inject_pkgconfig(cmd, kwargs):
    text = cmd if isinstance(cmd, str) else " ".join(str(part) for part in cmd)
    if "meson" not in text or "pkg-config-path" not in text or "gnome" not in text:
        return cmd, kwargs
    stage = _gfg_stage_transitive_pcs()
    present = [name for name in _GFG_TRANSITIVE_PC if os.path.isfile(os.path.join(stage, name))]
    wrap_dir = _gfg_write_pkgconfig_wrapper(stage)
    env = kwargs.get("env")
    env = dict(os.environ if env is None else env)
    kwargs["env"] = env
    current = env.get("PKG_CONFIG_PATH", "")
    if stage not in current.split(":"):
        env["PKG_CONFIG_PATH"] = stage + ((":" + current) if current else "")
    path = env.get("PATH", "")
    if not path.startswith(wrap_dir + os.pathsep):
        env["PATH"] = wrap_dir + os.pathsep + path
    if isinstance(cmd, str):
        cmd = _gfg_append_pkg_config_arg(cmd, stage)
    if not getattr(subprocess, "_gfg13934_logged", False):
        print("gfg13934: GOA meson pkg-config extra dir %s files=%s" % (stage, ",".join(present)))
        subprocess._gfg13934_logged = True
    return cmd, kwargs


def _gfg_is_goa_meson_setup(cmd):
    text = cmd if isinstance(cmd, str) else " ".join(str(part) for part in cmd)
    lowered = text.lower()
    return "meson" in lowered and "setup" in lowered and "gnome" in lowered and "pkg-config-path" in lowered


def _gfg_limit_goa_meson_compile(cmd):
    """Bound GOA's Meson build at two workers to finish within CI limits."""
    text = cmd if isinstance(cmd, str) else " ".join(str(part) for part in cmd)
    lowered = text.lower()
    if "meson" not in lowered or "compile" not in lowered or "gnome" not in lowered:
        return cmd, False

    if isinstance(cmd, str):
        match = re.search(r"\b(meson\s+compile)\b", cmd, flags=re.IGNORECASE)
        if not match:
            return cmd, False
        tail = cmd[match.end():]
        tail, count = re.subn(r"(?<!\S)(?:-j\s*\d+|--jobs(?:=|\s+)\d+)(?=\s|$)", "-j 2", tail)
        if not count:
            tail = " -j 2" + tail
        return cmd[:match.end()] + tail, True

    parts = list(cmd)
    for index in range(len(parts) - 1):
        if os.path.basename(str(parts[index])).lower() != "meson" or str(parts[index + 1]).lower() != "compile":
            continue
        position = index + 2
        found_jobs = False
        while position < len(parts):
            token = str(parts[position])
            if token in ("-j", "--jobs"):
                found_jobs = True
                if position + 1 < len(parts):
                    parts[position + 1] = "2"
                    position += 2
                else:
                    parts.append("1")
                    position += 2
                continue
            if token.startswith("--jobs="):
                parts[position] = "--jobs=2"
                found_jobs = True
            elif token.startswith("-j") and token != "-j":
                parts[position] = "-j2"
                found_jobs = True
            position += 1
        if not found_jobs:
            parts[index + 2:index + 2] = ["-j", "2"]
        return parts, True
    return cmd, False


def _gfg_meson_setup_with_wipe(cmd):
    """Discard a partial Meson build tree before retrying GOA compiler detection."""
    if isinstance(cmd, str):
        if re.search(r"\bmeson\s+setup\s+--wipe\b", cmd):
            return cmd
        return re.sub(r"\b(meson\s+setup)\b", r"\1 --wipe", cmd, count=1)
    parts = list(cmd)
    for index in range(len(parts) - 1):
        if os.path.basename(str(parts[index])) == "meson" and str(parts[index + 1]) == "setup":
            if index + 2 < len(parts) and str(parts[index + 2]) == "--wipe":
                return parts
            parts.insert(index + 2, "--wipe")
            break
    return parts


def _gfg_meson_log_paths(cmd, kwargs):
    roots = []
    cwd = kwargs.get("cwd")
    if cwd:
        cwd = os.fspath(cwd)
        roots.extend((cwd, os.path.join(cwd, "build")))
    try:
        tokens = shlex.split(cmd) if isinstance(cmd, str) else [str(part) for part in cmd]
    except ValueError:
        tokens = []
    for index in range(len(tokens) - 1):
        if os.path.basename(tokens[index]) != "meson" or tokens[index + 1] != "setup":
            continue
        position = index + 2
        while position < len(tokens):
            token = tokens[position]
            if token in ("--native-file", "--cross-file", "--pkg-config-path"):
                position += 2
                continue
            if token.startswith("-"):
                position += 1
                continue
            build_dir = token
            if not os.path.isabs(build_dir):
                build_dir = os.path.join(cwd or os.getcwd(), build_dir)
            roots.append(build_dir)
            break
    return [os.path.join(root, "meson-logs", "meson-log.txt") for root in roots]


def _gfg_is_eagain_failure(exc, cmd, kwargs):
    """Check command output and the local Meson log for the known transient spawn error."""
    fragments = []
    for value in (
        getattr(exc, "output", None),
        getattr(exc, "stdout", None),
        getattr(exc, "stderr", None),
    ):
        if value:
            fragments.append(value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value))
    for candidate in _gfg_meson_log_paths(cmd, kwargs):
        try:
            with open(candidate, "r", encoding="utf-8", errors="replace") as handle:
                fragments.append(handle.read())
        except OSError:
            pass
    detail = "\n".join(fragments).lower()
    return any(
        marker in detail
        for marker in (
            "errno 11",
            "resource temporarily unavailable",
            "eagain",
            "can't fork",
            "cannot fork",
        )
    )


def _gfg_patch_subprocess():
    if getattr(subprocess, "_gfg13934", None):
        return
    real_run = subprocess.run

    def run(cmd, *args, **kwargs):
        # CI has hit EAGAIN while GOA's Meson setup probes clang; retry only when
        # that specific setup's output/log confirms process creation failed.
        retry_goa_setup = _gfg_is_goa_meson_setup(cmd)
        cmd, limited_goa_compile = _gfg_limit_goa_meson_compile(cmd)
        if limited_goa_compile:
            print("gfg13934: capped GOA Meson compile to 2 jobs")
        try:
            cmd, kwargs = _gfg_inject_pkgconfig(cmd, kwargs)
        except Exception as exc:
            print("gfg13934: pkg-config inject skipped: %s" % exc)
        if not retry_goa_setup:
            return real_run(cmd, *args, **kwargs)
        capture_stderr = kwargs.get("stderr") is None and not kwargs.get("capture_output")
        if capture_stderr:
            # Keep Meson's normal stdout stream, but capture stderr so transient
            # shell/compiler fork failures can be distinguished from real errors.
            kwargs["stderr"] = subprocess.PIPE

        def replay_stderr(value):
            if not capture_stderr or not value:
                return
            if isinstance(value, bytes):
                value = value.decode("utf-8", "replace")
            sys.stderr.write(value)
            sys.stderr.flush()

        for attempt in range(3):
            try:
                result = real_run(cmd, *args, **kwargs)
            except subprocess.CalledProcessError as exc:
                replay_stderr(getattr(exc, "stderr", None))
                if attempt == 2 or not _gfg_is_eagain_failure(exc, cmd, kwargs):
                    raise
            except OSError as exc:
                if attempt == 2 or getattr(exc, "errno", None) != errno.EAGAIN:
                    raise
            else:
                replay_stderr(getattr(result, "stderr", None))
                if result.returncode == 0 or attempt == 2:
                    return result
                if not _gfg_is_eagain_failure(result, cmd, kwargs):
                    return result
            delay = attempt + 1
            print("gfg13934: GOA Meson setup hit EAGAIN; retry %d/2 after %ds with --wipe" % (attempt + 1, delay))
            time.sleep(delay)
            cmd = _gfg_meson_setup_with_wipe(cmd)
        raise RuntimeError("unreachable GOA Meson setup retry state")

    subprocess.run = run
    subprocess._gfg13934 = True


_gfg_patch_subprocess()


class LibgfbgraphConan(ConanFile):
    name = "libgfbgraph"
    version = "0.2.5"
    description = "GObject library for the Facebook Graph API"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/Archive/libgfbgraph"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("facebook", "gobject", "graph-api")
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

    def requirements(self):
        _gfg_patch_subprocess()
        # librest 0.10.2 与 libsoup3 3.6.5-r3 都钉在共享 glib/2.84.0.1.1。
        # gnome-online-accounts 3.56.5 的配方写的是 glib/2.88.0，这里用根配方
        # 统一版本，避免一张图里出现两套 glib。override 会让 CI 从源码重编 GOA，
        # 模块导入时已挂上 pkg-config 桥，把 libpcre2-8 / libffi / zlib / expat 补进搜索路径。
        self.requires(
            "glib/2.84.0.1.1",
            override=True,
            force=True,
            options={"shared": True},
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("json-glib/1.10.6", transitive_headers=True, transitive_libs=True)
        self.requires("libsoup3/3.6.5-r3", transitive_headers=True, transitive_libs=True)
        # libsoup-3.0.pc 的 Requires(.private) 点名 sqlite3。sqlite3 只是
        # libsoup3 的传递依赖时，Conan 会把 sqlite3/3.49.1 二进制标成 Skipped，
        # 而该配方的 package() 又不安装 sqlite3.pc。configure 的 pkg-config
        # 因此报 Package 'sqlite3', required by 'libsoup-3.0', not found。
        # 升成直接依赖后二进制会下载，generate() 再把 sqlite3.pc 写进 pc-fix。
        self.requires("sqlite3/3.49.1")
        self.requires("librest/0.10.2", transitive_headers=True, transitive_libs=True)
        self.requires("gnome-online-accounts/3.56.5", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3", transitive_libs=True)
        self.requires("dbus/1.14.10", transitive_libs=True)
        self.requires("zlib/1.3.1.1", override=True)

    def build_requirements(self):
        self.tool_requires("m4/1.4.19")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-introspection")
        # config.guess 2025-07-10 认不出 uname -s=HarmonyOS，而且探测编译
        # 写到 $HOME 会 Permission denied。config.sub 接受这个三元组。
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-ohos",
            "--host=aarch64-unknown-linux-ohos",
        ])
        if self.options.get_safe("shared"):
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()
        PkgConfigDeps(self).generate()
        pc_dir = os.path.join(self.generators_folder, "pc-fix")
        self._rewrite_pkgconfig(pc_dir)
        self.buildenv_info.prepend_path("PKG_CONFIG_PATH", pc_dir)
        # Conan's Perl tool-requirement exports PERL5LIB for its own Perl 5.42.
        # That path is incompatible with Harmonybrew/HNP Perl and can make Cwd.so
        # fail to load. Clear it in both CI and local builds, then use one explicit
        # Harmonybrew/HNP interpreter and pin any installed autotools executables.
        perl = _gfg_perl_executable()
        self.buildenv_info.define("PERL", perl)
        self.output.info("Using Perl %s; PERL5LIB is cleared for autotools" % perl)
        self.buildenv_info.prepend_path("PATH", os.path.dirname(perl))
        self.buildenv_info.prepend_path("PATH", os.path.expanduser("~/.harmonybrew/bin"))
        for var in (
            "PERL5LIB", "PERL5OPT", "PERL_LOCAL_LIB_ROOT", "PERLLIB",
            "PERL_MB_OPT", "PERL_MM_OPT", "ACLOCAL_PATH",
            "autom4te_perllibdir", "AC_MACRODIR", "trailer_m4",
            "autom4te_buildauxdir",
        ):
            self.buildenv_info.unset(var)
        for var, exe in (
            ("M4", "m4"),
            ("ACLOCAL", "aclocal"),
            ("AUTOMAKE", "automake"),
            ("AUTOCONF", "autoconf"),
            ("AUTOHEADER", "autoheader"),
            ("AUTOM4TE", "autom4te"),
            ("AUTORECONF", "autoreconf"),
            ("LIBTOOLIZE", "libtoolize"),
            ("PKG_CONFIG", "pkg-config"),
        ):
            path = _gfg_tool_executable(exe)
            if path:
                self.buildenv_info.define(var, path)
                if var == "AUTORECONF":
                    self.output.info("Pinned autoreconf: %s" % path)

    def _host_deps(self):
        host = getattr(self.dependencies, "host", None)
        if host is not None:
            return list(host.values())
        return list(self.dependencies.values())

    def _rewrite_pkgconfig(self, dest):
        """把依赖包里的 .pc 前缀改成包目录，避免 prefix=/ 让 pkg-config 落到根目录。"""
        os.makedirs(dest, exist_ok=True)
        written = 0
        for dep in self._host_deps():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            pc_dir = os.path.join(folder, "lib", "pkgconfig")
            if not os.path.isdir(pc_dir):
                continue
            for name in os.listdir(pc_dir):
                if not name.endswith(".pc"):
                    continue
                src = os.path.join(pc_dir, name)
                with open(src, "r", encoding="utf-8", errors="replace") as handle:
                    lines = handle.read().splitlines()
                out = []
                for line in lines:
                    if line.startswith("prefix="):
                        out.append("prefix=%s" % folder)
                    else:
                        out.append(line)
                if name == "goa-1.0.pc":
                    # goaconfig.h 装在 lib/goa-1.0/include，上游 pc 的 Cflags 没有这一项。
                    extra = "-I%s/lib/goa-1.0/include" % folder
                    for index, line in enumerate(out):
                        if line.startswith("Cflags:"):
                            if extra not in line:
                                out[index] = line + " " + extra
                            break
                    else:
                        out.append("Cflags: %s" % extra)
                with open(os.path.join(dest, name), "w", encoding="utf-8", newline="\n") as handle:
                    handle.write("\n".join(out) + "\n")
                written += 1
        if self._ensure_sqlite3_pc(dest):
            written += 1
        if written == 0:
            raise ConanInvalidConfiguration("依赖包中没有可用的 pkg-config 文件")
        self.output.info("rewrote %d pkg-config files into %s" % (written, dest))

    def _sqlite3_dep(self):
        for dep in self._host_deps():
            ref = getattr(dep, "ref", None)
            if ref is not None and getattr(ref, "name", None) == "sqlite3":
                return dep
        return None

    def _ensure_sqlite3_pc(self, dest):
        """sqlite3/3.49.1 只安装静态库和头文件，不带 sqlite3.pc。"""
        dest_pc = os.path.join(dest, "sqlite3.pc")
        if os.path.isfile(dest_pc):
            return False
        dep = self._sqlite3_dep()
        folder = getattr(dep, "package_folder", None) if dep is not None else None
        if not folder:
            raise ConanInvalidConfiguration(
                "sqlite3/3.49.1 没有包目录，无法为 libsoup-3.0 提供 sqlite3.pc"
            )
        version = str(dep.ref.version)
        body = (
            "prefix=%s\n"
            "exec_prefix=${prefix}\n"
            "libdir=${exec_prefix}/lib\n"
            "includedir=${prefix}/include\n"
            "\n"
            "Name: sqlite3\n"
            "Description: SQLite\n"
            "Version: %s\n"
            "Libs: -L${libdir} -lsqlite3 -ldl -lpthread -lm\n"
            "Cflags: -I${includedir}\n"
        ) % (folder, version)
        with open(dest_pc, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
        self.output.info("wrote sqlite3.pc for %s into %s" % (version, dest))
        return True

    def _ensure_source(self):
        marker = os.path.join(self.source_folder, "configure.ac")
        if not os.path.isfile(marker):
            get(self, **self.conan_data["sources"], strip_root=True, destination=self.source_folder)

    def _gfg_automake_perl_libdir(self):
        """Return the Perl module directory belonging to this build's Automake."""
        automake = self.dependencies.build["automake"]
        libdir = os.path.join(
            automake.package_folder, "share", "automake-1.18"
        )
        if not os.path.isfile(os.path.join(libdir, "Automake", "Config.pm")):
            raise ConanInvalidConfiguration(
                "Automake Perl modules not found in %s" % libdir
            )
        return libdir

    def _gfg_libtool_aclocal_path(self):
        """Return the aclocal directory containing this build's libtool macros."""
        libtool = self.dependencies.build["libtool"]
        aclocal_path = os.path.join(
            libtool.package_folder, "share", "aclocal"
        )
        if not os.path.isfile(os.path.join(aclocal_path, "libtool.m4")):
            raise ConanInvalidConfiguration(
                "libtool m4 macro not found in %s" % aclocal_path
            )
        return aclocal_path

    def _gfg_pkgconf_aclocal_path(self):
        """Return the aclocal directory containing pkgconf's pkg-config macros."""
        pkgconf = self.dependencies.build["pkgconf"]
        aclocal_path = os.path.join(
            pkgconf.package_folder, "share", "aclocal"
        )
        if not os.path.isfile(os.path.join(aclocal_path, "pkg.m4")):
            raise ConanInvalidConfiguration(
                "pkgconf m4 macros not found in %s" % aclocal_path
            )
        return aclocal_path

    def _shell_prefix(self):
        """清掉指向 CI perl 的 autotools 变量，并让 mktemp 建出可写目录。

        config.status 用 umask 077 创建临时目录。这台鸿蒙文件系统对
        0700 目录的后续写入返回 Permission denied。包装 mktemp，建完改成 0755。
        """
        wrapper = os.path.join(self.build_folder, "toolwrap")
        os.makedirs(wrapper, exist_ok=True)
        mktemp = os.path.join(wrapper, "mktemp")
        script = (
            "#!/bin/sh\n"
            "umask 022\n"
            "real=\n"
            "oldifs=$IFS\n"
            "IFS=:\n"
            "for d in $PATH; do\n"
            "  cand=\"$d/mktemp\"\n"
            "  if [ \"$cand\" != \"$0\" ] && [ -x \"$cand\" ]; then real=$cand; break; fi\n"
            "done\n"
            "IFS=$oldifs\n"
            "[ -n \"$real\" ] || real=/usr/bin/mktemp\n"
            "out=$(\"$real\" \"$@\") || exit $?\n"
            "if [ -d \"$out\" ]; then chmod 755 \"$out\"; fi\n"
            "printf '%s\\n' \"$out\"\n"
        )
        with open(mktemp, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(script)
        os.chmod(mktemp, 0o755)
        # automake 生成 test-suite.log 时调用 $(AWK)。AC_PROG_AWK 先找 mawk。
        # 鸿蒙自带 toybox 的 /usr/bin/awk，已能汇总本库这两个测试程序。
        # 包装放在 PATH 最前，避免用到其他账号目录里碰巧存在的 mawk。
        mawk = os.path.join(wrapper, "mawk")
        mawk_script = (
            "#!/bin/sh\n"
            "for c in /usr/bin/awk /bin/awk /system/bin/awk; do\n"
            "  if [ -x \"$c\" ]; then exec \"$c\" \"$@\"; fi\n"
            "done\n"
            "echo \"libgfbgraph: 找不到 awk，无法生成 test-suite.log\" >&2\n"
            "exit 127\n"
        )
        with open(mawk, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(mawk_script)
        os.chmod(mawk, 0o755)
        pc_fix = os.path.join(self.generators_folder, "pc-fix")
        perl = _gfg_perl_executable()
        perl_bin = os.path.dirname(perl)
        prefix = (
            "unset PERL5LIB PERL5OPT PERL_LOCAL_LIB_ROOT PERLLIB PERL_MB_OPT PERL_MM_OPT "
            "autom4te_perllibdir AC_MACRODIR trailer_m4 autom4te_buildauxdir ACLOCAL_PATH; "
            'export PERL="%s"; ' % perl
        )
        # Conan build requirements can export ACLOCAL/AUTOMAKE paths into their
        # own package wrappers. Pin the complete autotools chain here as well as
        # in buildenv_info so autoreconf cannot pick a broken Conan wrapper.
        for var, exe in (
            ("M4", "m4"),
            ("ACLOCAL", "aclocal"),
            ("AUTOMAKE", "automake"),
            ("AUTOCONF", "autoconf"),
            ("AUTOHEADER", "autoheader"),
            ("AUTOM4TE", "autom4te"),
            ("AUTORECONF", "autoreconf"),
            ("LIBTOOLIZE", "libtoolize"),
        ):
            path = _gfg_tool_executable(exe)
            if path:
                prefix += 'export %s="%s"; ' % (var, path)
        prefix += (
            "export PKG_CONFIG_PATH=\"%s:${PKG_CONFIG_PATH:-}\"; " % pc_fix
            + "export PATH=\"%s:%s:$HOME/.harmonybrew/bin:$PATH:/usr/bin:/system/bin\"; hash -r; "
            % (wrapper, perl_bin)
        )
        return prefix

    def _build_tree_libraries(self):
        """链接器刚写出的 .so 能被本机加载；meson install 复制后的副本会被拒绝。"""
        home = os.environ.get("CONAN_HOME", "")
        root = os.path.join(home, "p", "b") if home else ""
        found = {}
        if not os.path.isdir(root):
            return found
        for dirpath, _dirnames, filenames in os.walk(root):
            norm = dirpath.replace("\\", "/")
            if "/p/lib" in norm or "/runtime-" in norm:
                continue
            for filename in filenames:
                if ".so" not in filename or filename.endswith(".symbols"):
                    continue
                path = os.path.join(dirpath, filename)
                current = found.get(filename)
                if current is None:
                    found[filename] = path
                    continue
                # 构建目录里的链接器产物优先于测试时拷出来的副本。
                if "/build/" in norm and "/build/" not in current.replace("\\", "/"):
                    found[filename] = path
        return found

    def _build_json_glib_runtime(self):
        """Build a loadable test library when the published binary has no build tree.

        The published json-glib shared object cannot be loaded by the OHOS
        device linker after Meson install. A warm Conan cache hides this because
        _build_tree_libraries() finds Meson's original, loadable .so. CI downloads
        the binary without that build tree, so both upstream executables exit 127.
        Rebuilding the official pinned source here makes the test runtime
        independent of the cache state; the Conan dependency remains unchanged.
        """
        root = os.path.join(self.build_folder, "json-glib-test-runtime")
        source = os.path.join(root, "source")
        build = os.path.join(root, "build")
        os.makedirs(root, exist_ok=True)
        if not os.path.isfile(os.path.join(source, "meson.build")):
            get(
                self,
                **self.conan_data["json_glib_runtime"],
                strip_root=True,
                destination=source,
            )
        meson = _gfg_tool_executable("meson")
        if not meson:
            raise ConanInvalidConfiguration("meson is required for the json-glib test runtime")
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c") or shutil.which("clang")
        if not cc:
            raise ConanInvalidConfiguration("OHOS C compiler not found for json-glib test runtime")
        compiler_dir = os.path.dirname(cc)
        prefix = self._shell_prefix()
        if compiler_dir:
            prefix += 'export PATH="%s:$PATH"; ' % compiler_dir
        prefix += "export CC=%s; " % shlex.quote(cc)
        ar = os.path.join(compiler_dir, "llvm-ar")
        if os.path.isfile(ar):
            prefix += "export AR=%s; " % shlex.quote(ar)
        if not os.path.isfile(os.path.join(build, "build.ninja")):
            self.run(
                prefix
                + "%s setup %s %s " % (
                    shlex.quote(meson), shlex.quote(build), shlex.quote(source)
                )
                + "-Ddefault_library=shared -Dintrospection=disabled "
                + "-Dtests=false -Ddocumentation=disabled -Dman=false -Dnls=disabled",
                cwd=root,
            )
        jobs = int(self.conf.get("tools.build:jobs", default=2))
        self.run(
            prefix + "%s compile -C %s -j%d" % (
                shlex.quote(meson), shlex.quote(build), jobs
            ),
            cwd=root,
        )
        library = os.path.join(
            build, "json-glib", "libjson-glib-1.0.so.0.1000.6"
        )
        if not os.path.isfile(library):
            raise ConanInvalidConfiguration("json-glib test runtime was not linked")
        return library

    def _runtime_libdirs(self):
        stage = os.path.join(self.build_folder, "runtime-libs")
        if os.path.isdir(stage):
            shutil.rmtree(stage)
        os.makedirs(stage)
        fresh = self._build_tree_libraries()
        # Override an installed binary even when a warm local cache happens to
        # contain a usable linker output. CI only downloads the package binary.
        json_runtime = self._build_json_glib_runtime()
        fresh[os.path.basename(json_runtime)] = json_runtime
        for dep in self._host_deps():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            libdir = os.path.join(folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for name in os.listdir(libdir):
                if ".so" not in name:
                    continue
                src = os.path.join(libdir, name)
                real = os.path.realpath(src)
                if not os.path.isfile(real):
                    continue
                target = fresh.get(os.path.basename(real), real)
                dest = os.path.join(stage, name)
                if os.path.lexists(dest):
                    continue
                os.symlink(target, dest)
        built = os.path.join(self.build_folder, "gfbgraph", ".libs")
        paths = [stage]
        if os.path.isdir(built):
            paths.append(built)
        return paths

    def build(self):
        self._ensure_source()
        apply_conandata_patches(self)
        prefix = self._shell_prefix()
        # 上游 tag 归档不含 gtk-doc；autogen.sh 会因缺少 gtkdocize 退出。
        # Conan's aclocal wrapper has an incomplete embedded Perl module path;
        # pair it with Automake's own pure-Perl modules and the selected Perl.
        automake_perl_libdir = self._gfg_automake_perl_libdir()
        libtool_aclocal_path = self._gfg_libtool_aclocal_path()
        pkgconf_aclocal_path = self._gfg_pkgconf_aclocal_path()
        self.run(
            prefix + "export PERL5LIB=%s; " % shlex.quote(automake_perl_libdir)
            + '"${AUTORECONF:-autoreconf}" -I %s -I %s -fi'
            % (shlex.quote(pkgconf_aclocal_path), shlex.quote(libtool_aclocal_path)),
            cwd=self.source_folder,
        )
        os.makedirs(self.build_folder, exist_ok=True)
        shared = "--enable-shared --disable-static" if self.options.get_safe("shared", True) else "--disable-shared --enable-static"
        configure = (
            "\"%s/configure\" %s "
            "--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos "
            "--disable-introspection --prefix=/ "
            "'--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib' "
            "'--includedir=${prefix}/include' '--oldincludedir=${prefix}/include'"
        ) % (self.source_folder, shared)
        self.run(prefix + configure, cwd=self.build_folder)
        jobs = int(self.conf.get("tools.build:jobs", default=2))
        self.run(prefix + "make -j%d" % jobs, cwd=self.build_folder)
        if not can_run(self):
            raise ConanInvalidConfiguration("上游测试必须在目标机上执行，当前环境不能运行目标二进制")
        libdirs = ":".join(self._runtime_libdirs())
        self.output.info("upstream test LD_LIBRARY_PATH=%s" % libdirs)
        self.run(
            prefix + 'LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH" make check V=1' % libdirs,
            cwd=self.build_folder,
        )
        for name in ("autoptr", "gtestutils"):
            self.output.info("UPSTREAM_CASE_BEGIN %s" % name)
            self.run(
                prefix + 'LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH" ./tests/%s -k --verbose' % (libdirs, name),
                cwd=self.build_folder,
            )
            self.output.info("UPSTREAM_CASE_END %s" % name)

    def package(self):
        prefix = self._shell_prefix()
        self.run(
            prefix + 'make install DESTDIR="%s"' % self.package_folder,
            cwd=self.build_folder,
        )

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libgfbgraph-0.2")
        self.cpp_info.libs = ["gfbgraph-0.2"]
        self.cpp_info.includedirs = ["include/gfbgraph-0.2"]
        if self.settings.os in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.system_libs = ["pthread", "m", "dl"]
