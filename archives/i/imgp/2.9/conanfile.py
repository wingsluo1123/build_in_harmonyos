#!/usr/bin/env python3
"""Conan recipe for imgp — Python CLI image resizer/rotator.

imgp is a pure Python CLI tool that uses Pillow for image processing.
It is installed via pip from the PyPI source tarball.
System Python (pre-installed via cmd-pkgs) is used at build and run time.
"""
import os, sys

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class ImgpConan(ConanFile):
    name = "imgp"
    version = "2.9"
    description = "High-performance CLI batch image resizer & rotator"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/jarun/imgp"
    url = "https://github.com/jarun/imgp"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Use system Python (pre-installed via cmd-pkgs)
        python = "python3"

        # Change to the source directory since pip needs to find setup.py
        src_dir = self.source_folder

        # Install pillow (pre-built wheel for OHOS) separately
        self.run(f"{python} -m pip install pillow", env="conanrun")
        # Fix permissions on .so files installed by pillow (CI may have
        # restrictive umask that makes shared libraries unreadable).
        # Use os.walk to recursively find all .so files in the user
        # site-packages — glob.glob may miss files in subdirectories.
        chmod_script = os.path.join(self.build_folder, "fix_so_perms.py")
        with open(chmod_script, "w") as f:
            f.write("""import os
sp = os.path.expanduser('~/.local/lib/python3.12/site-packages')
for root, dirs, files in os.walk(sp):
    for f in files:
        if f.endswith('.so'):
            fp = os.path.join(root, f)
            os.chmod(fp, 0o644)
            print('fix', fp)
""")
        self.run(f"{python} '{chmod_script}'", env="conanrun")

        # Download and install setuptools from files.pythonhosted.org.
        # The CI's internal pip index (pypi.cnb.cool) does not have setuptools,
        # and the official PyPI (pypi.org) is not reachable from the CI network.
        # However, files.pythonhosted.org (the CDN) IS reachable.
        # The source tarball URL format is predictable:
        #   https://files.pythonhosted.org/packages/source/{first_letter}/{name}/{name}-{version}.tar.gz
        # Download to the build folder (which is always writable).
        # Use urlopen with a 120s timeout and chunked read with progress output
        # to prevent CI from killing the process due to no output.
        st_tarball = os.path.join(self.build_folder, "setuptools-75.8.0.tar.gz")
        st_url = "https://files.pythonhosted.org/packages/source/s/setuptools/setuptools-75.8.0.tar.gz"
        st_script = os.path.join(self.build_folder, "download_setuptools.py")
        with open(st_script, "w") as f:
            f.write(f"""import urllib.request, sys, socket
socket.setdefaulttimeout(30)
resp = urllib.request.urlopen('{st_url}', timeout=120)
total = int(resp.headers.get('Content-Length', 0))
downloaded = 0
with open('{st_tarball}', 'wb') as f:
    while True:
        chunk = resp.read(65536)
        if not chunk:
            break
        f.write(chunk)
        downloaded += len(chunk)
        if total:
            sys.stdout.write('\\rDownloading setuptools... ' + str(downloaded * 100 // total) + '%')
            sys.stdout.flush()
sys.stdout.write('\\n')
print('Download complete: ' + str(downloaded) + ' bytes')
""")
        self.run(f"{python} '{st_script}'", env="conanrun")
        self.run(f"{python} -m pip install '{st_tarball}' --no-build-isolation", env="conanrun")

        # Install imgp from source directory using --no-build-isolation
        # (setuptools is now available in the system Python)
        self.run(f"cd {src_dir} && {python} -m pip install --no-build-isolation .", env="conanrun")

    def package(self):
        # Find the installed files from the system Python
        python = "python3"
        python_bin = os.path.join(os.sep, "usr", "local", "bin")

        # Try to find the Python bin directory
        import subprocess
        try:
            result = subprocess.run([python, "-c", "import sys; print(sys.executable)"],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                python_bin = os.path.dirname(result.stdout.strip())
        except Exception:
            pass

        # Copy imgp executable
        copy(self, "imgp*", python_bin, os.path.join(self.package_folder, "bin"))

        # Try to find installed imgp files
        py_ver = "python3.12"
        for site_dir in [
            f"/usr/local/lib/{py_ver}/site-packages",
            f"/usr/lib/{py_ver}/site-packages",
            os.path.expanduser(f"~/.local/lib/{py_ver}/site-packages"),
            os.path.expanduser(f"~/usr/local/lib/{py_ver}/site-packages"),
        ]:
            if os.path.isdir(site_dir):
                dest = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
                # Copy imgp module
                copy(self, "imgp.py*", site_dir, dest)
                copy(self, "imgp-*.egg-info*", site_dir, dest)
                # Copy PIL (pillow) - runtime dependency
                pil_dir = os.path.join(site_dir, "PIL")
                if os.path.isdir(pil_dir):
                    copy(self, "*", pil_dir, os.path.join(dest, "PIL"))
                # Copy PIL dist-info
                for f in os.listdir(site_dir):
                    if f.startswith("PIL") and f.endswith("dist-info"):
                        copy(self, f, site_dir, dest)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []