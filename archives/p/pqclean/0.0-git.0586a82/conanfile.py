#!/usr/bin/env python3
"""Conan recipe for PQClean 0.0-git.0586a82 (post-quantum clean implementations).

Packages ML-KEM-768 (Kyber) and ML-DSA-65 (Dilithium) clean implementations
plus the shared common/ sources into a single static library. PQClean has no
unified build system (each scheme dir ships its own Makefile), so the recipe
compiles the sources directly with the HarmonyOS Clang toolchain, mirroring
the upstream scheme Makefiles and the upstream test/Makefile functest wiring.
"""

import io
import os
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# Transient worker-side process-spawn exhaustion signature. CI build 105508
# (#91805, worker CI-010) failed linking the first functest with
# "clang-15: error: unable to execute command: posix_spawn failed: Resource
# temporarily unavailable" after every library object and the static archive
# had compiled cleanly: the worker momentarily could not spawn the linker
# subprocess (EAGAIN). Real compile errors emit diagnostics that do not match
# this signature and fail on the first attempt, unchanged. The errno string
# alone ("Resource temporarily unavailable") is unambiguous for transient
# exhaustion; "unable to execute command" is deliberately NOT matched alone
# because clang uses that prefix for permanent errors too.
_TRANSIENT_SPAWN_RE = re.compile(
    r"posix_spawn failed|Resource temporarily unavailable",
    re.IGNORECASE,
)


