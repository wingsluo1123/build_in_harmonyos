#!/usr/bin/env python3
"""Conan consumer test for typeshare 1.13.4.

Layers of assertions:

  A. Generic consumer smoke/functional test — runs the packaged `typeshare`:
       A1 `typeshare --version` exits 0 and reports 1.13.4
       A2 `typeshare --help` exits 0 and lists the stable `--lang` values
       A3 `typeshare <src> -l typescript -o out.ts` produces a TypeScript file
          declaring the annotated struct
       A4 `typeshare <src> -l swift -o out.swift` produces Swift output
       A5 `typeshare <src> -l kotlin -o out.kt` produces Kotlin output
       A6 `typeshare <src> -l scala -o out.scala` produces Scala output
       A7 `typeshare --generate-config -c <file> <src>` writes a `typeshare.toml`
          template containing the `[typescript.type_mappings]` / `[scala]`
          sections

  B. HarmonyOS-specific (鸿蒙特有) assertions — verify the platform traits that
     make the artifact usable on OHOS at all:
       B1. ELF machine is AArch64 (the OHOS PC target)
       B2. PT_INTERP is the OHOS musl loader (ld-musl-aarch64.so.1)
       B3. the binary carries an OHOS code signature — HarmonyOS refuses to
           execve unsigned ELF (EACCES errno 13), so this is mandatory
       B4. the binary is a non-empty regular executable file

Every assertion is reported on its own line so the counts quoted in the PR
description stay auditable.
"""

import os
import struct
import subprocess
import sys
import tempfile

PASSED = 0
FAILED = 0

OHOS_MUSL_LOADER = "ld-musl-aarch64.so.1"
EM_AARCH64 = 183

# A source file exercising the parser: a struct, an enum and a type alias with
# the `#[typeshare]` attribute used by the upstream snapshot fixtures.
RUST_INPUT = """\
#[typeshare]
pub struct Sample {
    pub name: String,
    pub count: u32,
    pub tags: Vec<String>,
}

#[typeshare]
pub enum SampleKind {
    Alpha,
    Beta,
}
"""

EXPECTATIONS = {
    "typescript": ("out.ts", "interface Sample"),
    "swift": ("out.swift", "struct Sample"),
    "kotlin": ("out.kt", "data class Sample"),
    # Scala generation requires an explicit package: without it upstream
    # `core/src/language/scala.rs` panics with "package name must be provided".
    "scala": ("out.scala", "case class Sample", ["--scala-package",
                                                 "com.typeshare.consumer"]),
}


def check(name, ok, detail=""):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"[ok] {name}{(': ' + detail) if detail else ''}")
    else:
        FAILED += 1
        print(f"[fail] {name}{(': ' + detail) if detail else ''}", file=sys.stderr)
    return ok


