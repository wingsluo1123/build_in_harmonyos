#!/usr/bin/env python3
"""Conan 2.x recipe — gst-plugins-rs-quinn 0.15.3 (Rust / cargo)

GStreamer plugin for QUIC transport built on quinn-rs, from the
gst-plugins-rs workspace (net/quinn crate, cdylib `gstquinn`).

Build: cargo build -p gst-plugin-quinn --release
Output: libgstquinn.so → installed to lib/gstreamer-1.0/ (plugin dir)

System dependencies (not conan packages):
  - gstreamer 1.28.x + glib 2.x: prebuilt cmd-pkgs packages
    (gstreamer-1.28.3-ohos-aarch64.tar.gz), installed on demand into
    $HOME/usr/local (addrwatch precedent). No conan recipe for the
    C gstreamer stack exists in this archive set.
  - Rust toolchain: harmonybrew cargo/rustc, else probe HNP paths
    (signal-tlsd precedent).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GstPluginsRsQuinnConan(ConanFile):
    name = "gst-plugins-rs-quinn"
    version = "0.15.3"
    description = "GStreamer plugin for QUIC transport (quinn-rs)"
    license = "MPL-2.0"
    homepage = "https://gitlab.freedesktop.org/gstreamer/gst-plugins-rs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gst-plugins-rs-quinn supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _locate_rust_toolchain(self):
        """Locate cargo/rustc: harmonybrew first, then PATH, then common roots.

        Returns (cargo, rustc) absolute paths or (None, None).
        """
        env = os.environ
        cargo = shutil.which("cargo") or env.get("HNP_CARGO")
        rustc = shutil.which("rustc") or env.get("HNP_RUSTC")

        # Harmonybrew is the preferred on-device source on OHOS
        brew_bin = os.path.expanduser("~/.harmonybrew/bin")
        if not cargo and os.path.isfile(os.path.join(brew_bin, "cargo")):
            cargo = os.path.join(brew_bin, "cargo")
            os.environ["PATH"] = brew_bin + ":" + env.get("PATH", "")
        if not rustc and os.path.isfile(os.path.join(brew_bin, "rustc")):
            rustc = os.path.join(brew_bin, "rustc")

        if not cargo or not rustc or not os.path.exists(cargo) or not os.path.exists(rustc):
            self.output.warning(
                "Rust toolchain not found (cargo=%s rustc=%s); "
                "build will be skipped. Install via harmonybrew: "
                "brew install rust" % (cargo, rustc)
            )
            return None, None
        return cargo, rustc

    def _ensure_system_deps(self):
        """Install gstreamer/glib prebuilt packages from cmd-pkgs if missing."""
        import io
        import ssl
        import tarfile
        import urllib.request

        prefix = os.path.expanduser("~/usr/local")
        pc_dir = os.path.join(prefix, "lib", "pkgconfig")

        def _have(pc_name):
            return os.path.isfile(os.path.join(pc_dir, pc_name + ".pc"))

        if _have("gstreamer-1.0") and _have("gstreamer-base-1.0"):
            return  # already installed

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        for pkg, ver in (("gstreamer", "1.28.3"), ("glib", "2.88.0")):
            if pkg == "glib" and _have("glib-2.0"):
                continue
            url = (
                "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
                f"download/pkgs/{pkg}-{ver}-ohos-aarch64.tar.gz"
            )
            self.output.info(f"Installing {pkg} {ver} from cmd-pkgs...")
            try:
                req = urllib.request.urlopen(url, context=ctx, timeout=180)
                tf = tarfile.open(fileobj=io.BytesIO(req.read()), mode="r:gz")
                tf.extractall(prefix)
                tf.close()
                self.output.info(f"  Installed {pkg} {ver}")
            except Exception as e:
                self.output.warning(f"  Failed to install {pkg} {ver}: {e}")

    def generate(self):
        # Create .cargo/config.toml so cargo can reach crates.io reliably
        cargo_dir = os.path.join(self.build_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        with open(os.path.join(cargo_dir, "config.toml"), "w") as f:
            f.write('[net]\ngit-fetch-with-cli = true\n')

    def build(self):
        apply_conandata_patches(self)

        cargo, rustc = self._locate_rust_toolchain()
        if not cargo:
            from conan.errors import ConanInvalidConfiguration
            raise ConanInvalidConfiguration(
                'Rust toolchain (cargo/rustc) not found on CI worker. '
                'Install via harmonybrew: brew install rust'
            )

        self._ensure_system_deps()

        # Writable TMPDIR: /tmp is read-only on OHOS
        tmpdir = os.path.join(os.path.expanduser("~/tmp"), "gst-quinn")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        # pkg-config must see the cmd-pkgs gstreamer/glib install
        pc_paths = [
            os.path.expanduser("~/usr/local/lib/pkgconfig"),
            os.path.expanduser("~/usr/local/lib64/pkgconfig"),
        ]
        old_pc = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = ":".join(pc_paths + ([old_pc] if old_pc else []))

        # Keep cargo artifacts inside the conan build folder
        os.environ["CARGO_TARGET_DIR"] = os.path.join(self.build_folder, "target")

        # Cargo's default linker is `cc`, which CI worker PATH lacks.
        # Point cargo at the conan-provided clang (signal-tlsd precedent).
        cc = (self.conf.get("tools.build:compiler_executables", {}) or {}).get("c") \
            or shutil.which("clang") or shutil.which("cc") or "clang"
        os.environ.setdefault("CC", cc)
        os.environ.setdefault("CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER", cc)

        self.run(
            f"{cargo} build -p gst-plugin-quinn --release",
            env="conanbuild",
        )

    def _sign_elf(self, path):
        """Re-sign an ELF after byte mutation (OHOS code-signing requirement).

        OHOS XPM requires dlopen'ed .so files to carry a .codesign hash.
        patchelf/objcopy invalidate it, so the section must be removed and
        the ELF re-signed (fftw 3.3.10.2 precedent). OHOS-only tools live
        under /data/service/hnp/bin.
        """
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.exists(objcopy) or not os.path.exists(signer):
            self.output.warning("sign tools not found; skipping re-sign")
            return
        # objcopy 移除 .codesign 节：无节时返回非零，|| true 容忍（首次签名前无此节）
        self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
        self.run(f'{signer} sign -inFile "{path}" -outFile "{path}" -selfSign 1')

    def package(self):
        src = os.path.join(self.build_folder, "target", "release", "libgstquinn.so")
        if os.path.isfile(src):
            dst_dir = os.path.join(self.package_folder, "lib", "gstreamer-1.0")
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, "libgstquinn.so")
            shutil.copy2(src, dst)

            if str(self.settings.os) == "OHOS":
                # E186: OHOS musl ldso ignores LD_LIBRARY_PATH for dlopen'ed
                # deps; the plugin must carry a RUNPATH to the system
                # gstreamer stack (cmd-pkgs installs into ~/usr/local).
                patchelf = "/data/service/hnp/bin/patchelf"
                if os.path.exists(patchelf):
                    user_local = os.path.expanduser("~/usr/local/lib")
                    self.run(
                        f'{patchelf} --set-rpath "$ORIGIN:{user_local}" --force-rpath "{dst}"'
                    )
                # patchelf invalidates the code signature → re-sign
                self._sign_elf(dst)
        else:
            self.output.warning("libgstquinn.so not found; package may be incomplete")

    def package_info(self):
        self.cpp_info.libdirs = ["lib/gstreamer-1.0"]
        self.cpp_info.libs = []  # plugin .so is dlopened by gstreamer, not linked
