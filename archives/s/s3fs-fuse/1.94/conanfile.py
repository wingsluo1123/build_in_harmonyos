#!/usr/bin/env python3
"""Conan recipe for s3fs-fuse 1.94 — OHOS-ready.

s3fs-fuse is a FUSE-based file system that mounts Amazon S3 buckets.
It uses the FUSE2 API (FUSE_USE_VERSION 26).

Build system: Autotools (autoreconf + configure + make)
Upstream: https://github.com/s3fs-fuse/s3fs-fuse

OHOS adaptation:
- FUSE2 (libfuse 2.9.9) is not in the Conan artifact repo; it is built
  from source as part of this recipe's build() step.
- HarmonyOS musl libc lacks pthread_cancel / pthread_setcancelstate;
  stub implementations are provided via src/pthread_compat.c.
- libfuse is statically linked (-l:libfuse.a) to avoid pthread issues.
- config.status tmp dir uses TMPDIR to work around HMDFS limitations.
"""
import os
import shutil
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, download, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class S3fsFuseConan(ConanFile):
    name = "s3fs-fuse"
    version = "1.94"
    description = "FUSE-based file system backed by Amazon S3"
    license = "GPL-2.0"
    homepage = "https://github.com/s3fs-fuse/s3fs-fuse"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1")
        self.requires("libxml2/2.15.3")
        self.requires("curl/8.15.0")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: use in ("Linux", "OHOS") format
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("s3fs-fuse supports only Linux and OHOS")

    def build_requirements(self):
        self.tool_requires("automake/1.18")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-openssl")
        # E007: config.guess doesn't recognize HarmonyOS, use build triplet
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def _fix_config_status(self, build_dir):
        """Fix config.status: remove umask 077 for temp dir (HMDFS permission).

        config.status is a generated file, cannot be patched via conandata.yml.
        This fix must be applied inline after configure generates it.
        """
        path = os.path.join(build_dir, "config.status")
        if not os.path.exists(path):
            return
        content = load(self, path)
        content = content.replace("umask 077 && mktemp", "mktemp")
        content = content.replace("umask 077 && mkdir", "mkdir")
        content = content.replace(
            "ac_tmp=$tmp",
            'ac_tmp=$tmp\nchmod 755 "$tmp" 2>/dev/null'
        )
        save(self, path, content)

    def _get_cc(self):
        """Get C compiler from Conan settings (R33)."""
        cc = self.conf_info.get("tools.build:compiler_executables", {}).get("c", "clang") if self.conf_info else "clang"
        return cc

    def _patch_config_guess_sub(self, src_dir):
        """Patch config.guess and config.sub for HarmonyOS recognition (E007)."""
        import re
        for fname in ["config.guess", "config.sub"]:
            fpath = os.path.join(src_dir, fname)
            if not os.path.isfile(fpath):
                # Try subfolder
                for sub in ["build-aux", "aux", "config"]:
                    fpath2 = os.path.join(src_dir, sub, fname)
                    if os.path.isfile(fpath2):
                        fpath = fpath2
                        break
                else:
                    continue
            with open(fpath, "r") as f:
                content = f.read()
            if "__OHOS__" in content:
                continue
            # Add __OHOS__ LIBC detection after __ANDROID__
            content = re.sub(
                r"(#\s*if\s+defined\(__ANDROID__\)\s*\n\s*LIBC=android)",
                r"\1\n#elif defined(__OHOS__)\n    LIBC=ohos",
                content
            )
            # Add ohos to OS list in config.sub
            if fname == "config.sub":
                # Add ohos to the GNU/Linux case
                if "|ohos|" not in content:
                    content = content.replace(
                        "|linux-gnu|",
                        "|linux-gnu|linux-ohos|ohos|"
                    )
            with open(fpath, "w") as f:
                f.write(content)
            self.output.info(f"Patched {fname} for HarmonyOS (E007)")

    def _build_fuse2(self):
        """Build FUSE2 (libfuse 2.9.9) from source as a static library.

        FUSE2 is not available in the Conan artifact repo (only FUSE3/libfuse 3.x).
        s3fs-fuse 1.94 uses the FUSE2 API, so we build it here.
        """
        fuse_url = "https://github.com/libfuse/libfuse/archive/refs/tags/fuse-2.9.9.tar.gz"
        fuse_dir = os.path.join(self.build_folder, "fuse2-build")
        os.makedirs(fuse_dir, exist_ok=True)

        # Download fuse2 source
        fuse_tarball = os.path.join(fuse_dir, "fuse-2.9.9.tar.gz")
        download(self, fuse_url, fuse_tarball)
        self.run(f"cd {fuse_dir} && tar xzf fuse-2.9.9.tar.gz", env="conanbuild")

        fuse_src = os.path.join(fuse_dir, "libfuse-fuse-2.9.9")
        fuse_include = os.path.join(fuse_src, "include")
        fuse_install = os.path.join(self.build_folder, "fuse2-install")
        os.makedirs(os.path.join(fuse_install, "include"), exist_ok=True)
        os.makedirs(os.path.join(fuse_install, "pkgconfig"), exist_ok=True)

        # Create minimal config.h for fuse2
        config_h = os.path.join(fuse_src, "config.h")
        with open(config_h, "w") as f:
            f.write('#define PACKAGE "fuse"\n')
            f.write('#define VERSION "2.9.9"\n')
            f.write('#define PACKAGE_VERSION "2.9.9"\n')
            f.write('#define FUSERMOUNT_DIR "/usr/local/bin"\n')
            f.write('#define HAVE_MNTENT_H 1\n')
            f.write('#define HAVE_HASMNTOPT 1\n')
            f.write('#define HAVE_ENDMNTENT 1\n')

        # Compile fuse2 source files using Conan toolchain compiler
        cc = self._get_cc()
        cflags = f"-fPIC -O2 -I{fuse_include} -I{fuse_src} -D_FILE_OFFSET_BITS=64 -DFUSE_USE_VERSION=26"
        fuse_sources = [
            "buffer.c", "cuse_lowlevel.c", "fuse.c", "fuse_kern_chan.c",
            "fuse_loop.c", "fuse_loop_mt.c", "fuse_lowlevel.c", "fuse_mt.c",
            "fuse_opt.c", "fuse_session.c", "fuse_signals.c", "helper.c",
            "mount.c", "mount_util.c", "ulockmgr.c"
        ]
        obj_files = []
        for src in fuse_sources:
            obj = os.path.join(fuse_src, src.replace(".c", ".o"))
            self.run(f"{cc} {cflags} -c {os.path.join(fuse_src, 'lib', src)} -o {obj}", env="conanbuild")
            obj_files.append(obj)

        # Create static library
        libfuse_a = os.path.join(fuse_install, "libfuse.a")
        self.run(f"ar rcs {libfuse_a} {' '.join(obj_files)}", env="conanbuild")

        # Install fuse2 headers (skip subdirectories like 'old/')
        for h in os.listdir(fuse_include):
            src_path = os.path.join(fuse_include, h)
            if os.path.isfile(src_path):
                shutil.copy(src_path, os.path.join(fuse_install, "include"))

        # Create fuse.pc for pkg-config (static link via -l:libfuse.a)
        fuse_pc = os.path.join(fuse_install, "pkgconfig", "fuse.pc")
        with open(fuse_pc, "w") as f:
            f.write(f"prefix={fuse_install}\n")
            f.write("exec_prefix=${prefix}\n")
            f.write("libdir=${exec_prefix}\n")
            f.write(f"includedir={fuse_install}/include\n\n")
            f.write("Name: fuse\n")
            f.write("Description: Filesystem in Userspace (FUSE) 2.x API\n")
            f.write("Version: 2.9.9\n")
            f.write("Libs: -L${libdir} -l:libfuse.a -lpthread\n")
            f.write("Cflags: -I${includedir} -D_FILE_OFFSET_BITS=64 -DFUSE_USE_VERSION=26\n")

        return fuse_install

    def build(self):
        # 1. Apply patches
        apply_conandata_patches(self)

        # 2. Build FUSE2 from source
        fuse_install = self._build_fuse2()

        # 3. Create pthread_compat.c stub for musl pthread_cancel
        pthread_compat_path = os.path.join(self.source_folder, "src", "pthread_compat.c")
        os.makedirs(os.path.dirname(pthread_compat_path), exist_ok=True)
        with open(pthread_compat_path, "w") as f:
            f.write("""/*
 * pthread_compat.c - Stub implementations for pthread functions
 * not available in HarmonyOS musl libc.
 */
#include <pthread.h>
#include <errno.h>

int pthread_cancel(pthread_t thread)
{
    (void)thread;
    return 0;
}

int pthread_setcancelstate(int state, int *oldstate)
{
    if (oldstate) *oldstate = state;
    return 0;
}
""")

        # 3.5. Add pthread_compat.c to s3fs_SOURCES in Makefile.am
        makefile_am = os.path.join(self.source_folder, "src", "Makefile.am")
        if os.path.isfile(makefile_am):
            content = load(self, makefile_am)
            if "pthread_compat.c" not in content:
                content = content.replace(
                    "    common_auth.cpp\n",
                    "    common_auth.cpp \\\n    pthread_compat.c\n"
                )
                save(self, makefile_am, content)
                self.output.info("Added pthread_compat.c to s3fs_SOURCES in Makefile.am")

        # 4. Run autoreconf in source folder
        # Create m4 dir and set ACLOCAL_PATH for pkg.m4
        m4_dir = os.path.join(self.source_folder, "m4")
        os.makedirs(m4_dir, exist_ok=True)
        # Try to find pkg-config aclocal dir dynamically
        aclocal_paths = []
        for p in ["/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal",
                  "/data/service/hnp/gettext.org/gettext_0.26/share/aclocal",
                  os.path.expanduser("~/usr/local/share/aclocal")]:
            if os.path.isdir(p):
                aclocal_paths.append(p)
        aclocal = ":".join(aclocal_paths) if aclocal_paths else ""
        autoreconf_env = Environment()
        if aclocal:
            autoreconf_env.append("ACLOCAL_PATH", aclocal)
        autoreconf_env.vars(self).save_script("conanbuild_autoreconf")
        self.run(f"cd {self.source_folder} && autoreconf -iv", env="conanbuild")

        # 4.5. Patch config.guess/config.sub for HarmonyOS (E007)
        self._patch_config_guess_sub(self.source_folder)

        # 5. Configure with PKG_CONFIG_PATH pointing to fuse2
        # Set PKG_CONFIG_PATH directly in os.environ so configure finds fuse.pc
        pkg_config_path = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = f"{fuse_install}/pkgconfig:{pkg_config_path}" if pkg_config_path else f"{fuse_install}/pkgconfig"
        # Also set TMPDIR for HMDFS and LD_LIBRARY_PATH for lld
        os.environ["TMPDIR"] = self.build_folder
        sdk_lib = os.path.join(os.path.dirname(os.path.dirname(
            self.conf_info.get("tools.build:compiler_executables", {}).get("c", "/data/service/hnp/bin/clang") if self.conf_info else "/data/service/hnp/bin/clang"
        )), "lib")
        if os.path.isdir(sdk_lib):
            ld_path = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = f"{sdk_lib}:{ld_path}" if ld_path else sdk_lib

        autotools = Autotools(self)
        # Try configure - may fail due to HMDFS config.status temp dir issue
        try:
            autotools.configure()
        except Exception:
            self.output.info("Configure failed, attempting config.status fix...")
        # Fix config.status for HMDFS temp dir issue (generated file)
        self._fix_config_status(self.build_folder)
        # If config.status failed during configure, re-run it manually
        cs_path = os.path.join(self.build_folder, "config.status")
        mk_path = os.path.join(self.build_folder, "Makefile")
        if os.path.exists(cs_path) and not os.path.exists(mk_path):
            self._fix_config_status(self.build_folder)
            self.run(f"cd {self.build_folder} && bash config.status", env="conanbuild")

        # 6. Build (pthread_compat.c is in s3fs_SOURCES via patch)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
