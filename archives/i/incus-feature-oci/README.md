# incus-feature-oci

Incus 的 **OCI 镜像运行支持契约元包**（Alpine 源包 `incus-feature` 的 noarch
子包 `oci()`：pkgdesc "Install packages required to run OCI images under
Incus"，`depends skopeo`，`install -d`，不安装任何自有文件）。

- 上游：https://github.com/lxc/incus （tag v7.2.0，与 incus-feature-agent/client 同一源码）
- 许可证：Apache-2.0
- 语言/构建：无编译（noarch 元包，custom）
- 先例模式：`archives/a/abuild-rootbld`（noarch 元包 + 薄包装 + 依赖契约）

## OHOS 适配要点

1. 上游 incus 7.2.0 **无独立 incus-oci 二进制**；OCI 镜像处理内嵌于 incus
   客户端（`client/oci_images.go`），运行时 `exec.LookPath("skopeo")`。
2. `bin/incus-oci` 薄包装：`--version` 报告元包版本；其余参数先执行上游
   同款 skopeo 契约检查（原始报错逐字一致），再 `exec incus "$@"`。
3. `skopeo` 未发布 ohpcd 制品仓（PF4 禁止声明未发布依赖），不在
   `requirements()` 声明；其在 OHOS 上的适配是独立任务。
4. `requirements()` 声明 **incus-feature-client/7.2.0**（OCI 能力消费者，
   已发布含二进制，conan download 实测）。

## 产物

```bash
incus-oci --version   # -> incus-feature-oci 7.2.0 (OCI image support contract for Incus)
```

## 已编译版本

- 7.2.0 (2026-10-15) — status: built
