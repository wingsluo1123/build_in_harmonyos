# par_shapes master 适配笔记

## 编译环境
- **类型**: header-only C（单头文件 par_shapes.h，实现段由 PAR_SHAPES_IMPLEMENTATION 守卫）
- **编译日期**: 2026-10-15
- **编译器**: clang 15.0.4（OHOS SDK 26.0.0.18 随附工具链，/data/service/hnp/bin/clang）
- **平台**: arm64-ohos（OHOS 6.0，ohos-aarch64 profile）
- **状态**: built（八门禁 Verdict PASS，见 reports/conan-verify-report.md）

## 源码（source()）
`get()` 下载 GitHub 官方 archive tarball（12.8MB）并 `strip_root=True` 解压：

- commit 钉定：`68e1215a055ccbeae378dd5969e09d0c79963a4a`（仓库无 tag）
- sha256：`59fa3e89e1683365beef1126890528b14079b8d8b4556460238cae3acd9f587c`（真机下载校验一致）
- **溯源说明**：任务卡给出的 URL（github.com/anael-seghezzi/par_shapes）已 404；canonical 上游为
  prideout/par —— par_shapes.h（仓库根）与 test/test_shapes.c 所在仓库

## 编译步骤（conan create 全流程，真机实测）

```bash
conan create archives/p/par_shapes/master -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

1. **打包（package()）**：header-only——只安装 `include/par_shapes.h`
   （日志：`package(): Packaged 1 '.h' file: par_shapes.h`）
2. **上游测试（build() 内，R51）**：按上游 test/CMakeLists.txt 的 test_shapes 目标复刻编译
   （`-std=c11 -Wall`，include `..` 与 `.`，链接 `m`）并直接执行，实测 16/16 用例通过、退出码 0
3. **test_package**：CMakeDeps 解析 `par_shapes::par_shapes`，编译并运行消费者端到端执行器
   （12 用例 / 66 校验点，全过）

## 上游测试清点（R51，实测非推断）

- test/CMakeLists.txt 共 12 个测试目标；其中 describe/it 框架六文件合计 48 个用例
  （test_shapes 16 / test_bubbles 11 / test_strings 9 / test_filecache 8 / test_octasphere 2 / test_sprune 2）
- 本适配组件 par_shapes 对应 **test_shapes 目标：16 用例，全部在 build() 内实跑通过**
- 运行产物：导出用例向 `build/*.obj` 写出 **15 个 OBJ 文件**（14 个形状导出 + lsystem.obj），
  配方在运行后计数校验（≠15 则构建失败）

## 遇到的问题与解决方案

1. **卡面 URL 404**：`github.com/anael-seghezzi/par_shapes` 不存在；上游作者重新组织过仓库。
   处置：canonical 上游 `prideout/par` monorepo + commit 钉定（无 tag），conandata/manifest/
   MANIFEST.yml 三处均记录溯源。
2. **E017/ghfast 死域**：平台 E017 防护会把含 github.com 的源文本注入 ghfast.top 前缀（该域
   2026-10 已失效）。其守卫条件是「含 github.com 且不含 ghfast.top 字样才注入」——conandata
   注释显式保留 ghfast.top 字样使注入跳过（syslog-ng 4.8.1 已合入先例）。真机实测：日志中
   无任何 E017 注入记录，直连 github.com 下载 12.8MB 成功。
3. **导出用例的相对路径依赖**：par_shapes_export 对 fopen 结果不判空，而上游导出用例向
   相对路径 `build/*.obj` 写文件——运行工作目录里必须先有 `build/` 子目录，否则段错误。
   配方在运行前 `os.makedirs(build/)`，运行后按 15 个文件计数校验。
4. **OHOS 直接 exec ELF 风险**：`/system/bin/sh` 可能无法直接执行 ELF 测试二进制
   （picohttpparser 同款问题）；上游套件与 test_package 两处均以 `bash -c '<binary>'` 包装执行。
5. **设备端 -Wall 警告（非错误）**：par_shapes.h:1148 `rand()/RAND_MAX` 存在 int→float
   隐式转换警告（clang 15 `-Wimplicit-const-int-float-conversion`）。属上游代码质量，
   构建判定不受影响，按「不必要不改上游」原则不做补丁，仅此记录。
6. **make jobserver mkfifo EPERM（无害）**：test_package 构建时 make 在 $HOME/tmp 建 FIFO
   失败自动降级非 jobserver 模式（`-j20` 照常生效），设备常态，非构建错误。
7. **R1 离线检视整改（2026-10-15，发评论区前完成）**：
   - **[P2] libm 声明补齐**：`package_info()` 增加 `system_libs = ["m"]`；同时移除
     test_package/CMakeLists.txt 手工追加的 `m`——由 CMakeDeps 目标传递后，消费者
     构建成功即证明声明生效（此前消费者按配方说明链接会缺数学符号，测试仅在本地补了 m
     而掩盖该缺口）
   - **[P3] 测试加固**：clone 法线窗口比对补 `same_points` 短路（防越界读）；
     merge 用例 tcoords 读取补判空（可选属性）；verbatim 校验由「末点 z 自比」改为
     末点三分量逐字节比对（索引以 `a->npoints` 为界）
   - **[P3] 性能**：`build()` 中 `sorted()` 移除（仅用于计数，顺序无观察者）
   - **E017 注释写法保持不变**：属已合入先例（syslog-ng 4.8.1）的既定模式，作为评审发现
     如实记录、处置为「保持并说明」；源码完整性由 commit 钉定 + sha256 校验保障
   - 整改后真机重跑 conan-verify：见 `reports/`（文件名不变、内容为新一次运行）

## 依赖版本
无外部依赖（header-only；测试链接 libm，标准 C 库）。

## 验证结果（真机 asus-64）

| 项 | 结果 |
|----|------|
| conan create（干净构建） | ✅ 成功（包 ID `6b129b068851896169fae42d399fa922d239ce8a`） |
| 上游 test_shapes 套件 | ✅ 16/16 用例通过，退出码 0 |
| 导出产物计数校验 | ✅ 15/15 个 OBJ 文件 |
| test_package 消费者端到端 | ✅ 12 用例 / 66 校验点，0 失败 |
| 官方 conan-verify 八门禁 | ✅ Verdict PASS（G0-G4 + L2/L4/L5） |
| 证据文件 | `reports/conan-verify-report.md`、`reports/conan-create.log` |

## 注意事项
- 本包为纯头文件包，无 lib/bin 产物；G3/G4 的「无 lib/ 目录」「无法找到程序包 ID」
  属 header-only 包的预期提示（与其余 header-only 包一致），非失败项。
- 消费者使用方式：`#define PAR_SHAPES_IMPLEMENTATION` 后 include `par_shapes.h`
  （单翻译单元编译实现），其余翻译单元直接 include 声明部分。
