#!/usr/bin/env bash
#--------------------------------------------------------------------
# Consumer test for sfront 0.99 - runs the packaged bin/sfront.
#
# Usage: bash test_sfront.sh <package-folder> <work-dir> <cc>
#
# Groups:
#   A  the delivered artifact really is an AArch64 executable
#   B  upstream command-line surface (-help / -license / no args / bad option)
#   C  all 26 upstream example orchestras shipped in share/sfront/examples
#   D  upstream mp4test flow: encode to an MP4-SA bitstream and decode it back
#   E  diagnostics for malformed input
#   F  HarmonyOS-specific: compile generated C programs with the OHOS toolchain,
#      run the resulting AArch64 binaries and validate the audio they synthesise,
#      including the upstream bitstream-vs-orchestra audio comparison
#   G  shipped payload completeness (SAOL library, examples, manual, licences)
#
# Upstream ships no automated test suite at all (no tests/ directory, no `make
# check`); its executable specification is examples/, which is what C, D and F
# drive. Each row of EXAMPLES below mirrors the first `$(SFRONT)` line of that
# example's own Makefile, minus the options that need hardware or a peer on the
# network (-aout/-ain <soundcard>, -session/-passphrase). examples/rtime/linbuzz
# is the one example that cannot be translated here: it #includes <Slib/*.hs> and
# therefore needs `-cpp`, which upstream hard-codes to the external program `gcc`
# plus the compile-time constant SAOLLIBDIR="/usr/share/sfront"
# (sfmain.c:cppsystemcall). Neither exists in the OHOS toolchain, so -cpp is
# unavailable on this platform; notes.md records it.
#--------------------------------------------------------------------
set -uo pipefail

PKG="${1:?usage: test_sfront.sh <package-folder> <work-dir> <cc>}"
WORK="${2:?usage: test_sfront.sh <package-folder> <work-dir> <cc>}"
CC="${3:?usage: test_sfront.sh <package-folder> <work-dir> <cc>}"

SFRONT="$PKG/bin/sfront"
SHARE="$PKG/share/sfront"
EX="$SHARE/examples"
LIB="$SHARE/lib"

# The delivered translator is statically linked, so it starts both natively on an
# AArch64 worker and under qemu user mode on an x86 build host. A missing emulator
# is a failure, never a silent skip.
case "$(uname -m)" in
    aarch64|arm64)
        run_sf() { "$SFRONT" "$@"; }
        run_ohos() { "$@"; }
        ;;
    *)
        QEMU="$(command -v qemu-aarch64 || true)"
        if [ -z "$QEMU" ]; then
            echo "FAIL: qemu-aarch64 is required to run the AArch64 package on $(uname -m)"
            exit 1
        fi
        run_sf() { "$QEMU" "$SFRONT" "$@"; }
        run_ohos() { "$QEMU" "$@"; }
        ;;
esac

# python3 parses the rendered WAV headers; without it the render assertions could
# not be evaluated at all, so treat its absence as a hard failure.
if ! command -v python3 > /dev/null 2>&1; then
    echo "FAIL: python3 is required to validate the rendered WAV files"
    exit 1
fi

# Plain mkdir instead of mktemp -d: a 0700 temp dir is not writable on HMDFS
# (UID mapping, knowledge base E011).
rm -rf "$WORK"
mkdir -p "$WORK"

pass=0
fail=0
ok() { pass=$((pass + 1)); echo "PASS: $1"; }
bad() {
    fail=$((fail + 1))
    echo "FAIL: $1"
    # Never dump binaries (rendered WAV files): grep -I keeps text diagnostics only.
    if [ -n "${2:-}" ] && [ -f "$2" ] && grep -qI . "$2" 2>/dev/null; then
        echo "--- $(basename "$2")"; head -25 "$2"; echo "--- end"
    fi
}

# === A. the delivered artifact ========================================
if [ -x "$SFRONT" ]; then
    ok "packaged bin/sfront exists and is executable"
