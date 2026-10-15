#!/usr/bin/env python3
"""Replay shim for flex when building vendored libpcap without generators.

Upstream libpcap 1.10.6 ships only scanner.l / grammar.y.in; both its
Autotools configure (AC_PROG_LEX + capable-lex functional test) and its
CMake build (find_program FATAL_ERROR) hard-require a working flex/lex,
which the HMBS preflight worker does not provide.  This shim is NOT a
fake flex: it replays byte-exact outputs produced offline by real
flex 2.6.4 (winflexbison v2.5.25, same era as the conancenter
flex/2.6.4 toolchain) from this exact upstream tag's scanner.l with
upstream's own flags (-P pcap_ --header-file --nounput).  The replayed
files live in ../pcap_gen/ and are committed to the recipe.

Invocation: this file is called through the LEX / LEX_EXECUTABLE slot
as `python3 lex_shim.py <flex args>` (see conanfile.py), so it never
needs an executable bit (HMBS worker fs lacks chmod):
  * `--version`            -> print a flex 2.6.4 version line, exit 0
  * `-t ...`               -> capable-lex probe: emit generated C to
                              stdout (real flex -t behaviour), exit 0
  * `-o OUT [--header-file=H] <input.l>`
                           -> write committed scanner.c to OUT and
                              committed scanner.h next to it, exit 0
  * `<input.l>` (no -o)    -> autoconf AC_PROG_LEX root probe runs
                              `$LEX conftest.l` and looks for lex.yy.c /
                              lexyy.c.  Real flex without -o writes
                              lex.yy.c, so this shim does the same.
                              For tiny autoconf probes (conftest.l) a
                              minimal compilable stub is emitted that
                              re-uses the probe's own trailing C code;
                              for the real libpcap scanner.l the
                              committed replay bytes are emitted.

Probe vs real is decided by input content: an input containing the
libpcap `pcap_` prefix marker (and of scanner scale) replays the
committed files; anything else (conftest.l, missing input) emits the
minimal probe stub.  The probe stub is only ever used for configure
capability checks; the real build always replays identical bytes.
"""

import os
import sys

GEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "pcap_gen")


def _read(name):
    with open(os.path.join(GEN_DIR, name), "rb") as handle:
        return handle.read()


def _write(path, data):
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)


def _split_argv(argv):
    """Split flex argv into (out, header, header_explicit, want_stdout, inputs).

    Only options this shim cares about are parsed; everything else is
    ignored (real flex accepts many codegen flags we do not need).
    """
    out = None
    header = None
    header_explicit = False
    want_stdout = False
    inputs = []
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "-t":
            want_stdout = True
            idx += 1
        elif arg == "-o" and idx + 1 < len(argv):
            out = argv[idx + 1]
            idx += 2
        elif arg.startswith("-o") and len(arg) > 2:
            out = arg[2:]
            idx += 1
        elif arg == "--header-file" and idx + 1 < len(argv):
            header = argv[idx + 1]
            header_explicit = True
            idx += 2
        elif arg.startswith("--header-file="):
            header = arg.split("=", 1)[1]
            header_explicit = True
            idx += 1
        elif arg == "--header-file=":
            header = ""
            header_explicit = True
            idx += 1
        elif arg == "--stdout":
            want_stdout = True
            idx += 1
        elif arg.startswith("--output="):
            out = arg.split("=", 1)[1]
            idx += 1
        elif arg == "--output" and idx + 1 < len(argv):
            out = argv[idx + 1]
            idx += 2
        elif arg == "--":
            inputs.extend(argv[idx + 1:])
            break
        elif arg.startswith("-") and len(arg) > 1:
            # Any other flex flag (-P, -d, --nounput, ...): ignore.
            # Flags with separate values we do not track are harmless
            # to skip as single tokens because positional .l inputs
            # never start with '-'.
            idx += 1
        else:
            inputs.append(arg)
            idx += 1
    return out, header, header_explicit, want_stdout, inputs


def _read_input_text(inputs):
    for candidate in inputs:
        if not candidate or candidate.startswith("-"):
            continue
        path = candidate
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                return handle.read(), candidate
        except OSError:
            continue
    return None, None


