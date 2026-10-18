#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yaml-mode 0.0.16 test_package —— 适配自检(M 条,非上游用例)。

检查交付形态:数据本体与内容指纹、目录纯净、溯源齐备、许可交付、
无隐藏文件(JC5)、无构建产物、载荷清单与 conanfile.py::build() 同口径对账。

上游 N=4(ERT 测试依赖 emacs,CI 无 emacs,按 skipped 申报),替代方案是
consumer_ym.py 的独立第二实现,见 MANIFEST.yml。
"""
import hashlib
import os
import sys

# 与 conanfile.py / consumer_ym.py 同口径(三个文件必须同值同改)
PAYLOAD_MANIFEST = (
    ("share/emacs/site-lisp/yaml-mode/yaml-mode.el", 18356),
    ("share/doc/yaml-mode/upstream/README", 1972),
    ("share/doc/yaml-mode/upstream/Changes", 3930),
    ("share/doc/yaml-mode/upstream/Makefile", 812),
    ("share/doc/yaml-mode/upstream/test-files/allow-spaces-before-dash-1.yaml", 314),
    ("share/doc/yaml-mode/upstream/test-files/allow-spaces-before-dash-2.yaml", 151),
    ("share/doc/yaml-mode/upstream/test-files/allow-spaces-before-dash-3.yaml", 163),
    ("share/doc/yaml-mode/upstream/test-files/test-dash-newline-starts-sequence-1.yaml", 616),
    ("share/doc/yaml-mode/upstream/test-files/test-dash-newline-starts-sequence-2.yaml", 914),
    ("share/doc/yaml-mode/upstream/test-files/test-nested-map-single-line-match.yaml", 97),
    ("share/doc/yaml-mode/upstream/test-files/test-quotes-in-strings.yaml", 211),
    ("share/doc/yaml-mode/upstream/test-files/test-syntax-highlighting-list-of-dicts-containing-literal-block.yaml", 234),
    ("share/doc/yaml-mode/upstream/test-files/test-tricky-comments.yaml", 45),
    ("licenses/LICENSE.txt", 35149),
)
EXPECTED_FILES = len(PAYLOAD_MANIFEST)
EXPECTED_BYTES = sum(size for _name, size in PAYLOAD_MANIFEST)
EXPECTED_MANIFEST_DIGEST = "468bab40d95c19fcf752a8724f0fcabb7bf6e9bf2a95b79ce352c037dd057977"
PAYLOAD_SHA256 = "5e19a87a7e6cc5f9e3f829888eedadef37041e8d30a2526ce07f08108ccb71a5"

PKG = "yaml-mode"


def _p(package_folder, rel):
    return os.path.join(package_folder, rel.replace("/", os.sep))


def main(package_folder):
    print("== layout self-check (%s) ==" % PKG)
    checks = [0]
    fails = []

    def check(cond, what):
        checks[0] += 1
        if not cond:
            fails.append(what)
            print("  FAIL %s" % what)
        return bool(cond)

    # 1. 14 个交付文件逐项存在+字节数
    total = 0
    for rel, size in PAYLOAD_MANIFEST:
        p = _p(package_folder, rel)
        ok = check(os.path.isfile(p), "%s present" % rel)
        if ok:
            actual = os.path.getsize(p)
            check(actual == size, "%s == %d bytes (got %d)" % (rel, size, actual))
            total += actual

    # 2. 数据本体内容指纹
    main = _p(package_folder, "share/emacs/site-lisp/yaml-mode/yaml-mode.el")
    if check(os.path.isfile(main), "yaml-mode.el present"):
        with open(main, "rb") as handle:
            raw = handle.read()
        check(hashlib.sha256(raw).hexdigest() == PAYLOAD_SHA256,
              "yaml-mode.el sha256 pinned")

    # 3. 排序清单 sha256 对账(与 conanfile.py 同口径)
    digest = hashlib.sha256()
    for rel, size in sorted(PAYLOAD_MANIFEST):
        digest.update(("%s %d\n" % (rel, size)).encode("utf-8"))
    check(digest.hexdigest() == EXPECTED_MANIFEST_DIGEST,
          "manifest digest == pinned (got %s)" % digest.hexdigest())
    check(total == EXPECTED_BYTES, "total bytes == %d (got %d)"
          % (EXPECTED_BYTES, total))

    # 4. 数据目录纯净:site-lisp/yaml-mode/ 下只有 yaml-mode.el
    lispdir = _p(package_folder, "share/emacs/site-lisp/yaml-mode")
    if check(os.path.isdir(lispdir), "site-lisp/yaml-mode dir present"):
        check(sorted(os.listdir(lispdir)) == ["yaml-mode.el"],
              "site-lisp dir contains only yaml-mode.el (got %s)"
              % sorted(os.listdir(lispdir)))

    # 5. 无隐藏文件(JC5)
    hidden = []
    for root, _dirs, files in os.walk(package_folder):
        for name in files:
            if name.startswith("."):
                hidden.append(os.path.relpath(os.path.join(root, name), package_folder))
    check(not hidden, "no hidden files delivered (%s)" % hidden[:3])

    # 6. 无构建产物/归档(.elc 是 emacs 字节码=构建产物,明确不交付)
    junk = []
    for root, _dirs, files in os.walk(package_folder):
        for name in files:
            if name.endswith((".elc", ".tar.gz", ".tgz", ".zip", ".pyc", ".o", ".so")):
                junk.append(name)
    check(not junk, "no build artifacts delivered (%s)" % junk[:3])

    # 7. 无零字节文件(只扫交付树:share/ + licenses/;
    #    package 根目录的 conaninfo.txt 是 conan 注入的基础设施文件,不属于交付物)
    zeros = []
    for sub in ("share", "licenses"):
        root_base = os.path.join(package_folder, sub)
        if not os.path.isdir(root_base):
            continue
        for root, _dirs, files in os.walk(root_base):
            for name in files:
                full = os.path.join(root, name)
                if os.path.getsize(full) == 0:
                    zeros.append(os.path.relpath(full, package_folder))
    check(not zeros, "no zero-byte files (%s)" % zeros[:3])

    # 8. 上游 README/Changes 溯源价值抽查(README 提到 YAML mode)
    readme = _p(package_folder, "share/doc/yaml-mode/upstream/README")
    if check(os.path.isfile(readme), "README present"):
        with open(readme, "r", encoding="utf-8", errors="replace") as handle:
            head = handle.read(400)
        check("yaml" in head.lower(), "README mentions yaml")

    print("checks: %d, failures: %d" % (checks[0], len(fails)))
    if fails:
        for what in fails:
            print("  FAILED: %s" % what)
        return 1
    print("layout self-check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
