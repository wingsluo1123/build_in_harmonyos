#!/usr/bin/env sh
set -eu
if (set -o pipefail) 2>/dev/null; then
  set -o pipefail
fi

# Replays the source-bootstrap path used by the OHOS true-device probe from
# downloaded Swift release sources plus the pinned OHOS LLVM build substrate.

die() {
  echo "error: $*" >&2
  exit 1
}

log() {
  echo "[swift-source-bootstrap] $*"
}

first_existing_dir() {
  for path in "$@"; do
    if [ -n "$path" ] && [ -d "$path" ]; then
      printf '%s\n' "$path"
      return 0
    fi
  done
  return 1
}

first_existing_file() {
  for path in "$@"; do
    if [ -n "$path" ] && [ -f "$path" ]; then
      printf '%s\n' "$path"
      return 0
    fi
  done
  return 1
}

command_path() {
  command -v "$1" 2>/dev/null || true
}

run_logged() {
  log_file=$1
  shift
  log "$*"
  if "$@" > "$log_file" 2>&1; then
    rc=0
  else
    rc=$?
  fi
  if [ "$rc" -eq 0 ]; then
    tail -40 "$log_file" 2>/dev/null || true
    return 0
  fi
  echo "error: command failed with rc=$rc; log=$log_file" >&2
  tail -160 "$log_file" >&2 2>/dev/null || true
  exit "$rc"
}

link_or_copy() {
  src=$1
  dst=$2
  [ -d "$src" ] || die "missing source directory: $src"
  rm -rf "$dst"
  mkdir -p "$(dirname "$dst")"
  if ln -s "$src" "$dst" 2>/dev/null; then
    return 0
  fi
  cp -R "$src" "$dst"
}