else
    echo "FAIL: packaged bin/sfront missing or not executable: $SFRONT"
    exit 1
fi
# e_machine lives at offset 18 of the ELF header; EM_AARCH64 is 0xB7.
emachine=$(od -An -tx1 -j18 -N2 "$SFRONT" | tr -d ' \n')
if [ "$emachine" = "b700" ]; then
    ok "packaged bin/sfront is an AArch64 (EM_AARCH64) executable"
else
    bad "packaged bin/sfront is an AArch64 executable (e_machine=$emachine)" "$SFRONT"
fi

# === B. upstream command-line surface ================================
help_txt="$WORK/help.txt"
run_sf -help > "$help_txt" 2>&1
if grep -qF "sfront, a SAOL to C translator. Version 0.99 08/30/11." "$help_txt" \
        && grep -qF "Usage: sfront [options]" "$help_txt"; then
    ok "-help prints the 0.99 banner and the usage synopsis"
else
    bad "-help prints the 0.99 banner and the usage synopsis" "$help_txt"
fi
if grep -qF "[-orc f1 [f2 ...]]" "$help_txt" && grep -qF "[-bit mp4file]" "$help_txt" \
        && grep -qF "[-bitout" "$help_txt" && grep -qF "[-o cfile]" "$help_txt" \
        && grep -qF "[-ain fname.wav]" "$help_txt" \
        && grep -qF "[-aout fname.wav]" "$help_txt" \
        && grep -qF "[-cin linmidi]" "$help_txt"; then
    ok "-help documents -orc / -bit / -bitout / -o / -ain / -aout / -cin"
else
    bad "-help documents -orc / -bit / -bitout / -o / -ain / -aout / -cin" "$help_txt"
fi

lic_txt="$WORK/license.txt"
run_sf -license > "$lic_txt" 2>&1
if grep -qF "Copyright (c) 1999-2006, Regents of the University of California" "$lic_txt" \
        && grep -qF "Neither the name of the University of California, Berkeley" "$lic_txt"; then
    ok "-license prints the 3-clause UC Berkeley BSD notice"
else
    bad "-license prints the 3-clause UC Berkeley BSD notice" "$lic_txt"
fi

noargs_txt="$WORK/noargs.txt"
run_sf > "$noargs_txt" 2>&1
noargs_rc=$?
if [ "$noargs_rc" -ne 0 ] && grep -qF "Usage: sfront [options]" "$noargs_txt"; then
    ok "no arguments prints the usage synopsis and exits non-zero (rc=$noargs_rc)"
else
    bad "no arguments prints the usage synopsis and exits non-zero (rc=$noargs_rc)" "$noargs_txt"
fi

opt_txt="$WORK/badopt.txt"
run_sf -nosuchoption > "$opt_txt" 2>&1
opt_rc=$?
if [ "$opt_rc" -ne 0 ] \
        && grep -qF "Command-line option -nosuchoption unknown or incorrectly used." "$opt_txt"; then
    ok "an unknown option is rejected with a diagnostic (rc=$opt_rc)"
else
    bad "an unknown option is rejected with a diagnostic (rc=$opt_rc)" "$opt_txt"
fi