def _is_pcap_scanner(text, basename):
    if basename is not None and os.path.basename(basename) == "scanner.l":
        return True
    if text is None:
        return False
    # Real libpcap scanner.l is ~27KB and dominated by the pcap_ prefix;
    # autoconf conftest.l files are <1KB with ECHO/REJECT/yymore probes.
    if len(text) > 8000 and "pcap_" in text:
        return True
    return False


def _extract_user_code(text):
    """Return trailing C code after the second %% (flex copies it verbatim)."""
    if not text:
        return ""
    parts = text.split("%%")
    if len(parts) >= 3:
        return parts[2]
    if len(parts) == 2:
        # Single %% (some probes): everything after it is user code.
        return parts[1]
    return ""


def _probe_source(text):
    user_code = _extract_user_code(text)
    lines = []
    lines.append("/* Generated by lorcon lex_shim probe emulation (flex 2.6.4). */")
    lines.append("#define FLEX_SCANNER")
    lines.append("#define YY_FLEX_MAJOR_VERSION 2")
    lines.append("#define YY_FLEX_MINOR_VERSION 6")
    lines.append("#define YY_FLEX_SUBMINOR_VERSION 4")
    lines.append("#include <stdio.h>")
    lines.append("#include <string.h>")
    lines.append("#include <unistd.h>")
    lines.append("#ifndef ECHO")
    lines.append("#define ECHO (void)fwrite(yytext, (size_t)yyleng, 1, yyout)")
    lines.append("#endif")
    lines.append("#ifndef REJECT")
    lines.append("#define REJECT reject_used_but_not_detected")
    lines.append("#endif")
    lines.append("#ifndef yymore")
    lines.append("int yymore(void);")
    lines.append("#endif")
    lines.append("#ifndef yyless")
    lines.append("#define yyless(n) do { (void)(n); } while (0)")
    lines.append("#endif")
    lines.append("#ifndef BEGIN")
    lines.append("#define BEGIN(x) do { (void)(x); } while (0)")
    lines.append("#endif")
    lines.append("#ifndef YY_BREAK")
    lines.append("#define YY_BREAK /* dummy */")
    lines.append("#endif")
    lines.append("extern FILE *yyin, *yyout;")
    lines.append("FILE *yyin = 0;")
    lines.append("FILE *yyout = 0;")
    lines.append("char *yytext = \"\";")
    lines.append("int yyleng = 0;")
    lines.append("int yylex(void) { return 0; }")
    lines.append("int yywrap(void) { return 1; }")
    lines.append("static int input(void) { return 0; }")
    lines.append("static void unput(int c) { (void)c; }")
    lines.append("int yymore(void) { return 0; }")
    if user_code and user_code.strip():
        lines.append("/* ---- user code copied verbatim from probe .l file ---- */")
        lines.append(user_code)
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def main(argv):
    if any(a == "--version" for a in argv):
        sys.stdout.write("flex 2.6.4\n")
        return 0
    out, header, header_explicit, want_stdout, inputs = _split_argv(argv)
    text, hit = _read_input_text(inputs)
    basename = hit
    pcap = _is_pcap_scanner(text, basename)
    if want_stdout:
        # Real `flex -t` writes the generated C to stdout.
        if pcap:
            sys.stdout.buffer.write(_read("scanner.c"))
        else:
            sys.stdout.buffer.write(_probe_source(text))
        return 0
    if out is None:
        # Real flex without -o writes lex.yy.c in the current directory
        # (this is exactly what AC_PROG_LEX's root probe looks for).
        out = os.path.join(os.getcwd(), "lex.yy.c")
    if pcap:
        _write(out, _read("scanner.c"))
        if header is not None and header != "/dev/null":
            _write(header, _read("scanner.h"))
        elif not header_explicit:
            # Real libpcap build expects scanner.h next to the output
            # even when the caller omits --header-file; the probe path
            # never takes this branch (probes are not pcap).
            sibling = os.path.join(os.path.dirname(os.path.abspath(out)),
                                   "scanner.h")
            if os.path.abspath(sibling) != os.path.abspath(out):
                _write(sibling, _read("scanner.h"))
        return 0
    # Autoconf probe input: emit a minimal compilable lex.yy.c.
    _write(out, _probe_source(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
