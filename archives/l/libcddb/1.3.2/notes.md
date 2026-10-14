# libcddb 1.3.2 适配笔记（OHOS PC / aarch64 / musl）

## 结论

- 状态：**built**（`conan create` 全链路通过，含消费者测试）
- 源：Debian 归档的 pristine orig tarball
  `https://ftp.debian.org/debian/pool/main/libc/libcddb/libcddb_1.3.2.orig.tar.gz`
  （sha256 `93f7860bdafa26f21d60a4d0ce2a8e55a0573841116aade79d90b64651b2b664`，实测下载并校验）
- 构建系统：autotools（发布 tarball 自带 configure）
- 补丁：3 段（config.guess / config.sub / configure）
- 消费者测试：断言 `CDDB_VERSION` 自报 `1.3.2`（头文件与库配套）、`cddb_new()`/`cddb_destroy()`
  生命周期、`cddb_errno()` 新建连接初值为 0

## 源的选择（为什么不是 sourceforge）

上游官方发布位在 sourceforge（`downloads.sourceforge.net/.../libcddb-1.3.2.tar.bz2`），
但本沙箱内 sourceforge 及其各镜像**全部不可达**（实测 `Connection refused` / 0 字节响应）：

```
libcddb-1.3.2.tar.bz2   FAIL (0B)
netcologne/freefr/phoenixnap 等镜像   FAIL (0B)
```

→ 改用 Debian 归档的 **pristine orig tarball**：内容等同上游发布物（解包目录名同样是
`libcddb-1.3.2/`），且 sha256 可在本机核验；替代理由已写入 `conandata.yml` 与该文件。

## 配置选择

| 开关 | 原因 |
|---|---|
| `--disable-rpath` | 不把构建期路径写进产物（由 Conan 运行期环境负责） |
| `--enable-shared` + `--disable-static` | 交付共享库，与同族依赖一致 |

charset 转换：libcddb 的 iconv 探测会命中 **musl libc 内置 iconv**（configure 实测
`checking for iconv... yes` / `checking for working iconv... yes`），因此**不引入 libiconv 依赖**。

## 踩坑（可迁移）

### 1. HMDFS 上 `umask 077` 让 configure 直接失败

现象：`config.status: error: could not setup config files machinery`。
根因与修法与同批 libbluray 完全一致：configure 用 `(umask 077 && mktemp -d "./confXXXXXX")`
建 0700 临时目录，HMDFS 的 UID 映射下不可写 → patch 0003 改为 `umask 022`。

### 2. 补丁前缀必须是 `a/<相对源树根>` 的形式

首次生成的 `0003-configure.patch` 头为 `--- ca/configure` / `+++ cb/configure`
（因为我用 `diff -ruN ca cb` 生成），conan 应用时报
`source/target file does not exist: --- b'ca/configure'`。
→ 重新以 `diff -ruN a b` 生成（a/b 为源树根的原始/修改副本），`-p1` 语义即正确。

## 路径评估（按仓内口径）

- **路径 A（基础适配）**：已完成 —— `conan create` rc=0，消费者测试 3 条断言通过。
- **路径 B（知识库扩展）**：**可申报（候选，规模较小）** —— 两条可迁移经验：
  ① 官方源不可达时改用 Debian pristine orig tarball 的**合规替代判据**；
  ② HMDFS 的 umask/补丁前缀两条工程性坑（与 libbluray 共享同一模式）。
- **路径 C（高难度挑战）**：**不主张** —— 单体小库，无 bundled 依赖、无高成本验证矩阵。
