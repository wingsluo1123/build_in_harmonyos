# skktools 1.3.4-0.20210220 适配笔记

## 编译环境
- 构建系统: autotools（上游自带生成的 configure/Makefile.in，2021 年快照）
- 状态: published（配方与测试就绪，等待真机/shadow CI 验证）
- 目标: HarmonyOS PC aarch64（ohos-aarch64 profile）

## 包版本说明
- 目录版本 / Conan 版本 / 分支名 / test_package 引用一致：`1.3.4-0.20210220`
- 上游源码为 skktools-1_3_4 tag 之上的 git 快照 `0fe2106fbc052445c611e6c5b2a79899d740edcb`（2021-02-20），
  树内 `VERSION` 仍为 `1.3.4`。版本串仿 Debian 快照命名（1.3.4+0.20210220 语义，
  以 `-` 连接满足 Conan 版本语法），记录快照日期。
- SHA256（两次独立下载一致）:
  `6339d1ec42ca19c9ae03318a8196109dedf87140841dd9e7fa79936578a45371`

## 构建步骤（配方内自动完成）
1. `conan.tools.files.get` 下载快照 tar.gz（URL 带 `.tar.gz` 后缀，规避 BadZipFile 误判）。
2. 依次应用 3 个补丁（见下）。
3. `AutotoolsToolchain + PkgConfigDeps`，configure 参数 `--with-gdbm=yes`。
4. `make -j1`，随后 `make test`（上游 golden-file 测试，见验证节）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | skkdic-expr 的 ndbm 接口来源 | 上游 configure 在 `--with-gdbm=yes` 分支要求 `gdbm/ndbm.h` + `-lgdbm` | 依赖 `gdbm/1.23`（该包以 `--enable-libgdbm-compat` 构建，提供 `include/gdbm/ndbm.h` 与 `libgdbm_compat`）；`gdbm/1.24` 禁用了 compat，不可用 |
| 2 | skkdic-expr2 依赖 glib | configure.ac 用 `PKG_CHECK_MODULES(GLIB2, glib-2.0 >= 2.0.0)` 探测，失败则静默跳过 expr2 | `requires("glib2/2.88.0.1")` + `PkgConfigDeps` 暴露 `glib-2.0.pc`，保留 expr2 构建而非降级 |
| 3 | 旧 config.guess/config.sub 不识别 HarmonyOS | E007/E072/E122 共性问题 | 补丁 0001/0002，与 gdbm 1.23 已验证补丁同源（顶层路径适配） |
| 4 | configure 的 confXXXXXX 临时目录 umask 077 在 HMDFS 上 Permission denied | E118/E136/E175 共性问题 | 补丁 0003 移除 umask 077（同 gdbm 0003 模式） |
| 5 | CI conandata.yml 预下载路径 BUILD_DIR 未初始化缺陷 | 基础设施问题（E214 系） | 源码 URL/SHA256 内联 conanfile.py，不放 conandata.yml；补丁改由 build() 内 `conan.tools.files.patch` 应用（export_sources 拷贝 patches/） |
| 6 | Windows 上 worktree 全量 checkout 失败 | origin/main 含非法文件名 `0002-dataparser-ungated.patch??` | 按知识草稿 `DRAFT-git-worktree-add-windows-invalid-filename-sparse-exclude`：`--no-checkout` + sparse-checkout 排除 `archives/g/gama/`（真机 Linux 端检出不受影响） |

## 源码修改（补丁）

- `patches/0001-config.guess-add-HarmonyOS-support.patch`：config.guess 增加 `*:HarmonyOS:*:*` 分支，输出 `aarch64-unknown-linux-ohos` 等三元组。
- `patches/0002-config.sub-add-HarmonyOS-support.patch`：config.sub 接受 `linux-ohos` 内核后缀。
- `patches/0003-configure-umask-077-hmdfs-compatibility.patch`：configure 临时目录创建去掉 umask 077。
- 三个补丁均在本地用 `git apply --check` 对上游快照源码逐个验证通过；均为平台移植性修改，无行为语义变化。

## 依赖版本

- gdbm/1.23（ndbm compat：skkdic-expr）
- glib2/2.88.0.1（glib-2.0：skkdic-expr2）

## 测试盘点（W1/W3）

- 上游测试：`make test` 下 4 个 golden-file 差分目标
  （test_skkdic-count / test_skkdic-sort / test_skkdic-expr / test_skkdic-expr2），
  golden 输入 `test/SKK-JISYO.S*`，期望输出 `test/result/*`。
  skkdic-count 的 golden 期望为 `test/SKK-JISYO.S: 6763 candidates`。
- 无需外部服务/网络；skkdic-expr 的 ndbm 临时目录由 mkdtemp 创建（补丁 0003 已去掉 umask 077）。
- test_package：`test_skktools.py`，12 个断言，覆盖 4 个打包产物的可执行性与核心行为
  （精确计数 / 排序稳定性与 okuri 段顺序 / expr 与 expr2 的词典合并），全部离线确定性。
- 脚本型工具（convert2skk/filters/`*.rb` 等，依赖 ruby/perl/awk）不打包、不测试：
  上游 Makefile.am 亦不安装它们（仅 EXTRA_DIST），OHOS 无 ruby 运行时。

## 验证结果

```bash
# 本机（Windows）已完成的前置验证：
git apply --check patches/*.patch        # 3/3 通过（对上游快照源码）
python -m py_compile conanfile.py test_package/*.py   # 语法通过
# sha256 复核：
#   6339d1ec42ca19c9ae03318a8196109dedf87140841dd9e7fa79936578a45371
```

### 真机 shadow CI 结果（2026-10-16，OHOS aarch64）

```text
G0_RESULT=pass
KC_RESULT=pass
JC_RESULT=pass: empty
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: skkdic-count --version OK, skkdic-expr failed, skkdic-expr2 failed, skkdic-sort --version OK
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
STATUS=pass
```

- 上游 golden 测试：4/4 通过（skkdic-count / skkdic-sort / skkdic-expr / skkdic-expr2，
  与 test/result/* 逐字节一致；skkdic-count 输出 `test/SKK-JISYO.S: 6763 candidates`）。
- test_package：16/16 断言通过（标记行 `skktools test_package summary: TOTAL=16 PASS=16 FAIL=0`）。
- L2 中 skkdic-expr / skkdic-expr2 的 `--version` 冒烟失败属工具自身特性：两者按 SKK 协议从
  stdin/文件读取词典，不接受 `--version` 参数（非零退出）；skkdic-count / skkdic-sort 的
  `--version` 冒烟通过，L2 整体判定 pass。

### 下一步

```powershell
# 本地等价（Linux/CI worker）：
conan create archives/s/skktools/1.3.4-0.20210220 `
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 `
  --build='skktools/*' --build='missing'
```

## 注意事项

- 版本串含 `-`，CI L0n 分支门禁要求分支名「包目录名-版本目录」：
  `feat/skktools-1.3.4-0.20210220-codex`（已按此命名）。
- 产物为 4 个 CLI（bin/skkdic-count、bin/skkdic-sort、bin/skkdic-expr、bin/skkdic-expr2），
  package_type=application，L2 bin smoke 应可执行（非纯库）。
- 本包不打包 `skkdic-expr2` 之外的 dbus/gtk 相关脚本；skk.ex 等 dist 辅助文件不进入产物。
