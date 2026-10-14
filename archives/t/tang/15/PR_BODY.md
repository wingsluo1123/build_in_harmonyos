# Tang 15 HarmonyOS 适配

- **三方库名称**：tang
- **上游版本**：v15
- **上游仓库地址**：https://github.com/latchset/tang/tree/v15
- **适配路径**：路径 C（高难度挑战）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 1 | `test-keys`，来源：上游 Meson `tests/meson.build` |
| 集成测试 | 8 | advertisement/recovery 的 standalone 与 socat 测试，来源：上游 Meson `tests/meson.build` |
| 其他测试 | 0 | 无 |
| **合计** | **9** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-------------|------|
| 单元测试 | 1 | 不变 | 上游 `test-keys` |
| 集成测试 | 8 | 不变 | 上游 8 项 advertisement/recovery standalone 与 socat 测试 |
| 鸿蒙特有测试 | 1 | 新增 | Conan `test_package`：调用已安装 keygen、daemon 与 CLI，检查密钥权限及服务响应 |
| **合计** | **10** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改

1. **修改的测试文件**：`tests/helpers`
   - **修改原因**：HarmonyOS 设备没有 `shuf` 和 `ss`。
   - **修改内容**：在缺少命令时使用设备自带 Python 生成端口并探测本机 TCP 连接；测试断言与流程不变。
2. **修改的测试文件**：`tests/meson.build`
   - **修改原因**：设备 `/tmp` 不可写。
   - **修改内容**：为测试环境设置构建目录下可写的 `TMPDIR`。
3. **修改的测试文件**：`tests/test-util.c`
   - **修改原因**：单元测试原先将临时目录固定写入不可写的 `/tmp`。
   - **修改内容**：从 `TMPDIR` 创建临时目录；密钥读取和权限断言保持上游语义。
4. **构建配置**：`meson.build`
   - **原因与内容**：通过 Conan 生成的 pkg-config 元数据发现 `http-parser`，并保留原有非 Conan 探测逻辑。
5. **打包配置**：`conanfile.py`
   - **原因与内容**：设备上的 Meson install 会重新链接 `tangd` 并使 OHOS ELF 签名失效；改为将已经通过上游测试的构建产物原样复制到包目录。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

## 验证结果

- 编译状态：通过（设备 `conan create` 退出码 0，`tools.build:jobs=2`）
- 上游测试用例通过率：9/9（100%，0 跳过；`meson test --print-errorlogs --no-rebuild -j1`）
- 新增测试用例通过率：1/1（100%，Conan `test_package`）
- `CONAN_HOME` 独立于共享缓存；Conan 从 `ohpcd` 拉取 host、build 和 test-package 工具依赖。

## 依赖与 CI 失败调查

- 运行时依赖仍是已发布的 `jose/15` 和 `http-parser/2.9.4`。`build_requirements()` 明确声明 `meson/1.11.0`、`ninja/1.13.2`、`pkgconf/3.0.6`、测试 CLI `jose/15` 和 `socat/1.8.1.3`；消费者测试单独声明 `jose/15`，因为 `tangd-keygen` 会从 `PATH` 启动 jose CLI。
- `meson/1.11.0`、`ninja/1.13.2`、`pkgconf/3.0.6`、`socat/1.8.1.3`、`jose/15` 与 `http-parser/2.9.4` 均在 Registry API 可查；空 Conan home 从 `ohpcd` 下载了对应配方和二进制。传递依赖 `jansson/2.15.1.1`、`openssl/3.5.8.1` 的 Registry API 记录没有 `webUrl`/`registryAddress`，但空 home 仍从 `ohpcd` 获取了二进制，因此它们没有阻断 Conan 图解析。
- CI-039 构建 #88474 在 checkout 前因 worker 无法启动 `curl`、`wget` 而退出；配方尚未运行。CI-027 构建 #88870 已安装全部依赖，随后启动 `meson setup` 时返回 `[Errno 11] Resource temporarily unavailable`，Meson 没有输出配置日志；这是 worker 无法创建子进程的资源错误，不是缺包。
- 后续 CI-038 构建 #89256 发现工具链没有将 `llvm-ar` 放在 PATH 中。配方现在从配置的编译器/SDK 目录解析归档工具，并将绝对路径写入 Meson native file。
- OHOS 上 Conan 发布的 Ninja 二进制可启动，但执行任何子命令都会报 `posix_spawn: No such file or directory`。Conan 图仍固定 `ninja/1.13.2`；配方使用该 worker 已提供且可运行的 Ninja 1.13.2，并在缺少它时明确报错。
- 编译明确限制为 `meson compile --jobs=2`；上游测试串行 `-j1`。Meson `wrap_mode=nodownload`，源码树没有 subprojects，因此构建和测试没有无界并行或子项目下载。

## 补充说明

上游固定版本为 `latchset/tang` tag `v15`，commit `02105756ee2a3afbd7065a47664d202788c9b584`。上游共有 9 项：1 个 `test-keys` 单元测试和 8 个 advertisement/recovery 集成测试；本次全量实跑 9/9，0 失败、0 跳过。

构建与消费者测试修复记录：首次 Conan 源码解包因 codeload URL 缺少 `.tar.gz` 后缀而误判为 ZIP，改用 SHA256 相同的官方 GitHub v15 tarball URL。消费者测试最初假设安装产物位于 `libexec`，后按设备实际布局调整路径；之后发现 Meson install 重链接会使 `tangd` 的 OHOS `.codesign` 失效并返回 `Operation not permitted`，现由 `package()` 原样复制已测试构建产物。最终设备 `conan create` 与消费者测试均通过。
