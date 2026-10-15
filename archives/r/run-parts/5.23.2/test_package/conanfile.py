import os
import shutil
from io import StringIO

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RunPartsTestConan(ConanFile):
    """Consumer flow: build an OHOS ELF program (consumer_hook) with the Conan
    toolchain, install it as hook scripts and let the packaged run-parts binary
    execute them. Every assertion compares real output of the consumer program
    that run-parts launched."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _run_parts(self, args, stdin_text=None, tmpdir=None):
        """Run the packaged run-parts through bash; return (exit_code, stdout+stderr)."""
        dep = self.dependencies["run-parts"]
        rp = os.path.join(dep.package_folder, "bin", "run-parts")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        inner = f"TMPDIR={tmpdir} {rp} {args} 2>&1"
        if stdin_text is not None:
            stdin_file = os.path.join(self.build_folder, "stdin.txt")
            with open(stdin_file, "w") as f:
                f.write(stdin_text)
            inner += f" < {stdin_file}"
        out = StringIO()
        rc = self.run(f'{bash} -c "{inner}"', stdout=out, ignore_errors=True)
        return rc, out.getvalue()

    def test(self):
        hooks = os.path.join(self.build_folder, "hooks")
        tmpdir = os.path.join(self.build_folder, "rp-tmp")
        shutil.rmtree(hooks, ignore_errors=True)
        os.makedirs(hooks)
        os.makedirs(tmpdir, exist_ok=True)
        elf = os.path.join(self.build_folder, "consumer_hook")
        for name in ("10-consumer-hook", "20-consumer-hook", "15-not-executable"):
            shutil.copy(elf, os.path.join(hooks, name))
        os.chmod(os.path.join(hooks, "15-not-executable"), 0o644)
        with open(os.path.join(hooks, "README.txt"), "w") as f:
            f.write("ignored: name does not match run-parts default pattern\n")

        h10 = os.path.join(hooks, "10-consumer-hook")
        h15 = os.path.join(hooks, "15-not-executable")
        h20 = os.path.join(hooks, "20-consumer-hook")

        # --list: valid names (executable or not), README.txt filtered by name
        rc, out = self._run_parts(f"--list {hooks}", tmpdir=tmpdir)
        assert rc == 0 and out.split() == [h10, h15, h20], out
        # --test: only executable files would run
        rc, out = self._run_parts(f"--test {hooks}", tmpdir=tmpdir)
        assert rc == 0 and out.split() == [h10, h20], out

        # -a: arguments reach the consumer ELF program
        rc, out = self._run_parts(f"-a one -a two {hooks}", tmpdir=tmpdir)
        assert rc == 0 and out == (
            "HOOK 10-consumer-hook argc=3 [one] [two]\n"
            "HOOK 20-consumer-hook argc=3 [one] [two]\n"), out

        # --stdin: stdin is multiplexed to every hook through a temporary file
        # created under $TMPDIR (open(O_TMPFILE) with the mkstemp fallback patch; /tmp is read-only on OHOS)
        rc, out = self._run_parts(f"--stdin -a stdin {hooks}",
                                  stdin_text="hello-ohos\n", tmpdir=tmpdir)
        assert rc == 0 and out == (
            "HOOK 10-consumer-hook argc=2 [stdin]\nSTDIN 11 hello-ohos\n"
            "HOOK 20-consumer-hook argc=2 [stdin]\nSTDIN 11 hello-ohos\n"), out

        # -u: umask applied to the hooks
        rc, out = self._run_parts(f"-u 077 -a umask {hooks}", tmpdir=tmpdir)
        assert rc == 0 and out == (
            "HOOK 10-consumer-hook argc=2 [umask]\nUMASK 077\n"
            "HOOK 20-consumer-hook argc=2 [umask]\nUMASK 077\n"), out

        # --exit-on-error: hook exit code 3 is propagated, 20-consumer-hook never runs
        rc, out = self._run_parts(f"--exit-on-error -a fail {hooks}", tmpdir=tmpdir)
        assert rc == 3, (rc, out)
        assert "HOOK 10-consumer-hook argc=2 [fail]" in out, out
        assert "HOOK 20" not in out, out
        assert f"{h10} exited with return code 3" in out, out
