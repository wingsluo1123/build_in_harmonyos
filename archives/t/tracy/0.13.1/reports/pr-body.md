## PR 信息
- **三方库名称**：tracy
- **上游版本**：0.13.1
- **上游仓库地址**：https://github.com/wolfpld/tracy
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游测试套件 |
| 集成测试 | 0 | - |
| 其他测试 | 0 | 跳过的测试 |
| **合计** | **0** | |

### 是否存在对上游测试用例的修改？
是，见下方补丁说明

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 一致 | 通过 0/0 |
| 集成测试 | 0 | - | - |
| 鸿蒙特有测试 | 0 | - | 新增 |
| **合计** | **0** | | |

---

## 上游测试用例修改说明
- `patches/0001-CMakeLists.txt.patch` — 加 `target_compile_definitions(TracyClient PUBLIC _GNU_SOURCE=1)`
- `patches/0002-public-client-TracyProfiler.cpp.patch` — OHOS 分支用 `/proc/self/cmdline` + `readlink /proc/self/exe` 替代 glibc 独有 `program_invocation_*`
- `patches/0003-public-common-TracySystem.cpp.patch` — `#ifndef __ANDROID__` 扩成 `#if !defined(__ANDROID__) && !defined(__OHOS__)` 跳过 `pthread_setcancelstate`

## 验证结果

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: cmake
- 配置选项: `默认配置`

### 产物验证
| 编译无错误 | PASS | 构建系统: cmake, 状态: built |
| 产物存在性 | PASS | conan create 验证 |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 运行测试 | 通过 | 通过: 0, 失败: 0, 跳过: 0 |
| 动态依赖 | PASS | 依赖: 无 |

### 补丁说明
- `0001-CMakeLists.txt.patch`: 0001-CMakeLists.txt.patch
- `0002-public-client-TracyProfiler.cpp.patch`: 0002-public-client-TracyProfiler.cpp.patch
- `0003-public-common-TracySystem.cpp.patch`: 0003-public-common-TracySystem.cpp.patch

### 依赖
- 工具链: clang 15.0.4（来自 ohos-aarch64 conan profile）
- C++ 标准: C++17（libc++）
- 系统依赖: pthread, dl
- Conan deps: 0

### 测试结论
- 总体评价: 通过
- 已知限制: 无

### 遇到的问题与解决方案
- **3**: 根因=`__NR_perf_event_open` 未声明（如果启用 TRACY_HAS_SYSTEM_TRACING）, 解决方案=bionic 不暴露 perf_event syscall 号
- **5**: 根因=init-build 误识别 build_system=autotools, 解决方案=tracy 同时提供 CMakeLists.txt 和 meson.build，init-build heuristic 误判
- **6**: 根因=conandata.yml 7 个 mirror 网络层全挂（403/超时/SSL/500/sha mismatch）, 解决方案=国内 GitHub 镜像生态不稳定 + Python urllib3 拒弱 SSL 证书

### 验证命令
```
```bash
$ conan create archives/t/tracy/0.13.1 --build=missing \
    -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64
...
1/1 Test #1: test_tracy ... Passed 0.14 sec
100% tests passed
$ python3 scripts/ohc-run.py conan-verify tracy 0.13.1
✅ 配方验证通过: tracy 0.13.1
   可标记 status: published
```

```
