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


def compile_and_link_api_probe(pkg, cc, run_binary):
    autotrace_cflags = pkg_config_flags(["--cflags", "autotrace"])
    autotrace_libs = pkg_config_flags(["--static", "--libs", "autotrace"])

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
                *autotrace_cflags,
                source,
                *autotrace_libs,
                "-o",
                output,
            ],
            check=True,
        )
        require_path("linked API probe", output)
        if run_binary == "1":
            subprocess.run([output], check=True)


def run_cli_version(exe):
    result = subprocess.run(
        [exe, "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
    )
    if "0.31.10" not in result.stdout:
        raise AssertionError(f"unexpected autotrace version output: {result.stdout}")


def run_png_to_svg(exe):
    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "watch.png")
    require_path("upstream PNG fixture", fixture)
    with tempfile.TemporaryDirectory() as tmpdir:
        output = os.path.join(tmpdir, "watch.svg")
        subprocess.run(
            [
                exe,
                "-report-progress",
                "--centerline",
                "--background-color",
                "ffffff",
                "--color-count",
                "2",
                "--preserve-width",
                "-input-format",
                "PNG",
                fixture,
                "-output-format",
                "svg",
                "-output-file",
                output,
            ],
            check=True,
            timeout=30,
        )
        require_path("PNG to SVG output", output)
        if os.path.getsize(output) == 0:
            raise AssertionError("PNG to SVG output is empty")
        require_text(output, "<svg")


def run_missing_input_failure(exe):
    result = subprocess.run(
        [exe, "-input-format", "PNG", "missing-input.png", "-output-format", "svg"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode == 0:
        raise AssertionError(
            "autotrace unexpectedly accepted a missing PNG input: "
            f"{result.stdout}"
        )


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
    compile_and_link_api_probe(pkg, cc, run_binary)
    if run_binary == "1":
        run_cli_version(exe)
        run_png_to_svg(exe)
        run_missing_input_failure(exe)

    print(
        "PASS: autotrace package, linked C API, PNG-to-SVG conversion, "
        "and missing-input failure behavior are valid"
    )


if __name__ == "__main__":
    main()
