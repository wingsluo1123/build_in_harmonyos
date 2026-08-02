#!/usr/bin/env sh
set -eu
if (set -o pipefail) 2>/dev/null; then
  set -o pipefail
fi

# Assemble a reviewable Swift OHOS stage from a completed source-bootstrap
# workspace. The script avoids probe-machine absolute paths by accepting all
# nonstandard locations through environment variables.

die() {
  echo "error: $*" >&2
  exit 1
}

log() {
  echo "[swift-stage] $*"
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

copy_file_flattened() {
  src=$1
  dst=$2
  [ -e "$src" ] || die "missing file: $src"
  mkdir -p "$(dirname "$dst")"
  cp -L "$src" "$dst"
  chmod 755 "$dst" 2>/dev/null || true
}

copy_data_file_flattened() {
  src=$1
  dst=$2
  [ -e "$src" ] || die "missing file: $src"
  mkdir -p "$(dirname "$dst")"
  cp -L "$src" "$dst"
}

copy_tree_flattened() {
  src=$1
  dst=$2
  [ -d "$src" ] || die "missing directory: $src"
  mkdir -p "$(dirname "$dst")"
  cp -R -L "$src" "$dst"
}

copy_runtime_libs() {
  src=$1
  [ -d "$src" ] || return 0
  for lib in "$src"/*.so "$src"/*.so.[0-9]*; do
    [ -f "$lib" ] && cp -L "$lib" "$tmp/lib/"
  done
  return 0
}

build_tinfo_shim_if_needed() {
  [ -e "$tmp/lib/libtinfo.so.6" ] && return 0
  if [ -n "${SWIFT_OHOS_TINFO_LIB:-}" ]; then
    copy_file_flattened "$SWIFT_OHOS_TINFO_LIB" "$tmp/lib/libtinfo.so.6"
    return 0
  fi
  [ "${SWIFT_OHOS_BUILD_TINFO_SHIM:-1}" = "1" ] || return 0

  cc=${SWIFT_OHOS_CC:-}
  if [ -z "$cc" ]; then
    cc=$(first_existing_file \
      "${HOME:-/storage/Users/currentUser}/validation/toolchain-bin/ohos-clang" \
      "$root/toolchain/ohos-clang" \
      "${HOME:-/storage/Users/currentUser}/usr/local/bin/clang-15") || true
  fi
  [ -n "$cc" ] || die "libtinfo.so.6 is missing and no OHOS C compiler was found"

  shim_c=$TMPDIR/libtinfo-shim.$$.c
  cat > "$shim_c" <<'EOF'
typedef struct term TERMINAL;
TERMINAL *cur_term;

int setupterm(const char *term, int fildes, int *errret) {
  (void)term;
  (void)fildes;
  if (errret) *errret = 0;
  return -1;
}

TERMINAL *set_curterm(TERMINAL *nterm) {
  TERMINAL *old = cur_term;
  cur_term = nterm;
  return old;
}

int del_curterm(TERMINAL *oterm) {
  if (cur_term == oterm) cur_term = 0;
  return 0;
}

int tigetflag(const char *capname) {
  (void)capname;
  return -1;
}

int tigetnum(const char *capname) {
  (void)capname;
  return -1;
}

char *tigetstr(const char *capname) {
  (void)capname;
  return (char *)-1;
}

int tputs(const char *str, int affcnt, int (*putc_fn)(int)) {
  (void)affcnt;
  if (!str || !putc_fn) return 0;
  while (*str) putc_fn((unsigned char)*str++);
  return 0;
}
EOF

  log "building minimal libtinfo.so.6 compatibility shim with $cc"
  if [ -x "$cc" ]; then
    "$cc" -shared -fPIC -Wl,-soname,libtinfo.so.6 -Wl,--code-sign -o "$tmp/lib/libtinfo.so.6" "$shim_c"
  else
    sh "$cc" -shared -fPIC -Wl,-soname,libtinfo.so.6 -Wl,--code-sign -o "$tmp/lib/libtinfo.so.6" "$shim_c"
  fi
  cp -L "$tmp/lib/libtinfo.so.6" "$tmp/lib/libtinfo.so"
  rm -f "$shim_c"
}

sign_elf_if_requested() {
  path=$1
  [ "${SWIFT_OHOS_SIGN:-0}" = "1" ] || return 0
  if [ -n "${SWIFT_OHOS_OBJCOPY:-}" ] && command -v "$SWIFT_OHOS_OBJCOPY" >/dev/null 2>&1; then
    "$SWIFT_OHOS_OBJCOPY" --remove-section .codesign "$path" 2>/dev/null || true
  elif command -v llvm-objcopy >/dev/null 2>&1; then
    llvm-objcopy --remove-section .codesign "$path" 2>/dev/null || true
  fi
  if [ -n "${SWIFT_OHOS_SIGN_TOOL:-}" ]; then
    "$SWIFT_OHOS_SIGN_TOOL" sign -inFile "$path" -outFile "$path" -selfSign 1
  elif command -v binary-sign-tool >/dev/null 2>&1; then
    binary-sign-tool sign -inFile "$path" -outFile "$path" -selfSign 1
  else
    die "SWIFT_OHOS_SIGN=1 but binary-sign-tool is not available"
  fi
}

write_manifest() {
  manifest=$tmp/STAGE-MANIFEST.txt
  {
    echo "swift-ohos-stage"
    echo "created_at=$(date '+%Y-%m-%dT%H:%M:%S%z' 2>/dev/null || date)"
    echo "source_root=$root"
    echo "bin_source=$bin_src"
    echo "swiftpm_bin_source=$swiftpm_bin_src"
    echo "swiftpm_lib_source=$swiftpm_lib_src"
    echo "swift_driver_lib_source=$swift_driver_lib_src"
    echo "lib_swift_source=$lib_swift_src"
    echo
    echo "[files]"
  } > "$manifest"
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "$tmp" && find . -type f | sort | sed 's#^\./##' | while IFS= read -r file; do
      sha256sum "$file"
    done) >> "$manifest"
  else
    (cd "$tmp" && find . -type f | sort | sed 's#^\./##') >> "$manifest"
  fi
}

root=${SWIFT_OHOS_BOOTSTRAP_ROOT:-${HOME:-/storage/Users/currentUser}/swift-mainline-ohos-src}
out=${SWIFT_OHOS_STAGE_OUT:-$root/swift-ohos-stage}
TMPDIR=${TMPDIR:-$root/tmp}
export TMPDIR

[ -d "$root" ] || die "bootstrap root not found: $root"
[ ! -e "$out" ] || die "stage output already exists, choose a new SWIFT_OHOS_STAGE_OUT: $out"

mkdir -p "$TMPDIR" 2>/dev/null || true
tmp=$out.tmp.$$
trap 'rm -rf "$tmp"' EXIT INT TERM
mkdir -p "$tmp/bin" "$tmp/lib"

bin_src=${SWIFT_OHOS_BIN_DIR:-}
if [ -z "$bin_src" ]; then
  bin_src=$(first_existing_dir \
    "$root/toolchain/bin" \
    "$root/build/swift-manual-ohos-linuxsys2/bin" \
    "$root/build/swift-manual-ohos-notests/bin" \
    "$root/build/swift-manual-ohos-finalprobe/bin") || true
fi
[ -n "$bin_src" ] || die "unable to locate Swift bin directory; set SWIFT_OHOS_BIN_DIR"

lib_swift_src=${SWIFT_OHOS_LIB_SWIFT_DIR:-}
if [ -z "$lib_swift_src" ]; then
  lib_swift_src=$(first_existing_dir \
    "$root/toolchain/lib/swift" \
    "$root/build/swift-manual-ohos-linuxsys2/lib/swift" \
    "$root/build/swift-manual-ohos-notests/lib/swift" \
    "$root/build/swift-manual-ohos-finalprobe/lib/swift") || true
fi
[ -n "$lib_swift_src" ] || die "unable to locate lib/swift; set SWIFT_OHOS_LIB_SWIFT_DIR"

swiftpm_bin_src=${SWIFT_OHOS_SWIFTPM_BIN_DIR:-}
if [ -z "$swiftpm_bin_src" ]; then
  swiftpm_bin_src=$(first_existing_dir \
    "$bin_src" \
    "$root/build/swiftpm-ohos-probe1/bin" \
    "$root/tmp/swiftpm-bin-manifestapi-copy-20260802-1045") || true
fi
[ -n "$swiftpm_bin_src" ] || die "unable to locate SwiftPM bin directory; set SWIFT_OHOS_SWIFTPM_BIN_DIR"

for tool in swift swiftc swift-frontend swift-autolink-extract; do
  copy_file_flattened "$bin_src/$tool" "$tmp/bin/$tool"
done

for tool in swift-serialize-diagnostics; do
  [ -e "$bin_src/$tool" ] && copy_file_flattened "$bin_src/$tool" "$tmp/bin/$tool"
done

if [ "${SWIFT_OHOS_INCLUDE_DRIVER_NEW:-0}" = "1" ] && [ -e "$bin_src/swift-driver-new" ]; then
  copy_file_flattened "$bin_src/swift-driver-new" "$tmp/bin/swift-driver-new"
fi

for tool in swift-build swift-package; do
  copy_file_flattened "$swiftpm_bin_src/$tool" "$tmp/bin/$tool"
done

for extra in "$swiftpm_bin_src"/PackageDescription.*; do
  [ -e "$extra" ] && copy_data_file_flattened "$extra" "$tmp/bin/$(basename "$extra")"
done
if [ -e "$swiftpm_bin_src/libPackageDescription.so" ]; then
  copy_file_flattened "$swiftpm_bin_src/libPackageDescription.so" "$tmp/bin/libPackageDescription.so"
fi

copy_tree_flattened "$lib_swift_src" "$tmp/lib/swift"
find "$tmp" -type f \( -name '*.bak' -o -name '*.bak-*' -o -name '*.pre-*' -o -name '*.so.bak-*' -o -name '*.so.tinfo-*' \) -exec rm -f {} \;

swiftpm_lib_src=${SWIFT_OHOS_SWIFTPM_LIB_DIR:-}
if [ -z "$swiftpm_lib_src" ]; then
  swiftpm_lib_src=$(first_existing_dir \
    "$(dirname "$swiftpm_bin_src")/lib" \
    "$root/build/swiftpm-ohos-probe1/lib") || true
fi

swift_driver_lib_src=${SWIFT_OHOS_SWIFT_DRIVER_LIB_DIR:-}
if [ -z "$swift_driver_lib_src" ]; then
  swift_driver_lib_src=$(first_existing_dir \
    "$root/build/swift-driver-ohos-probe5/lib" \
    "$root/build/swift-driver-ohos-probe4/lib") || true
fi

copy_runtime_libs "$(dirname "$lib_swift_src")"
copy_runtime_libs "$swiftpm_bin_src"
copy_runtime_libs "$swiftpm_lib_src"
copy_runtime_libs "$swift_driver_lib_src"
copy_runtime_libs "$root/toolchain/lib"
copy_runtime_libs "$root/deps/lib"

if [ -n "${SWIFT_OHOS_RUNTIME_DIRS:-}" ]; then
  old_ifs=$IFS
  IFS=:
  for runtime_dir in $SWIFT_OHOS_RUNTIME_DIRS; do
    copy_runtime_libs "$runtime_dir"
  done
  IFS=$old_ifs
fi

build_tinfo_shim_if_needed

for required in \
  bin/swift \
  bin/swiftc \
  bin/swift-frontend \
  bin/swift-autolink-extract \
  bin/swift-build \
  bin/swift-package \
  lib/swift; do
  [ -e "$tmp/$required" ] || die "assembled stage is missing $required"
done

find "$tmp/bin" "$tmp/lib" -type f \( -perm -100 -o -name '*.so' -o -name '*.so.*' \) | while IFS= read -r file; do
  sign_elf_if_requested "$file"
done

write_manifest
mv "$tmp" "$out"
trap - EXIT INT TERM

log "stage assembled at $out"
log "validate with: SWIFT_OHOS_STAGED_ROOT=$out conan create archives/s/swift/6.0.3 -pr:h ohos_4_1_armv8 -pr:b default"
