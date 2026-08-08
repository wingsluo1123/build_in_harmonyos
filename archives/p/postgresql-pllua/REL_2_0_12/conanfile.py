#!/usr/bin/env python3
"""Conan recipe — postgresql-pllua REL_2_0_12 (PGXS build system).

PL/Lua is a PostgreSQL extension that provides Lua as a procedural language.
It uses PostgreSQL's PGXS (Extension Build System) which requires pg_config,
server headers, and the PGXS makefile infrastructure.

Since PostgreSQL server dev headers are not available as a conan package,
this recipe downloads the PostgreSQL source, configures it to generate
pg_config and PGXS, then builds PL/Lua against it.
"""
import os
import shutil
import glob
import json

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class PostgresqlPlluaConan(ConanFile):
    name = "postgresql-pllua"
    version = "rel_2_0_12"
    description = "PL/Lua — Lua as a procedural language for PostgreSQL"
    license = "MIT"
    homepage = "https://github.com/pllua/pllua"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpq/18.1")
        self.requires("lua/5.4.8")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        cc_conf = self.conf.get("tools.build:compiler_executables")
        if isinstance(cc_conf, str):
            cc_conf = json.loads(cc_conf)
        if isinstance(cc_conf, dict):
            return cc_conf.get("c", "clang")
        return "clang"

    def build(self):
        apply_conandata_patches(self)

        src_dir = self.source_folder
        cc = self._get_cc()

        # ── 1. Build PostgreSQL pg_config + PGXS + server headers ──
        pg_prefix = os.path.join(self.build_folder, "pg_prefix")
        pg_src_dir = os.path.join(self.build_folder, "pg_src")
        pg_build_dir = os.path.join(self.build_folder, "pg_build")

        # Download PostgreSQL source
        get(self, **self.conan_data["postgresql_source"],
            destination=os.path.join(self.build_folder, "pg_dl"),
            strip_root=False)
        dirs = [d for d in glob.glob(os.path.join(self.build_folder, "pg_dl", "*"))
                if os.path.isdir(d)]
        if dirs:
            shutil.copytree(dirs[0], pg_src_dir, dirs_exist_ok=True)

        # Out-of-tree build
        os.makedirs(pg_build_dir, exist_ok=True)

        # Patch umask 077 in configure script (HarmonyOS filesystem issue:
        # umask 077 creates dirs owned by different uid, causing permission denied)
        configure_script = os.path.join(pg_src_dir, "configure")
        if os.path.exists(configure_script):
            with open(configure_script, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure_script, "w") as f:
                f.write(content)

        self.run(
            f"cd {pg_build_dir} && "
            f"{pg_src_dir}/configure "
            f"--build=aarch64-unknown-linux-musl "
            f"--host=aarch64-unknown-linux-musl "
            f"--prefix={pg_prefix} "
            f"--without-readline --without-zlib --without-icu "
            f"--without-libxml --without-libxslt --without-ldap "
            f"--without-gssapi --without-pam --without-systemd "
            f"--without-lz4 --without-zstd --without-openssl",
            env="conanbuild")

        # Also patch config.status if generated (double safety)
        config_status = os.path.join(pg_build_dir, "config.status")
        if os.path.exists(config_status):
            with open(config_status, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(config_status, "w") as f:
                f.write(content)

        self.run(f"cd {pg_build_dir} && ./config.status", env="conanbuild")

        # Build pg_config and needed infrastructure
        self.run(f"cd {pg_build_dir} && make -C src/bin/pg_config -j1", env="conanbuild")
        self.run(f"cd {pg_build_dir} && make -C src/include install", env="conanbuild")
        self.run(f"cd {pg_build_dir} && make -C src/makefiles install", env="conanbuild")
        self.run(f"cd {pg_build_dir} && make -C src/bin/pg_config install", env="conanbuild")
        self.run(f"cd {pg_build_dir} && make -C src/port install", env="conanbuild")
        self.run(f"cd {pg_build_dir} && make -C src/common install", env="conanbuild")

        # Copy additional PGXS files
        pgxs_src = os.path.join(pg_src_dir, "src")
        pgxs_dest = os.path.join(pg_prefix, "lib", "pgxs", "src")
        os.makedirs(os.path.join(pgxs_dest, "makefiles"), exist_ok=True)
        copy(self, "Makefile.global", os.path.join(pg_build_dir, "src"), pgxs_dest)
        copy(self, "Makefile.shlib", pgxs_src, pgxs_dest)
        copy(self, "Makefile.port", os.path.join(pg_build_dir, "src"), pgxs_dest)
        # Manually copy pgxs.mk if make install didn't (common in conan env)
        copy(self, "pgxs.mk", os.path.join(pgxs_src, "makefiles"),
             os.path.join(pgxs_dest, "makefiles"))
        copy(self, "*", os.path.join(pg_src_dir, "config"),
             os.path.join(pg_prefix, "lib", "pgxs", "config"))
        os.makedirs(os.path.join(pg_prefix, "share", "postgresql"), exist_ok=True)
        copy(self, "errcodes.txt",
             os.path.join(pg_src_dir, "src", "backend", "utils"),
             os.path.join(pg_prefix, "share", "postgresql"))

        # Fix Makefile.global paths to point to pgxs install
        makefile_global = os.path.join(pgxs_dest, "Makefile.global")
        if os.path.exists(makefile_global):
            with open(makefile_global, "r") as f:
                content = f.read()
            content = content.replace(
                f"abs_top_builddir = {os.path.abspath(pg_build_dir)}",
                f"abs_top_builddir = {pgxs_dest}")
            content = content.replace(
                f"abs_top_srcdir = {os.path.abspath(pg_src_dir)}",
                f"abs_top_srcdir = {pgxs_dest}")
            with open(makefile_global, "w") as f:
                f.write(content)

        # ── 2. Build Lua interpreter (for codegen during PL/Lua build) ──
        lua_src_dir = os.path.join(self.build_folder, "lua_src")
        get(self, **self.conan_data["lua_source"],
            destination=os.path.join(self.build_folder, "lua_dl"),
            strip_root=False)
        dirs = [d for d in glob.glob(os.path.join(self.build_folder, "lua_dl", "*"))
                if os.path.isdir(d)]
        if dirs:
            shutil.copytree(dirs[0], lua_src_dir, dirs_exist_ok=True)

        # Build liblua.a, then lua and luac
        self.run(
            f"cd {lua_src_dir} && "
            f"make liblua.a MYCFLAGS='-fPIC -O2' CC={cc} 'AR=llvm-ar rcus' RANLIB=true -j1",
            env="conanbuild")
        # Compile lua.c separately (make liblua.a doesn't include lua.o)
        self.run(
            f"cd {lua_src_dir} && "
            f"{cc} -Wall -O2 -fPIC -fno-stack-protector -fno-common -c -o lua.o lua.c",
            env="conanbuild")
        self.run(
            f"cd {lua_src_dir} && "
            f"{cc} -o lua lua.o liblua.a -lm -ldl",
            env="conanbuild")

        # Build luac: if luac.c exists (official distribution), compile it.
        # If not (GitHub source), create a wrapper script using lua.
        luac_c = os.path.join(lua_src_dir, "luac.c")
        if os.path.exists(luac_c):
            self.run(
                f"cd {lua_src_dir} && "
                f"{cc} -Wall -O2 -fPIC -fno-stack-protector -fno-common -c -o luac.o luac.c && "
                f"{cc} -o luac luac.o liblua.a -lm -ldl",
                env="conanbuild")
        else:
            # Create luac wrapper script (GitHub source lacks luac.c)
            luac_script = os.path.join(lua_src_dir, "luac")
            with open(luac_script, "w") as f:
                f.write("""#!/bin/sh
# luac replacement using lua - compiles .lua to bytecode
OUTPUT="luac.out"
while [ $# -gt 0 ]; do
    case "$1" in
        -o) shift; OUTPUT="$1" ;;
        -s|-l) ;;
        --) shift; break ;;
        -*) ;;
        *) break ;;
    esac
    shift
done
INPUT="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/lua" -e "
local f = assert(loadfile('$INPUT'))
local chunk = string.dump(f)
local out = assert(io.open('$OUTPUT', 'wb'))
out:write(chunk)
out:close()
"
""")
            os.chmod(luac_script, 0o755)

        copy(self, "lua", lua_src_dir, os.path.join(pg_prefix, "bin"))
        copy(self, "luac", lua_src_dir, os.path.join(pg_prefix, "bin"))
        os.chmod(os.path.join(pg_prefix, "bin", "lua"), 0o755)
        os.chmod(os.path.join(pg_prefix, "bin", "luac"), 0o755)

        # ── 3. Build PL/Lua using PGXS ──
        pg_config = os.path.join(pg_prefix, "bin", "pg_config")
        pg_bin = os.path.join(pg_prefix, "bin")

        # Get Lua headers and library from conan dependency
        lua_pkg = self.dependencies["lua"]
        lua_incdir = lua_pkg.cpp_info.includedirs[0]
        lua_libdir = lua_pkg.cpp_info.libdirs[0]

        bin_ld = "ld.lld -m aarch64elf -r -b binary"

        # Compute PGXS path directly to avoid $(shell) issues in conan env
        pgxs_path = os.path.join(pg_prefix, "lib", "pgxs", "src", "makefiles", "pgxs.mk")

        # Verify PGXS files exist before building
        mg_path = os.path.join(pg_prefix, "lib", "pgxs", "src", "Makefile.global")
        if not os.path.exists(pgxs_path):
            # Try manual copy from source
            src_pgxs = os.path.join(pg_src_dir, "src", "makefiles", "pgxs.mk")
            if os.path.exists(src_pgxs):
                copy(self, "pgxs.mk", os.path.dirname(src_pgxs),
                     os.path.dirname(pgxs_path))
        if not os.path.exists(mg_path):
            # Try manual copy from build dir
            src_mg = os.path.join(pg_build_dir, "src", "Makefile.global")
            if os.path.exists(src_mg):
                copy(self, "Makefile.global", os.path.join(pg_build_dir, "src"), os.path.dirname(mg_path))

        # Get PostgreSQL CFLAGS and add warning suppression for clang 15
        # (clang 15 treats -Wint-conversion as error by default)
        import subprocess
        pg_cflags = subprocess.check_output(
            f"PATH={pg_bin}:$PATH {pg_config} --cflags",
            shell=True, text=True, env={**os.environ, "PATH": f"{pg_bin}:{os.environ.get('PATH', '')}"}).strip()
        extra_flags = "-Wno-error=int-conversion -Wno-error=incompatible-pointer-types -Wno-error=implicit-function-declaration"
        full_cflags = f"{pg_cflags} {extra_flags}"

        self.run(
            f"PATH={pg_bin}:$PATH make "
            f"PG_CONFIG={pg_config} "
            f"PGXS={pgxs_path} "
            f"LUA=lua LUAC=luac "
            f"LUA_INCDIR={lua_incdir} "
            f"LUALIB='-L{lua_libdir} -llua' "
            f"OBJCOPY=llvm-objcopy "
            f"'BIN_LD={bin_ld}' "
            f"CFLAGS='{full_cflags}' "
            f"VPATH= "
            f"-C {src_dir} "
            f"-j1",
            env="conanbuild")

    def package(self):
        pg_config = os.path.join(self.build_folder, "pg_prefix", "bin", "pg_config")
        pg_prefix = os.path.join(self.build_folder, "pg_prefix")
        pg_bin = os.path.join(pg_prefix, "bin")
        destdir = os.path.join(self.build_folder, "staging")
        src_dir = self.source_folder

        lua_pkg = self.dependencies["lua"]
        lua_incdir = lua_pkg.cpp_info.includedirs[0]
        lua_libdir = lua_pkg.cpp_info.libdirs[0]
        bin_ld = "ld.lld -m aarch64elf -r -b binary"
        pgxs_path = os.path.join(self.build_folder, "pg_prefix", "lib", "pgxs", "src", "makefiles", "pgxs.mk")

        # Reconstruct CFLAGS for make install (in case PGXS rebuilds)
        import subprocess
        pg_cflags = subprocess.check_output(
            f"PATH={pg_bin}:$PATH {pg_config} --cflags",
            shell=True, text=True, env={**os.environ, "PATH": f"{pg_bin}:{os.environ.get('PATH', '')}"}).strip()
        extra_flags = "-Wno-error=int-conversion -Wno-error=incompatible-pointer-types -Wno-error=implicit-function-declaration"
        full_cflags = f"{pg_cflags} {extra_flags}"

        self.run(
            f"PATH={pg_bin}:$PATH make install "
            f"PG_CONFIG={pg_config} "
            f"PGXS={pgxs_path} "
            f"LUA=lua LUAC=luac "
            f"LUA_INCDIR={lua_incdir} "
            f"LUALIB='-L{lua_libdir} -llua' "
            f"OBJCOPY=llvm-objcopy "
            f"'BIN_LD={bin_ld}' "
            f"CFLAGS='{full_cflags}' "
            f"VPATH= "
            f"-C {src_dir} "
            f"DESTDIR={destdir}",
            env="conanbuild")

        # Copy installed files to package folder
        # NOTE: pg_prefix is absolute, so os.path.join(destdir, pg_prefix) would
        # discard destdir. Must construct path manually: DESTDIR + prefix + subdir.
        staging_root = destdir + pg_prefix
        staging_lib = os.path.join(staging_root, "lib")
        staging_share = os.path.join(staging_root, "share")
        staging_include = os.path.join(staging_root, "include")

        for src, dst in [
            (staging_lib, os.path.join(self.package_folder, "lib")),
            (staging_share, os.path.join(self.package_folder, "share")),
            (staging_include, os.path.join(self.package_folder, "include")),
        ]:
            if os.path.isdir(src):
                copy(self, "*", src, dst)

        # PGXS installs to lib/postgresql/, flatten to lib/
        pgsql_lib = os.path.join(self.package_folder, "lib", "postgresql")
        if os.path.isdir(pgsql_lib):
            for f in os.listdir(pgsql_lib):
                src_f = os.path.join(pgsql_lib, f)
                dst_f = os.path.join(self.package_folder, "lib", f)
                if os.path.isfile(src_f):
                    copy(self, f, pgsql_lib, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["pllua"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "postgresql-pllua")
        self.cpp_info.set_property("cmake_target_name", "postgresql-pllua::postgresql-pllua")
