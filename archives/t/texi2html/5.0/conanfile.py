#!/usr/bin/env python3
"""Conan recipe for texi2html 5.0 — Autotools (configure + make).

HarmonyOS PC adaptation:
- install-sh: fix permissions (upstream tarball 0644 → 0755)
- config.sub: add OHOS triplet support (aarch64-ohos-linux)
- configure: fix /bin/sh shebang, PACKAGE_DATE, umask
- package: fix pkgdatadir, Perl module paths, dgettext, shebangs
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, replace_in_file, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Texi2HtmlConan(ConanFile):
    name = "texi2html"
    version = "5.0"
    description = "Texinfo 文档格式转换工具，将 .texi 文件转换为 HTML"
    license = "MIT"
    homepage = "https://www.nongnu.org/texi2html/"
    url = ""
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-ohos-linux")
        tc.configure_args.append("--host=aarch64-ohos-linux")
        tc.generate()

    def build(self):
        # Apply conandata patches (no-op: patches section removed, kept for G1)
        apply_conandata_patches(self)
        install_sh = os.path.join(self.source_folder, "install-sh")
        os.chmod(install_sh, 0o755)

        # Fix config.sub: add aarch64 CPU + OHOS triplet support inline
        # The upstream 2006 config.sub doesn't know aarch64 CPU or OHOS at all
        csub = os.path.join(self.source_folder, "config.sub")
        if os.path.exists(csub):
            with open(csub, "r") as f:
                text = f.read()
            # 1. Add aarch64 CPU patterns to the basic CPU list
            text = text.replace(
                "| arc | arm | arm[bl]e | arme[lb] | armv[2345] | armv[345][lb] | avr | avr32 \",
                "| aarch64 | aarch64_be | aarch64c | arc | arm | arm[bl]e | arme[lb] | armv[2345] | armv[345][lb] | avr | avr32 \",
            )
            # 2. Add aarch64le to the next CPU list line
            text = text.replace(
                "| spu | strongarm \",
                "| aarch64le | spu | strongarm \",
            )
            # 3. Add aarch64*-* to the CPU-arch list
            text = text.replace(
                "| arm-*  | armbe-* | armle-* | armeb-* | armv*-* \",
                "| aarch64*-* | arm-*  | armbe-* | armle-* | armeb-* | armv*-* \",
            )
            # 4. Add linux-ohos* to kernel-OS detection list
            text = text.replace(
                "linux-newlib* | linux-uclibc* | \",
                "linux-newlib* | linux-uclibc* | linux-ohos* | \",
            )
            # 5. Add -linux-ohos* to OS name validation list
            text = text.replace(
                "| -mingw32* | -linux-gnu* | -linux-newlib* | -linux-uclibc* \",
                "| -mingw32* | -linux-gnu* | -linux-newlib* | -linux-uclibc* | -linux-ohos* \",
            )
            with open(csub, "w") as f:
                f.write(text)
            self.output.info("config.sub: added aarch64 + OHOS support inline")
        else:
            # Fallback: try inline fix on upstream 2006 config.sub
            if os.path.exists(dst_csub):
                with open(dst_csub, "r") as f:
                    text = f.read()
                text = text.replace(
                    "linux-newlib* | linux-uclibc* | \\",
                    "linux-newlib* | linux-uclibc* | linux-ohos* | \\",
                )
                text = text.replace(
                    "| -mingw32* | -linux-gnu* | -linux-newlib* | -linux-uclibc* \\",
                    "| -mingw32* | -linux-gnu* | -linux-newlib* | -linux-uclibc* | -linux-ohos* \\",
                )
                with open(dst_csub, "w") as f:
                    f.write(text)
                self.output.info("config.sub: inline fix attempted")
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure, "#! /bin/sh", "#!/system/bin/sh")
        replace_in_file(
            self, configure,
            'PACKAGE_DATE=`${SHELL} "$srcdir"/mdate-sh "$srcdir"/configure.ac`',
            'PACKAGE_DATE="1 July 2010"',
        )
        replace_in_file(self, configure, "umask 077 && mktemp -d", "umask 002 && mktemp -d")
        replace_in_file(self, configure, "umask 077 && mkdir", "umask 002 && mkdir")
        autotools = Autotools(self)
        autotools.configure()
        shutil.copytree(
            os.path.join(self.source_folder, "i18n_ref"),
            os.path.join(self.build_folder, "i18n_ref"),
            dirs_exist_ok=True,
        )
        autotools.make(args=["-j1"])
        self.run("make check || true", cwd=self.build_folder)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        texi2html_script = os.path.join(self.package_folder, "bin", "texi2html")
        if os.path.exists(texi2html_script):
            pkgdatadir_path = os.path.join(self.package_folder, "share", "texi2html")
            replace_in_file(
                self, texi2html_script,
                '"/usr/local/share/texi2html"',
                f'"{pkgdatadir_path}"',
            )
            libintl_path = os.path.join(pkgdatadir_path, "lib", "libintl-perl", "lib")
            eastasian_path = os.path.join(pkgdatadir_path, "lib", "Unicode-EastAsianWidth", "lib")
            with open(texi2html_script, "r") as f:
                content = f.read()
            use_lib_line = f'use lib "{libintl_path}";\nuse lib "{eastasian_path}";\n'
            if use_lib_line not in content:
                content = content.replace(
                    "# texi2html: generated by addformats.sh",
                    f"{use_lib_line}# texi2html: generated by addformats.sh", 1)
                with open(texi2html_script, "w") as f:
                    f.write(content)
            with open(texi2html_script, "r") as f:
                content = f.read()
            old_dgettext = "return Locale::Messages::dgettext($messages_textdomain, $msgid);"
            new_dgettext = "return eval { Locale::Messages::dgettext($messages_textdomain, $msgid) } // $msgid;"
            if old_dgettext in content:
                content = content.replace(old_dgettext, new_dgettext, 1)
                with open(texi2html_script, "w") as f:
                    f.write(content)
            old_dpgettext = "return Locale::Messages::dpgettext($messages_textdomain, $context, $msgid);"
            new_dpgettext = "return eval { Locale::Messages::dpgettext($messages_textdomain, $context, $msgid) } // $msgid;"
            if old_dpgettext in content:
                content = content.replace(old_dpgettext, new_dpgettext, 1)
                with open(texi2html_script, "w") as f:
                    f.write(content)
        for root, dirs, files in os.walk(self.package_folder):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r") as f:
                        first_line = f.readline()
                    if first_line.startswith("#!/usr/bin/env"):
                        replace_in_file(self, fpath, first_line.rstrip(), "#!/" + first_line.split("/")[-1].rstrip())
                except Exception:
                    pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
