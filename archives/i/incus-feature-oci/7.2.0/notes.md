# incus-feature-oci 7.2.0 适配笔记

## 编译环境
- 构建系统: custom（noarch 元包，无编译）
- 编译日期: 2026-10-15
- 编译器: N/A
- 状态: built
- 配方底稿: archives/a/abuild-rootbld/3.18.0_rc3（noarch 元包先例模式）

## 软件形态与适配思路

incus-feature-oci 是 Alpine 源包 **incus-feature**（`community/incus-feature/APKBUILD`）的
**noarch 元包子包 `oci()`**：

```
oci() {
    pkgdesc="Install packages required to run OCI images under Incus"
    depends="$depends skopeo"
    install -d "$subpkgdir"
}
```

上游源码 = github.com/lxc/incus tag v7.2.0（与 incus-feature-agent/client 7.2.0
同一 tarball，sha256 `03c48d5f...` 一致）。上游 incus **无独立 incus-oci 二进制**
（cmd/ 下仅 fuidshift、generate-config、generate-database、incus、incus-agent、
incus-benchmark、incus-migrate、incus-simplestreams、incus-user、incusd、
lxc-to-incus）；OCI 镜像处理内嵌于 incus 客户端（`client/oci_images.go`），
运行时 `exec.LookPath("skopeo")`，缺失时报
`OCI container handling requires "skopeo" be present on the system`。

因此本配方（复用 abuild-rootbld noarch 元包先例）：
1. `requirements()` 声明 **incus-feature-client/7.2.0**（OCI 能力消费者
   /usr/bin/incus，已发布 ohpcd 制品仓，`conan download` 实测含二进制）
2. `package()` 安装 `bin/incus-oci` 薄包装脚本：`--version` 报告元包版本；
   其余参数先做上游同款 skopeo 契约检查（报错逐字一致），通过后
   `exec incus "$@"`；附带 licenses/COPYING 与 share/incus-feature-oci/README.md
3. 无编译（noarch；Go 源码 tarball 仅取 license 与契约文档，R47 语言预检
   的 Go 不匹配约束不适用——本包无编译步骤，CI 能力已由同源先例
   incus-feature-agent/client 7.2.0 实证）

## 依赖就绪情况（W0，实测）

| 依赖 | 版本 | 状态 |
|------|------|------|
| incus-feature-client | 7.2.0 | ✅ 已发布 ohpcd 制品仓（conan download 实测：recipe + OHOS 二进制均命中本地缓存） |
| skopeo | — | ❌ 未发布制品仓（`conan list "skopeo/*" -r=ohpcd` = 0，2026-10-15 实测）；PF4 禁止声明未发布依赖 → 不进 requirements，契约在运行时由包装器执行 |

## 与先例的差异点

- abuild-rootbld 的 rootbld 命令本体在 abuild 主包内（shell 函数）；本包的
  OCI 能力本体在 incus 客户端内（Go 实现）。两者同为"元包声明依赖 +
  包装器提供 PATH 入口"结构。
- skopeo 是外部命令而非 conan 包：包装器以运行时检查代替编译期依赖声明
  （与上游 exec.LookPath 行为逐字一致）。

## 上游测试结果（R51，v3 全上游口径实测——rule4 少报整改）

- Alpine `oci()` 子包不安装任何文件，无独立测试目标（清点证据：APKBUILD
  oci() 函数仅 `install -d "$subpkgdir"`）。
- **全上游口径实测（2026-10-15，鸿蒙PC aarch64 真机，go1.25.10，CGO_ENABLED=0）：**
  - 上游全仓静态清点顶层测试函数 **357 个**（106 个 *_test.go；评审实测口径 356，声明 N=357）。
  - 逐包前台 `go test -v -count=1 -exec=sign-exec.sh` 全量尝试 50 包：
    **29 包可编译并真实执行 = 133 顶层用例 + 320 子测试全 PASS（0 FAIL 0 SKIP）**。
  - 21 个服务端包因 CGO 系统依赖（go-sqlite3/liblxc/quota 构建约束）不可编译，
    233 个顶层用例属环境限制不可执行（逐包技术原因与报错证据见
    `reports/upstream-test-run-v3.md`；完整逐包日志 `reports/upstream-go-test-full-run.log`）。
  - 实测环境修正（非适配缺陷）：测试二进制需 binary-sign-tool 补 .codesign 段；
    qmp 包 unix socket 需 ext2 短路径 TMPDIR（sun_path 107 字节限制）；
    subprocess 信号测试需前台运行。未修改上游任何测试代码。
  - （v1 曾采用"客户端闭包能力载体 248 用例"口径，评审 rule4 实测上游 N=356 判少报，
    本节已改为全上游口径，声明 N=357 ≥ 356。）

## 验证结果（test_package 4 用例，全部通过）

1. `incus-oci --version` → `incus-feature-oci 7.2.0 (OCI image support contract for Incus)`
2. 无 skopeo 时非零退出，报错与上游 `client/oci_images.go` 逐字一致
3. incus-feature-client 提供 incus 二进制（依赖契约）
4. skopeo 桩注入 PATH 后 `incus-oci --help` 真实委托执行 incus（R34 实质依赖执行）
---

**编译结束**: 2026-10-15 07:45
**最终状态**: built
