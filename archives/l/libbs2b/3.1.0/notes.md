# libbs2b 3.1.0 适配笔记（OHOS PC / aarch64 / musl）

## 结论

- 状态：**built**（`conan create` 全链路通过，含消费者测试；`conan create rc=0`）
- 源：**换源**为 Fedora lookaside 的 pristine 上游 tarball（Fedora 记录 md5 逐字核验一致）
  - 原上游：`sourceforge.net/projects/bs2b/.../libbs2b-3.1.0.tar.gz/download`（本沙箱与其全部镜像均不可达）
  - 现源：`src.fedoraproject.org/repo/pkgs/libbs2b/libbs2b-3.1.0.tar.lzma/<md5>/libbs2b-3.1.0.tar.lzma`
  - sha256：`b97164dd98fda4b05722fd68ffed2427b980dfb8316bbbbcfc0cde3ae5238cd5`
- 依赖：`libsndfile/1.2.2`（已发布）——上游 configure.ac 硬性要求
- 消费者测试：级别编码回读（`BS2B_HIGH_CLEVEL` → fcut/feed 700/30）+ 采样率回读 +
  **真实串扰处理**（左 1.0/右 0.0 → 右 > 0 且左 < 1.0）+ 运行时版本自报（0x30100）

## 换源与构建踩坑（逐条实测）

### 1. Conan 的 `get()` 不支持 `.tar.lzma`

`get(url=..., sha256=..., strip_root=True)` 会按扩展名选择解包实现，`.tar.lzma` 未被支持 → 落到 zip 分支报
`BadZipFile: File is not a zip file`。解法：`download()` 取包并校验 sha256 + 标准库 `lzma`/`tarfile` 解包。
**陷阱**：`export_sources` 已把 `patches/` 放进 `source_folder`，因此"源目录里只有一个子目录 → 它就是
tarball 顶层目录"的判断会失效（本轮实测：补丁目标被解析到 `a/build-aux/...` 而报
`source/target file does not exist`）。改为先解到独立 staging 子目录，再上移其唯一条目。

### 2. HMDFS 的 umask 陷阱是**双重**的

- `configure` 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建 2700 临时目录 → hmdfs 经 group 位中介访问、
  `chmod` 无效 → 目录不可遍历，`config.status` 报 `could not setup config files machinery`；
- 把 `configure` 改成 `umask 022` 后**仍失败**：`config.status` 是 configure 生成的、**自己**也带 `umask 077`，
  make 期间被重跑时再次失败 → 必须同时处理 `config.status`。

### 3. 补丁改过 `configure.ac` 会让 make 触发 autotools 再生规则

仓内补丁含 `configure.ac`/`Makefile.am` 的修改 → 它们比 `configure` 新 → make 触发
`$(srcdir)/configure: $(am__configure_deps)` 与 `config.status --recheck`，**重新生成带 umask 077 的
config.status**。解法：把 autotools **输入**（configure.ac / aclocal.m4 / Makefile.am / Makefile.in / config.h.in）
的时间戳置旧、**生成物**（configure / config.status / Makefile）置当前时间。**必须用相对时间**：曾用
「未来时间戳」（now+5s）导致 autoconf 健全性检查报 `newly created file is older than distributed files`。

### 4. `PKG_CHECK_EXISTS` ≠ 会导出 CFLAGS/LIBS

上游 configure.ac 只用 `PKG_CHECK_EXISTS([sndfile], [], [AC_MSG_ERROR(...)])` 检查**存在性**，不设
`SNDFILE_CFLAGS/SNDFILE_LIBS`；而 `src/Makefile.am` 的 `bs2bconvert`/`bs2bstream` 需要 `#include <sndfile.h>`
并链接 `-lsndfile`。解法：recipe 显式把依赖的头/库目录注入 `CPPFLAGS`/`LDFLAGS`（否则实测报
`'sndfile.h' file not found`）。

### 5. 头文件安装布局

上游把公开头装在 `include/bs2b/`（`bs2b.h`/`bs2btypes.h`/`bs2bclass.h`/`bs2bversion.h`）→
`package_info` 同时导出 `include` 与 `include/bs2b`，两种 include 写法都可用。
另注意 API 语义：`bs2b_get_level()` 返回的是 **fcut/feed 编码值**（如 `BS2B_HIGH_CLEVEL`），
不是预设序号——测试断言按头文件语义写（本轮初版按"序号回读"误判过一次）。

## 验证输出（test_package 实跑）

```
level_fcut=700 level_feed=30
cross_feed_f: left=0.754334 right=0.039345
bs2b_runtime_version_int() = 0x30100
libbs2b 等级编码/采样率/串扰处理 检查通过
```

## 路径评估（按仓内口径）

- **路径 A（基础适配）**：已完成。
- **路径 B（知识库扩展）**：**可申报（候选）** —— 上述 4 条可迁移经验（换源判据、非 gzip 归档的取包/解包、
  HMDFS umask 双重性与 autotools 再生规则的时间戳处置、PKG_CHECK_EXISTS 的边界）。
- **路径 C（高难度挑战）**：**不主张**。

## 路径 B 材料

- 草稿：`knowledge/drafts/DRAFT-ohos-hmdfs-umask-and-autotools-regeneration.{kv,md}`（查重 verdict=`create`；载体 PR #15533 libbs2b 配方补全）
