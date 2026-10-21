#!/usr/bin/env python3
"""Conan recipe for SPDK 25.05 -- Storage Performance Development Kit.

SPDK is Intel's framework for building user-space, polled-mode, asynchronous,
lock-free storage applications.  It is a large multi-library C project built by
its own ``./configure`` + ``make`` system and it always builds against a DPDK
sub-module (``spdk/dpdk``), used here at the exact commit pinned by the
``v25.05`` tag.

OHOS adaptation notes -- see notes.md for the full write-up:

* SPDK's official source tarball does not ship the git sub-modules.  The recipe
  downloads the pinned DPDK fork as its own source entry and builds it into a
  private prefix, then points SPDK at it with ``--with-dpdk=``.
* DPDK is built as a *cross* build with ``system = 'linux'`` (the OHOS clang
  target is ``aarch64-unknown-linux-ohos``) and ``platform = 'generic'``.
* Both DPDK and SPDK are compiled with ``-fno-emulated-tls``.  The OHOS clang
  driver defaults to *emulated* TLS (``__emutls_v.*``); DPDK's per-lcore
  variables are exported through version scripts that do not list the emutls
  control symbols, so emulated TLS breaks shared-library links.  Native TLS is
  supported by the OHOS runtime and matches the upstream (Linux) layout.
* ISA-L is force-disabled on non-Linux (patch to ``configure``): its assembly
  requires GNU ``as`` >= 2.24 and is not required for the storage core.
* The DPDK/SPDK source patches live under ``patches/`` and are applied with
  ``apply_conandata_patches`` (G1 requirement).

The package exposes the header-only/CPU-only libraries (``spdk_util``,
``spdk_log``, ``spdk_json``) as the default link set -- those are the pieces
that do not need the DPDK EAL runtime (hugepages / vfio / uio), which OHOS
does not provide.  Every other SPDK library is still compiled and installed.
"""
import os
import glob
import shutil
import contextlib
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    save,
    unzip,
)

required_conan_version = ">=2.0"


