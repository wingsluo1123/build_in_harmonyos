#!/usr/bin/env python3
"""Conan recipe for php-pecl-memcache 8.2 — PHP PECL memcache extension.

Build system: phpize (PHP extension build system, not standard autotools)
Output: memcache.so (PHP extension module)

Dependencies:
  - zlib/1.3.1 (Conan, for compression support)
  - PHP development tools (phpize, php-config) — must be pre-installed on the
    build host and available in PATH via the Conan profile [buildenv] section.

The PHP runtime is not available as a Conan package. The CI worker must have
PHP development tools (phpize, php-config) pre-installed and the profile's
[buildenv] PATH must include the PHP bin directory.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PhpPeclMemcacheConan(ConanFile):
    name = "php-pecl-memcache"
    version = "8.2"
    description = "PECL memcache extension - PHP extension for memcached (memcache protocol)"
    license = "MIT"
    homepage = "https://pecl.php.net/package/memcache"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        # PECL tarball has memcache-8.2/ directory and package.xml at root.
        # strip_root fails when there are files outside the root dir.
        get(self, **self.conan_data["sources"], strip_root=False)

    @property
    def _src_dir(self):
        """The actual source directory inside the extracted tarball."""
        return os.path.join(self.source_folder, "memcache-8.2")

    @property
    def _php_prefix(self):
        """Determine PHP installation prefix from php-config location."""
        php_config = shutil.which("php-config")
        if php_config:
            return os.path.dirname(os.path.dirname(php_config))
        raise ConanException(
            "php-config not found in PATH. PHP development tools must be "
            "pre-installed and available via the Conan profile [buildenv]."
        )

    def _fix_config_status(self):
        """Fix config.status tmpdir for HMDFS compatibility.

        On HarmonyOS, config.status uses ./confXXXXXX pattern which fails
        on HMDFS due to Permission denied. Patch to use a writable tmpdir.
        """
        config_status = os.path.join(self._src_dir, "config.status")
        if not os.path.exists(config_status):
            return

        tmpdir = os.environ.get("TMPDIR", "/tmp")
        fix_dir = os.path.join(tmpdir, "memcache-config-tmp")
        os.makedirs(fix_dir, exist_ok=True)

        with open(config_status, "r") as f:
            content = f.read()

        # Replace the mktemp and fallback patterns with a fixed directory
        content = re.sub(
            r'tmp=`\(umask 077 && mktemp -d "\./confXXXXXX"\) 2>/dev/null`',
            f'tmp={fix_dir}',
            content
        )
        content = re.sub(
            r'tmp=\./conf\$\$-\$RANDOM',
            f'tmp={fix_dir}',
            content
        )
        # Ensure mkdir uses -p flag
        content = content.replace(
            f'(umask 077 && mkdir "$tmp")',
            f'(umask 077 && mkdir -p "$tmp")'
        )

        with open(config_status, "w") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)

        src = self._src_dir

        # Step 1: Run phpize to generate configure script
        self.run(f"cd {src} && phpize", env="conanbuild")

        # Step 2: Run configure with PHP and zlib paths
        # Note: configure generates config.status and then runs it.
        # On HarmonyOS/HMDFS, config.status fails because it uses
        # ./confXXXXXX pattern for temp files. We handle this by:
        # 1. Running configure (which creates config.status but fails)
        # 2. Fixing config.status to use a writable tmpdir
        # 3. Re-running config.status to generate remaining files
        php_config = shutil.which("php-config")
        if not php_config:
            raise ConanException("php-config not found in PATH")

        # Get zlib path from Conan dependency
        zlib_info = self.dependencies["zlib"]
        zlib_prefix = zlib_info.package_folder or self._php_prefix

        # Run configure — expected to fail at config.status step on HMDFS
        try:
            self.run(
                f'cd {src} && ./configure '
                f'--with-php-config={php_config} '
                f'--with-zlib-dir={zlib_prefix}',
                env="conanbuild"
            )
        except ConanException:
            # Expected: config.status tmpdir fails on HMDFS
            pass

        # Step 3: Fix config.status tmpdir for HMDFS and re-run
        self._fix_config_status()

        config_status = os.path.join(src, "config.status")
        if os.path.exists(config_status):
            shell = shutil.which("bash")
            if shell:
                self.run(f'cd {src} && {shell} {config_status}', env="conanbuild")

        # Step 4: Build the extension
        self.run(f"cd {src} && make -j1", env="conanbuild")

    def package(self):
        # Copy the built memcache.so to the package
        modules_dir = os.path.join(self._src_dir, "modules")
        copy(self, "memcache.so", modules_dir,
             os.path.join(self.package_folder, "lib", "php", "extensions"))

    def package_info(self):
        # This is a PHP extension module (.so), loaded by PHP at runtime
        self.cpp_info.libs = ["memcache"]
        self.cpp_info.libdirs = ["lib/php/extensions"]
