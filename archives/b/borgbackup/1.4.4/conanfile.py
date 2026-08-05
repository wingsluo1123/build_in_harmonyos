#!/usr/bin/env python3
"""Conan recipe for borgbackup — Python setuptools with Cython C extensions.

borgbackup is a deduplicating backup program. It uses Python setuptools
to build C extensions via Cython, linking against system-installed
C libraries (openssl, lz4, zstd, xxhash).

Build dependencies (Cython, msgpack, pkgconfig) are installed via pip
in the build() method. C libraries are expected to be pre-installed
on the build machine (via cmd-pkgs or equivalent).
"""
import os
import sysconfig

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BorgbackupConan(ConanFile):
    name = "borgbackup"
    version = "1.4.4"
    description = "Deduplicating backup program with compression and authenticated encryption"
    license = "BSD-3-Clause"
    homepage = "https://www.borgbackup.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    # R32: settings.os judgment must use "in" not "=="
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # C libraries are system-installed (cmd-pkgs) on the build machine
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Install Python build dependencies via pip (no --user, conflicts with Conan env)
        self.run("pip3 install Cython msgpack pkgconfig packaging setuptools_scm")

        # Create stub ACL headers (OpenHarmony has no libacl)
        stub_dir = os.path.join(self.source_folder, "src", "borg", "stub_acl")
        os.makedirs(os.path.join(stub_dir, "sys"), exist_ok=True)
        os.makedirs(os.path.join(stub_dir, "acl"), exist_ok=True)

        sys_acl_h = os.path.join(stub_dir, "sys", "acl.h")
        with open(sys_acl_h, "w") as f:
            f.write('''#ifndef _STUB_SYS_ACL_H
#define _STUB_SYS_ACL_H
#include <sys/types.h>
#ifdef BORG_NO_ACL
typedef void *acl_t;
typedef void *acl_entry_t;
typedef void *acl_permset_t;
typedef int acl_type_t;
typedef int acl_perm_t;
typedef int acl_tag_t;
typedef int acl_entry_id_t;
#define ACL_TYPE_ACCESS  0x8000
#define ACL_TYPE_DEFAULT 0x4000
#define ACL_FIRST_ENTRY  0
#define ACL_NEXT_ENTRY   1
#define ACL_USER_OBJ     0x01
#define ACL_USER         0x02
#define ACL_GROUP_OBJ    0x04
#define ACL_GROUP        0x08
#define ACL_MASK         0x10
#define ACL_OTHER        0x20
#define ACL_READ         0x04
#define ACL_WRITE        0x02
#define ACL_EXECUTE      0x01
#define ACL_UNDEFINED_TAG 0x00
static inline int acl_free(void *obj) { (void)obj; return 0; }
static inline acl_t acl_get_file(const char *p, acl_type_t t) { (void)p; (void)t; return 0; }
static inline int acl_set_file(const char *p, acl_type_t t, acl_t a) { (void)p; (void)t; (void)a; return 0; }
static inline acl_t acl_get_fd(int fd) { (void)fd; return 0; }
static inline int acl_set_fd(int fd, acl_t a) { (void)fd; (void)a; return 0; }
static inline int acl_valid(acl_t a) { (void)a; return 0; }
static inline acl_t acl_init(int c) { (void)c; return 0; }
static inline int acl_create_entry(acl_t *a, acl_entry_t *e) { (void)a; *e = 0; return -1; }
static inline int acl_get_entry(acl_t a, acl_entry_id_t i, acl_entry_t *e) { (void)a; (void)i; *e = 0; return -1; }
static inline char *acl_to_text(acl_t a, ssize_t *l) { (void)a; if(l) *l = 0; return 0; }
static inline acl_t acl_from_text(const char *t) { (void)t; return 0; }
static inline int acl_get_tag_type(acl_entry_t e, acl_tag_t *t) { (void)e; *t = 0; return -1; }
static inline void *acl_get_qualifier(acl_entry_t e) { (void)e; return 0; }
static inline int acl_get_permset(acl_entry_t e, acl_permset_t *p) { (void)e; *p = 0; return -1; }
static inline int acl_get_perm(acl_permset_t p, acl_perm_t m) { (void)p; (void)m; return 0; }
static inline int acl_add_perm(acl_permset_t p, acl_perm_t m) { (void)p; (void)m; return 0; }
static inline int acl_clear_perms(acl_permset_t p) { (void)p; return 0; }
static inline int acl_set_tag_type(acl_entry_t e, acl_tag_t t) { (void)e; (void)t; return -1; }
static inline int acl_set_qualifier(acl_entry_t e, const void *q) { (void)e; (void)q; return -1; }
static inline int acl_set_permset(acl_entry_t e, acl_permset_t p) { (void)e; (void)p; return -1; }
static inline int acl_calc_mask(acl_t *a) { (void)a; return -1; }
static inline int acl_dup(acl_t a, acl_t *n) { (void)a; *n = 0; return -1; }
static inline int acl_extended_file(const char *p) { (void)p; return 0; }
static inline int acl_extended_fd(int fd) { (void)fd; return 0; }
static inline int acl_extended_file_nofollow(const char *p) { (void)p; return 0; }
#endif /* BORG_NO_ACL */
#endif /* _STUB_SYS_ACL_H */
''')

        libacl_h = os.path.join(stub_dir, "acl", "libacl.h")
        with open(libacl_h, "w") as f:
            f.write('#ifndef _STUB_ACL_LIBACL_H\n#define _STUB_ACL_LIBACL_H\n#endif\n')

        # Set library prefixes — C libraries are system-installed via cmd-pkgs
        prefix = os.path.join(os.path.expanduser("~"), "usr", "local")
        os.environ["BORG_OPENSSL_PREFIX"] = prefix
        os.environ["BORG_LIBLZ4_PREFIX"] = prefix
        os.environ["BORG_LIBZSTD_PREFIX"] = prefix
        os.environ["BORG_LIBXXHASH_PREFIX"] = prefix
        # Ensure Python and SSL shared libraries are loadable (R33: no hardcoded paths)
        # Derive HNP external lib dir from Python executable path
        py_bin = os.path.dirname(os.path.realpath(sysconfig.get_config_var("BINDIR") or "/data/service/hnp/bin/python3"))
        hnp_lib = os.path.join(os.path.dirname(py_bin), "lib", "external")
        if not os.path.isdir(hnp_lib):
            # Fallback: search for libssl.so.3 relative to python
            import glob
            candidates = glob.glob("/data/service/hnp/*/lib/external")
            hnp_lib = candidates[0] if candidates else prefix + "/lib"
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = f"{hnp_lib}:{prefix}/lib:{current_ld}"

        # Build C extensions — run from source folder where setup.py lives
        self.run("python3 setup.py build_ext", cwd=self.source_folder)

    def package(self):
        # Install to package directory
        # Use --root=package_folder and --prefix=/usr to avoid nested paths
        prefix = os.path.join(os.environ.get("HOME", "/storage/Users/currentUser"), "usr", "local")
        os.environ["BORG_OPENSSL_PREFIX"] = prefix
        os.environ["BORG_LIBLZ4_PREFIX"] = prefix
        os.environ["BORG_LIBZSTD_PREFIX"] = prefix
        os.environ["BORG_LIBXXHASH_PREFIX"] = prefix
        # Ensure Python and SSL shared libraries are loadable (R33: dynamic path)
        py_bin = os.path.dirname(os.path.realpath(sysconfig.get_config_var("BINDIR") or "/data/service/hnp/bin/python3"))
        hnp_lib = os.path.join(os.path.dirname(py_bin), "lib", "external")
        if not os.path.isdir(hnp_lib):
            import glob
            candidates = glob.glob("/data/service/hnp/*/lib/external")
            hnp_lib = candidates[0] if candidates else prefix + "/lib"
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = f"{hnp_lib}:{prefix}/lib:{current_ld}"

        self.run(
            "python3 setup.py install "
            "--prefix=/usr "
            f"--root={self.package_folder} "
            "--single-version-externally-managed "
            "--no-compile",
            cwd=self.source_folder
        )

    def package_info(self):
        # borgbackup is a CLI tool — expose bin/ directory
        bin_dir = os.path.join(self.package_folder, "usr", "bin")
        if os.path.isdir(bin_dir):
            self.cpp_info.bindirs = ["usr/bin"]
        lib_dir = os.path.join(self.package_folder, "usr", "lib")
        if os.path.isdir(lib_dir):
            self.cpp_info.libdirs = ["usr/lib"]
        # Set PYTHONPATH so the borg entry point can find its package
        pyver = sysconfig.get_python_version()
        site_packages = f"usr/lib/python{pyver}/site-packages"
        self.runenv_info.append("PYTHONPATH", [site_packages])
