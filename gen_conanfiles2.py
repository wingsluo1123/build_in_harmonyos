#!/usr/bin/env python3
"""从 manifest.yaml 自动生成 conanfile.py（使用正则解析，非 YAML）"""
import os, re, sys

TEMPLATE = '''#!/usr/bin/env python3
"""Conan recipe — {name} {version} (auto-generated for Perl 5.42.2 rebuild)"""
import os, shutil
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

class {class_name}(ConanFile):
    name = "{name}"
    version = "{version}"
    description = "{name} {version}"
    license = "FIXME_VERIFY_LICENSE"  # FIXME: verify actual license (Artistic-1.0, Artistic-2.0, etc.)
    homepage = "{homepage}"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        src = self.source_folder
        apply_conandata_patches(self)
        self.run("perl Makefile.PL", cwd=src)
        # HarmonyOS: patch Makefile for CRT linker flags (R32: OHOS-only)
        if self.settings.os == "OHOS":
            makefile = os.path.join(src, "Makefile")
            if os.path.exists(makefile):
                with open(makefile, "r") as mf:
                    content = mf.read()
                if "-nostartfiles" not in content:
                    content = content.replace("LDDLFLAGS =", "LDDLFLAGS = -nostartfiles -nodefaultlibs -L/system/lib64 -lc")
                with open(makefile, "w") as mf:
                    mf.write(content)
        self.run("make -j1", cwd=src)

    def package(self):
        dest = self.package_folder
        src = self.source_folder
        self.run("make install DESTDIR=" + dest, cwd=src)

        for root, dirs, files in os.walk(dest):
            for fn in files:
                if fn.endswith(".so"):
                    lib_dir = os.path.join(dest, "lib")
                    os.makedirs(lib_dir, exist_ok=True)
                    shutil.copy2(os.path.join(root, fn), lib_dir)

    def package_info(self):
        # FIXME: replace "FIXME_SO_NAME" with the actual .so name (e.g. "DSA", "MD5")
        self.cpp_info.libs = ["{lib_name}"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
'''

def parse_manifest(path):
    """用正则提取 manifest.yaml 中的关键信息"""
    with open(path) as f:
        content = f.read()

    # 提取 version
    m = re.search(r'^version:\s*"([^"]+)"', content, re.M)
    version = m.group(1) if m else ""

    # 提取 software
    m = re.search(r'^software:\s*(\S+)', content, re.M)
    name = m.group(1) if m else os.path.basename(os.path.dirname(path))

    # 提取 url
    m = re.search(r'url:\s*"([^"]+)"', content)
    url = m.group(1) if m else ""

    # 提取 sha256
    m = re.search(r'sha256:\s*"([^"]*)"', content)
    sha256 = m.group(1) if m else ""

    return name, version, url, sha256

def generate(pkg_dir):
    manifest = os.path.join(pkg_dir, "manifest.yaml")
    if not os.path.exists(manifest):
        return None

    name, version, url, sha256 = parse_manifest(manifest)
    if not name or not version:
        return None

    # sha256 必须从 manifest.yaml 获取，禁止生成假值
    if not sha256:
        print(f"ERROR: {pkg_dir} manifest.yaml 缺少 sha256，请手动补充真实值", file=sys.stderr)
        return None

    class_name = "".join(p.capitalize() for p in name.split("-"))

    # 写 conandata.yml
    conandata_path = os.path.join(pkg_dir, "conandata.yml")
    if not os.path.exists(conandata_path):
        with open(conandata_path, "w") as f:
            f.write(f'sources:\n  url: "{url}"\n  sha256: "{sha256}"\n')

    # 生成 conanfile.py
    cpan_name = name.replace("perl-", "").replace("-", "::")
    # lib_name cannot be auto-derived: Perl XS .so names use mixed case (DSA.so, MD5.so)
    # that doesn't follow a deterministic pattern from the package name.
    # Use a placeholder that forces manual correction.
    lib_name = "FIXME_SO_NAME"
    conanfile = TEMPLATE.format(
        name=name, version=version, class_name=class_name,
        homepage=f"https://metacpan.org/pod/{cpan_name}",
        lib_name=lib_name,
    )

    path = os.path.join(pkg_dir, "conanfile.py")
    with open(path, "w") as f:
        f.write(conanfile)
    return path

if __name__ == "__main__":
    repo = os.path.dirname(os.path.abspath(__file__))
    missing = [
        "perl-crypt-openssl-dsa/0.20","perl-dbd-pg/3.18.0","perl-dbd-sqlite/1.78",
        "perl-dbi/1.637","perl-devel-lexalias/0.05","perl-digest-md5/2.59",
        "perl-digest-sha1/2.13","perl-digest-sha3/1.01","perl-encode-hanextra/0.23",
        "perl-encode-jis2k/0.05-r2","perl-ev/4.37","perl-html-parser/3.83-r1",
        "perl-http-parser-xs/0.17-r9","perl-io-tty/1.31","perl-ipc-sharelite/0.17-r14",
        "perl-json-maybexs/1.004008-r0","perl-json-xs/4.04","perl-list-moreutils-xs/0.430-r6",
        "perl-locale-gettext/1.07-r2","perl-match-simple-xs/0.002","perl-math-pari/2.030528-r1",
        "perl-math-random-mt-auto/6.23-r10","perl-mime-base64/3.16","perl-mouse/2.6.0-r0",
        "perl-netaddr-ip/4.079","perl-object-pad/0.821-r0","perl-package-anon/0.05-r16",
        "perl-params-util/1.102",
        "perl-params-validate/1.31","perl-perlio-utf8_strict/0.010","perl-set-object/1.43-r0",
        "perl-xml-parser/2.59",
    ]
    ok = 0; fail = 0
    for pv in missing:
        parts = pv.split("/")
        pkg_name, ver = parts[0], parts[1]
        d = os.path.join(repo, "archives", "p", pkg_name, ver)
        if not os.path.isdir(d):
            base_ver = ver.split("-r")[0]
            d = os.path.join(repo, "archives", "p", pkg_name, base_ver)
        if not os.path.isdir(d):
            print(f"❌ {pv}: 目录不存在")
            fail += 1; continue
        r = generate(d)
        if r:
            print(f"✅ {pv}")
            ok += 1
        else:
            print(f"❌ {pv}: 生成失败")
            fail += 1
    print(f"\n生成: {ok}, 失败: {fail}")
