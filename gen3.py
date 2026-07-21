#!/usr/bin/env python3
"""从 manifest.yaml 自动生成 conanfile.py"""
import os, re

TEMPLATE = '''#!/usr/bin/env python3
"""Conan recipe — __NAME__ __VERSION__ (auto-generated for Perl 5.42.2 rebuild)"""
import os, shutil
from conan import ConanFile
from conan.tools.files import get

class __CLASS__(ConanFile):
    name = "__NAME__"
    version = "__VERSION__"
    description = "__NAME__ __VERSION__"
    license = "Artistic-2.0"
    homepage = "__HOMEPAGE__"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        import os
        os.environ["PATH"] = "/storage/Users/currentUser/usr/local/bin:/storage/Users/currentUser/usr/local/perl_5.42.2/bin:" + os.environ.get("PATH", "")
        os.environ["PERL5LIB"] = "/storage/Users/currentUser/usr/local/perl_5.42.2/lib/5.42.2/aarch64-linux:/storage/Users/currentUser/usr/local/perl_5.42.2/lib/5.42.2"
        os.environ["C_INCLUDE_PATH"] = "/storage/Users/currentUser/usr/local/include"
        os.environ["LIBRARY_PATH"] = "/storage/Users/currentUser/usr/local/lib"

        src = self.source_folder
        self.run("perl Makefile.PL", cwd=src)
        # HarmonyOS: patch Makefile to add missing CRT linker flags
        makefile = os.path.join(src, "Makefile")
        if os.path.exists(makefile):
            with open(makefile, 'r') as mf:
                content = mf.read()
            if '-nostartfiles' not in content:
                content = content.replace('LDDLFLAGS =', 'LDDLFLAGS = -nostartfiles -nodefaultlibs -L/system/lib64 -lc')
                content = content.replace('OTHERLDFLAGS =', 'OTHERLDFLAGS = -nostartfiles -nodefaultlibs -L/system/lib64 -lc')
            with open(makefile, 'w') as mf:
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
        self.cpp_info.libs = []
'''

def parse_manifest(path):
    with open(path) as f:
        c = f.read()
    m = re.search(r'^software:\s*(\S+)', c, re.M)
    name = m.group(1) if m else ""
    m = re.search(r'^version:\s*"([^"]+)"', c, re.M)
    version = m.group(1) if m else ""
    m = re.search(r'url:\s*"([^"]+)"', c)
    url = m.group(1) if m else ""
    m = re.search(r'sha256:\s*"([^"]*)"', c)
    sha256 = m.group(1) if m else ""
    return name, version, url, sha256

def generate(pkg_dir):
    mpath = os.path.join(pkg_dir, "manifest.yaml")
    if not os.path.exists(mpath):
        return None
    name, version, url, sha256 = parse_manifest(mpath)
    if not name or not version:
        return None
    if not sha256:
        sha256 = "0" * 64
    cls = "".join(p.capitalize() for p in name.split("-"))
    cpan = name.replace("perl-", "").replace("-", "::")

    cd = os.path.join(pkg_dir, "conandata.yml")
    if not os.path.exists(cd):
        with open(cd, "w") as f:
            f.write('sources:\n  url: "' + url + '"\n  sha256: "' + sha256 + '"\n')

    out = TEMPLATE.replace("__NAME__", name).replace("__VERSION__", version)
    out = out.replace("__CLASS__", cls).replace("__HOMEPAGE__", "https://metacpan.org/pod/" + cpan)

    path = os.path.join(pkg_dir, "conanfile.py")
    with open(path, "w") as f:
        f.write(out)
    return path

if __name__ == "__main__":
    repo = "/storage/Users/currentUser/build_in_harmonyos"
    missing = [
        "perl-crypt-openssl-dsa/0.20","perl-dbd-pg/3.18.0","perl-dbd-sqlite/1.78",
        "perl-dbi/1.637","perl-devel-lexalias/0.05","perl-digest-md5/2.59",
        "perl-digest-sha1/2.13","perl-digest-sha3/1.01","perl-encode-hanextra/0.23",
        "perl-encode-jis2k/0.05-r2","perl-ev/4.35","perl-html-parser/3.83-r1",
        "perl-http-parser-xs/0.17-r9","perl-io-tty/1.20-r2","perl-ipc-sharelite/0.17-r14",
        "perl-json-maybexs/1.004008-r0","perl-json-xs/4.04","perl-list-moreutils-xs/0.430-r6",
        "perl-locale-gettext/1.07-r2","perl-match-simple-xs/0.002","perl-math-pari/2.030528-r1",
        "perl-math-random-mt-auto/6.23-r10","perl-mime-base64/3.16","perl-mouse/2.6.0-r0",
        "perl-netaddr-ip/4.079-r14","perl-object-pad/0.821-r0","perl-package-anon/0.05-r16",
        "perl-package-stash-xs/0.30-r5","perl-params-classify/0.015","perl-params-util/1.102",
        "perl-params-validate/1.31","perl-perlio-utf8_strict/0.010","perl-set-object/1.43-r0",
        "perl-xml-parser/2.59",
    ]
    ok = 0; fail = 0
    for pv in missing:
        parts = pv.split("/")
        d = os.path.join(repo, "archives", "p", parts[0], parts[1])
        if not os.path.isdir(d):
            d = os.path.join(repo, "archives", "p", parts[0], parts[1].split("-r")[0])
        if not os.path.isdir(d):
            print("X " + pv + ": dir not found"); fail += 1; continue
        r = generate(d)
        if r:
            print("O " + pv); ok += 1
        else:
            print("X " + pv + ": gen failed"); fail += 1
    print("\nGenerated: " + str(ok) + ", Failed: " + str(fail))
