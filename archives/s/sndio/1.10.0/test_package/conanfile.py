#!/usr/bin/env python3
"""HarmonyOS test package for sndio 1.10.0.

sndio upstream has no regression suite, so this test package *is* the test.
It is deliberately built out of things that can be proven on a bare OHOS
sandbox (no audio hardware, no running sndiod):

  1. a real consumer program is compiled against the package and run
     (header + shared library + ABI symbols + deterministic API contract)
  2. the installed layout is checked (header, pkg-config, all four tools)
  3. the ELF dynamic section of the consumer is parsed in pure Python and the
     DT_NEEDED entry for libsndio must be a bare soname -- on OHOS the
     toolchain emits no soname by default, so an absolute build path here is
     exactly the defect that breaks downstream packaging (L5)
  4. libsndio.so.7.3 must carry DT_SONAME=libsndio.so.7 (what configure's
     HarmonyOS case injects with -Wl,-soname)
  5. `aucat -n` runs an off-line playback->record pipeline over a real raw
     file: genuine audio data path through the built binaries, no device
  6. each installed tool executes and reports its usage string
"""
import os
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


ELF_PT_LOAD = 1
ELF_PT_DYNAMIC = 2
ELF_DT_NULL = 0
ELF_DT_NEEDED = 1
ELF_DT_STRTAB = 5
ELF_DT_SONAME = 14


