# E-draft: Debian 归档源包（native/纯打包）OHOS Conan 适配口径（source-url-substvars）

- 首报：debian-cloud-images 0.0.9 @ OHOS PC aarch64（conan 2.29.1，2026-10-05）
- 分类：packaging / source / testing，severity=P2
- 适用：源包只含 `debian/`（无编译源码）的 Debian **native**（`3.0 (native)`）/ 下游 repack / 纯数据 / 空元包类适配

## 症状

1. `conan create` 前 `preflight`（PF7/R39）直接拦下 conandata 的源 URL：
   `PF7 源URL闸(R39): … Debian 下游重打包源` —— 即便照抄 Debian 官方归档地址
   （`https://deb.debian.org/debian/pool/…`）也命中。
2. `test_package` 消费者解析 `debian/source.substvars` 报
   `缺少字段 debian-cloud-images-packages:Depends`（字段明明存在）。

## 根因

1. **源 URL 口径**：PF7 把 Debian 归档主机
   `deb.debian.org` / `snapshot.debian.org` / `security.debian.org` / `archive.debian.org`
   一律判为「Debian 下游重打包源」而拦截；同时拦截代理类镜像与明文 http。
   → 直接用归档主机不合法，须改走**权威发行版镜像**（如清华 TUNA）。
2. **substvars 不是 deb822**：`debian/source.substvars` 采用 debhelper substvar 格式
   `name:subfield=value`（冒号后**无空格**、分隔符是 `=`）。常规 deb822 解析器
   （按 `key: value` 切分）会在**第一个冒号**处把键截断为 `debian-cloud-images-packages`，
   于是 `<pkg>:Depends` 这类字段读不到。

## 处方

1. **源 URL 用权威 distro 镜像**，完整性以官方 `.dsc` 为准：
   ```yaml
   sources:
     "<ver>":
       url: "https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/<l>/<pkg>/<pkg>_<ver>.tar.xz"
       sha256: "<取自官方 <pkg>_<ver>.dsc 的 Checksums-Sha256>"
   ```
   校验（官方 `.dsc` **只用于校验，不写入 conandata**）：
   ```bash
   curl -sS https://deb.debian.org/debian/pool/main/<l>/<pkg>/<pkg>_<ver>.dsc | grep -A2 Checksums-Sha256
   curl -sS -o /tmp/x.tar.xz <mirror-url> && sha256sum /tmp/x.tar.xz   # 两者须逐字一致
   ```
   （对照：本仓 `archives/d/debian-astro/5.0` 亦走 TUNA 镜像，先例一致。）
2. **substvars 专用解析**（禁止 deb822）：
   ```python
   fields = {}
   for line in open("debian/source.substvars", encoding="utf-8"):
       key, _, value = line.rstrip("\n").partition("=")
       if ":" in key:                       # 必须是 name:subfield 形态
           fields.setdefault(key.strip(), value)
   ```
   后按 `dpkg` 语义把 `control` 里的 `${pkg:Depends}` 占位符代入（未知占位符留空）。
3. **纯数据/空元包交付**：`package_type="unknown"`、`cpp_info` 全置空；`package()` 逐字保留
   `debian/` 打包树 + 数据本体；`build()` 只做本体自检（清单载体/生成器必须在且可解析），
   **不伪造编译**（R34）。上游多用例通常 N=0，须按 R51 附清点证据（无 `tests/`、`debian/tests`、
   `Testsuite`、构建系统 test target）。

## 识别线索

- conandata 源 URL 命中 `deb.debian.org`/`snapshot.debian.org` 等 ⇒ 换 distro 镜像 + 对齐 `.dsc` sha256。
- 源包 `debian/source/format` 为 `3.0 (native)` 且树内只有 `debian/` ⇒ 纯打包/数据类，按数据包流程。
- 解析 `*.substvars` 出现「字段存在却读不到」⇒ 立刻怀疑误用 deb822（冒号后无空格）。

## 反例（本次实测）

- 照抄 `https://deb.debian.org/debian/pool/main/d/debian-cloud-images/debian-cloud-images_0.0.9.tar.xz`
  → PF7 拦（"Debian 下游重打包源"）；改 TUNA 后 sha256 与官方 `.dsc` 完全一致，通过。
- 用 deb822 解析器读 `source.substvars` → `consumer: source.substvars 缺少字段 …:Depends`；
  改 `partition("=")` 后 `conan create` EXIT=0，`test_package` 16/16 通过。

## 与既有条目的关系

- 取源/PF7/%编码/.dsc PGP 锚定的通用侧，见草稿 `E712-draft-trinculo-source-pf7-percent-encoding`
  （"取源三关"）；本条目聚焦**Debian native/纯打包源包**这一子类，且**新增 substvars 非 deb822**
  的解析陷阱与纯数据/空元包交付口径，二者互补不重复。
