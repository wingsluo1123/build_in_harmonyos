# librnd 4.5.0 适配笔记

## 编译环境
- 构建系统: custom（上游自研 scconfig：`sh ./configure` 生成 `Makefile.conf`，再 `make`；非 GNU autotools/CMake）
- 编译日期: 2026-09-30
- 编译器: clang/clang++
- 状态: built（配方完成，待 HarmonyOS aarch64 真机实测后转 published）

## 编译步骤

```bash
sh ./configure --prefix=/ \
  --disable-hid_gtk2_gdk --disable-hid_gtk2_gl --disable-hid_gtk4_gl \
  --disable-hid_lesstif \
  --disable-gd --disable-gd-gif --disable-gd-png --disable-gd-jpg \
  --disable-stroke --disable-xrender --disable-xinerama
make -j1
make test
make install DESTDIR=<package_folder> PREFIX=/
```

上游 `configure` 对缺失的 GUI 依赖只告警并自动禁用（warning + auto-disable），
显式 `--disable-*` 让无头构建确定性更强。`--disable-*` 名称来自
`scconfig/hooks.c` 的 `disable_libs[]` 与 `scconfig/plugins.h` 的 `plugin_def`
（hid_gtk2_gdk / hid_gtk2_gl / hid_gtk4_gl / hid_lesstif / stroke 均为真实插件名）。

## 上游测试盘点（与 conanfile build() 口径一致）

上游测试入口 `tests/Makefile` 的 `test` 目标顺序运行 5 个套件，
其中 4 个套件成功时打印 `*** QC PASS ***`，`tests/librnd` 套件无 QC 行、
以两个二进制退出 0 + 最终 `All tests passed` 横幅/下游套件进度为证据：

| # | 套件目录 | 测试内容 | 通过信号 |
|---|----------|----------|----------|
| 1 | tests/rnd_printf | `rnd_printf` 坐标格式化：tester 全量格式矩阵 + tester.ref diff | `pcb-printf: *** QC PASS ***` |
| 2 | tests/remote | hid_remote 协议解析：test_all.sh 跑 text/bin/simple/lists 共 4 组 msg/ref diff | `remote: *** QC PASS ***` |
| 3 | tests/librnd | 无外部依赖可链接性：librnd_test --gui batch + librnd_includes 头闭包 | 2 个二进制均退出 0 |
| 4 | tests/conf | 配置系统：conftest 跑 tests/ 下 list_merge/list_set/arr_merge/arr_set/scalar 共 5 组 .test/.ref diff | `conf: *** QC PASS ***` |
| 5 | tests/base64 | base64 编解码往返：main 跑 6 组向量 roundtrip | `*** QC PASS ***` |

- 计数口径：`upstream_test_total: 5`（顶层 `make test` 套件数），
  `upstream_test_count_method: autotools_tests`（make 驱动，最接近的可用口径；
  5 套件展开为 13 组 diff/binary 子检查，见上表）。
- `HMBS_UPSTREAM_TEST_RESULT` 的 discovered 固定 5（来自 `tests/Makefile` 审计），
  passed 为分套件判定之和：rnd_printf/remote/conf 各 1（QC 行前缀匹配）+
  base64 1（裸 `*** QC PASS ***` 行）+ librnd 1（`All tests passed` 横幅或
  已进入 conf/base64 阶段的日志证据）；failed 仅表示 `make test` 进程失败
  （至少 1 个套件失败），skipped = 5 - passed - failed；无 returncode 回写
  QC 数的修正分支，不满足 `passed + failed == executed` 时修数据源不凑数字。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游只有 http 源，R39 要求 https | repo.hu 的 https 握手失败（EOF，实测），上游不支持 https | conandata 保留官方 http 源并在配方注释说明；按守则官方原始 URL 放最后回退 |
