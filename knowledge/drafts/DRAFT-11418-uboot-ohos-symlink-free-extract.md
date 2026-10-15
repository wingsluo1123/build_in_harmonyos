# DRAFT-11418 — OHOS HMDFS 全域禁 symlink 压垮 tarfile.extractall：容错解包器（常规文件先落盘 + 链接 EPERM 物化为内容副本）

- **条目 ID**: `DRAFT-11418-uboot-ohos-symlink-free-extract`
- **严重度**: 1（source() 首轮即炸、无任何容错路径；但修复模式固定可复用）
- **类别**: filesystem, permissions, conan, packaging
- **触发工具/阶段**: tarfile | conan | extractall | symlink — conan_source
- **来源**: u-boot 2026.07 适配（task #11418，OHOS PC 真机 2026-09-29，上游 denx 发行包 + 补丁）

## 错误特征

```
PermissionError: [Errno 1] Operation not permitted: '<src>/COPYING'
conan: ERROR: Error in source() method — tarfile extractall 中断
```

（首轮用 conan `files.get()` 解包，在归档内第一个 symlink 成员处 EPERM 硬失败）

## 场景

OHOS HMDFS（应用存储文件系统）**全域禁止 symlink 创建**：`os.symlink()`
对任何目标/位置都 EPERM，与路径深度、属主、mode 无关（实测新建文件
同样被拒，即内核/文件系统级策略）。Python tarfile 的 extractall 对链接
成员直接 `os.symlink()`/`os.link()`，无逐成员容错——归档内第一个链接
即抛 PermissionError 终止整个解包。而 conan 社区配方 source() 的惯用
写法 `files.get(self, **self.conan_data["sources"])` 内部正是
extractall，在 Linux 构建机无感、在 OHOS 必炸。

任何发行 tar 含 symlink 的上游都踩中（惯例：COPYING 重定向、dts 别名、
board 目录链、脚本别名等）。u-boot 2026.07 发行包含 ~25 个 symlink：
`COPYING → Licenses/gpl-2.0.txt`、多个 dts 别名、xilinx board 目录链、
`tools/binman → main.py` 等；**目录链接**（整目录别名）需整树物化。

## 推荐方案（conanfile.py 内嵌，真机验证）

- 弃用 `files.get()`，source() 改 `download()`（落常规文件）+
  自定义容错解包器：
  - **pass 1** 顺序落盘全部常规文件/目录（保证链接目标先存在）；
  - **pass 2** 逐个尝试 `os.symlink()` 直建，EPERM 时按链接目标物化：
    文件链接 → 复制目标内容（恢复 tar mode 位）；硬链接 → 跨 fs 安全
    的副本；目录链接 → 目标目录整树物化到链接位置（子链接留给
    pass 2 主循环）；链式 symlink → 递归解析（深度上限 4，防环）；
  - 物化必须**恢复 +x 权限位**（构建脚本依赖；`open()` 默认 0644）；
  - 构建对源树只读消费，链接物化为副本语义等价（R5 同源治理：包内
    零软链，产物目录无链接）。
- 通用性：该解包器与 u-boot 无关，可原样搬到任何 tar 发行配方。

## 影响

适用任何「发行 tar 包含 symlink + conan 配方」在 OHOS 的适配：Linux
构建机无感（extractall 正常），OHOS 必炸。凡 source() 用 `files.get()`
的配方都要换成 `download()` + 容错解包。这是 OHOS 文件系统级通用约束，
与具体上游无关。

## 恢复

若目标文件系统允许 mount 到可 symlink 的 fs（tmpfs/网络盘），可绕开
物化；但 HMDFS 应用存储不可换。物化副本的唯一风险是「构建行为依赖
链接身份」（如脚本按 readlink 判断来源）——此类上游极罕见，遇之需在
物化后补一个路径文件注明物化来源。

## 证据链

真机 2026-09-29（上游 denx 2026.07 发行包 + 补丁，reports/）：

- 首轮 source() 用 conan `files.get()` 在第一个 symlink 成员 EPERM
  中断（build.log 实证）；
- 改造后 source() 全链通过：~25 链接成员全部物化，构建期 COPYING
  许可复制、dts 别名引用、xilinx board 目录均正常消费；
- 全树构建 sandbox + qemu_arm64 通过（补丁 0001 的 O= 分离构建
  source 链接物化同源验证：make 输出
  `NOTICE: ./source materialized as path file`）；
- 详见 conanfile.py `source()`/`_extract_tolerant`/`_materialize_link`。

## 验证命令

```sh
conan create . -pr:h=ohos-aarch64.profile -pr:b=ohos-aarch64.profile
# source() 阶段：修复前 EPERM 中断；修复后全部链接物化、构建推进
```

## 局限

1. 物化依赖链接目标在归档内可解析（相对链接名 + 链式递归上限 4）；
2. 物化副本不保留链接身份（readlink 依赖的上游不覆盖）；
3. 硬链接物化为副本会放大源树体积（u-boot 发行包仅个别硬链接，
   可接受）。