class PqcleanConan(ConanFile):
    name = "pqclean"
    version = "0.0-git.0586a82"
    # Bounded retry: 4 attempts, backoff 5s -> 10s -> 20s (35s worst case).
    _SPAWN_ATTEMPTS = 4
    _SPAWN_RETRY_BASE_DELAY = 5
    _TRANSIENT_SPAWN = _TRANSIENT_SPAWN_RE
    description = (
        "PQClean ML-KEM-768 (Kyber) and ML-DSA-65 (Dilithium) clean "
        "post-quantum cryptographic implementations, single static library"
    )
    license = "CC0-1.0"
    homepage = "https://github.com/PQClean/PQClean"
    url = "https://github.com/PQClean/PQClean"
    topics = ("post-quantum", "kyber", "ml-kem", "dilithium", "ml-dsa", "c99")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    # Source lists exactly as the upstream scheme Makefiles declare them.
    KEM_SOURCES = [
        "cbd", "indcpa", "kem", "ntt", "poly", "polyvec", "reduce",
        "symmetric-shake", "verify",
    ]
    SIGN_SOURCES = [
        "ntt", "packing", "poly", "polyvec", "reduce", "rounding", "sign",
        "symmetric-shake",
    ]
    COMMON_SOURCES = [
        "aes", "sha2", "fips202", "nistseedexpander", "sp800-185",
        "randombytes",
    ]

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "pqclean currently supports only OHOS armv8 in this recipe"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compile(self, cc, src, out, includes):
        inc = " ".join(f"-I{shlex.quote(str(i))}" for i in includes)
        self._run_resilient(
            f"{shlex.quote(cc)} -std=c99 -O3 -Wall -Wextra -c "
            f"{shlex.quote(str(src))} {inc} -o {shlex.quote(str(out))}",
        )

    def _run_resilient(self, command):
        """Run a build command, retrying only transient spawn exhaustion.

        The command output is captured so the failure signature can be
        inspected. If the output matches the worker-side transient spawn
        exhaustion signature (EAGAIN), sleep with backoff and retry, at most
        _SPAWN_ATTEMPTS times in total. Any other non-zero exit (real compile
        or link error) re-raises on the first attempt, so genuine failures
        keep their original diagnostics and behavior.
        """
        for attempt in range(1, self._SPAWN_ATTEMPTS + 1):
            buf = io.StringIO()
            try:
                self.run(command, env="conanbuild", stdout=buf, stderr=buf)
                return
            except ConanException:
                output = buf.getvalue()
                # Re-emit the captured command output so genuine failures
                # keep their diagnostics in the build log.
                if output:
                    self.output.writeln(output)
                if attempt >= self._SPAWN_ATTEMPTS or not self._TRANSIENT_SPAWN.search(output):
                    raise
                delay = self._SPAWN_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                self.output.warning(
                    f"transient process-spawn exhaustion (attempt {attempt}/"
                    f"{self._SPAWN_ATTEMPTS}), retrying in {delay}s: "
                    f"{output.strip()[-200:]}"
                )
                time.sleep(delay)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c") or "clang"
        ar = shutil.which("llvm-ar") or "/data/service/hnp/bin/llvm-ar"
        source = Path(self.source_folder)
        build = Path(self.build_folder)
        build.mkdir(parents=True, exist_ok=True)

        kem_dir = source / "crypto_kem" / "ml-kem-768" / "clean"
        sign_dir = source / "crypto_sign" / "ml-dsa-65" / "clean"
        common_dir = source / "common"

        objs = []
        for name in self.KEM_SOURCES:
            o = build / f"kem_{name}.o"
            self._compile(cc, kem_dir / f"{name}.c", o, [kem_dir, common_dir])
            objs.append(o)
        for name in self.SIGN_SOURCES:
            o = build / f"sign_{name}.o"
            self._compile(cc, sign_dir / f"{name}.c", o, [sign_dir, common_dir])
            objs.append(o)
        for name in self.COMMON_SOURCES:
            o = build / f"common_{name}.o"
            self._compile(cc, common_dir / f"{name}.c", o, [common_dir])
            objs.append(o)

        library = build / "libpqclean.a"
        self._run_resilient(
            f"{shlex.quote(ar)} rcs {shlex.quote(str(library))} "
            + " ".join(shlex.quote(str(o)) for o in objs),
        )

        # Upstream functional tests, compiled from the unmodified upstream
        # sources exactly as test/Makefile does:
        #   -DNTESTS=1 -DPQCLEAN_NAMESPACE=PQCLEAN_<SCHEME>_CLEAN
        #   -I<scheme_dir> crypto_{kem,sign}/functest.c + scheme + common
        # objects. Upstream CFLAGS keep -Wall -Wextra -std=c99; -Werror and
        # -Wpedantic are dropped because OHOS clang emits extra pedantic
        # diagnostics; the test sources themselves are unchanged.
        functests = [
            (
                "pqclean-kem-functest",
                "PQCLEAN_MLKEM768_CLEAN",
                source / "test" / "crypto_kem" / "functest.c",
                kem_dir,
            ),
            (
                "pqclean-sign-functest",
                "PQCLEAN_MLDSA65_CLEAN",
                source / "test" / "crypto_sign" / "functest.c",
                sign_dir,
            ),
        ]
        for exe_name, namespace, functest_src, scheme_dir in functests:
            exe = build / exe_name
            self._run_resilient(
                f"{shlex.quote(cc)} -std=c99 -O3 -Wall -Wextra "
                f"-DNTESTS=1 -DPQCLEAN_NAMESPACE={namespace} "
                f"-I{shlex.quote(str(scheme_dir))} -I{shlex.quote(str(common_dir))} "
                f"{shlex.quote(str(functest_src))} {shlex.quote(str(library))} "
                f"-o {shlex.quote(str(exe))}",
            )
            self._sign(exe)
            self.run(shlex.quote(str(exe)), env="conanrun")

    def package(self):
        copy(self, "libpqclean.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        pkg_include = os.path.join(self.package_folder, "include", "pqclean")
        copy(self, "api.h",
             src=os.path.join(self.source_folder, "crypto_kem", "ml-kem-768", "clean"),
             dst=os.path.join(pkg_include, "ml-kem-768"))
        copy(self, "api.h",
             src=os.path.join(self.source_folder, "crypto_sign", "ml-dsa-65", "clean"),
             dst=os.path.join(pkg_include, "ml-dsa-65"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "common"),
             dst=os.path.join(pkg_include, "common"))
        copy(self, "LICENSE",
             src=os.path.join(self.source_folder, "crypto_kem", "ml-kem-768", "clean"),
             dst=os.path.join(self.package_folder, "licenses", "ml-kem-768"))
        copy(self, "LICENSE",
             src=os.path.join(self.source_folder, "crypto_sign", "ml-dsa-65", "clean"),
             dst=os.path.join(self.package_folder, "licenses", "ml-dsa-65"))

    def package_info(self):
        self.cpp_info.libs = ["pqclean"]
        self.cpp_info.set_property("cmake_file_name", "PQClean")
        self.cpp_info.set_property("cmake_target_name", "PQClean::PQClean")
        self.cpp_info.set_property("pkg_config_name", "pqclean")

    @staticmethod
    def _sign(executable):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to execute upstream tests on OHOS"
            )
        signed = executable.with_suffix(executable.suffix + ".signed")
        if os.path.isfile(objcopy):
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", str(executable)],
                check=False,
            )
        subprocess.run(
            [signer, "sign", "-inFile", str(executable), "-outFile", str(signed),
             "-selfSign", "1"],
            check=True,
        )
        shutil.move(signed, executable)
        os.chmod(executable, 0o755)
