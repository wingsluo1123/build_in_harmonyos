#!/usr/bin/env python3
"""CMake installed-package numerical, original-model and DSO consumer tests."""
import io
import json
from pathlib import Path
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import check_sha256, download, unzip


class KaldiVoskTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _fixture(self, filename, urls, digest, fixtures):
        cached = self.conf.get("user.kaldi-vosk:fixtures", default="", check_type=str)
        archive = fixtures / filename
        if not archive.exists():
            if cached:
                candidate = Path(cached) / filename
                check_sha256(self, str(candidate), digest)
                shutil.copyfile(candidate, archive)
            else:
                download(self, urls, str(archive))
        check_sha256(self, str(archive), digest)
        return archive

    def generate(self):
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()
        fixtures = Path(self.build_folder) / "fixtures"
        fixtures.mkdir(parents=True, exist_ok=True)
        model = fixtures / "vosk-model-small-en-us-0.15"
        archive = self._fixture("vosk-model-small-en-us-0.15.zip",
            "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
            "30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498", fixtures)
        # Re-extract verified inputs so a stale modified model cannot mask a failure.
        unzip(self, str(archive), destination=str(fixtures))
        self._fixture("test.wav",
            "https://raw.githubusercontent.com/alphacep/vosk-api/v0.3.45/python/example/test.wav",
            "dcfea5712c43a43ba7ae8083afb39d36993e5a69c46e88b68aaa72b65cb615bb", fixtures)
        fst = fixtures / "openfst"
        archive = self._fixture("openfst-1.8.4.tar.gz",
            ["https://openfst.org/twiki/pub/FST/FstDownload/openfst-1.8.4.tar.gz",
             "https://distfiles.macports.org/openfst/openfst-1.8.4.tar.gz"],
            "a8ebbb6f3d92d07e671500587472518cfc87cb79b9a654a5a8abb2d0eb298016", fixtures)
        unzip(self, str(archive), destination=str(fst), strip_root=True)
        # The published core dependency has no ngram extension. These original,
        # version-matched test-only helpers read Gr.fst directly on the device.
        headers = fixtures / "ngram-headers"
        destination = headers / "fst/extensions/ngram"
        shutil.copytree(fst / "src/include/fst/extensions/ngram", destination, dirs_exist_ok=True)
        tc = CMakeToolchain(self, generator="Ninja")
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        ninja = Path(compilers.get("c", "clang")).parent / "ninja"
        if not ninja.is_file():
            ninja = Path(shutil.which("ninja") or "ninja")
        subprocess.run([str(ninja), "--version"], check=True)
        tc.variables["CMAKE_MAKE_PROGRAM"] = str(ninja)
        tc.variables["OPENFST_TEST_SOURCE"] = str(fst)
        tc.variables["OPENFST_TEST_HEADERS"] = str(headers)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def run_command(self, name, command, expected=0, stderr_contains=None):
        reports = Path(self.build_folder) / "reports"
        reports.mkdir(exist_ok=True)
        command = list(map(str, command))
        timeout = shutil.which("timeout")
        if not timeout:
            raise ConanInvalidConfiguration("timeout is required for bounded consumer execution")
        stdout, stderr = io.StringIO(), io.StringIO()
        rc = self.run(shlex.join([timeout, "--signal=KILL", "300"] + command),
                      stdout=stdout, stderr=stderr, ignore_errors=True, env=None)
        output, errors = stdout.getvalue(), stderr.getvalue()
        (reports / (name + ".stdout")).write_text(output, encoding="utf-8")
        (reports / (name + ".stderr")).write_text(errors, encoding="utf-8")
        record = dict(command=command, rc=rc, expected=expected, timeout_seconds=300)
        (reports / (name + ".json")).write_text(json.dumps(record, indent=2))
        self.output.info(output)
        self.output.info(errors)
        if rc != expected:
            raise ConanInvalidConfiguration(f"{name}: exit {rc}, expected {expected}")
        if stderr_contains and stderr_contains not in errors:
            raise ConanInvalidConfiguration(f"{name}: missing expected diagnostic {stderr_contains}")

    def test(self):
        build = Path(self.build_folder)
        executable = build / "test_native_chain"
        loader = build / "test_dlopen"
        probe = build / "libconsumer_probe.so"
        if str(self.settings.os) == "OHOS":
            signer = shutil.which("binary-sign-tool")
            if not signer:
                raise ConanInvalidConfiguration("binary-sign-tool is required for OHOS consumer tests")
            for path in (executable, loader, probe):
                subprocess.run([signer, "sign", "-inFile", str(path), "-outFile", str(path),
                                "-selfSign", "1"], check=True)
        environment = Environment()
        environment.define("OPENBLAS_NUM_THREADS", "1")
        environment.define("OMP_NUM_THREADS", "1")
        environment.define("PWD", self.build_folder)
        tmp = build / "tmp"
        tmp.mkdir(exist_ok=True)
        environment.define("TMPDIR", str(tmp))
        for dep in self.dependencies.host.values():
            if dep.package_folder:
                environment.prepend_path("LD_LIBRARY_PATH", str(Path(dep.package_folder) / "lib"))
        with environment.vars(self).apply():
            fixture = build / "fixtures"
            model = fixture / "vosk-model-small-en-us-0.15"
            wave = fixture / "test.wav"
            self.run_command("numeric", [executable, "numeric", build / "mfcc.txt"])
            self.run_command("decode-digits", [executable, "decode", model, wave])
            self.run_command("decode-original-lm", [executable, "decode", model, wave, "original"])
            self.run_command("missing-model", [executable, "decode", build / "absent-model", wave],
                      expected=1, stderr_contains="[FAIL]")
            self.run_command("dlopen", [loader, probe])
        self.output.info("[PASS] Installed consumer: numerical/features/FST, both original model decode modes, missing-model and dlopen")
