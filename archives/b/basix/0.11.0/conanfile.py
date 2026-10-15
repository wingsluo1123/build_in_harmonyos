"""Basix C++20 and CPython3.12 bindings with a single declared BLAS provider."""
import json
import hashlib
import os
import shlex
import shutil
import subprocess
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches, get


class BasixConan(ConanFile):
    name = "basix"
    version = "0.11.0"
    description = "Finite-element basis, tabulation and transformation library"
    license = "MIT"
    homepage = "https://github.com/FEniCS/basix"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "test-runtime-lock.json", "res/Basix-conan-extra.cmake"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("This adaptation targets native Linux/OHOS ELF builds")
        # Upstream's public target requires C++20. Preserve the generic worker
        # profile while declaring the real per-target requirement to consumers.

    def requirements(self):
        self.requires("openblas/0.3.34", transitive_headers=True, transitive_libs=True)
        self.requires("nanobind/2.13.0", headers=True, libs=False, run=False)
        self.requires("robin-map/1.4.1", headers=True, libs=False, run=False)

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"][self.version]
        get(self, url=source["url"], sha256=source["sha256"], strip_root=True)
        apply_conandata_patches(self)

    def _python(self):
        if hasattr(self, "_native_python"):
            return self._native_python
        return str(self.conf.get("user.basix:python", default=sys.executable))

    def _prepare_native_python(self, python):
        """Run the selected actual CPython library through an owned native ELF.

        HNP application launchers and ordinary signed native processes can have
        different dynamic-loading contexts. This preserves CPython's real CLI,
        library and standard library; it does not replace Python extension tests.
        """
        directory = Path(self.build_folder) / "original-cpython-launcher"
        directory.mkdir(mode=0o700)
        source = directory / "main.c"
        executable = directory / "python3"
        # FindPython treats a library ending in .so.1.0 as a static embed
        # artifact and appends sysconfig's private link dependencies. Give its
        # development target an ordinary .so name containing the exact loaded
        # runtime bytes; SONAME and runtime provider are unchanged.
        link_library = directory / "libpython3.12.so"
        shutil.copyfile(python["library"], link_library)
        self._python_link_library = str(link_library)
        home = json.dumps(python["prefix"], ensure_ascii=True)
        source.write_text(
            "#define _GNU_SOURCE\n#include <Python.h>\n"
            "#include <dlfcn.h>\n#include <stdlib.h>\n"
            "int main(int argc, char **argv) {\n"
            "  Dl_info info;\n"
            "  if (!dladdr((void *)Py_InitializeFromConfig, &info)\n"
            "      || !info.dli_fname\n"
            "      || setenv(\"BASIX_CPYTHON_LOADED_LIBRARY\", info.dli_fname, 1)) return 125;\n"
            "  PyConfig config; PyStatus status;\n"
            "  PyConfig_InitPythonConfig(&config);\n"
            "  status = PyConfig_SetBytesString(&config, &config.home, "
            + home + ");\n"
            "  if (PyStatus_Exception(status)) goto error;\n"
            "  status = PyConfig_SetBytesArgv(&config, argc, argv);\n"
            "  if (PyStatus_Exception(status)) goto error;\n"
            "  status = Py_InitializeFromConfig(&config);\n"
            "  if (PyStatus_Exception(status)) goto error;\n"
            "  PyConfig_Clear(&config);\n"
            "  return Py_RunMain();\n"
            "error:\n"
            "  PyConfig_Clear(&config);\n"
            "  Py_ExitStatusException(status);\n"
            "  return 1;\n"
            "}\n", encoding="utf8")
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        compiler = compilers.get("c") or os.environ.get("CC") or shutil.which("clang")
        if not compiler:
            raise ConanInvalidConfiguration("Actual native C compiler required for CPython launcher")
        command = [compiler, "-I" + python["include"], str(source),
                   python["library"], "-Wl,-rpath," + str(Path(python["library"]).parent),
                   "-rdynamic", "-o", str(executable)]
        self.run(shlex.join(command))
        self._sign_elf_tree(str(directory))
        probe = (
            "import hashlib,json,os,sys;from pathlib import Path;"
            "l=Path(os.environ['BASIX_CPYTHON_LOADED_LIBRARY']);"
            "print(json.dumps({'version':list(sys.version_info[:3]),"
            "'prefix':str(Path(sys.base_prefix).resolve()),"
            "'loaded_library':str(l),'library_sha256':hashlib.sha256(l.read_bytes()).hexdigest(),"
            "'maps':Path('/proc/self/maps').read_text()}))"
        )
        result = subprocess.run([str(executable), "-B", "-c", probe],
                                capture_output=True, text=True, timeout=20)
        if result.returncode:
            raise ConanInvalidConfiguration("Actual embedded CPython startup failed, rc="
                                            + str(result.returncode) + ": "
                                            + result.stderr[-2000:])
        actual = json.loads(result.stdout)
        if (actual["version"] != python["version"]
                or actual["prefix"] != python["prefix"]
                or actual["library_sha256"] != hashlib.sha256(
                    Path(python["library"]).read_bytes()).hexdigest()):
            raise ConanInvalidConfiguration("Embedded CPython does not match selected runtime")
        self.output.info("ACTUAL_NATIVE_CPYTHON=" + json.dumps({
            "executable": str(executable), "version": actual["version"],
            "prefix": actual["prefix"], "library": python["library"]}))
        self._native_python = str(executable)

    def _private_runtime(self):
        return os.path.join(self.build_folder, "original-python-runtime")

    def _environment(self):
        env = Environment()
        env.prepend_path("PYTHONPATH", self._private_runtime())
        env.prepend_path("PYTHONPATH", self.dependencies["nanobind"].package_folder)
        for directory in ("scipy.libs", "matplotlib.libs", "pillow.libs", "numba.libs"):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(self._private_runtime(), directory))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "cpp"))
        # The wheel's distinct same-SONAME BLAS is deliberately not materialized.
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.dependencies["openblas"].package_folder, "lib"))
        env.define("OPENBLAS_NUM_THREADS", "1")
        env.define("OMP_NUM_THREADS", "1")
        env.define("PYTHONDONTWRITEBYTECODE", "1")
        env.define("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
        env.define("MPLBACKEND", "Agg")
        # GNU make's FIFO must use the same owned POSIX root as the build.
        # A worker-wide TMPDIR may be a service-projected filesystem.
        temporary = os.path.join(self.build_folder, "original-build-tmp")
        os.makedirs(temporary, mode=0o700, exist_ok=True)
        env.define("TMPDIR", temporary)
        return env

    def generate(self):
        if self.settings.os == "OHOS":
            for value in (os.environ.get("TMPDIR"), "/data/storage/el2/base/cache"):
                if not value:
                    continue
                parent = Path(value)
                if (parent.is_absolute() and parent.is_dir()
                        and parent.resolve() == parent and not parent.is_symlink()
                        and parent.stat().st_uid == os.getuid()
                        and os.access(parent, os.W_OK | os.X_OK)):
                    self._native_build_manager = tempfile.TemporaryDirectory(
                        prefix="conan-basix-build-", dir=str(parent))
                    root = Path(self._native_build_manager.name)
                    break
            else:
                raise ConanInvalidConfiguration("Actual owned POSIX build parent required")
            if (root.resolve() != root or root.is_symlink()
                    or root.stat().st_uid != os.getuid()
                    or stat.S_IMODE(root.stat().st_mode) != 0o700):
                raise ConanInvalidConfiguration("Unsafe private native Basix build root")
            build = root / "build"
            generators = root / "generators"
            build.mkdir(mode=0o700)
            generators.mkdir(mode=0o700)
            self.folders.build = str(build)
            self.folders.generators = str(generators)
            self.output.info("ACTUAL_PRIVATE_BASIX_BUILD=" + str(build))
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["INSTALL_RUNTIME_DEPENDENCIES"] = False
        tc.variables["Python_EXECUTABLE"] = self._python()
        # A relocated interpreter can retain its original build-time LIBDIR.
        # Bind development artifacts from that actual interpreter's installed
        # prefix instead of allowing a second FindPython call to mix roots.
        query = (
            "import ctypes,json,sys,sysconfig;from pathlib import Path;"
            "p=Path(sys.base_prefix);i=Path(sysconfig.get_path('include'));"
            "I=type('I',(ctypes.Structure,),{'_fields_':[('fname',ctypes.c_char_p),"
            "('base',ctypes.c_void_p),('sname',ctypes.c_char_p),('saddr',ctypes.c_void_p)]});"
            "d=ctypes.CDLL(None).dladdr;d.argtypes=[ctypes.c_void_p,ctypes.POINTER(I)];"
            "d.restype=ctypes.c_int;a=I();"
            "assert d(ctypes.cast(ctypes.pythonapi.Py_InitializeFromConfig,ctypes.c_void_p),ctypes.byref(a)) and a.fname;"
            "l=Path(a.fname.decode()).resolve();"
            "assert l.is_file() and l.name.startswith('libpython3.12.so') and l.is_relative_to(p.resolve());"
            "assert (i/'Python.h').is_file() and (i/'pyconfig.h').is_file();"
            "print(json.dumps({'version':list(sys.version_info[:3]),"
            "'prefix':str(p.resolve()),'include':str(i.resolve()),'library':str(l)}))"
        )
        result = subprocess.run([self._python(), "-c", query],
                                capture_output=True, text=True, timeout=20)
        if result.returncode:
            raise ConanInvalidConfiguration(
                "Actual selected Python development artifacts unavailable: "
                + result.stderr[-2000:])
        python = json.loads(result.stdout)
        if python["version"][:2] != [3, 12]:
            raise ConanInvalidConfiguration("Matching actual CPython3.12 development required")
        self.output.info("ACTUAL_SELECTED_PYTHON_DEVELOPMENT=" + json.dumps(python))
        if self.settings.os == "OHOS":
            self._prepare_native_python(python)
            tc.variables["Python_EXECUTABLE"] = self._python()
        tc.variables["Python_ROOT_DIR"] = python["prefix"]
        tc.variables["Python_INCLUDE_DIR"] = python["include"]
        tc.variables["Python_LIBRARY"] = getattr(self, "_python_link_library", python["library"])
        tc.variables["BLA_VENDOR"] = "OpenBLAS"
        tc.variables["CMAKE_LIBRARY_PATH"] = os.path.join(self.dependencies["openblas"].package_folder, "lib")
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.variables["CMAKE_INSTALL_RPATH"] = ";".join((os.path.join(self.build_folder, "cpp"), os.path.join(self.dependencies["openblas"].package_folder, "lib")))
        tc.generate()
        VirtualRunEnv(self).generate()

    def _prepare_original_runtime(self):
        python = self._python()
        self.run(shlex.join([python, "-c", "import sys;assert sys.version_info[:2]==(3,12), 'Frozen original test runtime requires CPython3.12'"]))
        with open(os.path.join(self.source_folder, "test-runtime-lock.json"), encoding="utf8") as f:
            lock = json.load(f)
        assert lock["schema"] == "basix-cp312-original-runtime-lock-v1"
        runtime = self._private_runtime()
        os.makedirs(runtime, exist_ok=False)
        wheels = os.path.join(self.build_folder, "hash-bound-test-wheels")
        os.makedirs(wheels, exist_ok=False)
        for record in lock["wheels"]:
            path = os.path.join(wheels, record["filename"])
            download(self, record["url"].split("#", 1)[0], path, sha256=record["sha256"])
            with zipfile.ZipFile(path) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    parts = member.filename.replace("\\", "/").split("/")
                    assert not member.filename.startswith("/") and ".." not in parts
                    assert ((member.external_attr >> 16) & 0o170000) != 0o120000, "Wheel symlink must not escape the private runtime"
                    if record["package"] == "numpy" and member.filename.startswith("numpy.libs/libopenblas"):
                        continue
                    target = os.path.join(runtime, *parts)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    data = archive.read(member)
                    if os.path.exists(target):
                        with open(target, "rb") as f:
                            assert f.read() == data, "Distinct runtime inputs must not overwrite each other"
                    else:
                        with open(target, "xb") as f:
                            f.write(data)
        self._sign_elf_tree(runtime)

    def _sign_elf_tree(self, root):
        if self.settings.os != "OHOS":
            return
        signer = shutil.which("binary-sign-tool")
        objcopy = shutil.which("llvm-objcopy")
        if not signer or not objcopy:
            raise ConanInvalidConfiguration("Native signing tools are required for original extension execution")
        for directory, _, names in os.walk(root):
            for name in names:
                path = os.path.join(directory, name)
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                with open(path, "rb") as f:
                    header = f.read(20)
                # Signing ET_REL objects changes make dependency timestamps
                # and can relink an already signed extension before stubgen.
                # Only native executable/shared ELF files can be loaded.
                elf = (len(header) == 20 and header[:4] == b"\x7fELF"
                       and header[5] == 1
                       and int.from_bytes(header[16:18], "little") in (2, 3))
                if elf:
                    # Never ask the signer to overwrite its own input inode.
                    # Verify the staged signature before publishing final bytes.
                    with tempfile.TemporaryDirectory(
                            prefix=".basix-sign-", dir=directory) as temporary:
                        unsigned = os.path.join(temporary, "input.elf")
                        signed = os.path.join(temporary, "signed.elf")
                        shutil.copyfile(path, unsigned)
                        self.run(shlex.join([
                            objcopy, "--remove-section", ".codesign", unsigned]))
                        self.run(shlex.join([
                            signer, "sign", "-inFile", unsigned,
                            "-outFile", signed, "-selfSign", "1"]))
                        verified = subprocess.run(
                            [signer, "display-sign", "-inFile", signed],
                            capture_output=True, text=True, timeout=60)
                        self.output.info(verified.stdout)
                        if (verified.returncode or
                                "code signature is self-sign" not in verified.stdout):
                            raise ConanInvalidConfiguration(
                                "Actual staged ELF self-signature verification failed: "
                                + verified.stderr[-2000:])
                        os.chmod(signed, 0o755)
                        os.replace(signed, path)

    def build(self):
        self._prepare_original_runtime()
        with self._environment().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            if self.settings.os == "OHOS":
                # Upstream stubgen imports the extension during the full build.
                # Sign its real shared dependencies before linking the module,
                # then sign that module before the original stub target runs.
                cmake.build(target="basix")
                self._sign_elf_tree(os.path.join(self.build_folder, "cpp"))
                cmake.build(target="_basixcpp")
                self._sign_elf_tree(os.path.join(self.build_folder, "python"))
            cmake.build()
            self._sign_elf_tree(self.build_folder)
            prefix = os.path.join(self.build_folder, "original-basix-test-prefix")
            os.makedirs(prefix, exist_ok=False)
            copy(self, "*.py", src=os.path.join(self.source_folder, "python", "basix"), dst=os.path.join(prefix, "basix"))
            copy(self, "_basixcpp*.so", src=os.path.join(self.build_folder, "python"), dst=os.path.join(prefix, "basix"))
            self._official_metadata(prefix)
            self._sign_elf_tree(prefix)
            # Original framework and full denominator. Source-confirmed skip/xfail
            # are preserved in JUnit, never converted to PASS by the recipe.
            env = self._environment()
            env.prepend_path("PYTHONPATH", prefix)
            with env.vars(self).apply():
                command = [self._python(), "-m", "pytest", "--durations", "20",
                           "--junitxml=" + os.path.join(self.build_folder, "original-upstream.xml"),
                           os.path.join(self.source_folder, "test")]
                self.run(shlex.join(command))

    def _official_metadata(self, destination):
        code = ("import os;os.chdir(" + repr(self.source_folder) + ");"
                "from scikit_build_core.build import prepare_metadata_for_build_wheel;"
                "n=prepare_metadata_for_build_wheel(" + repr(destination) + ");"
                "assert n.endswith('.dist-info');print(n)")
        with self._environment().vars(self).apply():
            self.run(shlex.join([self._python(), "-c", code]))

    def package(self):
        with self._environment().vars(self).apply():
            CMake(self).install()
        copy(self, "*.py", src=os.path.join(self.source_folder, "python", "basix"), dst=os.path.join(self.package_folder, "basix"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "Basix-conan-extra.cmake", src=os.path.join(self.source_folder, "res"), dst=os.path.join(self.package_folder, "lib", "cmake", "basix"))
        # Preserve unmodified original test evidence before the owned build
        # manager removes only this instance's temporary directory.
        copy(self, "original-upstream.xml", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res", "original-test-evidence"))
        # Use the real upstream metadata backend, not a forged version/dist-info.
        self._official_metadata(self.package_folder)
        self._sign_elf_tree(self.package_folder)

    def package_info(self):
        self.cpp_info.libs = ["basix"]
        self.cpp_info.includedirs = [x for x in ("include", "basix/include") if os.path.isdir(os.path.join(self.package_folder, x))]
        self.cpp_info.libdirs = [x for x in ("lib", "basix/lib") if os.path.isdir(os.path.join(self.package_folder, x))]
        self.cpp_info.defines = ["MDSPAN_USE_PAREN_OPERATOR=1", "MDSPAN_USE_BRACKET_OPERATOR=0"]
        self.cpp_info.set_property("cmake_file_name", "Basix")
        self.cpp_info.set_property("cmake_target_name", "Basix::basix")
        self.cpp_info.set_property("cmake_build_modules", ["lib/cmake/basix/Basix-conan-extra.cmake"])
        self.runenv_info.prepend_path("PYTHONPATH", self.package_folder)
        for libdir in self.cpp_info.libdirs:
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, libdir))
