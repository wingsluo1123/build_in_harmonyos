## 三方库信息

- **三方库名称**：libbs2b（Bauer stereophonic-to-binaural DSP）
- **上游版本**：3.1.0
- **上游仓库地址**：http://bs2b.sourceforge.net/（官方发布位在本沙箱不可达，见「换源」）
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展，候选）
- **使用知识库**：openharmony-compile-agent（含 HMDFS umask 相关经验）

## 变更范围

此前仓内该版本目录**只有 manifest/notes/patches，没有配方**。本 PR 补全：

- 新增 `conandata.yml`（换源 + 4 段补丁声明）、`conanfile.py`、`test_package/`
- 补写 `manifest.yaml`（源/依赖/测试/路径评估）与 `notes.md`（换源与四类构建踩坑的完整记录）

## 换源（上游发布位不可达）

| 端点 | 结果 |
|---|---|
| `sourceforge.net/projects/bs2b/.../libbs2b-3.1.0.tar.gz/download` | 连接被拒 / 0 字节（sourceforge 及其镜像全部不可达） |
| Debian `3.1.0+dfsg` | 属**下游重打包**（dfsg 版删改内容），按仓内 R39/PF7 不宜作替代源 |
| **Fedora lookaside** `src.fedoraproject.org/repo/pkgs/libbs2b/` | **可用**：`libbs2b-3.1.0.tar.lzma`，Fedora 记录 md5 `00d32ffa6461dde6a632c846da3e0a13`（本包已逐字核验一致），sha256 `b97164dd…8cd5` |

这与 libcddb（Debian pristine orig）、live555（Fedora lookaside）构成**同一换源模式**：官方发布位不可用时，
改用官方发行版缓存的 **pristine 上游产物**，并用该缓存记录的强哈希核验。

## 适配要点（含四条可迁移经验）

1. **Conan 的 `get()` 不支持 `.tar.lzma`**（按扩展名落到 zip 分支报 `BadZipFile`）→ 改用 `download()` +
   标准库 `lzma`/`tarfile` 解包，并自行实现 `strip_root`。**陷阱**：`export_sources` 已把 `patches/`
   放进源目录，"只有一个子目录即顶层"的判断会失效（实测表现为补丁目标报 `source/target file does not exist`）。
2. **HMDFS 的 umask 陷阱是双重**：`configure` 与它生成的 `config.status` **都**带 `umask 077`；
   只改 `configure` 仍会在 make 重跑 `config.status` 时失败（`could not setup config files machinery`）。
3. **补丁改过 `configure.ac` 会触发 autotools 再生规则**：需把输入置旧、生成物置新；
   且**不能用未来时间戳**（autoconf 健全性检查会报 `newly created file is older than distributed files`）。
4. **`PKG_CHECK_EXISTS` ≠ 导出 CFLAGS/LIBS**：上游只用它检查 sndfile 存在性，而 `bs2bconvert`/`bs2bstream`
   需要 `sndfile.h` 与 `-lsndfile` → recipe 需显式注入 `CPPFLAGS`/`LDFLAGS`。

依赖：`libsndfile/1.2.2`（已发布）。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 上游自带测试 | 0 | 上游无测试目标（`make check` 无内容） |
| **合计** | **0** | 见下「补全测试」 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 消费者功能测试（test_package） | 1（5 条断言） | 新增 | 等级编码回读 + fcut/feed 校验 + 采样率回读 + **真实串扰处理** + 版本自报 |
| **合计** | **1 / 5 断言** | **+1** | `conan create` 内执行并全绿 |

## 上游测试用例修改说明

- [x] **否**，未修改上游任何测试（上游无测试）

## 补全测试用例说明

- [x] **是**，补 `test_package/test.c`（真实断言，任一失败即非零退出）：
  1. `bs2b_open()` 返回可用句柄；
  2. `bs2b_set_level(BS2B_HIGH_CLEVEL)` → `bs2b_get_level()` 回读同一编码值，且
     `bs2b_get_level_fcut()/feed()` 必须为该预设的 **700/30**（按头文件语义：get_level 返回的是
     fcut/feed **编码值**而非预设序号——本轮初版按"序号回读"误判过一次，已在 notes.md 记录）；
  3. `bs2b_set_srate(44100)` 回读一致；
  4. `bs2b_cross_feed_f()` **必须真的改变样本**：左 1.0/右 0.0 → 右声道 > 0 且左声道 < 1.0
     （空实现/滤镜未接入会失败）；
  5. `bs2b_runtime_version_int()` 打印并校验与打包版本一致（3.1.0 → 0x30100）。

## 验证结果

- 编译状态：**通过** —— `conan create archives/l/libbs2b/3.1.0 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing` → rc=0
- 上游测试用例通过率：**N/A（上游无测试用例）** —— 上游 libbs2b 不带测试套件（`测试用例对比` 合计 0），按规则 2/3 不触发；能力以本包新增的消费者用例覆盖
- 新增测试用例通过率：**1/1（100%）** —— `test_package` 消费者用例（`test.c`，5 项真实断言，任一失败即非零退出）
- test_package 实测输出：

```
level_fcut=700 level_feed=30
cross_feed_f: left=0.754334 right=0.039345
bs2b_runtime_version_int() = 0x30100
libbs2b 等级编码/采样率/串扰处理 检查通过
```

## 路径评估（按仓内口径）

- **路径 A（基础适配）**：已完成 —— 构建 + 消费者测试全绿。
- **路径 B（知识库扩展）**：**可申报（候选）** —— 四条经验：① pristine 换源判据（sourceforge 不可达 →
  Fedora lookaside + md5 核验，且拒绝 dfsg 重打包）；② 非 gzip 归档（.tar.lzma）的取包/解包与 `strip_root`
  自实现，含 `patches/` 干扰判断的陷阱；③ HMDFS umask 的**双重性**与 autotools 再生规则的相对时间戳处置；
  ④ `PKG_CHECK_EXISTS` 只做存在性检查时消费者仍需显式注入头库路径。
- **路径 C（高难度挑战）**：**不主张** —— 单体库 + autotools + 常规换源/构建修补。
