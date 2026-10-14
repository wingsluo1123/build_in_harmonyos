"""Parallel HDF5 C/HL with the complete original CTest inventory enabled."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import sys
import struct
import stat
import tempfile
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, check_sha256, copy, get, save, unzip


def _ctest_outcomes(inventory, suite):
    """Count explicit CTest JUnit outcomes; absence of failure is not PASS."""
    entries = inventory["tests"]
    original_names = [entry["name"] for entry in entries]
    cases = list(suite.iter("testcase"))
    names = [case.get("name") for case in cases]
    if (not entries or len(set(original_names)) != len(original_names)
            or len(cases) != len(entries) or len(set(names)) != len(names)
            or set(names) != set(original_names) or suite.tag != "testsuite"):
        raise ValueError("Original CTest inventory/JUnit identity mismatch")
    statuses = {"run": [], "fail": [], "notrun": [], "disabled": []}
    for case in cases:
        status = case.get("status")
        if status not in statuses:
            raise ValueError("Missing or unknown explicit CTest status")
        tags = {tag for tag in ("failure", "error", "skipped")
                if case.find(tag) is not None}
        if ((status == "run" and tags) or (status == "disabled" and tags)
                or (status == "notrun" and tags != {"skipped"})
                or (status == "fail" and not tags.intersection({"failure", "error"}))):
            raise ValueError("Contradictory CTest status/child outcome")
        statuses[status].append(case.get("name"))
    disabled_inventory = {
        entry["name"] for entry in entries
        if any(prop["name"] == "DISABLED" and prop["value"] is True
               for prop in entry.get("properties", []))
    }
    if disabled_inventory != set(statuses["disabled"]):
        raise ValueError("CTest disabled inventory/JUnit mismatch")
    for attribute, expected in (("tests", len(entries)),
                                ("failures", len(statuses["fail"])),
                                ("skipped", len(statuses["notrun"])),
                                ("disabled", len(statuses["disabled"]))):
        if int(suite.attrib[attribute]) != expected:
            raise ValueError("CTest suite aggregate/outcome mismatch")
    return {"total": len(entries), "passed": len(statuses["run"]),
            "failed": len(statuses["fail"]), "not_run": len(statuses["notrun"]),
            "disabled": len(statuses["disabled"]), "case_names_by_status": statuses}


class Hdf5Conan(ConanFile):
    name = "hdf5"
    version = "2.2.0"
    description = "Parallel HDF5 C/HL with relocatable MPI dependencies"
    license = "BSD-3-Clause"
    homepage = "https://www.hdfgroup.org/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "patches/*.patch", "compiler_proxy.py", "parallel-capability.cmake"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("This parallel repair supports Linux/OHOS")
        if self.options.shared:
            raise ConanInvalidConfiguration("This repair certifies the static parallel C/HL configuration only")

    def requirements(self):
        self.requires("mpich/5.0.1.2", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.2.1")
        self.requires("libaec/1.1.7")

    def layout(self):
        cmake_layout(self)

    def source(self):
        archive = self.conf.get("user.harmony:source_archive", default=None)
        if archive:
            # Offline projection of the frozen official bytes, never a fork or
            # alternate unchecked source. The official URL remains authoritative.
            check_sha256(self, archive, self.conan_data["sources"]["sha256"])
            unzip(self, archive, strip_root=False)
        else:
            get(self, **self.conan_data["sources"], strip_root=False)
        # The official archive spells its root ./hdf5-2.2.0; Conan's
        # strip_root strips only '.', not the actual source directory.
        source_root = Path(self.source_folder) / "hdf5-2.2.0"
        if not (source_root / "CMakeLists.txt").is_file():
            raise ConanInvalidConfiguration("Official hdf5-2.2.0 source root missing")
        # Unmodified official refresh-patch output; exact original/fixed inputs
        # and all nineteen actual patch-ng applications are independently bound.
        apply_conandata_patches(self)

    def generate(self):
        if self.settings.os == "OHOS":
            # Keep the Conan source and final package roots, while the native
            # build, generated environment and original CTest working files
            # use an actual process-owned POSIX directory.
            parents = [os.environ.get("TMPDIR"), "/data/storage/el2/base/cache"]
            for candidate in parents:
                if not candidate:
                    continue
                parent = Path(candidate)
                if (parent.is_absolute() and parent.is_dir()
                        and parent.resolve() == parent and not parent.is_symlink()
                        and parent.stat().st_uid == os.getuid()
                        and os.access(parent, os.W_OK | os.X_OK)):
                    self._native_build_manager = tempfile.TemporaryDirectory(
                        prefix="conan-hdf5-build-", dir=str(parent))
                    root = Path(self._native_build_manager.name)
                    break
            else:
                raise ConanInvalidConfiguration("Actual owned POSIX build parent required")
            if (root.resolve() != root or root.is_symlink()
                    or root.stat().st_uid != os.getuid()
                    or stat.S_IMODE(root.stat().st_mode) != 0o700):
                raise ConanInvalidConfiguration("Unsafe private native HDF5 build root")
            build = root / "build"
            generators = root / "generators"
            build.mkdir(mode=0o700)
            generators.mkdir(mode=0o700)
            self.folders.build = str(build)
            self.folders.generators = str(generators)
            self.output.info("ACTUAL_PRIVATE_HDF5_BUILD=" + str(build))
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # The four original test scripts are POSIX /bin/sh programs.
            # Do not implicitly select an HNP Bash launcher whose startup
            # cannot resolve the HMDFS CTest working directory. Keep all
            # original tests, IPC files, assertions and timeouts unchanged.
            test_shell = self.conf.get("user.harmony:test_shell", default=None) or "/system/bin/sh"
        else:
            test_shell = self.conf.get("user.harmony:bash", default=None) or shutil.which("bash")
        if not test_shell or not os.path.isabs(test_shell) or not Path(test_shell).is_file():
            raise ConanInvalidConfiguration("Actual absolute test shell required for original HDF5 shell tests")
        tc.variables["SH_PROGRAM"] = str(test_shell)
        tc.variables.update({
            # CMakeDeps usage requirements are CONFIG-qualified. Without
            # the actual configuration, try_compile sees an empty CONFIG
            # and silently loses the imported dependency's include/link data.
            "CMAKE_TRY_COMPILE_CONFIGURATION": str(self.settings.build_type),
            "BUILD_SHARED_LIBS": bool(self.options.shared),
            "BUILD_STATIC_LIBS": True,
            "HDF5_BUILD_STATIC_TOOLS": True,
            "CMAKE_POSITION_INDEPENDENT_CODE": bool(self.options.get_safe("fPIC", True)),
            "CMAKE_INSTALL_LIBDIR": "lib",
            "HDF5_ENABLE_PARALLEL": True,
            "BUILD_TESTING": True,
            "HDF5_BUILD_TOOLS": True,
            "HDF5_BUILD_CPP_LIB": False,
            "HDF5_BUILD_FORTRAN": False,
            "HDF5_BUILD_HL_LIB": True,
            "HDF5_BUILD_EXAMPLES": True,
            "HDF5_ENABLE_ZLIB_SUPPORT": True,
            "HDF5_ENABLE_SZIP_SUPPORT": True,
            "HDF5_ALLOW_EXTERNAL_SUPPORT": "NO",
            "HDF5_USE_LIBAEC_STATIC": False,
            "MPIEXEC_NUMPROC_FLAG": "-n",
            "MPIEXEC_MAX_NUMPROCS": 2,
        })
        mpi = self.dependencies["mpich"]
        mpi_c = mpi.cpp_info.components["c"]
        # CMakeToolchain variables are scalars: serialize a CMake list, not
        # Python's list repr (which becomes one nonexistent bracketed path).
        tc.variables["MPI_C_INCLUDE_DIRS"] = ";".join(mpi_c.includedirs)
        tc.variables["MPI_C_HEADER_DIR"] = mpi_c.includedirs[0]
        tc.variables["MPI_C_LIB_NAMES"] = "mpi"
        tc.variables["MPI_mpi_LIBRARY"] = os.path.join(mpi_c.libdirs[0], "libmpi.so")
        tc.variables["MPI_C_COMPILER"] = os.path.join(mpi.cpp_info.bindirs[0], "mpicc")
        tc.variables["MPIEXEC_EXECUTABLE"] = os.path.join(mpi.cpp_info.bindirs[0], "mpiexec")
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            signer = self.conf.get("user.harmony:signer", default=None) or shutil.which("binary-sign-tool")
            objcopy = compilers.get("objcopy") or shutil.which("llvm-objcopy")
            if not signer or not objcopy:
                raise ConanInvalidConfiguration("Real target signer/objcopy required")
            self._signer, self._objcopy = signer, objcopy
            for language, compiler in (("C", compilers.get("c") or shutil.which("clang")),
                                       ("CXX", compilers.get("cpp") or shutil.which("clang++"))):
                if not compiler:
                    raise ConanInvalidConfiguration("Missing actual compiler " + language)
                config = os.path.join(self.generators_folder, "compiler-" + language + ".json")
                save(self, config, json.dumps({"compiler": compiler, "language": language,
                                               "signer": signer, "objcopy": objcopy}))
                # The compilers block renders the configured executable after
                # generic variables. Bind the proxy in that authoritative block
                # so its ARG1 cannot be passed to the unwrapped clang driver.
                tc.blocks["compilers"].values["compilers"][language] = sys.executable
                tc.variables["CMAKE_" + language + "_COMPILER_ARG1"] = (
                    shlex.quote(os.path.join(self.export_sources_folder, "compiler_proxy.py"))
                    + " " + shlex.quote(config))
        tc.generate()
        CMakeDeps(self).generate()
        tmp = os.path.join(self.build_folder, "task-tmp")
        os.makedirs(tmp, exist_ok=True)
        env = Environment()
        env.define_path("TMPDIR", tmp)
        env.define("OMP_NUM_THREADS", "1")
        # Conan reserves conanbuild.sh for its aggregate activation. Giving a
        # custom environment that name makes the aggregate source itself.
        env.vars(self).save_script("hdf5-task-env")

    def build(self):
        cmake = CMake(self)
        try:
            cmake.configure(build_script_folder="hdf5-2.2.0")
        except Exception:
            # Preserve the actual failed compile/link diagnostic before the
            # private transaction releases its build cache. Do not change RC.
            for name in ("CMakeConfigureLog.yaml", "CMakeError.log"):
                path = Path(self.build_folder) / "CMakeFiles" / name
                if path.is_file():
                    data = path.read_bytes()
                    self.output.info("EXACT_FAILED_CONFIGURE_LOG " + str(path)
                                     + " bytes=" + str(len(data))
                                     + " sha256=" + hashlib.sha256(data).hexdigest())
                    print(data[-30000:].decode("utf-8", errors="replace"), flush=True)
            raise
        cmake.build()
        inventory_path=Path(self.build_folder)/"original-full-inventory.json"
        xml_path=Path(self.build_folder)/"original-full.xml"
        self.run("ctest --show-only=json-v1 > "+shlex.quote(str(inventory_path)),cwd=self.build_folder,env="conanbuild")
        inventory=json.loads(inventory_path.read_text())
        names={t["name"] for t in inventory["tests"]}
        required_shell = {"H5SHELL-test_flush_refresh", "H5SHELL-test_use_cases",
                          "H5SHELL-test_swmr", "H5SHELL-test_vds_swmr"}
        if len(inventory["tests"]) != len(names) or len(names) != 3216 or not required_shell <= names:
            raise ConanInvalidConfiguration(
                "Original complete inventory requires 3216 unique tests including all four shell groups; actual="
                + str(len(names)) + "; missing=" + repr(sorted(required_shell - names)))
        rc=self.run("ctest --parallel 1 --output-on-failure --no-tests=error --output-junit "+shlex.quote(str(xml_path)),cwd=self.build_folder,env="conanbuild",ignore_errors=True)
        outcomes=_ctest_outcomes(inventory,ET.parse(xml_path).getroot())
        save(self,str(Path(self.build_folder)/"original-full-outcomes.json"),json.dumps(dict(outcomes,actual_rc=rc,full_suite_executed=True),indent=2))
        self.output.info("ORIGINAL_FULL_CTEST_RESULT="+str(outcomes["passed"])+"/"+str(outcomes["total"])+"; FAILED="+str(outcomes["failed"])+"; NOT_RUN="+str(outcomes["not_run"])+"; DISABLED="+str(outcomes["disabled"]))
        if rc or outcomes["passed"]!=3216 or outcomes["failed"] or outcomes["not_run"] or outcomes["disabled"]:
            raise ConanInvalidConfiguration("Original complete CTest inventory not fully passed")
        self.output.info("UPSTREAM_TEST_PASS=3216/3216; SKIP=0")

    def package(self):
        CMake(self).install()
        # Preserve the complete raw original inventory and outcomes before
        # TemporaryDirectory removes only this instance's build directory.
        for name in ("original-full-inventory.json", "original-full.xml",
                     "original-full-outcomes.json", "CMakeCache.txt"):
            copy(self, name, src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res", "original-test-evidence"))
        copy(self, "CMakeConfigureLog.yaml",
             src=os.path.join(self.build_folder, "CMakeFiles"),
             dst=os.path.join(self.package_folder, "res", "original-test-evidence"))
        copy(self, "LICENSE", src=os.path.join(self.source_folder, "hdf5-2.2.0"), dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "parallel-capability.cmake", src=self.export_sources_folder,
             dst=os.path.join(self.package_folder, "lib", "cmake"))
        if self.settings.os == "OHOS":
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            signer = self.conf.get("user.harmony:signer", default=None) or shutil.which("binary-sign-tool")
            objcopy = compilers.get("objcopy") or shutil.which("llvm-objcopy")
            if not signer or not objcopy:
                raise ConanInvalidConfiguration("Package-local installed ELF signing tools unavailable")
            for folder in (Path(self.package_folder) / "bin", Path(self.package_folder) / "lib"):
                if not folder.is_dir():
                    continue
                for path in folder.iterdir():
                    if not path.is_file() or path.is_symlink():
                        continue
                    with path.open("rb") as stream:
                        header = stream.read(18)
                    if len(header) != 18 or header[:4] != b"\x7fELF":
                        continue
                    kind = struct.unpack("<H" if header[5] == 1 else ">H", header[16:18])[0]
                    if kind in (2, 3):
                        self.run(shlex.quote(objcopy) + " --remove-section .codesign " + shlex.quote(str(path)))
                        self.run(shlex.quote(signer) + " sign -inFile " + shlex.quote(str(path))
                                 + " -outFile " + shlex.quote(str(path)) + " -selfSign 1")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "HDF5")
        self.cpp_info.set_property("cmake_build_modules", ["lib/cmake/parallel-capability.cmake"])
        c = self.cpp_info.components["c"]
        c.libs = ["hdf5"]
        c.requires = ["mpich::c", "zlib::zlib", "libaec::sz", "libaec::aec"]
        c.set_property("cmake_target_name", "hdf5-static" if not self.options.shared else "hdf5-shared")
        hl = self.cpp_info.components["hl"]
        hl.libs = ["hdf5_hl"]
        hl.requires = ["c"]
        hl.set_property("cmake_target_name", "hdf5_hl-static")
        tools = self.cpp_info.components["tools"]
        tools.libs = ["hdf5_tools"]
        tools.requires = ["c"]
        tools.set_property("cmake_target_name", "hdf5_tools-static")
        if self.settings.os in ("Linux", "OHOS"):
            c.system_libs = ["m", "dl"]