def elf_dynamic_strings(path, wanted_tags):
    """Return {tag: [strings]} read from an ELF64-LE dynamic section.

    Needed because readelf / llvm-readelf are not guaranteed to be on the
    worker: parsing the bytes keeps the check honest instead of skipping it.
    """
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:4] != b"\x7fELF":
        raise ConanException(f"{path}: not an ELF file")
    if data[4] != 2 or data[5] != 1:
        raise ConanException(f"{path}: expected ELF64 little-endian")

    e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
    e_phentsize = struct.unpack_from("<H", data, 0x36)[0]
    e_phnum = struct.unpack_from("<H", data, 0x38)[0]

    loads, dynamic = [], None
    for index in range(e_phnum):
        base = e_phoff + index * e_phentsize
        p_type, _flags, p_offset, p_vaddr, _paddr, p_filesz, _memsz, _align = \
            struct.unpack_from("<IIQQQQQQ", data, base)
        if p_type == ELF_PT_LOAD:
            loads.append((p_offset, p_vaddr, p_filesz))
        elif p_type == ELF_PT_DYNAMIC:
            dynamic = (p_offset, p_filesz)
    if dynamic is None:
        raise ConanException(f"{path}: no PT_DYNAMIC segment")

    def vaddr_to_offset(vaddr):
        for p_offset, p_vaddr, p_filesz in loads:
            if p_vaddr <= vaddr < p_vaddr + p_filesz:
                return p_offset + (vaddr - p_vaddr)
        return None

    offsets, strtab_vaddr = [], None
    offset, size = dynamic
    for pos in range(offset, offset + size, 16):
        tag, val = struct.unpack_from("<qQ", data, pos)
        if tag == ELF_DT_NULL:
            break
        if tag in wanted_tags:
            offsets.append((tag, val))
        if tag == ELF_DT_STRTAB:
            strtab_vaddr = val
    if strtab_vaddr is None:
        raise ConanException(f"{path}: no DT_STRTAB")

    strtab_offset = vaddr_to_offset(strtab_vaddr)
    if strtab_offset is None:
        raise ConanException(f"{path}: DT_STRTAB is not inside a PT_LOAD segment")

    result = {tag: [] for tag in wanted_tags}
    for tag, rel in offsets:
        start = strtab_offset + rel
        end = data.index(b"\x00", start)
        result[tag].append(data[start:end].decode("utf-8", "replace"))
    return result


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ------------------------------------------------------------------ helpers
    def _dep(self):
        return self.dependencies["sndio"]

    def _env(self):
        package = self._dep().package_folder
        env = os.environ.copy()
        lib_dir = os.path.join(package, "lib")
        bin_dir = os.path.join(package, "bin")
        old_ld = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = lib_dir + (":" + old_ld if old_ld else "")
        env["PATH"] = bin_dir + ":" + env.get("PATH", "")
        return env

    def _exec(self, argv, cwd=None):
        proc = subprocess.run(argv, cwd=cwd, env=self._env(),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, errors="replace")
        return proc.returncode, proc.stdout

    def _find_binary(self, name):
        for root, _dirs, files in os.walk(self.build_folder):
            if name in files:
                return os.path.join(root, name)
        raise ConanException(f"built test binary {name} not found under {self.build_folder}")

    # -------------------------------------------------------------------- test
    def test(self):
        if not can_run(self):
            raise ConanException(
                "test_package must execute on the OHOS target; a cross-only "
                "build cannot claim the package works")

        package = self._dep().package_folder
        shared = os.path.exists(os.path.join(package, "lib", "libsndio.so"))
        tool = lambda name: os.path.join(package, "bin", name)  # noqa: E731
        failures = []
        skipped = []  # environment-dependent checks that could not run

        def check(condition, what, detail=""):
            if condition:
                self.output.info(f"[ok]   {what}")
            else:
                self.output.error(f"[FAIL] {what} {detail}".rstrip())
                failures.append(what)

        # 1 -- real consumer program -------------------------------------
        # self.run() (env=None) inherits the runtime environment built by
        # _env() above, i.e. the package's own lib/ is what the loader sees.
        exe = self._find_binary("test_sndio")
        os.environ.update(self._env())
        rc = self.run(f'"{exe}"', ignore_errors=True, env=None)
        check(rc == 0, "consumer program links and runs against libsndio", f"rc={rc}")

        # 2 -- installed layout ------------------------------------------
        for relative in ("include/sndio.h", "lib/pkgconfig/sndio.pc",
                         "bin/aucat", "bin/sndiod", "bin/sndioctl", "bin/midicat"):
            check(os.path.exists(os.path.join(package, relative)), f"installed {relative}")
        if shared:
            for relative in ("lib/libsndio.so", "lib/libsndio.so.7", "lib/libsndio.so.7.3"):
                check(os.path.exists(os.path.join(package, relative)),
                      f"installed {relative}")
        else:
            check(os.path.exists(os.path.join(package, "lib", "libsndio.a")),
                  "installed lib/libsndio.a")

        # 3 + 4 -- ELF dynamic section: OHOS-specific soname check ---------
        # A static build has no dynamic section at all: assert DT_NEEDED only
        # for the shared configuration, and say so instead of silently passing.
        if not shared:
            skipped.append("ELF DT_NEEDED/DT_SONAME checks (static build has no dynamic section)")
        else:
            try:
                dyn = elf_dynamic_strings(exe, (ELF_DT_NEEDED,))
                needed = dyn[ELF_DT_NEEDED]
                self.output.info("DT_NEEDED of the consumer: " + ", ".join(needed))
                check(any(entry == "libsndio.so.7" for entry in needed),
                      "consumer records DT_NEEDED=libsndio.so.7 (soname propagated)",
                      f"got {needed}")
                check(not any("/" in entry for entry in needed),
                      "no DT_NEEDED entry contains a build path", f"got {needed}")
                soname = os.path.join(package, "lib", "libsndio.so.7.3")
                if os.path.exists(soname):
                    son = elf_dynamic_strings(soname, (ELF_DT_SONAME,))[ELF_DT_SONAME]
                    check(son == ["libsndio.so.7"],
                          "libsndio.so.7.3 carries DT_SONAME=libsndio.so.7", f"got {son}")
            except ConanException as error:
                self.output.error(f"[FAIL] ELF dynamic section check: {error}")
                failures.append("ELF dynamic section check")

        # 5 -- pkg-config metadata ----------------------------------------
        pc_path = os.path.join(package, "lib", "pkgconfig", "sndio.pc")
        if os.path.exists(pc_path):
            with open(pc_path, encoding="utf-8", errors="replace") as handle:
                pc = handle.read()
            check("prefix=${pcfiledir}" in pc,
                  "sndio.pc is relocatable (prefix=${pcfiledir})")
            check("-lsndio" in pc, "sndio.pc links -lsndio")
            # The Version: field is checkable without the pkg-config binary.
            expected = self.dependencies["sndio"].ref.version
            check(f"Version: {expected}" in pc, f"sndio.pc declares Version: {expected}")
            pkgconfig = os.path.join(package, "lib", "pkgconfig")
            env_path = self._env()
            env_path["PKG_CONFIG_PATH"] = pkgconfig
            try:
                proc = subprocess.run(["pkg-config", "--modversion", "sndio"],
                                      env=env_path, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True)
                self.output.info(f"pkg-config --modversion sndio: {proc.stdout.strip()}"
                                 f" (rc={proc.returncode})")
                expected = self.dependencies["sndio"].ref.version
                check(proc.returncode == 0 and proc.stdout.strip() == expected,
                      f"pkg-config resolves sndio {expected}", proc.stdout.strip())
            except FileNotFoundError:
                # Not a pass and not a failure: recorded so the run reports it.
                skipped.append("pkg-config --modversion (binary absent on this worker)")
                self.output.warning("SKIP: pkg-config --modversion (binary absent)")

        # 6 -- real data path: aucat off-line playback -> record ----------
        workdir = os.path.join(self.build_folder, "_offline")
        os.makedirs(workdir, exist_ok=True)
        raw_in = os.path.join(workdir, "in.raw")
        raw_out = os.path.join(workdir, "out.raw")
        if os.path.exists(raw_out):
            os.unlink(raw_out)
        # 8000 frames, mono, 16 bit: a 440 Hz square wave (audible amplitude)
        payload = b"".join(struct.pack("<h", 8000 if (i % 9) < 5 else -8000)
                           for i in range(8000))
        with open(raw_in, "wb") as handle:
            handle.write(payload)
        # `-e` takes a sample encoding (s8/u8/s16/s16le/...), `-h` the header
        # type (raw/wav/aiff/au) -- here both files are headerless s16 mono.
        rc = self.run(f'"{tool("aucat")}" -n -e s16 -h raw -r 8000 -c 1 '
                      f'-i "{raw_in}" -o "{raw_out}"',
                      ignore_errors=True, env=None, cwd=workdir)
        written = os.path.getsize(raw_out) if os.path.exists(raw_out) else 0
        data = b""
        if written:
            with open(raw_out, "rb") as handle:
                data = handle.read()
        expected_bytes = os.path.getsize(raw_in)
        self.output.info(f"aucat -n: rc={rc}, in={expected_bytes} B, out={written} B")
        check(rc == 0, "aucat off-line conversion succeeds", f"rc={rc}")
        check(written == expected_bytes,
              "aucat preserves the exact frame count (16000 B in -> 16000 B out)",
              f"{written} B")
        # Real signal check: int16 samples must keep the input's energy. A
        # single non-zero byte would pass a "not silence" test, an RMS floor
        # cannot. Input RMS is 8000 for the square wave below.
        samples = struct.unpack(f"<{len(data) // 2}h", data[:len(data) // 2 * 2])
        rms = (sum(sample * sample for sample in samples) / len(samples)) ** 0.5 if samples else 0.0
        self.output.info(f"output RMS = {rms:.0f} (input RMS 8000)")
        check(rms > 8000 * 0.9,
              "aucat output carries the input signal energy (RMS within 10%)",
              f"rms={rms:.0f}")
        # Strongest form: no resampling, no clipping, nothing dropped.
        check(data == payload,
              "aucat output is byte-identical to the input (no drop/dup/clip)")

        # 7 -- every installed tool executes -------------------------------
        for name, marker in (("aucat", "usage: aucat"),
                             ("sndiod", "usage: sndiod"),
                             ("sndioctl", "usage: sndioctl"),
                             ("midicat", "usage: midicat")):
            rc, output = self._exec([tool(name), "--atomcode-bogus-option"])
            check(rc != 0 and marker in output,
                  f"{name} runs and reports its usage string", f"rc={rc}")

        if skipped:
            self.output.warning(f"{len(skipped)} check(s) SKIPPED (environment): "
                                + "; ".join(skipped))
        if failures:
            raise ConanException(f"{len(failures)} sndio test(s) failed: "
                                 + "; ".join(failures))
        self.output.success(f"sndio: all HarmonyOS consumer tests passed "
                            f"({len(skipped)} environment skip(s))")
