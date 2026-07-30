#!/usr/bin/env python3
"""Conan recipe for autotrace 0.31.10."""
import os
import shlex
import shutil
import subprocess
import struct

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class AutotraceConan(ConanFile):
    name = "autotrace"
    version = "0.31.10"
    description = "Bitmap to vector graphics converter and library"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/autotrace/autotrace"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if self.options.shared:
            raise ConanInvalidConfiguration("autotrace is packaged as a static library for OHOS")

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("libpng/1.6.58")

    def export_sources(self):
        export_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @property
    def _out_dir(self):
        return os.path.join(self.build_folder, "ohos-direct")

    @property
    def _obj_dir(self):
        return os.path.join(self._out_dir, "obj")

    def _compiler_executables(self):
        return self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}

    def _cc(self):
        return (
            self._compiler_executables().get("c")
            or os.environ.get("CC")
            or shutil.which("clang")
            or shutil.which("cc")
            or "cc"
        )

    def _tool(self, name, fallback):
        compilers = self._compiler_executables()
        cc = compilers.get("c", "")
        bindir = os.path.dirname(cc) if os.path.isabs(cc) else ""
        candidate = os.path.join(bindir, name) if bindir else ""
        return candidate if candidate and os.path.exists(candidate) else fallback

    def _run_checked(self, args, **kwargs):
        command = " ".join(shlex.quote(str(arg)) for arg in args)
        retcode = self.run(command, ignore_errors=True, **kwargs)
        if retcode not in (None, 0):
            raise RuntimeError(f"Command failed with exit code {retcode}: {command}")

    def _elf_has_section(self, path, section_name):
        try:
            with open(path, "rb") as file:
                data = file.read()
        except OSError:
            return True
        if len(data) < 16 or data[:4] != b"\x7fELF":
            return True
        endian = {"\x01": "<", "\x02": ">"}.get(chr(data[5]))
        if not endian:
            return True
        try:
            if data[4] == 1:
                fields = struct.unpack_from(endian + "16sHHIIIIIHHHHHH", data, 0)
                section_header_format = endian + "IIIIIIIIII"
            elif data[4] == 2:
                fields = struct.unpack_from(endian + "16sHHIQQQIHHHHHH", data, 0)
                section_header_format = endian + "IIQQQQIIQQ"
            else:
                return True
            section_offset, section_size = fields[6], fields[11]
            section_count, names_index = fields[12], fields[13]
            header_size = struct.calcsize(section_header_format)
            if section_size < header_size or names_index >= section_count:
                return True

            def section_header(index):
                return struct.unpack_from(
                    section_header_format,
                    data,
                    section_offset + index * section_size,
                )

            names_header = section_header(names_index)
            names_offset, names_size = names_header[4], names_header[5]
            names = data[names_offset:names_offset + names_size]
            for index in range(section_count):
                name_offset = section_header(index)[0]
                if name_offset >= len(names):
                    continue
                end = names.find(b"\x00", name_offset)
                if end == -1:
                    continue
                if names[name_offset:end].decode(errors="replace") == section_name:
                    return True
        except (struct.error, IndexError):
            return True
        return False

    def _pkg_config(self, args):
        pkg_config = os.environ.get("PKG_CONFIG") or shutil.which("pkg-config") or "pkg-config"
        env = os.environ.copy()
        pkg_config_paths = [self.generators_folder]
        if env.get("PKG_CONFIG_PATH"):
            pkg_config_paths.append(env["PKG_CONFIG_PATH"])
        env["PKG_CONFIG_PATH"] = os.pathsep.join(pkg_config_paths)
        try:
            result = subprocess.run(
                [pkg_config, *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                env=env,
            )
        except FileNotFoundError as exc:
            raise ConanInvalidConfiguration("pkg-config is required to build autotrace") from exc
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                f"pkg-config {' '.join(args)} failed: {result.stderr.strip()}"
            )
        return self._without_ohos_loader_link_flags(shlex.split(result.stdout.strip()))

    @staticmethod
    def _without_ohos_loader_link_flags(flags):
        return [
            flag for flag in flags
            if not (flag.startswith("-l:ld-musl-") and flag.endswith(".so.1"))
        ]

    def _dependency_pkg_config_name(self, dependency):
        dependency_info = self.dependencies[dependency]
        return (
            dependency_info.cpp_info.get_property("pkg_config_name")
            or dependency_info.ref.name
        )

    def _write_config_header(self):
        save(
            self,
            os.path.join(self.build_folder, "config.h"),
            """#pragma once
#define PACKAGE "autotrace"
#define PACKAGE_NAME "autotrace"
#define PACKAGE_VERSION "0.31.10"
#define AUTOTRACE_VERSION "0.31.10"
#define AUTOTRACE_WEB "https://github.com/autotrace/autotrace"
#define HAVE_LOCALTIME_R 1
#define HAVE_LIBPNG 1
#define HAVE_STDINT_H 1
#define HAVE_STRING_H 1
#define HAVE_STRINGS_H 1
#define STDC_HEADERS 1
""",
        )

    def _build_type_flags(self):
        return {
            "Debug": ["-O0", "-g"],
            "Release": ["-O2", "-DNDEBUG"],
            "RelWithDebInfo": ["-O2", "-g", "-DNDEBUG"],
            "MinSizeRel": ["-Os", "-DNDEBUG"],
        }.get(str(self.settings.build_type), ["-O2", "-DNDEBUG"])

    def _compile(self, cc, source, cflags):
        rel = source.replace("/", "_").replace("\\", "_")
        obj = os.path.join(self._obj_dir, rel + ".o")
        self._run_checked([cc, *cflags, "-c", os.path.join(self.source_folder, source), "-o", obj])
        return obj

    def _run_upstream_tests(self, cli_path):
        if not can_run(self):
            self.output.warning(
                "Skipping upstream runtime tests because the target binary cannot run "
                "in the current build context"
            )
            return

        test_script = os.path.join(self.source_folder, "tests", "runtests.sh")
        command = (
            f"AUTOTRACE={shlex.quote(cli_path)} "
            f"sh {shlex.quote(test_script)}"
        )
        self.run(command, cwd=self.source_folder)

    def build(self):
        apply_conandata_patches(self)
        os.makedirs(self._out_dir, exist_ok=True)
        os.makedirs(self._obj_dir, exist_ok=True)
        self._write_config_header()

        cc = self._cc()
        ar = self._tool(
            "llvm-ar",
            os.environ.get("AR") or shutil.which("llvm-ar") or shutil.which("ar") or "ar",
        )
        ranlib = self._tool(
            "llvm-ranlib",
            os.environ.get("RANLIB") or shutil.which("llvm-ranlib") or shutil.which("ranlib") or "ranlib",
        )
        glib_pc = self._dependency_pkg_config_name("glib")
        png_pc = self._dependency_pkg_config_name("libpng")
        glib_cflags = self._pkg_config(["--cflags", glib_pc])
        glib_libs = self._pkg_config(["--libs", glib_pc])
        png_cflags = self._pkg_config(["--cflags", png_pc])
        png_libs = self._pkg_config(["--libs", png_pc])

        cflags = [
            *self._build_type_flags(),
            "-DHAVE_CONFIG_H",
            "-DLOCALEDIR=\"share/locale\"",
            "-I" + self.build_folder,
            "-I" + os.path.join(self.source_folder, "src"),
            "-I" + self.source_folder,
        ]
        if self.options.fPIC:
            cflags.append("-fPIC")

        lib_sources = [
            "src/input-gf.c",
            "src/input-bmp.c",
            "src/input-pnm.c",
            "src/input-tga.c",
            "src/input-png.c",
            "src/output-eps.c",
            "src/output-er.c",
            "src/output-fig.c",
            "src/output-sk.c",
            "src/output-svg.c",
            "src/output-ugs.c",
            "src/output-p2e.c",
            "src/output-emf.c",
            "src/output-dxf.c",
            "src/output-epd.c",
            "src/output-pdf.c",
            "src/output-mif.c",
            "src/output-cgm.c",
            "src/output-dr2d.c",
            "src/output-pov.c",
            "src/output-plt.c",
            "src/output-ild.c",
            "src/fit.c",
            "src/bitmap.c",
            "src/spline.c",
            "src/curve.c",
            "src/epsilon-equal.c",
            "src/vector.c",
            "src/color.c",
            "src/datetime.c",
            "src/autotrace.c",
            "src/output.c",
            "src/input.c",
            "src/pxl-outline.c",
            "src/median.c",
            "src/thin-image.c",
            "src/logreport.c",
            "src/filename.c",
            "src/despeckle.c",
            "src/exception.c",
            "src/image-proc.c",
            "src/module.c",
        ]
        objects = [
            self._compile(cc, source, [*cflags, *glib_cflags, *png_cflags])
            for source in lib_sources
        ]
        lib_path = os.path.join(self._out_dir, "libautotrace.a")
        self._run_checked([ar, "rcs", lib_path, *objects])
        self._run_checked([ranlib, lib_path])

        cli_objects = [
            self._compile(cc, "src/main.c", [*cflags, *glib_cflags]),
            self._compile(cc, "src/atou.c", [*cflags, *glib_cflags]),
        ]
        cli_path = os.path.join(self._out_dir, "autotrace")
        self._run_checked(
            [cc, "-o", cli_path, *cli_objects, lib_path, *glib_libs, *png_libs, "-lm"]
        )
        os.chmod(cli_path, 0o755)
        self._run_upstream_tests(cli_path)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include", "autotrace")
        pcdir = os.path.join(libdir, "pkgconfig")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(incdir, exist_ok=True)
        os.makedirs(pcdir, exist_ok=True)

        copy(self, "autotrace", src=self._out_dir, dst=bindir, keep_path=False)
        copy(self, "libautotrace.a", src=self._out_dir, dst=libdir, keep_path=False)
        for header in ("types.h", "autotrace.h", "input.h", "output.h", "spline.h", "exception.h", "color.h"):
            copy(self, header, src=os.path.join(self.source_folder, "src"), dst=incdir, keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYING.LIB", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        glib_pc = self._dependency_pkg_config_name("glib")
        png_pc = self._dependency_pkg_config_name("libpng")
        save(
            self,
            os.path.join(pcdir, "autotrace.pc"),
            f"""prefix=${{pcfiledir}}/../..
exec_prefix=${{prefix}}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Name: autotrace
Description: Bitmap to vector graphics converter and library
Version: 0.31.10
Requires: {glib_pc} {png_pc}
Libs: -L${{libdir}} -lautotrace -lm
Cflags: -I${{includedir}}
""",
        )

        bin_path = os.path.join(bindir, "autotrace")
        if os.path.exists(bin_path):
            os.chmod(bin_path, 0o755)
            self._sign_binary_if_available(bin_path)

    def _find_external_tool(self, env_name, tool_name):
        configured = os.environ.get(env_name)
        if configured:
            return configured if os.path.exists(configured) else ""
        return shutil.which(tool_name) or ""

    def _sign_binary_if_available(self, bin_path):
        if str(self.settings.os) != "OHOS":
            return
        objcopy = self._find_external_tool("LLVM_OBJCOPY", "llvm-objcopy")
        sign_tool = self._find_external_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        if not objcopy or not sign_tool:
            self.output.warning("Skipping OHOS binary signing because signing tools are not configured")
            return

        tmp_signed = bin_path + ".signed"
        if self._elf_has_section(bin_path, ".codesign"):
            self._run_checked([objcopy, "--remove-section", ".codesign", bin_path])
        else:
            self.output.info("Skipping .codesign removal for unsigned autotrace ELF")
        self._run_checked([sign_tool, "sign", "-inFile", bin_path, "-outFile", tmp_signed, "-selfSign", "1"])
        if not os.path.exists(tmp_signed):
            raise RuntimeError(f"Signing did not create output file: {tmp_signed}")
        os.replace(tmp_signed, bin_path)
        os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["autotrace"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("pkg_config_name", "autotrace")
