#!/usr/bin/env python3
r"""Debian 云镜像「所需软件包清单」消费者用例 —— 按 Debian 打包语义**消费**已安装的交付数据。

用法: python3 consumer_cloud_images.py <package_folder> [out_dir]

端到端消费链路（不是文件存在性断言）：

  1. `share/debian-cloud-images/debian/control` —— 二进制包 `debian-cloud-images-packages`
     的声明，其 `Depends:` 是打包期占位符 `${debian-cloud-images-packages:Depends}`；
  2. `share/debian-cloud-images/debian/source.substvars` —— 打包期生成的 substvar，
     提供 `debian-cloud-images-packages:Depends=` 字段（逗号分隔的包条目，条目可带
     `[arch1 arch2]` 架构限定）；
  3. 按 dpkg 的替换语义把 control 的占位符代入 → 得到最终 Depends 清单；
  4. 展开条目 → 去重裸包名 → 过滤出 OHOS PC（arm64）适用子集（无限定 = 全架构适用）。

输出（给 out_dir 时落盘，否则仅 stdout；CI/测试用 stdout 形态，不在源码树落文件）：
  <out_dir>/dependencies.txt   最终 Depends 清单（每行一个条目）
  <out_dir>/packages.txt       去重后的裸包名
  <out_dir>/packages-arm64.txt OHOS PC（arm64）适用裸包名

退出码：任一环节缺失/解析为空/arm64 子集为空 → 非 0。
"""

import os
import re
import sys

DEBIAN_REL = os.path.join("share", "debian-cloud-images", "debian")
CONTROL = "control"
SUBSTVARS = "source.substvars"
BIN_STANZA = "debian-cloud-images-packages"
SUBSTVAR_FIELD = "debian-cloud-images-packages:Depends"

# 条目形如: name  或  name [arch1 arch2]
ENTRY_RE = re.compile(r"^([a-z0-9][a-z0-9+.-]*)(?:\s*\[([^\]]+)\])?$")


def read_binary_stanza(control_text):
    """定位二进制包 `debian-cloud-images-packages` 的段落 → 字段字典。"""
    stanzas, cur = [], {}
    for raw in control_text.splitlines():
        if raw and raw[0] in " \t":
            if cur:
                k = list(cur)[-1]
                cur[k] += "\n" + raw.strip()
            continue
        if not raw.strip():
            if cur:
                stanzas.append(cur)
                cur = {}
            continue
        if ":" not in raw:
            continue
        k, v = raw.split(":", 1)
        cur.setdefault(k.strip(), v.strip())
    if cur:
        stanzas.append(cur)
    for st in stanzas:
        if st.get("Package") == BIN_STANZA:
            return st
    raise SystemExit(f"consumer: control 中找不到 Package: {BIN_STANZA} 段")


def parse_substvars(text):
    """解析 debhelper substvars 文本：每行 `name:subfield=value`（值可含逗号/空格）。

    注意：substvars **不是 deb822**（没有冒号后的空格），必须按 `=` 切分。
    """
    out = {}
    for raw in text.splitlines():
        raw = raw.rstrip("\r\n")
        if not raw or "=" not in raw:
            continue
        key, _, value = raw.partition("=")
        key = key.strip()
        if ":" in key:
            out.setdefault(key, value)
    return out


def substitute(depends_value, substvars):
    """按 dpkg 语义替换 ${field} 占位符；未知占位符（如 misc:Depends）视为空。"""
    def repl(m):
        return substvars.get(m.group(1), "")
    return re.sub(r"\$\{([^}]+)\}", repl, depends_value)


def expand_entries(depends_value):
    """逗号切分 → 去空白 → 解析 (name, arches|None)；非法条目抛错。"""
    out = []
    for part in depends_value.replace("\n", " ").split(","):
        part = part.strip()
        if not part:
            continue
        m = ENTRY_RE.match(part)
        if not m:
            raise SystemExit(f"consumer: 非法依赖条目 {part!r}")
        name, arches = m.group(1), m.group(2)
        out.append((name, arches.split() if arches else None))
    return out


def main():
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        return 2
    package_folder = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) == 3 else None

    data_dir = os.path.join(package_folder, DEBIAN_REL)
    control_path = os.path.join(data_dir, CONTROL)
    substvars_path = os.path.join(data_dir, SUBSTVARS)
    for path in (control_path, substvars_path):
        if not os.path.isfile(path):
            raise SystemExit(f"consumer: 缺少 {path}")

    with open(control_path, encoding="utf-8", errors="replace") as h:
        stanza = read_binary_stanza(h.read())
    depends_value = stanza.get("Depends", "")
    if SUBSTVAR_FIELD not in depends_value:
        raise SystemExit(
            f"consumer: control 的 Depends 未引用 ${{{SUBSTVAR_FIELD}}} 占位符")

    with open(substvars_path, encoding="utf-8", errors="replace") as h:
        substvars = parse_substvars(h.read())
    if SUBSTVAR_FIELD not in substvars:
        raise SystemExit(f"consumer: {SUBSTVARS} 缺少字段 {SUBSTVAR_FIELD}")

    final_depends = substitute(depends_value, substvars)
    entries = expand_entries(final_depends)
    if not entries:
        raise SystemExit("consumer: 替换后 Depends 清单为空")

    raw_names = sorted({n for n, _ in entries})
    arm64_names = sorted({n for n, arches in entries
                          if arches is None or "arm64" in arches})
    if not arm64_names:
        raise SystemExit("consumer: OHOS PC（arm64）适用子集为空")

    print(f"        [consumer] {BIN_STANZA}: Depends 条目 {len(entries)} 个"
          f"（去重裸包名 {len(raw_names)}）")
    print(f"        [consumer] OHOS PC（arm64）适用裸包名 {len(arm64_names)} 个")
    for name, arches in entries[:5]:
        print(f"        [consumer]   - {name}"
              + (f" [{ ' '.join(arches) }]" if arches else " [all]"))
    print(f"        [consumer]   ...（共 {len(entries)} 条）")

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "dependencies.txt"), "w",
                  encoding="utf-8") as h:
            h.write("\n".join(e + (f" [{' '.join(a)}]" if a else "")
                              for e, a in entries) + "\n")
        with open(os.path.join(out_dir, "packages.txt"), "w",
                  encoding="utf-8") as h:
            h.write("\n".join(raw_names) + "\n")
        with open(os.path.join(out_dir, "packages-arm64.txt"), "w",
                  encoding="utf-8") as h:
            h.write("\n".join(arm64_names) + "\n")
        print(f"        [consumer] 输出: {out_dir}/dependencies.txt,"
              " packages.txt, packages-arm64.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
