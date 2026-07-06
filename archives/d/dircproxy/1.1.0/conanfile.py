#!/usr/bin/env python3
"""Conan recipe — dircproxy 1.1.0 (Autotools, no deps).

dircproxy: an IRC proxy server (bouncer).
Source from GitHub archive requires autoreconf to generate configure.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DircproxyConan(ConanFile):
    name = "dircproxy"
    version = "1.1.0"
    description = "dircproxy is an IRC proxy server (bouncer)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/w8tvi/dircproxy"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix: use system getopt instead of bundled one (OHOS musl has getopt_long)
        for path in ["src/main.c", "crypt/main.c"]:
            fp = os.path.join(self.source_folder, path)
            if os.path.exists(fp):
                with open(fp, "r") as f:
                    content = f.read()
                content = content.replace('#include "getopt/getopt.h"', '#include <getopt.h>')
                with open(fp, "w") as f:
                    f.write(content)
        # Fix: crypt() not available on OHOS — add stub at top of irc_client.c
        irc_client = os.path.join(self.source_folder, "src/irc_client.c")
        if os.path.exists(irc_client):
            with open(irc_client, "r") as f:
                content = f.read()
            if "crypt" in content and "OHOS stub" not in content:
                content = "/* OHOS stub: crypt() not available */\nchar *crypt(const char *key, const char *salt) { return (char *)key; }\n" + content
                with open(irc_client, "w") as f:
                    f.write(content)
        # Fix: ternary assignment and address-of-ternary (GCC extension, clang doesn't support)
        import re
        for path in ["src/irc_server.c", "src/dcc_net.c", "src/net.c", "src/cfgfile.c"]:
            fp = os.path.join(self.source_folder, path)
            if os.path.exists(fp):
                with open(fp, "r") as f:
                    content = f.read()
                # irc_server.c: s = (l ? l->next : p->squelch_modes) = n;
                content = content.replace(
                    "s = (l ? l->next : p->squelch_modes) = n;",
                    "if (l) { l->next = n; } else { p->squelch_modes = n; } s = n;"
                )
                # dcc_net.c: p = (l ? l->next : proxies) = n;
                content = content.replace(
                    "p = (l ? l->next : proxies) = n;",
                    "if (l) { l->next = n; } else { proxies = n; } p = n;"
                )
                # net.c: l = &(buff == SB_IN ? s->in_buff_last : s->out_buff_last);
                content = content.replace(
                    "l = &(buff == SB_IN ? s->in_buff_last : s->out_buff_last);",
                    "if (buff == SB_IN) { l = &s->in_buff_last; } else { l = &s->out_buff_last; }"
                )
                # cfgfile.c: &(class ? class : def)->field → (class ? &class->field : &def->field)
                content = re.sub(
                    r'&\(class \? class : def\)->(\w+)',
                    r'(class ? &class->\1 : &def->\1)',
                    content
                )
                with open(fp, "w") as f:
                    f.write(content)
        # Remove getopt from SUBDIRS and LDADD
        for path in ["Makefile.am", "src/Makefile.am", "crypt/Makefile.am"]:
            fp = os.path.join(self.source_folder, path)
            if os.path.exists(fp):
                with open(fp, "r") as f:
                    content = f.read()
                # Remove getopt and crypt from SUBDIRS (getopt: use system; crypt: OHOS has no crypt())
                content = content.replace("getopt \\\n", "")
                content = content.replace("crypt \\\n", "")
                # Replace LDADD that references getopt library
                content = content.replace(
                    "dircproxy_LDADD = \\\n\t../getopt/libgetopt.a",
                    "dircproxy_LDADD ="
                )
                content = content.replace(
                    "dircproxy_crypt_LDADD = \\\n\t../getopt/libgetopt.a",
                    "dircproxy_crypt_LDADD ="
                )
                with open(fp, "w") as f:
                    f.write(content)
        # GitHub archive doesn't include pre-generated configure; run autoreconf
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            self.run(f"cd {self.source_folder} && autoreconf -fi")
        # E007/E072: patch config.sub for OHOS (AFTER autoreconf)
        for cs_path in ["build-aux/config.sub", "config.sub", "config/config.sub"]:
            config_sub = os.path.join(self.source_folder, cs_path)
            if os.path.exists(config_sub):
                with open(config_sub, "r") as f:
                    content = f.read()
                if "ohos-linux" not in content:
                    content = content.replace(
                        "android-linux)\n\t\tbasic_machine=$field1-unknown\n\t\tbasic_os=linux-android",
                        "android-linux)\n\t\tbasic_machine=$field1-unknown\n\t\tbasic_os=linux-android\n\tohos-linux)\n\t\tbasic_machine=$field1-unknown\n\t\tbasic_os=linux-ohos"
                    )
                if "ohos*" not in content:
                    content = content.replace(
                        "gnu* | android* | bsd*",
                        "ohos* | gnu* | android* | bsd*"
                    )
                if "linux-ohos" not in content:
                    content = content.replace(
                        "linux-musl*- | linux-relibc*",
                        "linux-musl*- | linux-ohos*- | linux-relibc*"
                    )
                with open(config_sub, "w") as f:
                    f.write(content)
                break
        # Also fix config.guess for OHOS (uname -s returns "HarmonyOS")
        for cg_path in ["build-aux/config.guess", "config.guess", "config/config.guess"]:
            config_guess = os.path.join(self.source_folder, cg_path)
            if os.path.exists(config_guess):
                with open(config_guess, "r") as f:
                    content = f.read()
                if "HarmonyOS" not in content:
                    content = content.replace(
                        "esac\n\n# Note: order is significant",
                        "HarmonyOS)\n\t\techo \"$UNAME_MACHINE\"-unknown-linux-ohos\n\t\texit ;;\nesac\n\n# Note: order is significant"
                    )
                with open(config_guess, "w") as f:
                    f.write(content)
                break
        # E011: fix umask 077 -> 022 (AFTER autoreconf)
        configure = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure):
            with open(configure, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure, "w") as f:
                f.write(content)
        autotools = Autotools(self)
        autotools.configure()
        # Workaround: makeinfo not available
        build_dir = self.build_folder
        for doc_file in ["doc/dircproxy.info", "doc/stamp-vti", "doc/version.texi"]:
            fp = os.path.join(build_dir, doc_file)
            if os.path.exists(os.path.dirname(fp)):
                with open(fp, "w") as f:
                    f.write("")
                try:
                    os.utime(fp, (1e11, 1e11))
                except:
                    pass
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
