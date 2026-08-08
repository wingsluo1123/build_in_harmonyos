import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.gnu.pkgconfigdeps import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class AlsaUtilsConan(ConanFile):
    name = "alsa-utils"
    version = "1.2.14"
    description = "ALSA Utilities - Advanced Linux Sound Architecture userspace tools"
    license = "GPL-2.0"
    homepage = "https://www.alsa-project.org/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-udev-rules-dir=no")
        tc.configure_args.append("--with-curses=ncursesw")

        # alsa-lib is installed system-wide; add its paths to the toolchain
        alsa_prefix = os.path.expanduser("~/usr/local")
        if str(self.settings.os) in ("Linux", "OHOS"):
            tc.extra_cflags.append(f"-I{alsa_prefix}/include")
            tc.extra_ldflags.append(f"-L{alsa_prefix}/lib")
        tc.generate()

        env = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define_path("TMPDIR", tmpdir)
        if str(self.settings.os) == "OHOS":
            env.define("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            env.define("SHELL", "/data/service/hnp/bin/bash")
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)
        env.append_path("PKG_CONFIG_PATH", f"{alsa_prefix}/lib/pkgconfig")
        env.append_path("LD_LIBRARY_PATH", f"{alsa_prefix}/lib")
        env.vars(self).save_script("ohos_env")

    def build(self):
        apply_conandata_patches(self)

        # Platform adaptation: fix shebangs for HarmonyOS (E165)
        # HarmonyOS has no /bin directory; sh is at /system/bin/sh
        if str(self.settings.os) == "OHOS":
            for root, _, files in os.walk(self.source_folder):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "rb") as f:
                            raw = f.read()
                        if not raw[:2] == b"#!":
                            continue
                        newline = b"\r\n" if b"\r\n" in raw[:100] else b"\n"
                        first_line = raw.split(newline, 1)[0]
                        new_first = first_line
                        if b"/bin/bash" in first_line:
                            new_first = first_line.replace(b"/bin/bash", b"/data/service/hnp/bin/bash")
                        elif b"/bin/sh" in first_line or b"/usr/bin/sh" in first_line:
                            new_first = (first_line.replace(b"/usr/bin/sh", b"/system/bin/sh")
                                         .replace(b"/bin/sh", b"/system/bin/sh"))
                        if new_first != first_line:
                            rest = raw[len(first_line):]
                            with open(fpath, "wb") as f:
                                f.write(new_first + rest)
                    except (PermissionError, OSError, IndexError):
                        pass

        # Create pthread_compat.c for musl libc (no pthread_cancel)
        compat_dir = os.path.join(self.source_folder, "bat")
        compat_file = os.path.join(compat_dir, "pthread_compat.c")
        if not os.path.exists(compat_file):
            with open(compat_file, "w") as f:
                f.write(
                    "/* HarmonyOS: musl libc does not implement POSIX thread cancellation API */\n"
                    "#ifdef __OHOS__\n"
                    "#include <pthread.h>\n\n"
                    "int pthread_cancel(pthread_t t) { (void)t; return 0; }\n"
                    "int pthread_testcancel(void) { return 0; }\n"
                    "int pthread_setcancelstate(int s, int *os) {\n"
                    "    if(os) *os = PTHREAD_CANCEL_ENABLE;\n"
                    "    return 0;\n"
                    "}\n"
                    "int pthread_setcanceltype(int t, int *ot) {\n"
                    "    if(ot) *ot = PTHREAD_CANCEL_DEFERRED;\n"
                    "    return 0;\n"
                    "}\n"
                    "#endif /* __OHOS__ */\n"
                )

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.system_libs = ["asound"]