# === C. every upstream example orchestra =============================
# "example-subdir|orchestra-file|extra sfront args", mirroring each example's own
# Makefile invocation (soundcard and network options omitted, see the header).
EXAMPLES="min|min.saol|-sco min.sasl
bach|bach.saol|-sco bach.sasl -midi bach.mid
beat|beat.saol|-fixedseed -sco beat.sasl
claps|claps.saol|-fixedseed -sco claps.sasl
elpelele|elpelele.saol|-sco elpelele.sasl -midi elpelele.mid
gliss|gliss.saol|-cin gliss
in|in.saol|
pc|pc.saol|-fixedseed -sco pc.sasl
perc|perc.saol|-sco perc.sasl -midi perc.mid
scr1|scr1.saol|-sco scr1.sasl -midi scr1.mid
speedt|speedt.saol|-sco speedt.sasl
torvalds|torvalds.saol|
vowels|vowels.saol|-fixedseed -sco vowels.sasl
rtime/aatest|aatest.saol|-sco aatest.sasl -midi aatest.mid
rtime/ascii|ascii.saol|-sco ascii.sasl -cin ascii
rtime/au/hiss|hiss.saol|
rtime/au/lpf|lpf.saol|
rtime/au/sin|sin.saol|
rtime/linain|linain.saol|-latency 0.002 -sco linain.sasl
rtime/linmidi|linmidi.saol|-sco linmidi.sasl -cin linmidi
rtime/linvoc|linvoc.saol|-sco linvoc.sasl -cin linmidi
rtime/network/mirror|mirror.saol|-sco mirror.sasl -cin ascii
rtime/network/nmp_audio|nmp.saol|-sco nmp.sasl -cin ascii
rtime/network/nmp_null|silence.saol|-sco silence.sasl -cin ascii
rtime/network/nmp_stream|stream.saol|-sco stream.sasl -cin fstr -mstr bach.mid"

translated=0
while IFS='|' read -r sub orc extra; do
    [ -z "${sub:-}" ] && continue
    d="$WORK/c-$sub"
    rm -rf "$d"; mkdir -p "$d"
    cp -r "$EX/$sub/." "$d/" 2>/dev/null
    # shellcheck disable=SC2086
    ( cd "$d" && run_sf -orc "$orc" $extra -o out.c ) > "$d/translate.log" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ] || [ ! -s "$d/out.c" ] || ! grep -qF "int main" "$d/out.c"; then
        bad "examples/$sub translates to a C program (rc=$rc)" "$d/translate.log"
        continue
    fi
    translated=$((translated + 1))
    ok "examples/$sub translates to a $(wc -c < "$d/out.c")-byte C program"
done <<EOF
$EXAMPLES
EOF

if [ "$translated" -eq 25 ]; then
    ok "all 25 translatable upstream example orchestras succeeded (rtime/linbuzz needs -cpp, see notes.md)"
else
    bad "all 25 translatable upstream example orchestras succeeded (got $translated)"
fi

# The control-driver selection must reach the generated program, not just the CLI.
if grep -qF "ascii control driver" "$WORK/c-rtime/ascii/out.c" 2>/dev/null; then
    ok "-cin ascii embeds the ASCII keyboard MIDI control driver in the program"
else
    bad "-cin ascii embeds the ASCII keyboard MIDI control driver in the program" \
        "$WORK/c-rtime/ascii/out.c"
fi
if grep -qF "linmidi control driver" "$WORK/c-rtime/linvoc/out.c" 2>/dev/null; then
    ok "-cin linmidi embeds the Linux OSS MIDI control driver in the program"
else
    bad "-cin linmidi embeds the Linux OSS MIDI control driver in the program" \
        "$WORK/c-rtime/linvoc/out.c"
fi

# An orchestra written by hand, in the inline-instrument form the book uses.
d="$WORK/c-inline"
rm -rf "$d"; mkdir -p "$d"
cat > "$d/tone.saol" <<'EOF_SAOL'
// instr tone - plays a 1 kHz sine wave (inline instrument form)
instr tone ()
{
  asig x, y, init;
  if (init == 0)
    {
      init = 1;
      x = 0.5;
    }
  x = x - 0.196307*y;
  y = y + 0.196307*x;
  output(y);
}
EOF_SAOL
cat > "$d/tone.sasl" <<'EOF_SASL'
0.25 tone 4.0
4.50 end
EOF_SASL
( cd "$d" && run_sf -orc tone.saol -sco tone.sasl -o out.c ) > "$d/translate.log" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && [ -s "$d/out.c" ] && grep -qF "int main" "$d/out.c"; then
    ok "a hand-written inline-instrument orchestra translates ($(wc -c < "$d/out.c") bytes of C)"
else
    bad "a hand-written inline-instrument orchestra translates (rc=$rc)" "$d/translate.log"
fi