def elfinfo(path):
    """Return (e_machine, interp) or (None, None) when unreadable."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return None, None
    if data[:4] != b"\x7fELF":
        return None, None
    e_machine = struct.unpack_from("<H", data, 18)[0]
    phoff = struct.unpack_from("<Q", data, 0x20)[0]
    phentsize = struct.unpack_from("<H", data, 0x36)[0]
    phnum = struct.unpack_from("<H", data, 0x38)[0]
    interp = None
    for i in range(phnum):
        off = phoff + i * phentsize
        if struct.unpack_from("<I", data, off)[0] == 3:  # PT_INTERP
            p_offset = struct.unpack_from("<Q", data, off + 8)[0]
            p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
            interp = (data[p_offset:p_offset + p_filesz]
                      .rstrip(b"\x00").decode("utf-8", "replace"))
            break
    return e_machine, interp


def main():
    package_folder = os.environ.get("PACKAGE_FOLDER", "")
    exe = os.path.join(package_folder, "bin", "typeshare")

    # ── B. 鸿蒙特有测试 (HarmonyOS-specific) ──
    print("== 鸿蒙特有测试 / HarmonyOS-specific assertions ==")
    if not check("B4: typeshare is a non-empty regular executable file",
                 os.path.isfile(exe) and os.path.getsize(exe) > 0,
                 f"{exe} ({os.path.getsize(exe) if os.path.isfile(exe) else 0} bytes)"):
        raise AssertionError(f"Missing typeshare executable: {exe}")

    e_machine, interp = elfinfo(exe)
    check("B1: ELF machine is AArch64 (EM_AARCH64=183)",
          e_machine == EM_AARCH64, f"e_machine={e_machine}")

    check(f"B2: PT_INTERP is the OHOS musl loader ({OHOS_MUSL_LOADER})",
          interp is not None and OHOS_MUSL_LOADER in interp, f"interp={interp}")

    with open(exe, "rb") as fh:
        payload = fh.read()
    check("B3: OHOS code signature present (unsigned ELF cannot execve)",
          b"codesign" in payload)

    # ── A. 通用消费者冒烟/功能测试 ──
    print("== 消费者冒烟测试 / consumer smoke test ==")
    version_run = subprocess.run([exe, "--version"], capture_output=True,
                                 text=True, timeout=30)
    check("A1: `typeshare --version` exits 0 and reports 1.13.4",
          version_run.returncode == 0 and "1.13.4" in version_run.stdout,
          f"rc={version_run.returncode} out={version_run.stdout.strip()[:80]}")

    help_run = subprocess.run([exe, "--help"], capture_output=True,
                              text=True, timeout=30)
    langs = ("kotlin", "scala", "swift", "typescript")
    check("A2: `typeshare --help` exits 0 and lists kotlin/scala/swift/typescript",
          help_run.returncode == 0
          and all(lang in help_run.stdout for lang in langs),
          f"rc={help_run.returncode}")

    with tempfile.TemporaryDirectory(prefix="typeshare-tp-") as work:
        src = os.path.join(work, "src")
        os.makedirs(src, exist_ok=True)
        with open(os.path.join(src, "sample.rs"), "w", encoding="utf-8") as fh:
            fh.write(RUST_INPUT)

        for idx, (lang, spec) in enumerate(EXPECTATIONS.items()):
            out_name, needle = spec[0], spec[1]
            extra = spec[2] if len(spec) > 2 else []
            out = os.path.join(work, out_name)
            run = subprocess.run([exe, src, "-l", lang, "-o", out] + extra,
                                 capture_output=True, text=True, timeout=60)
            content = ""
            if os.path.isfile(out):
                with open(out, encoding="utf-8") as fh:
                    content = fh.read()
            check(f"A{3 + idx}: `typeshare -l {lang}` generates {out_name} "
                  f"declaring the struct",
                  run.returncode == 0 and needle in content,
                  f"rc={run.returncode} bytes={len(content)}")

        # `--generate-config` still requires a source directory argument
        # (clap: `directories` is `required = true`); the template is written
        # next to `--config-file` (default ./typeshare.toml).
        cfg = os.path.join(work, "typeshare.toml")
        cfg_run = subprocess.run([exe, "--generate-config", "-c", cfg, src],
                                 capture_output=True, text=True, timeout=30)
        cfgtxt = ""
        if os.path.isfile(cfg):
            with open(cfg, encoding="utf-8") as fh:
                cfgtxt = fh.read()
        check("A7: `typeshare --generate-config` writes a typeshare.toml template",
              cfg_run.returncode == 0
              and "[typescript.type_mappings]" in cfgtxt
              and "[scala]" in cfgtxt,
              f"rc={cfg_run.returncode} bytes={len(cfgtxt)}")

    print(f"SUMMARY: executed={PASSED + FAILED} passed={PASSED} "
          f"failed={FAILED} (harmonyos_specific=4)")
    if FAILED:
        raise AssertionError(f"{FAILED} assertion(s) failed")
    print("typeshare test_package OK: HarmonyOS traits + code generation verified")


if __name__ == "__main__":
    sys.exit(main())
