#!/usr/bin/env python3
"""从 manifest.yaml 自动生成 conanfile.py 模板"""
import os, sys, yaml

TEMPLATE = '''#!/usr/bin/env python3
"""Conan recipe — {name} {version} (auto-generated from manifest.yaml)"""
import os, shutil
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout

class {class_name}(ConanFile):
    name = "{name}"
    version = "{version}"
    description = "{description}"
    license = "{license}"
    homepage = "{homepage}"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"])

    def build(self):
        import os
        os.environ["PATH"] = "/storage/Users/currentUser/usr/local/bin:/storage/Users/currentUser/usr/local/perl_5.42.2/bin:" + os.environ.get("PATH", "")
        os.environ["PERL5LIB"] = "/storage/Users/currentUser/usr/local/perl_5.42.2/lib/5.42.2/aarch64-linux:/storage/Users/currentUser/usr/local/perl_5.42.2/lib/5.42.2"
        os.environ["C_INCLUDE_PATH"] = "/storage/Users/currentUser/usr/local/include"
        os.environ["LIBRARY_PATH"] = "/storage/Users/currentUser/usr/local/lib"

        src = self.source_folder
        self.run("perl Makefile.PL", cwd=src)
        self.run("make -j1", cwd=src)

    def package(self):
        dest = self.package_folder
        src = self.source_folder
        self.run(f"make install DESTDIR={dest}", cwd=src)

        # Copy .so files to lib/ for package checks
        site_arch = os.path.join(dest, "storage", "Users", "currentUser", "usr", "local", "perl_5.42.2", "lib", "site_perl", "5.42.2", "aarch64-linux")
        if not os.path.isdir(site_arch):
            # Try alternative paths
            for root, dirs, files in os.walk(dest):
                for f in files:
                    if f.endswith(".so"):
                        so_src = os.path.join(root, f)
                        rel = os.path.relpath(so_src, dest)
                        # Also copy to lib/
                        lib_dir = os.path.join(dest, "lib")
                        os.makedirs(lib_dir, exist_ok=True)
                        copy(self, "*.so", root, lib_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
'''

def generate_conanfile(pkg_dir):
    manifest_path = os.path.join(pkg_dir, "manifest.yaml")
    if not os.path.exists(manifest_path):
        return None

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    if not manifest:
        return None

    name = manifest.get("software", os.path.basename(os.path.dirname(pkg_dir)))
    version = manifest.get("version", "")

    source = manifest.get("source", {})
    url = source.get("url", "")
    sha256 = source.get("sha256", "")

    build = manifest.get("build", {})
    build_system = build.get("system", build.get("build_system", "perl"))

    class_name = "".join(p.capitalize() for p in name.split("-"))

    conandata = {
        "sources": {
            "url": url,
            "sha256": sha256 if sha256 else "0" * 64,
        }
    }

    # Write conandata.yml
    conandata_path = os.path.join(pkg_dir, "conandata.yml")
    if not os.path.exists(conandata_path):
        with open(conandata_path, "w") as f:
            yaml.dump(conandata, f, default_flow_style=False)

    # Generate conanfile.py
    conanfile = TEMPLATE.format(
        name=name,
        version=version,
        class_name=class_name,
        description=f"{name} {version}",
        license="Artistic-2.0",
        homepage=f"https://metacpan.org/pod/{name.replace('perl-', '').replace('-', '::')}",
    )

    conanfile_path = os.path.join(pkg_dir, "conanfile.py")
    with open(conanfile_path, "w") as f:
        f.write(conanfile)

    return conanfile_path

if __name__ == "__main__":
    repo_dir = "/storage/Users/currentUser/build_in_harmonyos"

    # 34 missing packages
    missing = [
        "perl-crypt-openssl-dsa/0.20",
        "perl-dbd-pg/3.18.0",
        "perl-dbd-sqlite/1.78",
        "perl-dbi/1.637",
        "perl-devel-lexalias/0.05",
        "perl-digest-md5/2.59",
        "perl-digest-sha1/2.13",
        "perl-digest-sha3/1.01",
        "perl-encode-hanextra/0.23",
        "perl-encode-jis2k/0.05-r2",
        "perl-ev/4.35",
        "perl-html-parser/3.83-r1",
        "perl-http-parser-xs/0.17-r9",
        "perl-io-tty/1.20-r2",
        "perl-ipc-sharelite/0.17-r14",
        "perl-json-maybexs/1.004008-r0",
        "perl-json-xs/4.04",
        "perl-list-moreutils-xs/0.430-r6",
        "perl-locale-gettext/1.07-r2",
        "perl-match-simple-xs/0.002",
        "perl-math-pari/2.030528-r1",
        "perl-math-random-mt-auto/6.23-r10",
        "perl-mime-base64/3.16",
        "perl-mouse/2.6.0-r0",
        "perl-netaddr-ip/4.079-r14",
        "perl-object-pad/0.821-r0",
        "perl-package-anon/0.05-r16",
        "perl-package-stash-xs/0.30-r5",
        "perl-params-classify/0.015",
        "perl-params-util/1.102",
        "perl-params-validate/1.31",
        "perl-perlio-utf8_strict/0.010",
        "perl-set-object/1.43-r0",
        "perl-xml-parser/2.59",
    ]

    generated = 0
    failed = 0
    for pkg_ver in missing:
        pkg_dir = os.path.join(repo_dir, "archives", "p", *pkg_ver.split("/"))
        if not os.path.isdir(pkg_dir):
            # Try without -rN
            base_ver = pkg_ver.split("/")[-1].split("-r")[0]
            pkg_name = pkg_ver.split("/")[0]
            pkg_dir = os.path.join(repo_dir, "archives", "p", pkg_name, base_ver)

        if not os.path.isdir(pkg_dir):
            print(f"❌ {pkg_ver}: 目录不存在")
            failed += 1
            continue

        result = generate_conanfile(pkg_dir)
        if result:
            print(f"✅ {pkg_ver}: {result}")
            generated += 1
        else:
            print(f"❌ {pkg_ver}: 生成失败")
            failed += 1

    print(f"\n生成: {generated}, 失败: {failed}")