# === D. MP4-SA bitstream encode/decode (upstream mp4test flow) ======
# bitstream <label> <example-subdir> <orchestra> <extra args...>
bitstream() {
    _label="$1"; _sub="$2"; _orc="$3"; shift 3
    _d="$WORK/d-$_label"
    rm -rf "$_d"; mkdir -p "$_d"
    cp -r "$EX/$_sub/." "$_d/" 2>/dev/null
    ( cd "$_d" && run_sf -orc "$_orc" "$@" -o orc.c ) > "$_d/orc.log" 2>&1
    ( cd "$_d" && run_sf -orc "$_orc" "$@" -bitout bit.mp4 ) > "$_d/bitout.log" 2>&1
    _rc=$?
    if [ "$_rc" -ne 0 ] || [ ! -s "$_d/bit.mp4" ]; then
        bad "$_label encodes an MP4-SA bitstream (rc=$_rc)" "$_d/bitout.log"
        return
    fi
    ok "$_label encodes a $(wc -c < "$_d/bit.mp4")-byte MP4-SA bitstream"
    _start=$(od -An -tx1 -N1 "$_d/bit.mp4" | tr -d ' \n')
    if [ "$_start" = "80" ]; then
        ok "$_label bitstream starts with the 0x80 BIFS start code"
    else
        bad "$_label bitstream starts with the 0x80 BIFS start code (got $_start)" "$_d/bitout.log"
    fi
    ( cd "$_d" && run_sf -bit bit.mp4 -o frombit.c ) > "$_d/bit.log" 2>&1
    _rc=$?
    _orc_size=$(wc -c < "$_d/orc.c" 2>/dev/null || echo 0)
    _bit_size=$(wc -c < "$_d/frombit.c" 2>/dev/null || echo 0)
    if [ "$_rc" -eq 0 ] && grep -qF "int main" "$_d/frombit.c" 2>/dev/null \
            && [ "$_bit_size" -gt $((_orc_size / 2)) ] && [ "$_bit_size" -lt $((_orc_size * 2)) ]; then
        ok "$_label bitstream decodes back to an equivalent program ($_orc_size -> $_bit_size bytes of C)"
    else
        bad "$_label bitstream decodes back to an equivalent program (rc=$_rc, $_orc_size -> $_bit_size bytes)" \
            "$_d/bit.log"
    fi
}

bitstream "min" "min" "min.saol" -sco min.sasl
bitstream "bach" "bach" "bach.saol" -sco bach.sasl -midi bach.mid

# -symtab adds the symbol table to the bitstream and must not break decoding.
d="$WORK/d-symtab"
rm -rf "$d"; mkdir -p "$d"
cp -r "$EX/min/." "$d/" 2>/dev/null
( cd "$d" && run_sf -orc min.saol -sco min.sasl -bitout plain.mp4 ) > "$d/plain.log" 2>&1
( cd "$d" && run_sf -symtab -orc min.saol -sco min.sasl -bitout sym.mp4 ) > "$d/sym.log" 2>&1
sym_rc=$?
( cd "$d" && run_sf -bit sym.mp4 -o sym.c ) > "$d/decode.log" 2>&1
decode_rc=$?
plain_size=$(wc -c < "$d/plain.mp4" 2>/dev/null || echo 0)
sym_size=$(wc -c < "$d/sym.mp4" 2>/dev/null || echo 0)
if [ "$sym_rc" -eq 0 ] && [ "$decode_rc" -eq 0 ] && [ -s "$d/sym.c" ] \
        && grep -qF "int main" "$d/sym.c" && [ "$sym_size" -gt "$plain_size" ]; then
    ok "-symtab grows the bitstream ($plain_size -> $sym_size bytes) and it still decodes"
else
    bad "-symtab grows the bitstream ($plain_size -> $sym_size bytes) and it still decodes (sym rc=$sym_rc, decode rc=$decode_rc)" \
        "$d/sym.log"
fi

