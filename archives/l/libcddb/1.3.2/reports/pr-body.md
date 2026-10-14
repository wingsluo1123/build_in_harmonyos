## 三方库信息

- **三方库名称**：libcddb
- **上游版本**：1.3.2
- **上游仓库地址**：http://libcddb.sourceforge.net/（sourceforge；本沙箱不可达，见下）
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展，候选）
- **使用知识库**：openharmony-compile-agent

## 变更范围

- 新增 `conandata.yml`、`conanfile.py`、`test_package/`（本轮补齐此前只有 manifest/notes/patches 的包）
- 新增 `patches/0003-configure.patch`（umask 077 → 022）
- 更新 `manifest.yaml`（源、补丁、测试与路径评估）与 `notes.md`

## 源说明（重要）

上游发布位在 **sourceforge**，但本沙箱内 sourceforge 及其镜像**全部不可达**（实测 `Connection refused` / 0 字节响应）。
因此改取 **Debian 归档的 pristine orig tarball**：

```
url:    https://ftp.debian.org/debian/pool/main/libc/libcddb/libcddb_1.3.2.orig.tar.gz
sha256: 93f7860bdafa26f21d60a4d0ce2a8e55a0573841116aade79d90b64651b2b664
```

内容等同上游发布物（解包目录名同为 `libcddb-1.3.2/`），sha256 已在本机核验；替代理由写入 `conandata.yml` 与 `notes.md`。
charset 转换使用 **musl libc 内置 iconv**（configure 实测 `checking for working iconv... yes`），不引入 libiconv 依赖。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元/集成（shell 脚本） | 5 | `tests/`：check_cache / check_charset / check_discid / check_parse / check_server |
| **合计** | **5** | 其中 `check_server` 需外网 CDDB 服务器、`check_cache`/`check_discid` 需光驱或缓存夹具 → 离线不可复现 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 上游测试 | 0 | −5 | 上游 5 项均需外网/光驱，离线环境不可执行（已在 `test_package/MANIFEST.yml` 逐个说明） |
| 消费者功能测试 | 3 | 新增 | OHOS 上真实执行：版本自报 / 句柄生命周期 / 错误码初值 |
| **合计** | **3** | **+3** | `conan create` 全链路执行并 3/3 通过 |

## 上游测试用例修改说明

- [x] **否**，未修改上游任何测试用例（上游脚本原样保留在 tarball 内，未纳入执行）

## 补全测试用例说明

- [x] **是**，上游 5 项测试全部依赖外网或光驱，在无网络/无光驱的 CI 与沙箱中不可执行；
  适配后补 `test_package/test.c`（离线消费者测试）：
  1. `CDDB_VERSION` 必须自报 `1.3.2`（头文件与库配套，防止版本错配的假通过）
  2. `cddb_new()` 必须返回可用句柄，`cddb_destroy()` 可安全释放
  3. 新建连接（未做任何 I/O）的 `cddb_errno()` 必须为 0

## 验证结果

- 编译状态：**通过** —— `conan create archives/l/libcddb/1.3.2 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing` rc=0
- 测试通过率：**3/3（100%）**，实测输出：

```
libcddb version: 1.3.2 aarch64-unknown-linux-ohos
cddb_errno() = 0（新建连接的初始状态）
cddb_new/cddb_destroy 生命周期正常
```

## 路径评估（按仓内口径）

- **路径 A（基础适配）**：已完成 —— 配方可构建/安装，离线消费者测试全绿。
- **路径 B（知识库扩展）**：**可申报（候选，规模较小）** —— 两条可迁移经验：
  1. 官方源主机不可达时，**Debian 归档 pristine orig tarball** 作为合规替代源的判据（内容等同上游、sha256 可核验、目录名一致）；
  2. HMDFS 下 configure 的 `umask 077` 必须改 `022`（否则 `config.status` 报 `could not setup config files machinery`），
     以及补丁头必须是 `a/b` 相对源树根形式（否则 conan 报 `source/target file does not exist`）。
- **路径 C（高难度挑战）**：**不主张** —— 单体小库 + autotools + 3 段可移植性补丁，无 bundled 依赖与高成本验证矩阵。
