## PR 信息
- **三方库名称**：loudgain
- **上游版本**：0.6.8（上游最后版本，2020-07）
- **上游仓库地址**：https://github.com/Moonbase59/loudgain
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

---

## 测试用例对比

### 测试用例说明检查项
- [x] 已补全测试用例说明（上游用例清点证据与适配后端到端用例详见下文）
- [x] 已如实申报上游测试用例数与通过率（上游 0 用例，通过率 N/A）

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游源码无测试套件（清点证据见下） |
| 集成测试 | 0 | - |
| 其他测试 | 0 | - |
| **合计** | **0** | |

**上游测试用例通过率**：N/A（上游 v0.6.8 无任何测试用例，0/0 无从统计；适配后 test_package 消费者用例 6/6 全过）

**上游无测试清点证据（R51）**：v0.6.8 tag 归档（sha256 `1137c193ad941b366e87c5d84ccc95a7aa8571affc060db0bd1cf72c489aeaee`，真机下载核对）不含 tests/、test/ 目录；CMakeLists.txt 无 `enable_testing()`/`add_test()`；文件清点仅 src/、docs/、bin/、cmake/、debian/（docs/images/ 为 README 截图，非测试）。

### 是否存在对上游测试用例的修改？
否。上游不存在测试用例，无需修改。补丁 0001 仅改构建系统层（依赖解析 + 编译旗标），不涉及任何上游测试代码，无平台宏空壳 stub。

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 上游本就无 | - |
| 集成测试 | 0 | - | - |
| 鸿蒙特有测试 | 1 | 新增 | test_package 端到端消费者用例（test_loudgain.sh，6 断言） |
| **合计** | **1（6 断言）** | | 通过 6/6 |

**鸿蒙特有测试说明**：test_package 以 conan 消费者身份对安装后的 loudgain 可执行文件执行完整工作流：version banner（0.6.8）→ ReplayGain help banner → 纯 shell 生成 16044 字节噪声 WAV（printf RIFF 头 + dd /dev/urandom，无外部 fixture）→ `loudgain -s i` 扫描写标签（FFmpeg 解码 → libebur128 EBU R128 分析 → TagLib WAV "ID3 " chunk 写入，rc=0）→ `REPLAYGAIN_TRACK_GAIN` 帧字节级断言 → 带预存标签二次运行（标签重读路径）。

---

## 上游测试用例修改说明
不适用：上游 v0.6.8 无任何测试用例（见上方清点证据）。本 PR 的补丁 0001 为构建系统 portability 修复，与测试用例无关：
- PKG_CHECK_MODULES（pkg-config，OHOS 不可用）改写为 find_path/find_library，由配方注入 CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH（ffmpeg 包为 components 布局，配方聚合 components 的 include/lib 目录；taglib 扁平头文件走 PATH_SUFFIXES）；
- `SET(CMAKE_C/CXX_FLAGS ...)` 覆盖式赋值改为追加，保留 conan 工具链标志。

## 验证结果

### 编译验证
- 编译器: clang 15 (aarch64-unknown-linux-ohos, profile ohos-aarch64)
- 编译状态: 成功（`conan create` rc=0）
- 构建系统: cmake（系统 cmake 4.1.2，`-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容上游 cmake_minimum_required(2.8)）
- 配置选项: `默认配置`（package_type=application，无 options）

### 产物验证
| 编译无错误 | PASS | 构建系统: cmake, 状态: published |
| 产物存在性 | PASS | conan create 验证通过（bin/loudgain + bin/rgbpm） |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 运行测试 | 通过 | test_package: 通过 6 断言, 失败 0, 跳过 0（HMBS_TEST_PACKAGE_RESULT passed=true，CI 构建 #84860 通过） |
| 动态依赖 | PASS | 依赖: libebur128/1.2.6, taglib/1.13.1, ffmpeg/4.4.8, zlib/1.3.1.1 (override 对齐 taglib 1.3.1 / ffmpeg 1.3.1.1 版本冲突) |

### 补丁说明
- `0001-cmakelists-deps.patch`: 依赖解析改走 conan 注入的 CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH（pkg-config 在 OHOS 不可用；find_path/find_library 替代 PKG_CHECK_MODULES；taglib 扁平 include 走 PATH_SUFFIXES；静态 libtag.a 的 zlib inflate* 符号由最终可执行文件链接）；CMAKE_C/CXX_FLAGS 改追加保留工具链标志。patch_type: portability，无平台宏。

### 依赖（W0 全部已发布到 ohpcd 制品仓，conan download 核验）
- libebur128/1.2.6
- taglib/1.13.1（选 1.x：上游写死 -std=gnu++11，taglib 2.x 头文件要求 C++17）
- ffmpeg/4.4.8（FFmpeg 5+ 移除 av_register_all()，scan.c 仍在使用）
- zlib/1.3.1.1（override：taglib/1.13.1 声明 1.3.1、ffmpeg/4.4.8 声明 1.3.1.1，对齐到 R37 修复版）

### 测试结论
- 总体评价: 通过（conan create rc=0；conan-verify G1–G4 + L2/L4/L5 全过；test_package 6/6 断言）
- 已知限制: WAV 标签写入为上游实验性功能（TagLib RIFF::WAV "ID3 " chunk），本用例已实测验证可行

### 遇到的问题与解决方案
1. taglib(1.3.1) 与 ffmpeg(1.3.1.1) 的 zlib 版本冲突 → 配方 `requires("zlib/1.3.1.1", override=True)` 对齐。
2. 链接期 `inflateInit_/inflate/inflateEnd` 未定义（静态 libtag.a 的 zlib 未被链接）→ patch 0001 追加 `find_library(LZ_LIBRARIES z)` 至 TARGET_LINK_LIBRARIES 末尾。
3. CMake 4.x 拒绝 cmake_minimum_required(2.8) → configure 命令行 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（toolchain set() 在 CMakeLists 解析前不生效，必须落 -D）。
4. loudgain 默认 `mode='s'`（仅测量不写标签）→ 消费者用例显式 `-s i`。

### 验证命令
```
# W0 依赖检查（全部已发布）
conan download "libebur128/1.2.6" -r=ohpcd --only-recipe   # OK
conan download "taglib/1.13.1"    -r=ohpcd --only-recipe   # OK
conan download "ffmpeg/4.4.8"     -r=ohpcd --only-recipe   # OK

# 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight loudgain 0.6.8 --src <src>   # cpp, 匹配

# 配方验证（G1-G4 + L2/L4/L5 全过）
python3 scripts/ohc-run.py conan-verify loudgain 0.6.8                 # PASS

# W3 本地 CI 模拟（JC/L0-L5 全过）
python3 scripts/ohc-run.py finish loudgain 0.6.8 published             # finish_success

# 构建 + 消费者端到端测试
conan create archives/l/loudgain/0.6.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing                                                      # rc=0
# test_package 输出: ALL 6 ASSERTIONS PASSED
# HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "command": "test_loudgain.sh"}

# W4 独立审计
python3 scripts/pre_pr_audit.py generate --repo-dir <repo> --package loudgain --version 0.6.8
# verdict=pass, P0=0 P1=0
```