| 2 | 源码包 sha256 无官方公布 | 下载页只给 .sig/.crt 签名，无哈希文件 | 本地下载 .tar.gz/.tar.bz2 并算哈希；.tar.bz2 哈希与 Debian 官方 `dae47e45…93efa4` 完全一致，交叉验证下载无篡改 |
| 3 | 无历史适配可抄 | 仓库内无 pcb-rnd/librnd 系先例 | 按 INSTALL + hooks.c/plugins.h 源码审计立配方；test_package 仿上游 tests/base64/main.c 写 base64 往返 |
| 4 | `make test` 在 tests/librnd 阶段 `mkdir /tmp/librnd-dummy` 只读失败 | `src/Makefile.in` 硬编码 `INST_DUMMY=/tmp/librnd-dummy`，真机 /tmp 只读 | 新增 `patches/0001-use-tmpdir-for-inst-dummy.patch`，用 `$(or $(TMPDIR),$(TMP),$(TEMP),/tmp)` 做根目录；仅替换临时根目录，不跳过任何测试 |
| 5 | `make install` 在安装 sccbox 自拷贝行 `../scconfig/sccbox: Operation not permitted` + Error 126 | 刚构建的 sccbox ELF 从 conan 缓存执行被 HMDFS 拒绝（E077 同族，平台探测 chmod:0/hardlink:0；头文件/.a 拷贝用 sccbox 仍可执行，唯自拷贝失败） | 配方 `_fix_helper_install` 在 configure 前后用 Python 重写 `src/Makefile.in` 与生成的 `src/Makefile` 中 4 个 ELF helper 行（puplug/sphash/cquote/sccbox）为 `cp -p` 加 `chmod 755` 容错，不再 exec sccbox 拷自身；不用 conandata 补丁（上轮 0002 补丁被 conan 严格校验拒绝）；package() 前仍 chmod 加有条件自签后再 `make install` |

## 源码修改

`patches/0001-use-tmpdir-for-inst-dummy.patch` （portability）：`src/Makefile.in` 的被转向 genlist 安装目录 `INST_DUMMY` 由硬编码 `/tmp/librnd-dummy` 改为 `$(or $(TMPDIR),$(TMP),$(TEMP),/tmp)/librnd-dummy`，适配真机 /tmp 只读；仅替换临时根目录，不删减测试。GUI 相关功能通过 configure 开关关闭。

配方内重写（无补丁）：`conanfile._fix_helper_install` 在 `./configure` 前后分别重写 `src/Makefile.in` 与生成的 `src/Makefile` 中 4 个 ELF helper 安装行（puplug/sphash/cquote/sccbox）为 `cp -p` 加 `chmod 755` 容错，避免 package() 执行刚构建的 sccbox 拷贝自身时触发 HMDFS exec EPERM (Error 126)；仅替换拷贝工具，不删减任何安装文件。行级替换不依赖补丁行号，避开上轮 conan 严格校验拒绝。package() 前对 4 个 helper 做最佳努力 chmod 加 binary-sign-tool 自签（失败回退，不阻塞）。

## 依赖版本

无外部依赖（bundled src_3rd；GUI/GTK/GD 全部关闭）。构建仅需 C 编译器 + make，
由真机工具链提供。

## 验证结果

```bash
# 待 HMBS 真机预检（conan create，含 build() 内 make test + test_package）后回填：
# - 上游测试用例通过率：待实测（目标 5/5）
# - 新增测试用例通过率：待实测（目标 6/6）
```

- 为跑测试所做的改动均已进配方（build() 内 `make test` + test_package 用例），无纯本地验证改动。
- 退出码为 0 不等于真跑：`make test` 的每个套件都有 .ref diff 或二进制退出码断言；
  空文件比空文件式假阳性不适用（各套件均有非空 .ref：remote/*.ref、conf/tests/*.ref、
  rnd_printf/tester.ref）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | scconfig 定制配方（含上游 make test + HMBS_UPSTREAM_TEST_RESULT） |
| conandata.yml | 官方 http 源 + sha256（.tar.bz2 哈希与 Debian 交叉验证一致） |
| test_package/test.c | base64 编解码 6 断言（真实调用 librnd-core API） |

## 注意事项

- `test_package` 链接全部 8 个 librnd 库，确保每个产出物都被消费验证。
- 头文件路径为 `include/librnd4`（上游 librnd.mak 的 LIBRND_INCDIR 口径），
  消费代码用 `#include <librnd/core/base64.h>`。
- shared 默认为 True：插件体系静态链接会失败（上游 `--static-librnd` 帮助原文
  "will fail with plugins"），故保留动态库。
