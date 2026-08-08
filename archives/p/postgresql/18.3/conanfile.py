from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import re


class PostgresqlConan(ConanFile):
    name = "postgresql"
    version = "18.3"
    description = "PostgreSQL is a powerful, open source object-relational database system"
    license = "PostgreSQL"
    homepage = "https://www.postgresql.org/"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-icu",
            "--without-readline",
            "--without-zlib",
            "--without-openssl",
        ])
        # R15: AutotoolsToolchain handles cross-compilation flags automatically
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E002: OHOS /tmp is read-only, use build folder for temp files
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o777)
        os.environ["TMPDIR"] = tmpdir
        # Fix umask for hmdfs filesystem (E046: hmdfs creates dirs with 077 umask)
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            replace_in_file(self, configure_path, "umask 077", "umask 022")
        # R15: Patch config.guess/config.sub to recognize HarmonyOS
        if self.settings.os == "OHOS":
            self._patch_config_for_ohos()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub to recognize HarmonyOS/OHOS (R15)."""
        cg_path = os.path.join(self.source_folder, "config.guess")
        cs_path = os.path.join(self.source_folder, "config.sub")

        if not os.path.exists(cg_path) or not os.path.exists(cs_path):
            self.output.info("config.guess/config.sub not found, skipping OHOS patch")
            return

        self._manual_patch_config_guess(cg_path)
        self._manual_patch_config_sub(cs_path)

    def _manual_patch_config_guess(self, cg_path):
        """Manually patch config.guess for HarmonyOS detection."""
        with open(cg_path, "r") as f:
            content = f.read()

        changed = False

        # 1. Add __OHOS__ LIBC detection after __ANDROID__
        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos"
            if old in content:
                content = content.replace(old, new, 1)
                changed = True
                self.output.info("[ok] Added __OHOS__ LIBC detection to config.guess")

        # 2. Add HarmonyOS case block before NetBSD
        if "HarmonyOS" not in content:
            block = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                '\t    i?86)          MACHINE=i686 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                '\t;;\n\n'
                '    *:NetBSD:*:*)'
            )
            if "    *:NetBSD:*:*)" in content:
                content = content.replace("    *:NetBSD:*:*)", block, 1)
                changed = True
                self.output.info("[ok] Added HarmonyOS system identification to config.guess")

        if changed:
            with open(cg_path, "w") as f:
                f.write(content)

    def _manual_patch_config_sub(self, cs_path):
        """Manually patch config.sub for ohos-linux support."""
        with open(cs_path, "r") as f:
            content = f.read()

        changed = False

        # 1. Add ohos-linux triplet after android-linux
        if "ohos-linux" not in content:
            pattern = r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)'
            replacement = r'\1\tohos-linux)\n\tbasic_machine=$field1-unknown\n\tbasic_os=linux-ohos\n\t;;\n'
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changed = True
                self.output.info("[ok] Added ohos-linux triplet to config.sub")

        # 2. Add ohos* to OS type list
        if "ohos*" not in content:
            content = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            changed = True
            self.output.info("[ok] Added ohos* to OS list in config.sub")

        # 3. Add linux-ohos to kernel-OS validation list
        if "linux-ohos" not in content:
            content = content.replace("linux-android", "linux-android\n\t\t\t| linux-ohos", 1)
            changed = True
            self.output.info("[ok] Added linux-ohos to kernel-OS validation in config.sub")

        if changed:
            with open(cs_path, "w") as f:
                f.write(content)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["pq", "pgcommon", "pgport"]
        self.cpp_info.includedirs = [
            "include",
            "include/postgresql",
            "include/postgresql/server",
            "include/postgresql/internal",
        ]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib", "lib/postgresql"]