safe_remove_stage() {
  stage=$1
  case "$stage" in
    "$build_root"/*) rm -rf "$stage" ;;
    *) [ ! -e "$stage" ] || die "stage output already exists outside build root: $stage" ;;
  esac
}

build_uuid_shim() {
  if [ -n "${SWIFT_OHOS_UUID_INCLUDE_DIR:-}" ] && [ -n "${SWIFT_OHOS_UUID_LIBRARY:-}" ]; then
    [ -d "$SWIFT_OHOS_UUID_INCLUDE_DIR" ] || die "UUID include directory is missing: $SWIFT_OHOS_UUID_INCLUDE_DIR"
    [ -f "$SWIFT_OHOS_UUID_LIBRARY" ] || die "UUID library is missing: $SWIFT_OHOS_UUID_LIBRARY"
    uuid_include=$SWIFT_OHOS_UUID_INCLUDE_DIR
    uuid_library=$SWIFT_OHOS_UUID_LIBRARY
    return 0
  fi

  uuid_root=$bootstrap_root/shims/uuid
  mkdir -p "$uuid_root/include/uuid" "$uuid_root/src" "$uuid_root/build"
  cat > "$uuid_root/include/uuid/uuid.h" <<'EOF'
#ifndef UUID_UUID_H
#define UUID_UUID_H
#ifdef __cplusplus
extern "C" {
#endif
typedef unsigned char uuid_t[16];
void uuid_clear(uuid_t uu);
int uuid_is_null(const uuid_t uu);
void uuid_generate(uuid_t out);
void uuid_generate_random(uuid_t out);
void uuid_generate_time(uuid_t out);
void uuid_unparse_lower(const uuid_t uu, char *out);
void uuid_unparse_upper(const uuid_t uu, char *out);
int uuid_parse(const char *in, uuid_t uu);
int uuid_compare(const uuid_t a, const uuid_t b);
#ifdef __cplusplus
}
#endif
#endif
EOF
  cat > "$uuid_root/src/uuid.c" <<'EOF'
#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include "uuid/uuid.h"

void uuid_clear(uuid_t uu) { memset(uu, 0, 16); }

int uuid_is_null(const uuid_t uu) {
  for (int i = 0; i < 16; ++i)
    if (uu[i]) return 0;
  return 1;
}

void uuid_generate(uuid_t out) {
  uint64_t seed = (uint64_t)time(0) ^ ((uint64_t)getpid() << 32);
  static uint64_t counter;
  seed ^= ++counter;
  for (int i = 0; i < 16; ++i) {
    seed = seed * 6364136223846793005ULL + 1442695040888963407ULL;
    out[i] = (unsigned char)(seed >> 32);
  }
  out[6] = (unsigned char)((out[6] & 0x0f) | 0x40);
  out[8] = (unsigned char)((out[8] & 0x3f) | 0x80);
}

void uuid_generate_random(uuid_t out) { uuid_generate(out); }

void uuid_generate_time(uuid_t out) { uuid_generate(out); }

void uuid_unparse_lower(const uuid_t uu, char *out) {
  static const char hex[] = "0123456789abcdef";
  int j = 0;
  for (int i = 0; i < 16; ++i) {
    if (i == 4 || i == 6 || i == 8 || i == 10) out[j++] = '-';
    out[j++] = hex[(uu[i] >> 4) & 0xf];
    out[j++] = hex[uu[i] & 0xf];
  }
  out[j] = 0;
}

void uuid_unparse_upper(const uuid_t uu, char *out) {
  uuid_unparse_lower(uu, out);
  for (char *p = out; *p; ++p)
    *p = (char)toupper((unsigned char)*p);
}

int uuid_compare(const uuid_t a, const uuid_t b) {
  return memcmp(a, b, 16);
}

static int hexval(int c) {
  if (c >= '0' && c <= '9') return c - '0';
  c = tolower(c);
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  return -1;
}

int uuid_parse(const char *in, uuid_t uu) {
  int n = 0;
  uuid_clear(uu);
  for (const char *p = in; *p && n < 16; ) {
    if (*p == '-') {
      ++p;
      continue;
    }
    int hi = hexval((unsigned char)p[0]);
    int lo = hexval((unsigned char)p[1]);
    if (hi < 0 || lo < 0) return -1;
    uu[n++] = (unsigned char)((hi << 4) | lo);
    p += 2;
  }
  return n == 16 ? 0 : -1;
}
EOF

  uuid_log=$logs/uuid-shim-build.log
  if [ -x "$cc" ]; then
    "$cc" -I"$uuid_root/include" -fPIC -c "$uuid_root/src/uuid.c" -o "$uuid_root/build/uuid.o" > "$uuid_log" 2>&1
  else
    sh "$cc" -I"$uuid_root/include" -fPIC -c "$uuid_root/src/uuid.c" -o "$uuid_root/build/uuid.o" > "$uuid_log" 2>&1
  fi
  ar_cmd=${SWIFT_OHOS_AR:-$(command_path llvm-ar)}
  [ -n "$ar_cmd" ] || ar_cmd=$(command_path ar)
  [ -n "$ar_cmd" ] || die "llvm-ar/ar is required for the UUID shim"
  "$ar_cmd" rcs "$uuid_root/build/libuuid.a" "$uuid_root/build/uuid.o" >> "$uuid_log" 2>&1
  uuid_include=$uuid_root/include
  uuid_library=$uuid_root/build/libuuid.a
}

build_llvm_resource_targets() {
  [ -f "$llvm_build/build.ninja" ] || return 0
  targets_file=$logs/llvm-resource-targets.targets
  targets_log=$logs/llvm-resource-targets-list.log
  if "$ninja" -C "$llvm_build" -t targets all > "$targets_file" 2>"$targets_log"; then
    targets=
    for candidate in clang-resource-headers clang-features-file; do
      if grep -Eq "(^|/)$candidate:" "$targets_file"; then
        targets="$targets $candidate"
      else
        log "skipping missing LLVM target: $candidate"
      fi
    done
    [ -n "$targets" ] || return 0
  else
    log "could not list LLVM targets; falling back to clang-resource-headers"
    targets=clang-resource-headers
  fi
  run_logged "$logs/llvm-resource-targets.log" \
    "$ninja" -C "$llvm_build" -j"$jobs" $targets
}

build_cmark() {
  cmark_build=$bootstrap_root/build/cmark-ohos-aarch64
  mkdir -p "$cmark_build"
  run_logged "$logs/cmark-config-build.log" \
    "$cmake" -G Ninja \
      -S "$repos/cmark" \
      -B "$cmark_build" \
      -DCMAKE_SYSTEM_NAME=Linux \
      -DCMAKE_C_COMPILER="$cmake_cc" \
      -DCMAKE_C_COMPILER_ARG1="$cmake_cc_arg1" \
      -DCMAKE_CXX_COMPILER="$cmake_cxx" \
      -DCMAKE_CXX_COMPILER_ARG1="$cmake_cxx_arg1" \
      -DCMAKE_MAKE_PROGRAM="$ninja" \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMARK_THREADING=ON \
      -DCMARK_TESTS=OFF \
      -DCMAKE_INSTALL_PREFIX="$cmark_build/install"
  run_logged "$logs/cmark-build.log" "$ninja" -C "$cmark_build" -j"$jobs"
}

configure_swift() {
  swift_build=$bootstrap_root/build/swift-manual-ohos-linuxsys2
  mkdir -p "$swift_build"
  run_logged "$logs/swift-cmake-configure.log" \
    "$cmake" -G Ninja \
      -S "$repos/swift" \
      -B "$swift_build" \
      -DCMAKE_SYSTEM_NAME=Linux \
      -DCMAKE_C_COMPILER:PATH="$cmake_cc" \
      -DCMAKE_CXX_COMPILER:PATH="$cmake_cxx" \
      -DCMAKE_C_COMPILER_ARG1="$cmake_cc_arg1" \
      -DCMAKE_CXX_COMPILER_ARG1="$cmake_cxx_arg1" \
      -DCMAKE_MAKE_PROGRAM="$ninja" \
      -DCMAKE_BUILD_TYPE:STRING="${SWIFT_OHOS_SWIFT_BUILD_TYPE:-Debug}" \
      -DCMAKE_CXX_STANDARD_LIBRARIES:STRING="$cxx_standard_libraries" \
      -DCMAKE_Swift_COMPILER:PATH= \
      -DLLVM_DIR:PATH="$llvm_build/lib/cmake/llvm" \
      -DClang_DIR:PATH="$llvm_build/lib/cmake/clang" \
      -DLLVM_INCLUDE_DOCS:BOOL=FALSE \
      -DSWIFT_NATIVE_LLVM_TOOLS_PATH:STRING="$llvm_build/bin" \
      -DSWIFT_NATIVE_CLANG_TOOLS_PATH:STRING="$llvm_build/bin" \
      -DSWIFT_NATIVE_SWIFT_TOOLS_PATH:STRING= \
      -DSWIFT_USE_SYMLINKS:BOOL=FALSE \
      -DSWIFT_PATH_TO_CMARK_SOURCE:PATH="$repos/cmark" \
      -DSWIFT_PATH_TO_CMARK_BUILD:PATH="$cmark_build" \
      -DUUID_INCLUDE_DIR:PATH="$uuid_include" \
      -DUUID_LIBRARY:FILEPATH="$uuid_library" \
      -DSWIFT_SDKS:STRING=OHOS \
      -DSWIFT_SDK_OHOS_ARCHITECTURES:STRING=aarch64 \
      -DSWIFT_SDK_OHOS_ARCH_aarch64_PATH:PATH="$sysroot" \
      -DSWIFT_HOST_TRIPLE:STRING=aarch64-unknown-linux-ohos \
      -DSWIFT_HOST_VARIANT=ohos \
      -DSWIFT_HOST_VARIANT_SDK=OHOS \
      -DSWIFT_HOST_VARIANT_ARCH=aarch64 \
      -DSWIFT_INCLUDE_TOOLS:BOOL=TRUE \
      -DSWIFT_INCLUDE_TESTS:BOOL=FALSE \
      -DSWIFT_INCLUDE_DOCS:BOOL=FALSE \
      -DSWIFT_BUILD_SOURCEKIT:BOOL=FALSE \
      -DSWIFT_ENABLE_DISPATCH:BOOL=FALSE \
      -DSWIFT_BUILD_DYNAMIC_STDLIB:BOOL=TRUE \
      -DSWIFT_BUILD_STATIC_STDLIB:BOOL=FALSE \
      -DSWIFT_BUILD_REGEX_PARSER_IN_COMPILER:BOOL=FALSE \
      -DSWIFT_BUILD_RUNTIME_WITH_HOST_COMPILER:BOOL=FALSE \
      -DSWIFT_BUILD_SWIFT_SYNTAX:BOOL=FALSE \
      -USWIFT_DARWIN_SUPPORTED_ARCHS
  "$python_bin" - "$llvm_build" "$cmake_cc" "$cmake_cxx" \
    "$swift_build/build.ninja" "$swift_build/CMakeFiles/rules.ninja" <<'PY'
from pathlib import Path
import re
import sys

llvm_build = Path(sys.argv[1])
cmake_cc = sys.argv[2]
cmake_cxx = sys.argv[3]
paths = [Path(arg) for arg in sys.argv[4:]]
clang_versions_by_major = {}
clang_root = llvm_build / "lib" / "clang"
if clang_root.is_dir():
    for candidate in sorted(clang_root.iterdir()):
        if candidate.is_dir():
            clang_versions_by_major.setdefault(candidate.name.split(".", 1)[0], candidate.name)

bad_clang = str(llvm_build / "bin" / "clang")
bad_clangxx = str(llvm_build / "bin" / "clang++")
for path in paths:
    if not path.is_file():
        continue
    text = path.read_text()
    updated = []
    changed = 0
    for line in text.splitlines(keepends=True):
        for old, new in ((bad_clangxx, cmake_cxx), (bad_clang, cmake_cc)):
            replaced = line.replace(old, new)
            if replaced != line:
                changed += 1
                line = replaced
        for lib in ("-lLLVMirprinter", "-lLLVMtargetparser", "-lLLVMTargetParser"):
            line = line.replace(f"  {lib}", "")
            line = line.replace(f" {lib} ", " ")
        for feature in ("Macros", "FreestandingMacros", "DebugDescriptionMacro"):
            line = line.replace(f" -enable-experimental-feature {feature}", "")
        line = re.sub(r" -external-plugin-path [^ ]+", "", line)
        for major, actual in clang_versions_by_major.items():
            if actual != major and not (clang_root / major).exists():
                replaced = line.replace(f"/lib/clang/{major} ", f"/lib/clang/{actual} ")
                replaced = replaced.replace(f"/lib/clang/{major}/", f"/lib/clang/{actual}/")
                if replaced != line:
                    changed += 1
                    line = replaced
        if "cmake -E create_symlink " in line:
            if "/lib/clang/" in line or "FrameworkABIBaseline" in line:
                replacement = "cmake -E copy_directory "
            else:
                replacement = "cmake -E copy_if_different "
            line = line.replace("cmake -E create_symlink ", replacement)
            changed += 1
        updated.append(line)
    if changed:
        path.write_text("".join(updated))
PY
}

patch_ohos_stdlib_outputs() {
  [ -d "$swift_build" ] || return 0
  "$python_bin" - "$swift_build" "$sysroot" "$repos/swift" <<'PY'
from pathlib import Path
import re
import sys

swift_build = Path(sys.argv[1])
sysroot = Path(sys.argv[2])
swift_source = Path(sys.argv[3])

def rewrite(path, transform):
    if not path.is_file():
        return
    text = path.read_text()
    updated = transform(text)
    if updated != text:
        path.write_text(updated)

platform_dir = swift_build / "stdlib" / "public" / "Platform" / "8"
tgmath = platform_dir / "tgmath.swift"

def patch_tgmath(text):
    if "import SwiftGlibc\n" not in text:
        text = text.replace("import SwiftShims\n", "import SwiftShims\nimport SwiftGlibc\n", 1)
    text = text.replace("return Float(nanf(tag))", "return Float(SwiftGlibc.nanf(tag))")
    text = text.replace("return jn(Int32(n), x)", "return SwiftGlibc.jn(Int32(n), x)")
    text = text.replace("return yn(Int32(n), x)", "return SwiftGlibc.yn(Int32(n), x)")
    return text

rewrite(tgmath, patch_tgmath)

thread_extras = swift_source / "stdlib" / "private" / "SwiftPrivateThreadExtras" / "SwiftPrivateThreadExtras.swift"

def patch_thread_extras(text):
    return text.replace(
        "#if (os(Linux) && !canImport(Musl)) || os(Android)",
        "#if (os(Linux) && !canImport(Musl) && !os(OHOS)) || os(Android)",
    )

rewrite(thread_extras, patch_thread_extras)

module_dir = swift_build / "lib" / "swift" / "ohos" / "aarch64"
modulemap = module_dir / "glibc.modulemap"
swift_glibc_h = module_dir / "SwiftGlibc.h"

def patch_modulemap(text):
    assert_header = (sysroot / "usr" / "include" / "assert.h").as_posix()
    text = text.replace('textual header "assert.h"', f'textual header "{assert_header}"')
    return text

rewrite(modulemap, patch_modulemap)

def patch_swift_glibc_h(text):
    if "_GNU_SOURCE" not in text.splitlines()[:12]:
        text = "#ifndef _GNU_SOURCE\n#define _GNU_SOURCE\n#endif\n" + text
    return text

rewrite(swift_glibc_h, patch_swift_glibc_h)

builtin_float_module = """
module _Builtin_float [system] [extern_c] {
  header "float.h"
  export *
}
"""

def patch_builtin_float_modulemap(text):
    if "module _Builtin_float" in text:
        return text
    if not text.endswith("\n"):
        text += "\n"
    return text + "\n" + builtin_float_module

for clang_modulemap in (
    swift_build / "lib" / "swift" / "clang" / "include" / "module.modulemap",
    swift_build / "lib" / "swift_static" / "clang" / "include" / "module.modulemap",
):
    rewrite(clang_modulemap, patch_builtin_float_modulemap)

modulemap_flag = f"-Xcc -fmodule-map-file={modulemap.as_posix()}"
include_flag = f"-Xcc -I{module_dir.as_posix()}"
glibc_dependent_modules = {
    "SwiftPrivate",
    "SwiftPrivateLibcExtras",
    "SwiftPrivateThreadExtras",
    "StdlibUnittest",
    "StdlibCollectionUnittest",
    "StdlibUnicodeUnittest",
    "RuntimeUnittest",
}

def patch_ninja(text):
    updated = []
    for line in text.splitlines(keepends=True):
        body = line[:-1] if line.endswith("\n") else line
        newline = "\n" if line.endswith("\n") else ""
        if (
            "swiftc" in body
            and "-frontend" in body
            and "-target aarch64-unknown-linux-ohos" in body
            and "-module-name SwiftOnoneSupport" in body
            and "-parse-stdlib" not in body
        ):
            body += " -parse-stdlib"
        if (
            ("swiftc" in body or "swift-frontend" in body)
            and "-frontend" in body
            and "-target aarch64-unknown-linux-ohos" in body
            and modulemap_flag not in body
        ):
            matched = any(f"-module-name {name}" in body for name in glibc_dependent_modules)
            if matched:
                body += f" {modulemap_flag} {include_flag}"
        if (
            "-target aarch64-unknown-linux-ohos" in body
            and ("clang" in body or "ohos-clang" in body)
            and "-fPIC" not in body
            and any(token in body for token in (
                "stdlib/public/runtime",
                "stdlib/public/stubs",
                "stdlib/public/Threading",
                "stdlib/public/SwiftRemoteMirror",
                "SwiftRemoteMirror",
            ))
        ):
            body += " -fPIC"
        updated.append(body + newline)
    return "".join(updated)

for ninja_file in (swift_build / "build.ninja", swift_build / "CMakeFiles" / "rules.ninja"):
    rewrite(ninja_file, patch_ninja)
PY
}

compile_irhandoff_wrapper() {
  [ "${SWIFT_OHOS_ENABLE_IRHANDOFF_WRAPPER:-1}" = "1" ] || return 0
  wrapper_src=$script_dir/swift-irhandoff-wrapper.c
  [ -f "$wrapper_src" ] || die "missing IR handoff wrapper source: $wrapper_src"
  mkdir -p "$bootstrap_root/bin"
  irhandoff_wrapper=$bootstrap_root/bin/swift-irhandoff-wrapper
  log "building Swift IR handoff wrapper"
  if [ -x "$cc" ]; then
    "$cc" -O2 -Wl,--code-sign "$wrapper_src" -o "$irhandoff_wrapper" > "$logs/irhandoff-wrapper-build.log" 2>&1
  else
    sh "$cc" -O2 -Wl,--code-sign "$wrapper_src" -o "$irhandoff_wrapper" > "$logs/irhandoff-wrapper-build.log" 2>&1
  fi
  chmod 755 "$irhandoff_wrapper" 2>/dev/null || true
}

is_irhandoff_wrapper_file() {
  if command -v strings >/dev/null 2>&1; then
    strings "$1" 2>/dev/null | grep -q "ohos-irhandoff"
  else
    grep -a -q "ohos-irhandoff" "$1" 2>/dev/null
  fi
}

install_irhandoff_tool_wrapper() {
  tool=$1
  bin_dir=$swift_build/bin
  current=$bin_dir/$tool
  passthrough=$bin_dir/$tool.real-irhandoff
  real=$bin_dir/$tool.real-irhandoff.real
  [ -f "$current" ] || die "IR handoff wrapper needs $current"
  if [ ! -f "$real" ]; then
    if [ -f "$passthrough" ] && ! is_irhandoff_wrapper_file "$passthrough"; then
      cp -p "$passthrough" "$real"
    elif ! is_irhandoff_wrapper_file "$current"; then
      cp -p "$current" "$real"
    else
      die "unable to find the real $tool binary before installing IR handoff wrapper"
    fi
  fi
  cp -p "$irhandoff_wrapper" "$current"
  cp -p "$irhandoff_wrapper" "$passthrough"
  chmod 755 "$current" "$passthrough" "$real" 2>/dev/null || true
}

install_irhandoff_wrapper() {
  [ "${SWIFT_OHOS_ENABLE_IRHANDOFF_WRAPPER:-1}" = "1" ] || return 0
  if [ -z "${SWIFT_OHOS_LLC:-}" ]; then
    found_llc=$(first_existing_file "$toolchain_root/bin/llc" "$llvm_build/bin/llc" "$(command_path llc)") || true
    [ -n "$found_llc" ] && SWIFT_OHOS_LLC=$found_llc
  fi
  if [ -z "${SWIFT_OHOS_OPT:-}" ]; then
    found_opt=$(first_existing_file "$toolchain_root/bin/opt" "$llvm_build/bin/opt" "$(command_path opt)") || true
    [ -n "$found_opt" ] && SWIFT_OHOS_OPT=$found_opt
  fi
  [ -n "${SWIFT_OHOS_LLC:-}" ] || die "llc is required for Swift OHOS IR handoff"
  [ -n "${SWIFT_OHOS_OPT:-}" ] || die "opt is required for Swift OHOS IR handoff"
  export SWIFT_OHOS_LLC
  export SWIFT_OHOS_OPT
  compile_irhandoff_wrapper
  install_irhandoff_tool_wrapper swiftc
  install_irhandoff_tool_wrapper swift-frontend
  log "installed Swift IR handoff wrapper in $swift_build/bin"
}

build_llvm_static_deps() {
  [ "${SWIFT_OHOS_BUILD_LLVM_STATIC_DEPS:-1}" = "1" ] || return 0
  [ -f "$swift_build/build.ninja" ] || return 0
  targets_file=$logs/llvm-static-deps.targets
  "$python_bin" - "$swift_build/build.ninja" "$llvm_build" > "$targets_file" <<'PY'
import sys
from pathlib import Path
swift_build = Path(sys.argv[1]).parent.resolve()
llvm_build = Path(sys.argv[2]).resolve()
line = ""
for current in Path(sys.argv[1]).read_text(errors="ignore").splitlines():
    if "bin/swift-frontend:" in current:
        line = current
        break
names = []
def ninja_target(item):
    normalized = item.replace("\\", "/")
    if normalized.startswith("lib/"):
        return normalized
    path = Path(item)
    candidate = path if path.is_absolute() else swift_build / path
    try:
        return candidate.resolve().relative_to(llvm_build).as_posix()
    except ValueError:
        return normalized
for item in line.split():
    base = Path(item).name
    if base.startswith("libLLVM") and base.endswith(".a"):
        names.append(ninja_target(item))
    elif base.startswith("libclang") and base.endswith(".a"):
        names.append(ninja_target(item))
for name in ["clang-resource-headers"] + list(dict.fromkeys(names)):
    print(name)
PY
  [ -s "$targets_file" ] || return 0
  targets=$(cat "$targets_file")
  log "building LLVM static dependency targets listed in $targets_file"
  if (cd "$llvm_build" && "$ninja" -j"$jobs" $targets) > "$logs/llvm-static-deps-build.log" 2>&1; then
    rc=0
  else
    rc=$?
  fi
  if [ "$rc" -eq 0 ]; then
    tail -40 "$logs/llvm-static-deps-build.log" 2>/dev/null || true
    return 0
  fi
  echo "error: command failed with rc=$rc; log=$logs/llvm-static-deps-build.log" >&2
  tail -160 "$logs/llvm-static-deps-build.log" >&2 2>/dev/null || true
  exit "$rc"
}

build_swift_targets() {
  targets=${SWIFT_OHOS_NINJA_TARGETS:-swift-frontend}
  if [ "${SWIFT_OHOS_ENABLE_IRHANDOFF_WRAPPER:-1}" = "1" ]; then
    prereq_targets=${SWIFT_OHOS_IRHANDOFF_PREREQ_TARGETS:-swiftc swift-frontend swift-autolink-extract}
    log "building Swift IR handoff prerequisite targets: $prereq_targets"
    run_logged "$logs/swift-irhandoff-prereq-build.log" \
      "$ninja" -C "$swift_build" -j"$jobs" $prereq_targets
    install_irhandoff_wrapper
  fi
  log "building Swift targets: $targets"
  if "$ninja" -C "$swift_build" -j"$jobs" $targets > "$logs/swift-targets-build.log" 2>&1; then
    rc=0
  else
    rc=$?
  fi
  if [ "$rc" -eq 0 ]; then
    tail -80 "$logs/swift-targets-build.log" 2>/dev/null || true
    return 0
  fi
  echo "error: command failed with rc=$rc; log=$logs/swift-targets-build.log" >&2
  tail -200 "$logs/swift-targets-build.log" >&2 2>/dev/null || true
  exit "$rc"
}

build_swiftpm() {
  [ "${SWIFT_OHOS_BUILD_SWIFTPM:-1}" = "1" ] || return 0
  if [ -e "$swift_build/bin/swift-build" ] && [ -e "$swift_build/bin/swift-package" ]; then
    return 0
  fi

  swiftc_path=$(first_existing_file "$swift_build/bin/swiftc" "$swift_build/bin/swiftc.real-irhandoff") || true
  [ -n "$swiftc_path" ] || die "SwiftPM bootstrap needs a built swiftc; adjust SWIFT_OHOS_NINJA_TARGETS"

  swiftpm_build=$bootstrap_root/build/swiftpm-ohos
  swiftpm_prefix=$bootstrap_root/build/swiftpm-install
  mkdir -p "$swiftpm_build" "$swiftpm_prefix"
  export SWIFT_EXEC=$swiftc_path
  PATH=$(dirname "$swiftc_path"):$PATH
  export PATH
  LD_LIBRARY_PATH=$swift_build/lib:$swift_build/lib/swift/ohos:${LD_LIBRARY_PATH:-}
  export LD_LIBRARY_PATH

  log "building SwiftPM with Utilities/bootstrap"
  run_logged "$logs/swiftpm-bootstrap-install.log" \
    "$python_bin" "$repos/swiftpm/Utilities/bootstrap" install \
      --build-dir "$swiftpm_build" \
      --swiftc-path "$swiftc_path" \
      --clang-path "$cc" \
      --cmake-path "$cmake" \
      --ninja-path "$ninja" \
      --release \
      --prefix "$swiftpm_prefix"

  if [ -d "$swiftpm_prefix/bin" ]; then
    export SWIFT_OHOS_SWIFTPM_BIN_DIR=$swiftpm_prefix/bin
  fi
  if [ -d "$swiftpm_prefix/lib" ]; then
    export SWIFT_OHOS_SWIFTPM_LIB_DIR=$swiftpm_prefix/lib
  fi
}

assemble_stage() {
  safe_remove_stage "$stage_out"
  export SWIFT_OHOS_BOOTSTRAP_ROOT=$bootstrap_root
  export SWIFT_OHOS_STAGE_OUT=$stage_out
  export SWIFT_OHOS_BIN_DIR=${SWIFT_OHOS_BIN_DIR:-$swift_build/bin}
  export SWIFT_OHOS_LIB_SWIFT_DIR=${SWIFT_OHOS_LIB_SWIFT_DIR:-$swift_build/lib/swift}
  sh "$script_dir/assemble-stage-ohos.sh"
}

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)
source_root=${SWIFT_OHOS_SOURCE_ROOT:-$(pwd)}
build_root=${SWIFT_OHOS_BUILD_ROOT:-$source_root/.ohos-source-bootstrap}
bootstrap_root=${SWIFT_OHOS_BOOTSTRAP_ROOT:-$build_root/bootstrap}
stage_out=${SWIFT_OHOS_STAGE_OUT:-$build_root/stage}
tmpdir=${TMPDIR:-$build_root/tmp}
jobs=${SWIFT_OHOS_JOBS:-${CONAN_CPU_COUNT:-2}}
case "$jobs" in
  ''|*[!0-9]*) jobs=2 ;;
esac
[ "$jobs" -ge 1 ] 2>/dev/null || jobs=1

export TMPDIR=$tmpdir
PATH=${SWIFT_OHOS_PATH_PREFIX:-${HOME:-/storage/Users/currentUser}/usr/local/bin}:$PATH
export PATH

repos=$bootstrap_root/repos
logs=$bootstrap_root/logs
mkdir -p "$repos" "$bootstrap_root/build" "$logs" "$tmpdir"

cmake=${SWIFT_OHOS_CMAKE:-$(command_path cmake)}
ninja=${SWIFT_OHOS_NINJA:-$(command_path ninja)}
python_bin=${SWIFT_OHOS_PYTHON3:-$(command_path python3)}
[ -n "$cmake" ] || die "cmake is required"
[ -n "$ninja" ] || die "ninja is required"
[ -n "$python_bin" ] || die "python3 is required"

cc=${SWIFT_OHOS_CC:-}
if [ -z "$cc" ]; then
  cc=$(first_existing_file \
    "$bootstrap_root/toolchain/ohos-clang" \
    "${HOME:-/storage/Users/currentUser}/validation/toolchain-bin/ohos-clang" \
    "${HOME:-/storage/Users/currentUser}/usr/local/bin/ohos-clang") || true
fi
cxx=${SWIFT_OHOS_CXX:-}
if [ -z "$cxx" ]; then
  cxx=$(first_existing_file \
    "$bootstrap_root/toolchain/ohos-clang++" \
    "$bootstrap_root/toolchain/ohos-clangxx" \
    "${HOME:-/storage/Users/currentUser}/validation/toolchain-bin/ohos-clang++" \
    "${HOME:-/storage/Users/currentUser}/validation/toolchain-bin/ohos-clangxx" \
    "${HOME:-/storage/Users/currentUser}/usr/local/bin/ohos-clang++") || true
fi
[ -n "$cc" ] || die "set SWIFT_OHOS_CC to the OHOS clang wrapper"
[ -n "$cxx" ] || die "set SWIFT_OHOS_CXX to the OHOS clang++ wrapper"
cmake_cc=$cc
cmake_cxx=$cxx
cmake_cc_arg1=
cmake_cxx_arg1=
if [ ! -x "$cc" ]; then
  cmake_cc=/bin/sh
  cmake_cc_arg1=$cc
fi
if [ ! -x "$cxx" ]; then
  cmake_cxx=/bin/sh
  cmake_cxx_arg1=$cxx
fi

sysroot=${OHOS_SYSROOT:-${OHOS_SDKROOT:-${SDKROOT:-}}}
if [ -z "$sysroot" ]; then
  sysroot=$(first_existing_dir "${HOME:-/storage/Users/currentUser}/usr/local/sysroot") || true
fi
[ -n "$sysroot" ] || die "set OHOS_SYSROOT/OHOS_SDKROOT/SDKROOT to the OHOS sysroot"
export SDKROOT=$sysroot
export OHOS_SYSROOT=$sysroot
export OHOS_SDKROOT=$sysroot
toolchain_root=${SWIFT_OHOS_TOOLCHAIN_ROOT:-$(cd "$sysroot/.." && pwd)}
cxx_runtime_libdir=${SWIFT_OHOS_CXX_RUNTIME_LIBDIR:-$toolchain_root/lib/aarch64-linux-ohos}
cxx_standard_libraries=${SWIFT_OHOS_CXX_STANDARD_LIBRARIES:-"-L$cxx_runtime_libdir -lc++ -lc++abi -lunwind"}
[ -d "$cxx_runtime_libdir" ] || die "OHOS C++ runtime library directory is missing: $cxx_runtime_libdir"

llvm_build=${SWIFT_OHOS_LLVM_BUILD_DIR:-}
if [ -z "$llvm_build" ]; then
  llvm_build=$(first_existing_dir \
    "$bootstrap_root/build/llvm-host-tools-ohos" \
    "${HOME:-/storage/Users/currentUser}/swift-mainline-ohos-src/build/llvm-host-tools-ohos") || true
fi
[ -n "$llvm_build" ] || die "set SWIFT_OHOS_LLVM_BUILD_DIR to a pinned OHOS LLVM build directory"
[ -d "$llvm_build/lib/cmake/llvm" ] || die "LLVM CMake package is missing under $llvm_build"
[ -d "$llvm_build/lib/cmake/clang" ] || die "Clang CMake package is missing under $llvm_build"

swift_src=$(first_existing_dir "$source_root/swift-swift-6.0.3-RELEASE" "$source_root/swift") || die "missing swift source"
driver_src=$(first_existing_dir "$source_root/swift-driver-swift-6.0.3-RELEASE" "$source_root/swift-driver") || die "missing swift-driver source"
swiftpm_src=$(first_existing_dir "$source_root/swift-package-manager-swift-6.0.3-RELEASE" "$source_root/swiftpm") || die "missing swiftpm source"
foundation_src=$(first_existing_dir "$source_root/swift-corelibs-foundation-swift-6.0.3-RELEASE" "$source_root/swift-corelibs-foundation") || die "missing swift-corelibs-foundation source"
cmark_src=$(first_existing_dir "$source_root/swift-cmark-swift-6.0.3-RELEASE" "$source_root/swift-cmark-release-6.0.2" "$source_root/swift-cmark-6.0.2" "$source_root/cmark") || die "missing swift-cmark source"

link_or_copy "$swift_src" "$repos/swift"
link_or_copy "$driver_src" "$repos/swift-driver"
link_or_copy "$swiftpm_src" "$repos/swiftpm"
link_or_copy "$foundation_src" "$repos/swift-corelibs-foundation"
link_or_copy "$cmark_src" "$repos/cmark"

log "source_root=$source_root"
log "build_root=$build_root"
log "llvm_build=$llvm_build"
log "jobs=$jobs"

build_uuid_shim
build_llvm_resource_targets
build_cmark
configure_swift
patch_ohos_stdlib_outputs
build_llvm_static_deps
build_swift_targets
build_swiftpm
assemble_stage

log "source bootstrap produced stage at $stage_out"
