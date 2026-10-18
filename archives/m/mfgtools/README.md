# mfgtools (NXP uuu)

- **上游**：https://github.com/NXPmicro/mfgtools （产物叫 **`uuu`** = Universal Update Utility，i.MX 系列烧写工具）
- **版本**：**1.5.243**（平台条目为 `mfgtools 1.5.243`）
- **形态**：C++（`libuuu` 静态库 + `uuu` CLI）/ CMake
- **许可证**：BSD-3-Clause（NXP 2018）
- **依赖**：libusb 1.0.27、zstd 1.5.7.1、tinyxml2 11.0.0、zlib 1.3.2、bzip2 1.0.8、openssl 3.5.6
  —— **全部已在仓库归档**

## 归档内容

```
mfgtools/
  commands.json            软件级命令声明（R38：本包产出真编译的 ELF 可执行文件）
  1.5.243/
    conandata.yml          源（GitHub release 资产 + sha256，已本地校验）
    conanfile.py           配方（CMake + 依赖注入 5 处适配 + 补的测试）
    manifest.yaml          版本级 manifest（dependencies / upstream_tests / knowledge_gained）
    notes.md               适配要点（五处坑 + 实测输出）
    test_package/          消费者校验（8 项，全部离线；其中 1 项原生行为为具名平台限制 skip）
```

## 构建要点（五处，详见 notes.md）

1. **`PkgConfigDeps`**：上游用 `pkg_check_modules(... REQUIRED ...)` 找依赖 → 必须生成 `.pc`
2. **补 BZip2 include**：上游 `include_directories` 漏了它 → `bzlib.h` not found
3. **无条件定义 `UUUSSL` + 直接把 OpenSSL include 加进去**：上游 `base64_encode` 的定义在
   `#ifdef UUUSSL` 内而使用处没有守卫；conan 下 `find_package(OpenSSL)` 不命中
4. **用 `-Wl,-rpath,...`**：上游 `set(CMAKE_SKIP_RPATH ON)` 会让 `CMAKE_*_RPATH` 全失效 → 否则运行期
   `Error relocating …: <tinyxml2 符号> symbol not found`
5. **无 USB 环境**：无 USB 子系统时 uuu 会在参数解析前 `libusb_init` 失败并 abort（rc=134/‑6）→ 用
   **LD_PRELOAD 打桩**（仅让 init/热插拔注册/设备枚举成功且无设备、不伪造设备）让真实二进制的 CLI 路径
   **真跑通**并断言其输出；原生失败则单独记 skip、不计入通过。

## 上游测试

**上游测试数 = 0**（源码树无 `test/`，CMake 无 `enable_testing`/`add_test`）→ 配方里补功能级断言：
**用 LD_PRELOAD 给 libusb 打桩**（无 USB 子系统时 uuu 在解析参数前就 `libusb_init` 失败，连 `-h`/`-V` 都跑不到；
打桩只让 init/热插拔注册/设备枚举“成功且无设备”，**不伪造设备**）后跑真实二进制：`uuu -h` rc=0 且打印上游
用法、`uuu -V` 打印 libuuu 版本横幅 ⇒ **1/1（100%）**；原生（不打桩）的 rc=-6 作为具名平台限制单独记 skip、
不计入通过。消费者校验 **8 项**（`checks=8 fails=0 skips=1` / `RESULT: PASS`）。