class SpdkConan(ConanFile):
    name = "spdk"
    version = "25.05"
    description = ("SPDK - Storage Performance Development Kit "
                   "(user-space storage framework, C)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/spdk/spdk"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "run_unit_tests.py"

    # ------------------------------------------------------------------ source
    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OpenSSL: spdk_md5 uses the EVP interface unconditionally (25.05).
        # libuuid: lib/util links -luuid and uses uuid_generate_sha1.
        # libaio: the bdev_aio module uses the Linux native AIO API.
        self.requires("libuuid/2.42.2")
        self.requires("openssl/3.5.6.1")
        self.requires("libaio/0.3.112.1")

    def build_requirements(self):
        # DPDK's pmdinfogen (ELF PMD metadata extraction) is a Python tool.
        self.tool_requires("pyelftools/0.33")
        self.test_requires("cunit/2.1-3")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "The spdk OHOS adaptation is only validated on Linux/OHOS, "
                "not " + str(self.settings.os))

    def _fetch(self, key, destination):
        """Download+extract a source entry.

        The canonical GitHub archive URL is kept as a single ``url`` in
        conandata.yml so the CI mirror injection applies to it, while the
        byte-identical codeload endpoint (reachable from the OHOS device, where
        github.com is commonly unreachable) is tried first.
        """
        info = self.conan_data["sources"][key]
        urls = ([info["codeload"]] if info.get("codeload") else []) + [info["url"]]
        filename = os.path.join(self.source_folder, key + ".tar.gz")
        download(self, urls, filename, sha256=info["sha256"])
        unzip(self, filename, destination=destination, strip_root=True)
        os.remove(filename)

    def source(self):
        self._fetch("spdk", self.source_folder)
        self._fetch("dpdk", os.path.join(self.source_folder, "dpdk"))

    # ----------------------------------------------------------------- helpers
    def _dep_paths(self, name, attr):
        dep = self.dependencies[name]
        out = []
        for d in getattr(dep.cpp_info.aggregated_components(), attr):
            out.append(d if os.path.isabs(d)
                       else os.path.join(dep.package_folder, d))
        return sorted(set(out))

    def _compilers(self):
        exe = self.conf.get("tools.build:compiler_executables",
                            default={}, check_type=dict)
        return exe.get("c") or "clang", exe.get("cpp") or "clang++"

    def _llvm_tool(self, compiler, name):
        # CI exposes clang through a launcher/symlink directory which need not
        # contain its LLVM siblings. Resolve the real compiler first, then the
        # profile PATH. In particular, never return a bare name for a symlink
        # target: it would be resolved relative to shim/, not searched in PATH.
        with VirtualBuildEnv(self).vars().apply():
            compiler_path = shutil.which(compiler) or compiler
            for directory in (os.path.dirname(os.path.realpath(compiler_path)),
                              os.path.dirname(compiler_path)):
                candidate = os.path.join(directory, name)
                if os.path.isfile(candidate):
                    return os.path.abspath(candidate)
            candidate = shutil.which(name)
            if candidate:
                # llvm-ranlib/llvm-strip can be aliases of llvm-ar/objcopy;
                # their invocation name selects the operation to perform.
                return os.path.abspath(candidate)
        raise ConanInvalidConfiguration("Required LLVM tool not found: " + name)

    def _pyelftools_pythonpath(self):
        dep = self.dependencies.build["pyelftools"]
        return sorted(glob.glob(os.path.join(
            dep.package_folder, "lib", "python*", "site-packages")))

    def _shim_dir(self):
        """A PATH entry providing the tools toybox/HMDFS lack."""
        compiler, _ = self._compilers()
        shim = os.path.join(self.build_folder, "shim")
        os.makedirs(shim, exist_ok=True)
        ar_link = os.path.join(shim, "ar")
        archiver = self._llvm_tool(compiler, "llvm-ar")
        if os.path.lexists(ar_link):
            os.remove(ar_link)
        os.symlink(archiver, ar_link)
        self.output.info("Archiver shim: {} -> {}".format(ar_link, archiver))
        return shim

    @contextlib.contextmanager
    def _extra_env(self, mapping, path_prepend=None):
        """Apply the profile/dependency environment before recipe overrides.

        Commands in this context use run(env=None), so a generated
        conanbuild.sh cannot replace the PATH/PYTHONPATH applied here.
        """
        overlay = Environment()
        for key, value in mapping.items():
            overlay.define(key, value)
        for path in reversed(path_prepend or []):
            overlay.prepend_path("PATH", path)
        with VirtualBuildEnv(self).vars().apply():
            with overlay.vars(self).apply():
                yield

    # ------------------------------------------------------------------- build
    def build(self):
        apply_conandata_patches(self)
        self._build_dpdk()
        self._build_spdk()

    def _build_dpdk(self):
        dpdk_dir = os.path.join(self.source_folder, "dpdk")
        prefix = os.path.join(self.build_folder, "dpdk-install")
        shutil.rmtree(os.path.join(dpdk_dir, "build"), ignore_errors=True)
        shutil.rmtree(prefix, ignore_errors=True)
        compiler, cpp = self._compilers()
        cross = os.path.join(self.build_folder, "ohos-cross.txt")
        with open(cross, "w", encoding="utf-8") as handle:
            handle.write(
                "[binaries]\n"
                "c = '%s'\n"
                "cpp = '%s'\n"
                "ar = '%s'\n"
                "strip = '%s'\n"
                "nm = '%s'\n"
                "ranlib = '%s'\n"
                "pkg-config = 'pkg-config'\n"
                "\n[properties]\n"
                "platform = 'generic'\n"
                "numa = false\n"
                "\n[host_machine]\n"
                "system = 'linux'\n"
                "cpu_family = 'aarch64'\n"
                "cpu = 'armv8-a'\n"
                "endian = 'little'\n"
                % (compiler, cpp,
                   self._llvm_tool(compiler, "llvm-ar"),
                   self._llvm_tool(compiler, "llvm-strip"),
                   self._llvm_tool(compiler, "llvm-nm"),
                   self._llvm_tool(compiler, "llvm-ranlib")))

        mapping = {"PYTHONPATH": os.pathsep.join(self._pyelftools_pythonpath())}
        jobs = build_jobs(self)
        with self._extra_env(mapping, path_prepend=[self._shim_dir()]):
            self.run(
                'meson setup build --cross-file "%s"'
                " -Ddefault_library=static"
                " -Dc_args=-fno-emulated-tls -Dcpp_args=-fno-emulated-tls"
                " -Denable_docs=false -Dtests=false -Denable_kmods=false"
                " -Ddisable_drivers=*/*,*/*/* -Ddisable_apps=*" % cross,
                cwd=dpdk_dir, env=None)
            self.run("ninja -C build -j%d" % jobs, cwd=dpdk_dir, env=None)
            self.run('meson configure build -Dprefix="%s"' % prefix,
                     cwd=dpdk_dir, env=None)
            # meson install re-runs ninja; PYTHONPATH (pyelftools) must be set
            self.run("meson install -C build", cwd=dpdk_dir, env=None)

    def _build_spdk(self):
        dpdk_prefix = os.path.join(self.build_folder, "dpdk-install")
        compiler, cpp = self._compilers()

        def inc(name):
            return ["-I" + d for d in self._dep_paths(name, "includedirs")]

        def lib(name):
            return ["-L" + d for d in self._dep_paths(name, "libdirs")]

        cflags = " ".join(["-fno-emulated-tls"]
                          + inc("libuuid") + inc("openssl") + inc("libaio")
                          + inc("cunit"))
        ldflags = " ".join(lib("libuuid") + lib("openssl") + lib("libaio")
                           + lib("cunit"))

        mapping = {
            "CC": compiler,
            "CXX": cpp,
            "LD": self._llvm_tool(compiler, "ld.lld"),
            "AR": self._llvm_tool(compiler, "llvm-ar"),
            "RANLIB": self._llvm_tool(compiler, "llvm-ranlib"),
            "NM": self._llvm_tool(compiler, "llvm-nm"),
            "STRIP": self._llvm_tool(compiler, "llvm-strip"),
            "CFLAGS": cflags,
            "CXXFLAGS": cflags,
            "LDFLAGS": ldflags,
        }
        options = [
            '--prefix="%s"' % os.path.join(self.build_folder, "spdk-install"),
            '--with-dpdk="%s"' % dpdk_prefix,
            "--disable-tests", "--enable-unit-tests",
            "--disable-examples", "--disable-apps",
            "--without-vhost", "--without-virtio", "--without-uring",
            "--without-rbd", "--without-daos", "--without-fc",
            "--without-idxd", "--without-crypto", "--without-vbdev-compress",
            "--without-dpdk-compressdev", "--without-vfio-user",
            "--without-xnvme", "--without-ocf", "--without-fuse",
            "--without-nvme-cuse", "--without-avahi", "--without-golang",
            "--without-usdt", "--without-vtune", "--without-rdma",
            "--without-ublk", "--without-aio-fsdev",
        ]
        jobs = build_jobs(self)
        with self._extra_env(mapping,
                             path_prepend=[self._shim_dir(),
                                           os.path.dirname(compiler)]):
            self.run("./configure " + " ".join(options),
                     cwd=self.source_folder, env=None)
            self.run("make -j%d --jobserver-style=pipe" % jobs,
                     cwd=self.source_folder, env=None)
            self.run('"{}" "{}" "{}"'.format(
                sys.executable,
                os.path.join(self.source_folder, "run_unit_tests.py"),
                self.source_folder), cwd=self.source_folder, env=None)

    # ----------------------------------------------------------------- package
    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include", "spdk"),
             dst=os.path.join(self.package_folder, "include", "spdk"))
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include", "spdk_internal"),
             dst=os.path.join(self.package_folder, "include", "spdk_internal"))
        copy(self, "*.a",
             src=os.path.join(self.source_folder, "build", "lib"),
             dst=os.path.join(self.package_folder, "lib"),
             excludes=("libspdk_ut.a", "libspdk_ut_mock.a"))
        copy(self, "summary.json",
             src=os.path.join(self.source_folder, "unit-test-results"),
             dst=os.path.join(self.package_folder, "res"))
        # Bundle the pinned DPDK that the SPDK libraries were built against.
        copy(self, "*.a",
             src=os.path.join(self.build_folder, "dpdk-install", "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h",
             src=os.path.join(self.build_folder, "dpdk-install", "include"),
             dst=os.path.join(self.package_folder, "include"))
        save(self, os.path.join(self.package_folder, "res", "build-info.txt"),
             "spdk 25.05 / DPDK 25.03.0 (spdk fork commit "
             "cf36799c473a686fa14fde9af97f917a2125d3d5)\n"
             "OHOS aarch64, native TLS (-fno-emulated-tls), "
             "ISA-L disabled (non-Linux)\n")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "spdk")
        self.cpp_info.set_property("cmake_target_name", "spdk::spdk")
        self.cpp_info.set_property("pkg_config_name", "spdk")
        # Link order matters for static archives: dependents first.
        self.cpp_info.libs = ["spdk_json", "spdk_log", "spdk_util"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.system_libs = ["pthread", "m", "dl"]
        self.cpp_info.cflags = ["-fno-emulated-tls"]
