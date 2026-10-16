# E429 — conan skip_shared_packages 下 shared 包的传递依赖 cpp_info 为空

## 错误特征

```
CMake Error ... 'fmt/core.h' file not found
Undefined symbols for architecture ...: "fmt::v8::..."
-- Could NOT find fmt (missing: fmt_INCLUDE_DIRS_RELEASE fmt_LIBS_RELEASE)
```

上游用 `FetchContent` 引入 spdlog（或任何“以 shared 形式存在于制品仓的包”），
把 FetchContent 换成 `find_package(spdlog CONFIG REQUIRED)` 之后，其外部传递依赖
fmt 的头文件/库信息突然消失。

## 触发条件

- 构建系统: cmake（CMakeDeps 消费 conan 依赖信息）
- 阶段: configuration / compilation / linking
- 制品仓 profile 启用 `skip_shared_packages`，且依赖图中存在 shared 包
  （本仓 spdlog/1.11.0、fmt/8.1.1 均为 shared）

## 根因分析

skip_shared_packages 之下，shared 包在依赖聚合时被跳过——包括它带进来的
传递依赖的 cpp_info。于是 fmt 虽然被下载、安装、存在于图中，但 CMakeDeps
为它生成的变量全是空串。最小化验证（临时配方 A：直接 requires fmt；
配方 B：仅 requires shared spdlog 让 fmt 传递进来）确认：A 的
`fmt_INCLUDE_DIRS_RELEASE` 完整，B 的为空。

## 解决方案

### 推荐方案

1. 配方 `requirements()` 中把该传递依赖提升为直接依赖：
   ```python
   self.requires("fmt/8.1.1")  # skip_shared_packages: fmt 是 shared spdlog 的传递依赖，
                               # 不直接声明则 cpp_info 为空
   ```
2. 上游 CMake 补丁处 `find_package(fmt CONFIG REQUIRED)`，
   链接处显式 `fmt::fmt`（ws CLI 与测试目标都要加）。

### 禁止做法

- ❌ 保留/退回 FetchContent 内嵌 fmt/spdlog 源码——破坏离线构建与依赖锁定
- ❌ 在消费者侧手工拼 include/lib 路径——脆弱且不可复现

## 验证

```bash
conan graph info --requires=ws/11.4.6@ohpcd/stable -pr:h ci/conan/profiles/ohos-aarch64
conan create archives/w/ws/11.4.6 -pr:h ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

ws 11.4.6 适配实录：`ws --version` 输出 ixwebsocket/11.4.6 + OpenSSL 3.5.8 +
zlib 1.3.1；14 个上游测试 13/14 通过（详见 archives/w/ws/11.4.6/notes.md）。

## 关联条目

- 相关: E298（conanrun 运行环境）、E430（CMakeDeps 模块变量为空）
