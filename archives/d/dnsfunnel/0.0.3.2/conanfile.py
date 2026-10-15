#!/usr/bin/env python3
"""Conan recipe for dnsfunnel 0.0.3.2 — skarnet.org local DNS forwarding funnel.

dnsfunnel uses skarnet's own configure + make system (NOT standard autotools
and NOT cmake), exactly like the rest of the skarnet.org family (the skalibs
and s6-dns recipes in this repository use the same pattern).

It is a thin front-end: two executables (dnsfunneld, dnsfunnel-translate) that
link statically against skalibs (libskarnet.a) and s6-dns (libs6dns.a). No
library is installed for consumers, so package_type is "application".

Dependencies are consumed as raw package folders (--with-include/--with-lib/
--with-sysdeps) because skarnet configure is not Conan-toolchain aware; this
also keeps the recipe working with s6-dns, whose own recipe declares
package_type="application" (its cpp_info is therefore not propagated).
"""
import glob
import os
import shlex

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DnsfunnelConan(ConanFile):
    name = "dnsfunnel"
    version = "0.0.3.2"
    description = "skarnet.org dnsfunnel — small local DNS forwarder (dnsfunneld, dnsfunnel-translate)"
    license = "ISC"
    homepage = "https://skarnet.org/software/dnsfunnel/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("skalibs/2.15.1.0")
        self.requires("s6-dns/2.4.1.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # skarnet configure is NOT standard autotools — do not use AutotoolsToolchain.
        # R33: do not reference CC/CFLAGS as shell variables in the command; the
        #      configure script probes CC, then ${cross}gcc, then ${cross}clang on
        #      its own, and the conanbuild env (profile [buildenv] + PATH) puts the
        #      OHOS clang directory first, so the probe resolves to clang.
        src = self.source_folder
        prefix = self.package_folder

        skalibs = self.dependencies["skalibs"].package_folder
        s6dns = self.dependencies["s6-dns"].package_folder

        # OHOS clang ships without a default sysroot, so skarnet configure's link
        # probes (tryldflag / detectlibs) cannot locate CRT startup objects
        # (Scrt1.o, crti.o, crtn.o) and abort with "unable to determine required
        # linker flags for socket functions". Inject --sysroot via LDFLAGS so the
        # probes can link. The profile only declares CC/PATH/SHELL (buildenv), it
        # does not declare LDFLAGS, so LDFLAGS is exported into this process
        # environment and inherited by the subprocesses of self.run(...,
        # env="conanbuild") — conanbuild adds the profile variables on top of
        # this environment, it does not replace it.
        # Sysroot resolution is explicit and loud: OHOS_NATIVE_SYSROOT env first,
        # then the SDK glob; on OHOS with neither available we warn instead of
        # silently skipping the injection (otherwise the later link-probe error
        # points at the wrong cause).
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os in ("Linux", "OHOS"):
            sysroot = os.environ.get("OHOS_NATIVE_SYSROOT", "").strip()
            if not sysroot:
                sysroots = sorted(glob.glob(
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot"
                ))
                sysroot = sysroots[-1] if sysroots else ""
            if sysroot:
                self.output.info(f"sysroot = {sysroot}")
                cur = os.environ.get("LDFLAGS", "").strip()
                os.environ["LDFLAGS"] = f"{cur} --sysroot={sysroot}".strip()
            elif self.settings.os == "OHOS":
                self.output.warning(
                    "OHOS 上未找到 native sysroot：环境变量 OHOS_NATIVE_SYSROOT 为空，"
                    "且 /data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot 无匹配项。"
                    "skarnet configure 的链接探测可能因缺少 CRT 启动对象失败，"
                    "请设置 OHOS_NATIVE_SYSROOT 后重试。")

        configure_cmd = (
            f"cd {shlex.quote(src)} && ./configure --prefix={shlex.quote(prefix)} "
            f"--disable-shared "
            f"--with-sysdeps={shlex.quote(os.path.join(skalibs, 'lib/skalibs/sysdeps'))} "
            f"--with-include={shlex.quote(os.path.join(skalibs, 'include'))} "
            f"--with-include={shlex.quote(os.path.join(s6dns, 'include'))} "
            f"--with-lib={shlex.quote(os.path.join(skalibs, 'lib'))} "
            f"--with-lib={shlex.quote(os.path.join(s6dns, 'lib'))}"
        )
        self.run(configure_cmd, env="conanbuild")
        # R9: -j1 (skarnet build order matters; family recipes use -j1)
        self.run(f"cd {shlex.quote(src)} && make -j1", env="conanbuild")
        self.run(f"cd {shlex.quote(src)} && make install", env="conanbuild")

    def package(self):
        # make install already writes into package_folder: skarnet configure was
        # given --prefix=package_folder, so bin/dnsfunneld,
        # bin/dnsfunnel-translate and include/dnsfunnel/config.h end up there.
        pass

    def package_info(self):
        # application: two CLI tools, no consumer-facing library.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []
