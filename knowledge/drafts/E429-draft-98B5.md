# cmake 上游 CACHE PATH 默认绝对系统目录：Conan 前缀打包时 cmake --install 报 file cannot create directory

- **草稿 ID**: E429-draft-98B5
- **来源**: rdma/64.0（上游 linux-rdma/rdma-core v64.0）OHOS 适配本地验证
- **分类**: cmake / conan / install / absolute-path / ohos-platform
- **状态**: 本地草稿（未创建 Issue/PR，未生成知识编号，无远端链接，无审核结论）

## 问题 / 错误签名

- `conan create` 的 `package()` 阶段（`cmake.install()`）中断，日志尾部：

  ```
  CMake Error at srp_daemon/CMakeLists.txt:... (install):
    file cannot create directory: /usr/lib/sysusers.d.
    Maybe need administrative privileges.
  ```

- 特征：报错路径是**绝对系统路径**（不在 Conan 包前缀下），不是构建目录内的相对路径。
- 复现：任何 `install(FILES ... DESTINATION <绝对目录>)` 的目标在 `cmake --install --prefix <包目录>` 下都会命中。

## 触发条件

- 构建系统: cmake（Conan `CMakeToolchain` + `cmake_layout`，`cmake.install()` 以包目录为前缀）
- 阶段: installation（`package()`）
- 上游把某个安装目标声明成 `CACHE PATH`，且默认值回退到绝对系统目录

## 根因分析

上游 `CMakeLists.txt`（rdma-core 64.0）写法等价于：

```cmake
set(SYSUSERS_DIR "" CACHE PATH "Where to install the sysusers.d file")
if (NOT SYSUSERS_DIR)
  set(SYSUSERS_DIR "/usr/lib/sysusers.d")   # 空默认值 → 绝对系统路径
endif()
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/rdma-sysusers.conf
        DESTINATION ${SYSUSERS_DIR})
```

`CMAKE_INSTALL_PREFIX` 重定位只对**相对** `DESTINATION` 生效：CMake 把相对目标拼到
`--prefix` 下，而**绝对** `DESTINATION` 被原样使用。Conan 打包时 `--prefix` 指向包目录，
`/usr/lib/sysusers.d` 却仍指向真实根文件系统；沙箱/无特权环境无法创建该目录，`cmake --install`
以非 0 退出，整个 `package()` 阶段终止，产物不完整。

注意这与 `.gitignore`/DESTDIR 无关，是安装期路径语义问题；**不能**用 `DESTDIR` 绕过
（本仓已废弃 DESTDIR 模式），也不要让构建向宿主根文件系统写入。

## 最小修复方案

在 `archives/r/rdma/64.0/**` 范围内：

1. **配方** `conanfile.py` `generate()`：把该 CACHE PATH 覆盖成相对路径，随 `--prefix` 重定位。

   ```python
   tc.variables["SYSUSERS_DIR"] = "lib/sysusers.d"
   ```

   覆盖后 `cmake --install` 写入 `<package_folder>/lib/sysusers.d/rdma-sysusers.conf`。

2. **验证**：`conan create` 通过；`ls <package>/lib/sysusers.d` 存在 `rdma-sysusers.conf`；
   宿主 `/usr/lib/sysusers.d` 未被创建/写入。

3. **回退**：若变量不是 `CACHE PATH`（无法从配方覆盖，或项目内部硬编码绝对路径），
   用最小上游补丁把默认值改为 `lib/sysusers.d` 或
   `${CMAKE_INSTALL_PREFIX}/lib/sysusers.d`，再走常规 `patches/` 流程。

## 实际验证结果（rdma/64.0）

- 未修复时：`package()` 报 `file cannot create directory: /usr/lib/sysusers.d`，conan create 失败。
- 覆盖 `SYSUSERS_DIR=lib/sysusers.d` 后：`conan-verify` G0-G4/L2/L4/L5 全 PASS（exit=0），
  `conan create` 成功，`lib/sysusers.d/rdma-sysusers.conf` 落在包前缀内。

## 适用范围

- 在 Conan/CMake 前缀打包下构建、且上游 CMakeLists 把安装目标默认成绝对系统目录的库：
  `sysusers.d`、systemd unit 目录、`/etc/...` 下的配置文件、`/usr/share/...` 数据等。
- 症状判据：安装期报错路径是根文件系统下的绝对路径，且该路径由上游默认值给出。

## 非适用边界

- 构建目录/工作目录的临时文件问题不属本模式（那是构建期而非安装期）。
- 若项目已正确使用相对 `DESTINATION`（CMake 会随 `--prefix` 重定位），无需本方案。
- 不得通过在构建机预创建绝对目录或提升特权来"修复"——那只是掩盖路径语义错误，
  在 CI 干净环境中必然再次失败。
