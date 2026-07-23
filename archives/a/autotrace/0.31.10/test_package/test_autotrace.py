#!/usr/bin/env python3
"""Validate autotrace package layout and public API."""
import os
import subprocess
import sys
import tempfile
import textwrap


def require_path(name, path):
    if not os.path.exists(path):
        raise AssertionError(f"missing {name}: {path}")


def require_text(path, *needles):
    with open(path, "r", encoding="utf-8") as handle:
        content = handle.read()
    missing = [needle for needle in needles if needle not in content]
    if missing:
        raise AssertionError(f"{path} is missing expected text: {missing}")


def pkg_config_flags(args):
    result = subprocess.run(
        ["pkg-config", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"pkg-config {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.split()


def compile_and_link_api_probe(pkg, cc):
    include_dir = os.path.join(pkg, "include")
    lib_dir = os.path.join(pkg, "lib")
    glib_modules = ["glib-2.0", "gmodule-2.0", "gthread-2.0", "gobject-2.0"]
    glib_cflags = pkg_config_flags(["--cflags", *glib_modules])
    glib_libs = pkg_config_flags(["--libs", *glib_modules])

    with tempfile.TemporaryDirectory() as tmpdir:
        source = os.path.join(tmpdir, "autotrace_api_probe.c")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write(
                textwrap.dedent(
                    """
                    #include <string.h>
                    #include <autotrace/autotrace.h>

                    int main(void)
                    {
                        autotrace_init();
                        const char *version = at_version(0);
                        if (!version || strcmp(version, "0.31.10") != 0) {
                            return 1;
                        }

                        at_color *white = at_color_new(255, 255, 255);
                        if (!white || !at_color_equal(white, white)) {
                            return 2;
                        }

                        at_bitmap *bitmap = at_bitmap_new(1, 1, 3);
                        if (!bitmap || at_bitmap_get_width(bitmap) != 1 ||
                            at_bitmap_get_height(bitmap) != 1 ||
                            at_bitmap_get_planes(bitmap) != 3) {
                            return 3;
                        }

                        at_bitmap_free(bitmap);
                        at_color_free(white);
                        return 0;
                    }
                    """
                )
            )
        output = os.path.join(tmpdir, "autotrace_api_probe")
        subprocess.run(
            [
                cc,
                "-I",
                include_dir,
                *glib_cflags,
                source,
                "-L",
                lib_dir,
                "-lautotrace",
                *glib_libs,
                "-lm",
                "-o",
                output,
            ],
            check=True,
        )
        require_path("linked API probe", output)


def run_cli_version(exe):
    result = subprocess.run(
        [exe, "-version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
    )
    if "0.31.10" not in result.stdout:
        raise AssertionError(f"unexpected autotrace version output: {result.stdout}")


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: test_autotrace.py <package-folder> <c-compiler> <run-binary-flag>")

    pkg, cc, run_binary = sys.argv[1:]
    exe = os.path.join(pkg, "bin", "autotrace")
    header = os.path.join(pkg, "include", "autotrace", "autotrace.h")
    library = os.path.join(pkg, "lib", "libautotrace.a")
    pc = os.path.join(pkg, "lib", "pkgconfig", "autotrace.pc")

    for name, path in (
        ("autotrace CLI", exe),
        ("autotrace header", header),
        ("autotrace library", library),
        ("autotrace pkgconfig", pc),
    ):
        require_path(name, path)

    require_text(pc, "Name: autotrace", "Version: 0.31.10", "-lautotrace")
    compile_and_link_api_probe(pkg, cc)
    if run_binary == "1":
        run_cli_version(exe)

    print("PASS: autotrace CLI metadata and linked C API consumer are valid")


if __name__ == "__main__":
    main()
