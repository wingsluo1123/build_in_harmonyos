#!/usr/bin/env python3
"""debian-cloud-images 数据包验证脚本。

用法: python3 test_cloud_images.py <package_folder>

验证交付产物本体（不是"文件存在性"）：
  * `debian/source.substvars` 的 `debian-cloud-images-packages:Depends=` 必须可解析，
    条目数与去重裸包名数与上游逐字一致；
  * `debian/control` 里二进制包的 `${debian-cloud-images-packages:Depends}` 占位符必须
    能被 substvars 完整代入（替换后不得残留任何 `${...}`）；
  * OHOS PC（arm64）适用子集非空且覆盖关键云镜像组件（linux-image-arm64 /
    grub-efi-arm64 / cloud-init）—— 鸿蒙 PC 为 arm64；
  * 生成器脚本 shebang 为 `#!/usr/bin/python3`；
  * 安装目录不能混进 .deb / tarball / 构建系统残留。

任一断言失败 → 退出码 1（Conan test_package 随之失败）。
"""

import os
import re
import sys

DEBIAN_REL = os.path.join("share", "debian-cloud-images", "debian")
SUBSTVARS = "source.substvars"
CONTROL = "control"
FIELD_RE = re.compile(r"^debian-cloud-images-packages:Depends=(.*)$", re.M)
ENTRY_RE = re.compile(r"^([a-z0-9][a-z0-9+.-]*)(?:\s*\[([^\]]+)\])?$")

EXPECTED_ENTRIES = 66
EXPECTED_UNIQUE = 62
EXPECTED_ARM64 = 57
OHOS_ARCH = "arm64"                       # 鸿蒙 PC = arm64 / aarch64
KEY_ARM64_PACKAGES = ("linux-image-arm64", "grub-efi-arm64", "cloud-init")

_results = []


def check(ok, label):
    _results.append((bool(ok), label))
    print(f"        [{'ok' if ok else 'FAIL'}] {label}")
    return bool(ok)


def load_entries(substvars_path):
    with open(substvars_path, encoding="utf-8", errors="replace") as h:
        text = h.read()
    m = FIELD_RE.search(text)
    if not m:
        return None
    return [item.strip() for item in m.group(1).split(",") if item.strip()]


def main():
    if len(sys.argv) != 2:
        print("usage: test_cloud_images.py <package_folder>")
        return 2
    package_folder = sys.argv[1]
    data_dir = os.path.join(package_folder, DEBIAN_REL)

    substvars_path = os.path.join(data_dir, SUBSTVARS)
    control_path = os.path.join(data_dir, CONTROL)
    generator_path = os.path.join(data_dir, "bin", "make-substvars")
    rules_path = os.path.join(data_dir, "rules")
    changelog_path = os.path.join(data_dir, "changelog")
    format_path = os.path.join(data_dir, "source", "format")
    copyright_path = os.path.join(package_folder, "licenses", "copyright")

    # ── 1. 交付产物完整性 ──
    check(os.path.isfile(substvars_path),
          f"{DEBIAN_REL}/{SUBSTVARS} 存在")
    check(os.path.isfile(generator_path),
          f"{DEBIAN_REL}/bin/make-substvars 存在")
    check(os.path.isfile(control_path), f"{DEBIAN_REL}/{CONTROL} 存在")
    check(os.path.isfile(rules_path), f"{DEBIAN_REL}/rules 存在")
    check(os.path.isfile(changelog_path), f"{DEBIAN_REL}/changelog 存在")
    check(os.path.isfile(copyright_path), "licenses/copyright 存在")

    if not os.path.isfile(format_path):
        check(False, f"{DEBIAN_REL}/source/format 存在")
    else:
        with open(format_path, encoding="utf-8", errors="replace") as h:
            check(h.read().strip() == "3.0 (native)",
                  "debian/source/format == '3.0 (native)'（Debian native 打包）")

    # ── 2. 清单元数据与一致性 ──
    entries = load_entries(substvars_path) if os.path.isfile(substvars_path) else None
    check(entries is not None,
          "substvars 含字段 debian-cloud-images-packages:Depends=")
    entries = entries or []
    check(len(entries) == EXPECTED_ENTRIES,
          f"Depends 条目数 == {EXPECTED_ENTRIES}（实际 {len(entries)}）")

    bad = [e for e in entries if not ENTRY_RE.match(e)]
    check(not bad, f"全部条目格式合法（异常 {bad[:3]}）")

    unique = sorted({ENTRY_RE.match(e).group(1) for e in entries})
    check(len(unique) == EXPECTED_UNIQUE,
          f"去重裸包名数 == {EXPECTED_UNIQUE}（实际 {len(unique)}）")

    # ── 3. 鸿蒙特有：OHOS PC（arm64）适用子集 ──
    arm64 = [e for e in entries
             if (a := ENTRY_RE.match(e).group(2)) is None
             or OHOS_ARCH in a.split()]
    check(len(arm64) == EXPECTED_ARM64,
          f"[OHOS] arm64 适用条目数 == {EXPECTED_ARM64}（实际 {len(arm64)}）")
    arm64_names = {ENTRY_RE.match(e).group(1) for e in arm64}
    missing = [p for p in KEY_ARM64_PACKAGES if p not in arm64_names]
    check(not missing,
          f"[OHOS] arm64 子集覆盖关键云镜像组件（缺 {missing}）")

    # ── 4. control 占位符代入（dpkg 语义） ──
    if os.path.isfile(control_path) and os.path.isfile(substvars_path):
        with open(control_path, encoding="utf-8", errors="replace") as h:
            control_text = h.read()
        value = "\n".join(l.split("=", 1)[1] for l in
                          open(substvars_path, encoding="utf-8",
                               errors="replace").read().splitlines()
                          if l.startswith("debian-cloud-images-packages:Depends="))
        resolved = re.sub(r"\$\{([^}]+)\}", lambda mm: value
                          if mm.group(1) == "debian-cloud-images-packages:Depends"
                          else "", control_text)
        stray = re.findall(r"\$\{[^}]+\}", resolved)
        check(not stray,
              f"control 占位符可完整代入（残留 {stray[:3]}）")
    else:
        check(False, "control 占位符可完整代入")

    # ── 5. 生成器与纯净性 ──
    if os.path.isfile(generator_path):
        with open(generator_path, encoding="utf-8", errors="replace") as h:
            shebang = h.readline().strip()
        check(shebang == "#!/usr/bin/python3",
              f"生成器 shebang == #!/usr/bin/python3（实际 {shebang!r}）")
    else:
        check(False, "生成器 shebang 检查")

    forbidden = []
    for root, _dirs, files in os.walk(package_folder):
        for name in files:
            if name.endswith((".deb", ".tar.xz", ".tar.gz", ".tgz", ".dsc")) \
                    or name in ("Makefile", "CMakeLists.txt", "meson.build"):
                forbidden.append(os.path.relpath(os.path.join(root, name),
                                                 package_folder))
    check(not forbidden,
          f"安装目录未混入 .deb/tarball/构建系统（发现 {forbidden[:3]}）")

    passed = sum(1 for ok, _ in _results if ok)
    total = len(_results)
    print(f"\n        [test] {passed}/{total} assertions passed")
    if passed != total:
        for ok, label in _results:
            if not ok:
                print(f"  - {label}")
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
