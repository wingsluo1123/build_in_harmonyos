#!/usr/bin/env python3
"""Conan recipe — vde 2.3.3 (autotools)

VDE (Virtual Distributed Ethernet) is a virtual network infrastructure that
emulates Ethernet switches/cables between processes and VMs. It is built
with autotools and ships four public libraries (libvdeplug, libvdehist, libvdemgmt,
libvdesnmp) plus command-line tools (vde_switch, vde_plug, vde_plug2tap,
wirefilter, vdeterm, dpipe, unixcmd, vde_autolink).

OHOS adaptations:
  * The upstream release tarball ships no pre-generated `configure` (only
    configure.ac), so build() bootstraps with `autoreconf -fi` (automake /
    libtool come from tool_requires).
  * Native OHOS build: --build/--host are pinned to the
    aarch64-unknown-linux-ohos triplet accepted by the config.sub regenerated
    by automake 1.18 / libtool 2.5.4.
  * OHOS uses a musl-based libc. The kernel UAPI headers
    (<linux/socket.h>, pulled in via <linux/if.h> from <linux/if_tun.h>)
    redefine `struct sockaddr_storage`; the OHOS <sys/socket.h> guards its own
    copy with #ifndef __MUSL__, so -D__MUSL__ is added globally (same
    validated fix as the audispd recipe) to avoid the redefinition error in
    vde_plug2tap.c / vde_switch/tuntap.c which include both header families.
  * Optional components that need undeclared system libraries/devices are
    disabled: libwolfssl (--disable-cryptcab), libpcap (--disable-pcap),
    TUN/TAP (--disable-tuntap; there is no /dev/net/tun on HarmonyOS), and
    vde_router (--disable-router; OHOS musl lacks pthread_cancel, E085/E127).
  * OHOS: after install, every ELF under bin/ lib/ libexec/ is self-signed
    with binary-sign-tool + llvm-objcopy so the packaged programs and shared
    libraries can be executed/loaded on the device.
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _is_elf(path):
    try:
        with open(path, "rb") as handle:
            return handle.read(4) == b"\x7fELF"
    except OSError:
        return False


class VdeConan(ConanFile):
    name = "vde"
    version = "2.3.3"
    description = "Virtual Distributed Ethernet: virtual network switches, plugs and libraries"
    license = "GPL-2.0-or-later"
    homepage = "https://vde.sourceforge.net/"
    url = "https://github.com/virtualsquare/vde-2"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "vde is supported only on Linux/OHOS, not "
                + str(self.settings.os)
            )
        if self.settings.os == "OHOS" and self.settings.arch not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                "OHOS builds require armv8/aarch64"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build_requirements(self):
        # The GitHub tag archive ships no pre-generated `configure`
        # (autoreconf output is not committed upstream). The OHOS build host
        # provides autoconf but no automake/aclocal/libtoolize, so pull those
        # in as tool_requires (same approach as aribb24/adcli/audispd).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Native OHOS build: pin the GNU triplet so the (regenerated)
            # config.sub accepts aarch64-unknown-linux-ohos (config.guess
            # cannot identify the HarmonyOS uname output).
            tc.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-ohos",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
            # Optional components that require undeclared system libs/devices:
            #  - wolfssl -> vde_cryptcab (not in the OHOS sysroot)
            #  - libpcap -> vde_pcapplug / pdump plugin (not in the OHOS sysroot)
            #  - TUN/TAP -> libvdetap/vdetap (no /dev/net/tun on HarmonyOS)
            #  - pthread_cancel -> vde_router (OHOS musl lacks pthread cancellation, E085/E127)
            tc.configure_args.extend(
                [
                    "--disable-cryptcab",
                    "--disable-pcap",
                    "--disable-tuntap",
                    "--disable-router",
                ]
            )
            # E091: with -D__MUSL__ the OHOS <sys/socket.h> skips its
            # `struct sockaddr_storage` definition (guarded by #ifndef
            # __MUSL__), leaving only the kernel UAPI one.
            tc.extra_cflags.append("-D__MUSL__")
        if not self.options.shared:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        else:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        tc.generate()

    def _patch_mkstemp_umask(self):
        """E114/E011: HMDFS turns umask 077 + mktemp -d into an unwritable
        drwx--S--- dir, so configure/config.status cannot write its conf*
        temp files. Rewrite the generated configure to use umask 022."""
        cfg = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cfg):
            return
        with open(cfg, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        if "umask 077" in text:
            with open(cfg, "w", encoding="utf-8") as f:
                f.write(text.replace("umask 077", "umask 022"))
            self.output.info("patched generated configure: umask 077 -> 022")

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: parent dirs of the conan build tree deny getcwd(); pin PWD
        # plus a writable TMPDIR for configure/config.status (E114/E011).
        os.environ["PWD"] = self.build_folder
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, ".tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

        autotools = Autotools(self)
        # Bootstrap: the GitHub tag archive has no `configure`.
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info(
                "No pre-generated configure in source tree; "
                "bootstrapping with autoreconf -fi"
            )
            autotools.autoreconf(args=["-fi"])
        self._patch_mkstemp_umask()
        autotools.configure()
        autotools.make(args=["-j1"])

    def _write_install_shim(self):
        """E182/E188: on the OHOS worker the `install` command (toybox shim)
        fails with Error 64 for `-c`/multi-source installs (very common in
        autotools trees: `install -c -m 644 a.txt b.txt dir/`). Write a
        cp/mkdir based shim and point the generated Makefiles' INSTALL at it
        (same validated approach as aribb24/adms/libfstconst)."""
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    '  case "$1" in\n'
                    "    -p|-c) shift ;;\n"
                    '    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n'
                    '    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p "$@"; exit 0 ;;\n'
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "dest=\n"
                    'for arg in "$@"; do dest=$arg; done\n'
                    "count=$(($# - 1))\n"
                    'case "$dest" in\n'
                    "  */) is_dir=yes ;;\n"
                    '  *) if [ -d "$dest" ]; then is_dir=yes; else is_dir=no; fi ;;\n'
                    "esac\n"
                    'if [ "$is_dir" = yes ]; then\n'
                    '  mkdir -p "$dest"\n'
                    "  i=1\n"
                    '  for src in "$@"; do\n'
                    "    [ $i -gt $count ] && break\n"
                    '    cp -f "$src" "$dest/"\n'
                    '    if [ -n "$mode" ]; then\n'
                    '      chmod "$mode" "$dest/${src##*/}" 2>/dev/null || true\n'
                    "    fi\n"
                    "    i=$((i + 1))\n"
                    "  done\n"
                    "else\n"
                    "  [ $count -eq 1 ] || exit 1\n"
                    '  mkdir -p "$(dirname "$dest")"\n'
                    '  cp -f "$1" "$dest"\n'
                    '  if [ -n "$mode" ]; then\n'
                    '    chmod "$mode" "$dest" 2>/dev/null || true\n'
                    "  fi\n"
                    "fi\n"
                )
        except Exception:
            os.close(fd)
            raise
        os.chmod(install, 0o755)
        return install

    def _redirect_install_to_shim(self, shim_install):
        """Point every generated Makefile's INSTALL variable at the shim so
        `make install` never touches the device's limited `install` binary."""
        bf = self.build_folder
        for root, _dirs, files in os.walk(bf):
            for name in files:
                if name != "Makefile":
                    continue
                mp = os.path.join(root, name)
                with open(mp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "INSTALL =" not in content:
                    continue
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if stripped.startswith("INSTALL = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append(f"{indent}INSTALL = {shim_install}\n")
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    with open(mp, "w", encoding="utf-8") as f:
                        f.write("".join(lines))

    def _find_tool(self, name):
        p = shutil.which(name)
        if p and os.path.isfile(p):
            return p
        for candidate in (
            f"/data/service/hnp/bin/{name}",
            f"/storage/Users/currentUser/usr/local/bin/{name}",
            f"/usr/local/bin/{name}",
            f"/usr/bin/{name}",
        ):
            if os.path.isfile(candidate):
                return candidate
        return None

    def _sign_elf(self, path):
        """Self-sign one ELF for OHOS using binary-sign-tool + llvm-objcopy."""
        signer = self._find_tool("binary-sign-tool")
        objcopy = self._find_tool("llvm-objcopy")
        if not signer or not objcopy:
            self.output.warning(
                f"binary-sign-tool or llvm-objcopy unavailable; skipping codesign for {path}"
            )
            return
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("LD_LIBRARY")
        }
        self.output.info(f"signing ELF: {path}")
        unsigned = path + ".unsigned"
        signed = path + ".signed"
        shutil.copy2(path, unsigned)
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", unsigned],
            check=False,
            capture_output=True,
            env=env,
        )
        try:
            subprocess.check_call(
                [signer, "sign", "-inFile", unsigned, "-outFile", signed, "-selfSign", "1"],
                env=env,
            )
            os.replace(signed, path)
        finally:
            if os.path.exists(unsigned):
                try:
                    os.unlink(unsigned)
                except OSError:
                    pass
            if os.path.exists(signed):
                try:
                    os.unlink(signed)
                except OSError:
                    pass
        os.chmod(path, 0o755)

    def _sign_ohos_package(self, pkg_root):
        """Self-sign every regular ELF in the package (bin/ tools, lib/
        libraries, libexec/ helpers). Symlinks are skipped."""
        for top in ("bin", "lib", "libexec"):
            base = os.path.join(pkg_root, top)
            if not os.path.isdir(base):
                continue
            for entry in sorted(glob.glob(os.path.join(base, "**"), recursive=True)):
                if os.path.islink(entry) or not os.path.isfile(entry):
                    continue
                if _is_elf(entry):
                    self._sign_elf(entry)

    def package(self):
        autotools = Autotools(self)
        install_args = ["-j1"]
        if str(self.settings.os) == "OHOS":
            shim = self._write_install_shim()
            self._redirect_install_to_shim(shim)
            install_args.append(f"INSTALL={shim}")
        autotools.install(args=install_args)
        # libtool .la wrappers are not needed; drop them.
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for root, _dirs, files in os.walk(libdir):
                for name in files:
                    if name.endswith(".la"):
                        try:
                            os.remove(os.path.join(root, name))
                        except OSError:
                            pass
        # OHOS: self-sign package ELFs.
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_package(self.package_folder)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "vde")
        self.cpp_info.set_property("cmake_target_name", "vde::vde")
        self.cpp_info.set_property("pkg_config_name", "vdeplug")
        self.cpp_info.libs = [
            "vdesnmp", "vdemgmt", "vdeplug", "vdehist",
        ]
        self.cpp_info.system_libs = ["dl", "m"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
