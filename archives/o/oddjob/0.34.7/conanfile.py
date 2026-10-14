#!/usr/bin/env python3
"""Conan recipe — oddjob 0.34.7 (autotools, direct cross build).

oddjob: a D-Bus system service which runs odd jobs on behalf of client
applications (daemon oddjobd + helpers oddjob_request / oddjob_mkhomedir).
Upstream ships a host-oriented autotools build; this recipe drives the cross
compiler directly. No upstream source modifications ship in this package."""

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
import os

required_conan_version = ">=2.0"


class OddjobConan(ConanFile):
    name = "oddjob"
    version = "0.34.7"
    description = "oddjob: D-Bus system service which runs odd jobs for clients (direct compiler build)"
    license = "BSD-3-Clause"
    url = "https://releases.pagure.org/oddjob/"
    homepage = "https://releases.pagure.org/oddjob/"
    topics = ("dbus", "service", "pam", "mkhomedir")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    requires = ("dbus/1.14.10.2", "libxml2/2.15.3.1")
    exports_sources = "patches/*"
    no_copy_source = True

    def export_sources(self):
        # Self-written build driver (recipe asset, not an upstream
        # modification): upstream autotools build is host-oriented, so
        # build() drives the cross compiler directly.
        pass

    def validate(self):
        # OHOS PC 交叉构建目标平台白名单（R32 口径：Linux/OHOS 兼容族）
        from conan.errors import ConanInvalidConfiguration
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"oddjob supports Linux/OHOS only, got {self.settings.os}")

    def apply_conandata_patches(self):
        # 0001：非 SELinux 构建守卫（上游 Gentoo 已知缺陷，portability 补丁）
        apply_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)
        self.apply_conandata_patches()

    def build(self):
        src = self.source_folder
        bld = self.build_folder
        cc = self.conf.get("tools.build:compiler_executables", {}).get(
            "c") or "cc"
        deps = self.dependencies
        incs = []
        libs = []
        for name in ("dbus", "libxml2"):
            dep = deps[name]
            for d in dep.cpp_info.includedirs:
                incs.append(f"-I{d}")
            for d in dep.cpp_info.libdirs:
                libs.append(f"-L{d}")
        incs = " ".join(incs)
        libs = " ".join(libs)

        # 源码 src/*.c 里 #include "../config.h"（相对源文件 → 源码根）。
        # 生成最小 config.h 到源码根（autotools 产物等价物）。
        config_h = os.path.join(src, "config.h")
        with open(config_h, "w") as fh:
            fh.write(
                "/* minimal config.h for OHOS cross build (recipe-generated) */\n"
                "#define PACKAGE \"oddjob\"\n"
                "#define VERSION \"0.34.7\"\n"
                "#define PACKAGE_NAME \"oddjob\"\n"
                "#define PACKAGE_NAME_CAPS \"ODDJOB\"\n"
                "#define PACKAGE_VERSION \"0.34.7\"\n"
                "#define ODDJOB_NAMESPACE \"com.redhat\"\n"
                "#define ODDJOB_NAMESPACE_PATH \"/com/redhat\"\n"
                "#define SYSCONFDIR \"/etc\"\n"
                "#define ODDJOB_DCONF_FILE SYSCONFDIR \"/oddjobd.conf\"\n"
                "#define LIBEXECDIR \"/usr/libexec\"\n"
                "#define PKGLIBEXECDIR LIBEXECDIR \"/oddjob\"\n"
                "#define DEFAULT_FAST_RECONNECT_ATTEMPTS 10\n"
                "#define DEFAULT_FAST_RECONNECT_TIMEOUT 5\n"
                "#define DEFAULT_RECONNECT_TIMEOUT 30\n"
                "#define ODDJOB_DBUS_MAJOR_VERSION 1\n"
                "#define ODDJOB_DBUS_MICRO_VERSION 10\n"
                "#define ODDJOB_DBUS_MINOR_VERSION 14\n"
                "#define STDC_HEADERS 1\n"
                "#define HAVE_DLFCN_H 1\n"
                "#define HAVE_INTTYPES_H 1\n"
                "#define HAVE_MEMORY_H 1\n"
                "#define HAVE_STDINT_H 1\n"
                "#define HAVE_STDLIB_H 1\n"
                "#define HAVE_STRING_H 1\n"
                "#define HAVE_STRINGS_H 1\n"
                "#define HAVE_SYS_STAT_H 1\n"
                "#define HAVE_SYS_TYPES_H 1\n"
                "#define HAVE_UNISTD_H 1\n"
                "#define HAVE_SYS_SOCKET_H 1\n"
                "#define HAVE_SYS_SELECT_H 1\n"
                "#define HAVE_SYS_TIME_H 1\n"
                "#define HAVE_POLL_H 1\n"
                "#define HAVE_SYSLOG_H 1\n"
                "#define HAVE_SIGACTION 1\n"
                "#define HAVE_SNPRINTF 1\n"
                "#define HAVE_SOCKET 1\n"
                "#define HAVE_SELECT 1\n"
                "#define HAVE_POLL 1\n"
                "#define HAVE_MEMSET 1\n"
                "#define HAVE_STRDUP 1\n"
                "#define HAVE_STRSTR 1\n"
                "#define HAVE_SETENV 1\n"
                "#define HAVE_UNSETENV 1\n"
                "#define SIZEOF_INT 4\n"
                "#define SIZEOF_LONG 8\n"
                "#define SIZEOF_VOID_P 8\n"
                "#define RETSIGTYPE void\n")
        incs += f" -I{bld}"

        objs = []
        # liboddjob.a（上游 src/Makefile.am：liboddjob_la_SOURCES）——
        # oddjobd 与 oddjob_request 共用的核心库。宏统一由生成的 config.h
        # 提供（单一来源，命令行不重复 -D）。
        for f in ("buffer.c", "util.c", "oddjob_dbus.c", "mainloop.c"):
            obj = os.path.join(bld, f + ".o")
            self.run(f'{cc} -DHAVE_CONFIG_H -I{bld} -I{src} -I{src}/src {incs} '
                     f"-fPIC -O2 -c {os.path.join(src, 'src', f)} -o {obj}")
            objs.append(obj)
        # oddjob_request（上游 oddjob_request_SOURCES = common.h oddjob_request.c
        # + LDADD liboddjob.la @DBUS_LIBS@）
        req_objs = []
        obj = os.path.join(bld, "oddjob_request.c.o")
        self.run(f'{cc} -DHAVE_CONFIG_H -I{bld} -I{src} -I{src}/src {incs} '
                 f"-fPIC -O2 "
                 f"-c {os.path.join(src, 'src', 'oddjob_request.c')} -o {obj}")
        req_objs.append(obj)
        self.run(f"{cc} -o {os.path.join(bld, 'oddjob_request')} "
                 + " ".join(req_objs) + " " + " ".join(objs)
                 + f" {libs} -ldbus-1")
        # oddjobd 守护进程（上游 oddjobd_SOURCES = oddjobd.c；LDADD =
        # libodddbus(la: oddjob_dbus/mainloop) + liboddcommon(la: buffer/util)
        # + @DBUS_LIBS@ @XML_LIBS@）
        dd_obj = os.path.join(bld, "oddjobd.c.o")
        self.run(f'{cc} -DHAVE_CONFIG_H -I{bld} -I{src} -I{src}/src {incs} '
                 f"-fPIC -O2 "
                 f"-c {os.path.join(src, 'src', 'oddjobd.c')} -o {dd_obj}")
        self.run(f"{cc} -o {os.path.join(bld, 'oddjobd')} {dd_obj} "
                 + " ".join(objs) + f" {libs} -ldbus-1 -lxml2")

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "oddjob_request", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "oddjobd", src=self.build_folder,
             dst=os.path.join(self.package_folder, "sbin"))

    def package_id(self):
        del self.info.settings.compiler

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin", "sbin"]
