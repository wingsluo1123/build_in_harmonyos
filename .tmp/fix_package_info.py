import os

BASE = "/storage/Users/currentUser/build_in_harmonyos/archives/p"

# (package_name, version, so_name, libdirs)
packages = [
    ("perl-crypt-openssl-dsa", "0.20", "DSA", "lib/auto/Crypt/OpenSSL/DSA"),
    ("perl-dbi", "1.637", "DBI", "lib/auto/DBI"),
    ("perl-devel-lexalias", "0.05", "LexAlias", "lib/auto/Devel/LexAlias"),
    ("perl-digest-md5", "2.59", "MD5", "lib/auto/Digest/MD5"),
    ("perl-digest-sha1", "2.13", "SHA1", "lib/auto/Digest/SHA1"),
    ("perl-digest-sha3", "1.01", "SHA3", "lib/auto/Digest/SHA3"),
    ("perl-encode-jis2k", "0.05-r2", "JIS2K", "lib/auto/Encode/JIS2K"),
    ("perl-ev", "4.37", "EV", "lib/auto/EV"),
    ("perl-html-parser", "3.83-r1", "Parser", "lib/auto/HTML/Parser"),
    ("perl-io-tty", "1.31", "Tty", "lib/auto/IO/Tty"),
    ("perl-ipc-sharelite", "0.17-r14", "ShareLite", "lib/auto/IPC/ShareLite"),
    ("perl-json-xs", "4.04", "XS", "lib/auto/JSON/XS"),
    ("perl-match-simple-xs", "0.002", "XS", "lib/auto/match/simple/XS"),
    ("perl-math-random-mt-auto", "6.23-r10", "Auto", "lib/auto/Math/Random/MT/Auto"),
    ("perl-mime-base64", "3.16", "Base64", "lib/auto/MIME/Base64"),
    ("perl-perlio-utf8_strict", "0.010", "utf8_strict", "lib/auto/PerlIO/utf8_strict"),
    ("perl-netaddr-ip", "4.079", "Util", "lib/auto/NetAddr/IP/Util"),
]

old_pattern = """    def package_info(self):
        self.cpp_info.libs = []"""

fixed_count = 0
for pkg_name, version, so_name, libdirs in packages:
    conanfile = os.path.join(BASE, pkg_name, version, "conanfile.py")
    with open(conanfile, "r") as f:
        content = f.read()
    
    if old_pattern not in content:
        print(f"WARNING: pattern not found in {conanfile}")
        continue
    
    new_pattern = f"""    def package_info(self):
        # The shared library is {so_name}.so (Perl XS extension)
        self.cpp_info.libs = ["{so_name}"]
        self.cpp_info.libdirs = ["{libdirs}"]
        # Perl module path for consumers
        self.cpp_info.includedirs = []"""
    
    content = content.replace(old_pattern, new_pattern)
    
    with open(conanfile, "w") as f:
        f.write(content)
    
    fixed_count += 1
    print(f"Fixed: {conanfile}")
    print(f"  libs = [\"{so_name}\"], libdirs = [\"{libdirs}\"]")

print(f"\nTotal: {fixed_count} conanfile.py package_info() fixed")
