import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TaopmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _tool(self, name):
        """Absolute path of a packaged command line tool."""
        return os.path.join(self.dependencies["taopm"].package_folder, "bin", name)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: the packaged tools only run on OHOS")
            return

        bindir = self.cpp.build.bindirs[0]
        if not os.path.isabs(bindir):
            bindir = os.path.normpath(os.path.join(self.build_folder, bindir))

        # 1) Library API: a real Tao program renders 0.25 s of a plucked
        #    220 Hz string through a TaoOutput device and validates the .dat
        #    stream it just wrote (magic, rate, channels, length, finiteness,
        #    energy and pitch).
        stem = os.path.join(bindir, "tao_api_test_out1")
        self.run(f'"{os.path.join(bindir, "test_tao_api")}" "{stem}"', env="conanrun")

        # 2) Script workflow: taoparse translated the example score at build
        #    time (with a bare relative script name, so the stream names are
        #    test_script_out1/out2); running the generated program drives
        #    tao.main() headless and must produce both Output streams.
        #
        #    The binaries are copied into a dedicated run directory and invoked
        #    through the relative name: Conan shortens absolute command paths to
        #    a basename, which breaks them once `cd' has changed the directory.
        rundir = os.path.join(self.build_folder, "tao-run")
        os.makedirs(rundir, exist_ok=True)
        for executable in (os.path.join(bindir, "test_tao_script"), self._tool("taosf")):
            target = os.path.join(rundir, os.path.basename(executable))
            if os.path.lexists(target):
                os.remove(target)
            shutil.copy2(executable, target)
        self.run(f'cd "{rundir}" && ./test_tao_script', env="conanrun")
        produced = [name for name in ("test_script_out1.dat", "test_script_out2.dat")
                    if os.path.isfile(os.path.join(rundir, name))]
        if len(produced) != 2:
            raise ConanException(
                "the generated score program did not write both Tao output "
                f"streams in {rundir} (found: {produced})")
        self.output.info("generated score wrote test_script_out1.dat and "
                         "test_script_out2.dat")

        # 3) tao2wav + libaudiofile: convert the rendered stream to WAVE and
        #    validate the container and PCM payload.
        dat1 = os.path.join(rundir, "test_script_out1.dat")
        wav1 = os.path.join(rundir, "test_script_out1.wav")
        self.run(f'"{self._tool("tao2wav")}" "{dat1}" "{wav1}"', env="conanrun")
        self.run(f'"{os.path.join(bindir, "check_wav")}" "{wav1}"', env="conanrun")

        # 4) The packaged taosf helper performs the same conversion by itself.
        #    It calls `tao2wav' by name, so the package's bin directory has to be
        #    on PATH — this is the runner/user environment the helper expects.
        wav2 = os.path.join(rundir, "test_script_out2.wav")
        pkg_bin = os.path.dirname(self._tool("tao2wav"))
        self.run(f'cd "{rundir}" && PATH="{pkg_bin}:$PATH" ./taosf test_script_out2',
                 env="conanrun")
        self.run(f'"{os.path.join(bindir, "check_wav")}" "{wav2}"', env="conanrun")
