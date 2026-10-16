import glob
import os
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class LibatomicConan(ConanFile):
    name = "libatomic"
    version = "16.1.1"
    description = "GCC atomic operations runtime library"
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org/"
    url = "https://github.com/gcc-mirror/gcc"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # GCC 16.1.1 is a release-branch snapshot, not a published tarball tag.
        # Fetch only the runtime and shared GCC configure files at the tested SHA.
        commit = self.conan_data["sources"][self.version]["commit"]
        self.run("git init -q")
        self.run("git remote add origin https://github.com/gcc-mirror/gcc.git")
        for attempt in range(1, 5):
            try:
                self.run(f"git fetch --depth=1 --filter=blob:none origin {commit}")
                break
            except ConanException:
                if attempt == 4:
                    raise
                self.output.warning(f"GitHub connection failed; retrying fetch ({attempt}/4)")
                time.sleep(5 * attempt)
        self.run("git sparse-checkout init --cone")
        self.run("git sparse-checkout set libatomic config")
        for attempt in range(1, 5):
            try:
                self.run("git checkout --detach FETCH_HEAD")
                break
            except ConanException:
                if attempt == 4:
                    raise
                self.output.warning(f"GitHub blob fetch failed; retrying checkout ({attempt}/4)")
                time.sleep(5 * attempt)
        apply_conandata_patches(self)

    def _compiler(self):
        executables = self.conf.get("tools.build:compiler_executables", default={})
        return executables.get("c", "clang")

    def _build_env(self):
        cc = self._compiler()
        sdk_bin = os.path.dirname(cc)
        env = os.environ.copy()
        env["PATH"] = sdk_bin + os.pathsep + env.get("PATH", "")
        env.update({
            "CC": cc,
            "CXX": self.conf.get("tools.build:compiler_executables", default={}).get("cpp", "clang++"),
            "AR": os.path.join(sdk_bin, "llvm-ar"),
            "NM": os.path.join(sdk_bin, "llvm-nm"),
            "RANLIB": os.path.join(sdk_bin, "llvm-ranlib"),
            "LD": os.path.join(sdk_bin, "ld.lld"),
            "STRIP": os.path.join(sdk_bin, "llvm-strip"),
            "CFLAGS": "-O2 -fPIC",
        })
        return env

    def _run(self, args, env, cwd=None):
        self.output.info("Running: " + " ".join(args))
        completed = subprocess.run(args, cwd=cwd, env=env, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if completed.returncode:
            self.output.error(completed.stdout[-6000:])
            raise ConanException(f"Command exited {completed.returncode}: {args[0]}")
        return completed.stdout

    def build(self):
        src = self.source_folder
        os.makedirs(self.build_folder, exist_ok=True)
        env = self._build_env()
        configure = os.path.join(src, "libatomic", "configure")
        self._run(["sh", configure, "--build=aarch64-unknown-linux-musl",
                   "--host=aarch64-unknown-linux-musl", "--disable-multilib",
                   "--disable-shared", "--enable-static",
                   f"--prefix={self.package_folder}", "--no-create"],
                  env, cwd=self.build_folder)

        # OHOS HMDFS does not allow the 0700 directory made by mktemp -d to
        # be written even by its creator. Autoconf's generated config.status
        # needs a normal group-writable temporary directory on this device.
        status = os.path.join(self.build_folder, "config.status")
        with open(status, encoding="utf-8") as f:
            data = f.read()
        old = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&'
        new = 'tmp=./conf-libatomic; mkdir -p "$tmp" &&'
        if old not in data:
            raise ConanException("Unknown Autoconf config.status temporary-directory logic")
        with open(status, "w", encoding="utf-8") as f:
            f.write(data.replace(old, new))
        self._run(["sh", "config.status"], env, cwd=self.build_folder)
        self._run(["make", "-j2", "libatomic.la"], env, cwd=self.build_folder)

        # Every upstream libatomic.c source is a dg-do run test. Execute the
        # complete 27-program set against the just-built library on OHOS.
        tests = sorted(glob.glob(os.path.join(src, "libatomic", "testsuite",
                                              "libatomic.c", "*.c")))
        if len(tests) != 27:
            raise ConanException(f"Expected 27 upstream C tests, found {len(tests)}")
        library = os.path.join(self.build_folder, ".libs", "libatomic.a")
        for test in tests:
            name = os.path.basename(test)[:-2]
            executable = os.path.join(self.build_folder, "test-" + name)
            flags = [] if name.endswith("-4") else ["-g"]
            if name == "atomic-generic":
                flags = ["-w"]
            self._run([self._compiler(), *flags, test, library, "-o", executable], env)
            self._run([executable], env)
            self.output.info(f"UPSTREAM_PASS {name}")
        self.output.info("UPSTREAM_RESULT 27/27 PASS, 0 FAIL")

    def package(self):
        copy(self, "libatomic.a", src=os.path.join(self.build_folder, ".libs"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["atomic"]