# === E. diagnostics for malformed input =============================
d="$WORK/e-bad"
rm -rf "$d"; mkdir -p "$d"
cat > "$d/broken.saol" <<'EOF_SAOL'
saol {
  global { aosc gains; }
  partial osc halfdeclared {
    thisOUT outsig nowhere;
EOF_SAOL
( cd "$d" && run_sf -orc broken.saol -o broken.c ) > "$d/bad.log" 2>&1
rc=$?
if [ "$rc" -ne 0 ] && grep -qF "Error occured near line" "$d/bad.log"; then
    ok "a malformed orchestra is rejected with a line-accurate diagnostic (rc=$rc)"
else
    bad "a malformed orchestra is rejected with a line-accurate diagnostic (rc=$rc)" "$d/bad.log"
fi

# === F. HarmonyOS-specific end-to-end cases ==========================
# wav_info <file> -> "<channels> <rate> <bits> <frames> <nonzero> <peak>"
#                   or NOT-RIFF / NO-FMT / NOT-PCM
wav_info() {
    python3 - "$1" <<'PY'
import array, struct, sys
raw = open(sys.argv[1], "rb").read()
if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
    print("NOT-RIFF"); raise SystemExit(0)
pos, fmt, data = 12, None, b""
while pos + 8 <= len(raw):
    cid = raw[pos:pos + 4]
    size = struct.unpack("<I", raw[pos + 4:pos + 8])[0]
    body = raw[pos + 8:pos + 8 + size]
    if cid == b"fmt ":
        tag, channels, rate, _brate, _align, bits = struct.unpack("<HHIIHH", body[:16])
        if tag != 1:
            print("NOT-PCM"); raise SystemExit(0)
        fmt = (channels, rate, bits)
    elif cid == b"data":
        data = body
    pos += 8 + size + (size & 1)
if fmt is None:
    print("NO-FMT"); raise SystemExit(0)
channels, rate, bits = fmt
frames = len(data) * 8 // (channels * bits)
samples = array.array("h")
samples.frombytes(data[: len(data) // 2 * 2])
nonzero = sum(1 for v in samples if v != 0)
peak = max((abs(v) for v in samples), default=0)
print(f"{channels} {rate} {bits} {frames} {nonzero} {peak}")
PY
}

# build_and_run <dir> <c-source> - compile with the OHOS toolchain, run the
# resulting AArch64 binary in <dir>. Sets BR_COMPILED / BR_EMACHINE / BR_RC.
build_and_run() {
    _d="$1"; _src="$2"
    BR_COMPILED=0; BR_EMACHINE=""; BR_RC=1
    if ( cd "$_d" && "$CC" -O2 -static "$_src" -lm -o prog ) > "$_d/cc.log" 2>&1; then
        BR_COMPILED=1
        BR_EMACHINE=$(od -An -tx1 -j18 -N2 "$_d/prog" | tr -d ' \n')
        ( cd "$_d" && run_ohos ./prog ) > "$_d/run.log" 2>&1
        BR_RC=$?
    fi
}

# check_render <label> <info> <want-channels> <want-rate> <min-frames> <wav>
check_render() {
    _label="$1"; _info="$2"; _ch_want="$3"; _rate="$4"; _frames="$5"; _wav="$6"
    case "$_info" in
        NOT-RIFF|NO-FMT|NOT-PCM)
            bad "$_label: the rendered file is a RIFF/WAVE PCM stream" "$_wav"
            return
            ;;
    esac
    ok "$_label: the rendered file is a RIFF/WAVE PCM stream"
    # shellcheck disable=SC2086
    set -- $_info
    _ch=$1; _r=$2; _bits=$3; _fr=$4; _nz=$5; _peak=$6
    if [ "$_r" = "$_rate" ] && [ "$_ch" = "$_ch_want" ] && [ "$_bits" = "16" ]; then
        ok "$_label: rendered PCM is $_ch ch / $_r Hz / $_bits bit as the orchestra asks"
    else
        bad "$_label: rendered PCM is $_ch ch / $_r Hz / $_bits bit (want $_ch_want ch / $_rate Hz / 16 bit)" "$_wav"
    fi
    if [ "$_fr" -ge "$_frames" ]; then
        ok "$_label: rendered $_fr frames (>= $_frames)"
    else
        bad "$_label: rendered $_fr frames (want >= $_frames)" "$_wav"
    fi
    if [ "$_nz" -gt 0 ] && [ "$_peak" -gt 1000 ]; then
        ok "$_label: rendered audio is not silence ($_nz non-zero samples, peak $_peak)"
    else
        bad "$_label: rendered audio is not silence ($_nz non-zero samples, peak $_peak)" "$_wav"
    fi
}

# ohos_render <label> <example-subdir> <want-channels> <want-rate> <min-frames> <args...>
ohos_render() {
    _label="$1"; _sub="$2"; _ch_want="$3"; _rate="$4"; _frames="$5"; shift 5
    _d="$WORK/f-$_label"
    rm -rf "$_d"; mkdir -p "$_d"
    cp -r "$EX/$_sub/." "$_d/" 2>/dev/null
    ( cd "$_d" && run_sf "$@" -o sa.c ) > "$_d/translate.log" 2>&1
    _rc=$?
    if [ "$_rc" -ne 0 ] || [ ! -s "$_d/sa.c" ]; then
        bad "$_label: packaged sfront emits an OHOS-buildable C program (rc=$_rc)" "$_d/translate.log"
        return
    fi
    build_and_run "$_d" sa.c
    if [ "$BR_COMPILED" = "1" ]; then
        ok "$_label: the generated program compiles and links with the OHOS toolchain"
    else
        bad "$_label: the generated program compiles and links with the OHOS toolchain" "$_d/cc.log"
        return
    fi
    if [ "$BR_EMACHINE" = "b700" ]; then
        ok "$_label: the generated program is an AArch64 (EM_AARCH64) executable"
    else
        bad "$_label: the generated program is an AArch64 executable (e_machine=$BR_EMACHINE)" "$_d/cc.log"
    fi
    if [ "$BR_RC" -eq 0 ]; then
        ok "$_label: the generated AArch64 program runs on OHOS"
    else
        bad "$_label: the generated AArch64 program runs on OHOS (rc=$BR_RC)" "$_d/run.log"
        return
    fi
    if [ -s "$_d/out.wav" ]; then
        ok "$_label: the generated program renders a WAV file"
    else
        bad "$_label: the generated program renders a WAV file" "$_d/run.log"
        return
    fi
    check_render "$_label" "$(wav_info "$_d/out.wav")" "$_ch_want" "$_rate" "$_frames" "$_d/out.wav"
}

# A single synthesised instrument rendered through the whole OHOS chain
# (examples/min declares one output bus, so it renders mono at 44.1 kHz).
ohos_render "min" "min" 1 44100 80000 -aout out.wav -orc min.saol -sco min.sasl

# torvalds mixes a real 8 kHz voice recording down to stereo and cleans it up, so
# its output can only cover the whole input if the OHOS build really decoded the
# WAV and ran the signal chain.
in_frames=$(wav_info "$EX/torvalds/english.wav" | awk '{print $4}')
ohos_render "torvalds" "torvalds" 2 8000 $in_frames \
    -aout out.wav -ain english.wav -orc torvalds.saol

# Upstream's mp4test target, executed on OHOS: the program regenerated from the
# MP4-SA bitstream must render byte-identical audio to the one generated straight
# from the orchestra.
d="$WORK/f-bitstream-audio"
rm -rf "$d"; mkdir -p "$d/orc" "$d/bit"
cp -r "$EX/min/." "$d/orc/" 2>/dev/null
cp -r "$EX/min/." "$d/bit/" 2>/dev/null
( cd "$d/orc" && run_sf -aout out.wav -orc min.saol -sco min.sasl -o sa.c ) > "$d/orc.log" 2>&1
orc_tr_rc=$?
( cd "$d/bit" && run_sf -orc min.saol -sco min.sasl -bitout bit.mp4 ) > "$d/bitout.log" 2>&1
bitout_rc=$?
( cd "$d/bit" && run_sf -aout out.wav -bit bit.mp4 -o sa.c ) > "$d/bit.log" 2>&1
bit_rc=$?
if [ "$orc_tr_rc" -ne 0 ] || [ "$bitout_rc" -ne 0 ] || [ "$bit_rc" -ne 0 ]; then
    bad "min: both the -orc and the -bit translation succeed (rc=$orc_tr_rc/$bitout_rc/$bit_rc)" \
        "$d/bit.log"
else
    ok "min: both the -orc and the -bit translation succeed"
    build_and_run "$d/orc" sa.c
    orc_compiled=$BR_COMPILED; orc_machine=$BR_EMACHINE; orc_run=$BR_RC
    build_and_run "$d/bit" sa.c
    bit_compiled=$BR_COMPILED; bit_machine=$BR_EMACHINE; bit_run=$BR_RC
    if [ "$orc_compiled" = "1" ] && [ "$bit_compiled" = "1" ]; then
        ok "min: both regenerated programs compile and link with the OHOS toolchain"
    else
        bad "min: both regenerated programs compile and link with the OHOS toolchain" "$d/bit/cc.log"
    fi
    if [ "$orc_machine" = "b700" ] && [ "$bit_machine" = "b700" ]; then
        ok "min: both regenerated programs are AArch64 (EM_AARCH64) executables"
    else
        bad "min: both regenerated programs are AArch64 executables ($orc_machine/$bit_machine)" \
            "$d/bit/cc.log"
    fi
    if [ "$orc_run" -eq 0 ] && [ "$bit_run" -eq 0 ] && [ -s "$d/orc/out.wav" ] && [ -s "$d/bit/out.wav" ]; then
        ok "min: both AArch64 programs run on OHOS and render a WAV"
        if cmp -s "$d/orc/out.wav" "$d/bit/out.wav"; then
            ok "min: the bitstream-decoded program renders byte-identical audio (upstream mp4test)"
        else
            bad "min: the bitstream-decoded program renders byte-identical audio (upstream mp4test)" \
                "$d/bit/run.log"
        fi
    else
        bad "min: both AArch64 programs run on OHOS and render a WAV (rc=$orc_run/$bit_run)" \
            "$d/bit/run.log"
    fi
fi

# === G. shipped payload completeness ================================
missing=""
for f in Slib/std.hs Slib/trig.hs Slib/ssm.hs Slib/gmidi.hs \
         reson/README reson/macros.hs reson/sreson.hs reson/string.hs \
         reson/abar.hs reson/marimba.hs; do
    [ -s "$LIB/$f" ] || missing="$missing $f"
done
if [ -z "$missing" ]; then
    ok "the Slib/reson SAOL library (10 files) is shipped intact"
else
    bad "the Slib/reson SAOL library is shipped intact (missing:$missing)"
fi

saol_count=$(find "$EX" -name '*.saol' | wc -l)
sasl_count=$(find "$EX" -name '*.sasl' | wc -l)
if [ "$saol_count" -eq 26 ] && [ "$sasl_count" -eq 20 ]; then
    ok "all 26 upstream example orchestras and 20 SASL scores are shipped"
else
    bad "all upstream example material is shipped (found $saol_count .saol / $sasl_count .sasl)" "$EX"
fi

if [ -s "$PKG/share/doc/sfront/html/README.HTML" ] && [ -d "$PKG/share/doc/sfront/html/book" ] \
        && [ -s "$PKG/licenses/bsd.html" ] && [ -s "$PKG/licenses/gfdl.html" ]; then
    ok "the HTML manual, the MPEG-4 Structured Audio Book and both licences are shipped"
else
    bad "the HTML manual, the MPEG-4 Structured Audio Book and both licences are shipped"
fi

echo "SFRONT_TEST_SUMMARY pass=$pass fail=$fail total=$((pass + fail))"
[ "$fail" -eq 0 ]
