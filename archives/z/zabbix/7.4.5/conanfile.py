#!/usr/bin/env python3
"""Conan recipe - zabbix 7.4.5 (Autotools: configure + make).

Enterprise-class open source monitoring solution.
This recipe builds zabbix agent, get, and sender for HarmonyOS PC arm64.

Dependencies:
  - openssl/3.5.6.1.1  (TLS support)
  - pcre2/10.45         (regular expression support)
  - zlib/1.3.1          (compression support)

R26: Not a system same-name library - dynamic linking is OK.
R32: settings.os must check in ("Linux", "OHOS").

No source patches. All platform adaptations are handled via configure
feature detection injection in source() and OHOS-only build() workarounds.
"""

import os
import re
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
    load, save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class ZabbixConan(ConanFile):
    name = "zabbix"
    version = "7.4.5"
    description = "Enterprise-class open source monitoring solution"
    license = "AGPL-3.0"
    homepage = "https://www.zabbix.com"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1.1")
        self.requires("pcre2/10.45")
        self.requires("zlib/1.3.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "zabbix is only supported on Linux/OHOS, not "
                + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

        configure_path = os.path.join(self.source_folder, "configure")
        content = load(self, configure_path)

        # Fix 1: DEFAULT_INCLUDES lacks -I$(top_builddir) for out-of-source builds
        content = content.replace(
            "DEFAULT_INCLUDES='-I$(top_srcdir)/include/common -I$(top_srcdir)/include'",
            "DEFAULT_INCLUDES='-I$(top_builddir)/include/common -I$(top_srcdir)/include/common -I$(top_srcdir)/include'",
        )

        # Fix 2: Complete resolver capability detection.
        # dns.c has two code paths — thread-safe (res_ninit+res_nsend)
        # and thread-unsafe (_res+res_init+res_send). If neither path
        # is fully available, HAVE_RES_QUERY is removed from config.h,
        # causing dns.c to skip DNS monitoring via its existing guard.
        # No platform-specific macros are used.
        _res_check = r'''
{ printf "%s\n" "$as_me:${as_lineno-$LINENO}: checking whether _res is declared" >&5
printf %s "checking whether _res is declared... " >&6; }
cat confdefs.h - <<_ACEOF >conftest.$ac_ext
#include <resolv.h>
int
main (void)
{
#ifndef _res
  (void) _res;
#endif
  ;
  return 0;
}
_ACEOF
if ac_fn_c_try_compile "$LINENO"
then :
  printf "%s\n" "#define HAVE_DECL__RES 1" >>confdefs.h
  ac_cv_have_decl__res=yes
  { printf "%s\n" "$as_me:${as_lineno-$LINENO}: result: yes" >&5
printf "%s\n" "yes" >&6; }
else $as_nop
  printf "%s\n" "#define HAVE_DECL__RES 0" >>confdefs.h
  ac_cv_have_decl__res=no
  { printf "%s\n" "$as_me:${as_lineno-$LINENO}: result: no" >&5
printf "%s\n" "no" >&6; }
fi
rm -f core conftest.err conftest.$ac_objext conftest.beam conftest.$ac_ext

for ac_func in res_init res_send res_nsend
do :
  as_ac_var=ac_cv_func_$ac_func
  { printf "%s\n" "$as_me:${as_lineno-$LINENO}: checking for $ac_func" >&5
printf %s "checking for $ac_func... " >&6; }
  cat confdefs.h - <<_ACEOF >conftest.$ac_ext
#include <resolv.h>
char $ac_func ();
int
main (void)
{
return $ac_func ();
  ;
  return 0;
}
_ACEOF
if ac_fn_c_try_link "$LINENO"
then :
  eval "$as_ac_var=yes"
  { printf "%s\n" "$as_me:${as_lineno-$LINENO}: result: yes" >&5
printf "%s\n" "yes" >&6; }
else $as_nop
  eval "$as_ac_var=no"
  { printf "%s\n" "$as_me:${as_lineno-$LINENO}: result: no" >&5
printf "%s\n" "no" >&6; }
fi
rm -f core conftest.err conftest.$ac_objext conftest.beam \
    conftest$ac_exeext conftest.$ac_ext
done

# Resolver completeness check:
#   Thread-safe path  = res_ninit + res_nsend
#   Thread-unsafe path = _res + res_init + res_send
# If neither path is fully available, remove HAVE_RES_QUERY.
{ printf "%s\n" "$as_me:${as_lineno-$LINENO}: checking for complete resolver API" >&5
printf %s "checking for complete resolver API... " >&6; }
thread_safe=no
thread_unsafe=no
if test "x$ac_cv_func_res_ninit" = "xyes" && test "x$ac_cv_func_res_nsend" = "xyes"; then
  thread_safe=yes
fi
if test "x$ac_cv_have_decl__res" = "xyes" && test "x$ac_cv_func_res_init" = "xyes" && test "x$ac_cv_func_res_send" = "xyes"; then
  thread_unsafe=yes
fi
if test "x$thread_safe" = "xyes" || test "x$thread_unsafe" = "xyes"; then
  { printf "%s\n" "$as_me:${as_lineno-$LINENO}: result: yes (thread_safe=$thread_safe thread_unsafe=$thread_unsafe)" >&5
printf "%s\n" "yes (thread_safe=$thread_safe thread_unsafe=$thread_unsafe)" >&6; }
else
  { printf "%s\n" "$as_me:${as_lineno-$LINENO}: result: no — resolver API incomplete, disabling HAVE_RES_QUERY" >&5
printf "%s\n" "no — resolver API incomplete, disabling HAVE_RES_QUERY" >&6; }
  cat confdefs.h | grep -v '#define HAVE_RES_QUERY 1' > confdefs.h.tmp
  mv confdefs.h.tmp confdefs.h
fi
'''
        # Insert after HAVE_RES_EXT_EXT check
        marker = "rm -f core conftest.err conftest.$ac_objext conftest.beam \\\n    conftest$ac_exeext conftest.$ac_ext\n\n{ printf \"%s\\n\" \"$as_me:${as_lineno-$LINENO}: checking for struct sockaddr_in6.sin6_len\""
        replacement = "rm -f core conftest.err conftest.$ac_objext conftest.beam \\\n    conftest$ac_exeext conftest.$ac_ext\n" + _res_check + "\n{ printf \"%s\\n\" \"$as_me:${as_lineno-$LINENO}: checking for struct sockaddr_in6.sin6_len\""
        if marker in content:
            content = content.replace(marker, replacement)

        save(self, configure_path, content)

    def generate(self):
        pkgdeps = PkgConfigDeps(self)
        pkgdeps.generate()

        tc = AutotoolsToolchain(self)
        openssl_root = self.dependencies["openssl"].package_folder
        pcre2_root = self.dependencies["pcre2"].package_folder
        zlib_root = self.dependencies["zlib"].package_folder

        gen_dir = os.path.join(self.build_folder, "build-release", "conan")
        os.makedirs(gen_dir, exist_ok=True)
        libpcre2_pc = os.path.join(gen_dir, "libpcre2-8.pc")
        save(self, libpcre2_pc,
            "prefix=" + pcre2_root + "\n"
            "libdir=${prefix}/lib\n"
            "includedir=${prefix}/include\n\n"
            "Name: libpcre2-8\n"
            "Description: PCRE2 - Perl compatible regular expressions C library\n"
            "Version: 10.45\n"
            "Libs: -L${libdir} -lpcre2-8\n"
            "Cflags: -I${includedir}\n"
        )

        tc.configure_args.extend([
            "--build=aarch64-linux-gnu",
            "--host=aarch64-linux-gnu",
            "--enable-agent",
            "--disable-server",
            "--disable-proxy",
            "--disable-agent2",
            "--disable-java",
            "--disable-webservice",
            "--without-mysql",
            "--without-postgresql",
            "--without-sqlite3",
            "--without-libxml2",
            "--without-unixodbc",
            "--without-net-snmp",
            "--without-ssh2",
            "--without-ssh",
            "--without-openipmi",
            "--without-ares",
            "--without-libevent",
            "--without-gnutls",
            "--without-libmodbus",
            "--without-ldap",
            "--without-libcurl",
            "--without-iconv",
            "--with-openssl=" + openssl_root,
            "--with-libpcre2=" + pcre2_root,
            "--with-zlib=" + zlib_root,
        ])
        tc.generate()

    def build(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        old_tmp = os.environ.get("TMPDIR", "")
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir

        pcre2_root = self.dependencies["pcre2"].package_folder
        pcre2_pc = os.path.join(pcre2_root, "lib", "pkgconfig", "libpcre2-8.pc")
        orig_pc = load(self, pcre2_pc)
        fixed_pc = re.sub(
            r'^prefix=/$',
            'prefix=' + pcre2_root,
            orig_pc, count=1, flags=re.MULTILINE,
        )
        save(self, pcre2_pc, fixed_pc)

        try:
            os.environ["ACLOCAL"] = "true"
            os.environ["AUTOCONF"] = "true"
            os.environ["AUTOHEADER"] = "true"
            os.environ["AUTOMAKE"] = "true"
            autotools = Autotools(self)

            # OHOS-only: HMDFS ownership model — mktemp with umask 077 creates
            # directories owned by file_manager that are unwritable.
            # Fix the configure script template in the build copy only.
            if self.settings.os == "OHOS":
                cfg_path = os.path.join(self.source_folder, "configure")
                if os.path.exists(cfg_path):
                    cfg_content = load(self, cfg_path)
                    cfg_content = cfg_content.replace(
                        'umask 077 && mktemp', 'umask 000 && mktemp')
                    cfg_content = cfg_content.replace(
                        'umask 077 && mkdir', 'umask 000 && mkdir')
                    save(self, cfg_path, cfg_content)

            autotools.configure()
            autotools.make(args=["-j2"])
        finally:
            if old_tmp:
                os.environ["TMPDIR"] = old_tmp
            else:
                os.environ.pop("TMPDIR", None)
            os.environ.pop("TMP", None)
            for v in ["ACLOCAL", "AUTOCONF", "AUTOHEADER", "AUTOMAKE"]:
                os.environ.pop(v, None)
            os.environ.pop("LIBPCRE2_CFLAGS", None)
            os.environ.pop("LIBPCRE2_LIBS", None)

    def package(self):
        agent_mf = os.path.join(self.build_folder, "src", "zabbix_agent", "Makefile")
        if os.path.exists(agent_mf):
            mf_content = load(self, agent_mf)
            mf_content = mf_content.replace(
                'cp "../../conf/',
                'cp "' + os.path.join(self.source_folder, "conf") + '/'
            )
            save(self, agent_mf, mf_content)

        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["sbin", "bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "sbin")
        )
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
