# DRAFT: conan 清洗环境毒化自举工具链的运行时与宿主探测

## 现象（错误面）

配方内自举了一个自带工具链二进制（如静态 zig），直接在 shell 里一切正常，
但 `conan create`（`self.run(..., env="conanbuild")`）里：

1. CMake 编译器探测即失败：
   `error: unable to create compilation: LibCStdLibHeaderNotFound`
   （或 `AppDataDirUnavailable`、`error: AccessDenied`）——**表面像头文件
   缺失，实际与头文件无关**。
2. 同一个包装器在 `env -i PATH=... ` 最小环境下又能编译通过。
3. 共享机上高并发时包装器内 `$(dirname ...)` 报
   `dirname: Out of memory` / `can't fork - try again`。

## 根因（两个独立的环境面）

1. **conan 的 conanbuild 环境按 profile 重建而非继承**：`HOME` 等被清除。
   zig 的全局缓存目录默认 `~/.cache/zig`，无 `HOME` 时解析失败，
   以 `LibCStdLibHeaderNotFound` / `AppDataDirUnavailable` 的面貌抛出。
2. **PATH 上被注入共享工具 shim**：`work/shared/bin/ld` 是
   `exec lld --code-sign "$@"` 的包装脚本；zig 做**原生目标** libc 探测时
   会 sh 出 PATH 上的 `ld`，被该 shim 破坏，同样报
   `LibCStdLibHeaderNotFound`（与 wasm 交叉编译无关时也会发生）。
3. 包装器若每次调用都 `$(dirname "$0")`/`$(cd ... && pwd)`，在共享机
   高负载下放大 fork 压力（数千次编译 × 多次 fork）。

## 定位方法（逐变量对照）

```sh
# 最小环境基线（应通过）
env -i PATH=<brew-bin>:/usr/bin <zig> cc -c t.c -o t.o
# 逐项加回 conan 环境变量，找到毒化变量
env -i PATH=<brew>:<shared-bin>:/usr/bin <zig> cc -c t.c -o t.o   # FAIL→PATH 注入
env -i ZIG_GLOBAL_CACHE_DIR=<dir> PATH=<brew>:/usr/bin <zig> cc ... # OK→缓存目录可自足
```

## 推荐做法（已在 wasi-libc 0.0-git20260129.ec0effd 验证）

包装器内：
1. `export ZIG_GLOBAL_CACHE_DIR="${HERE}/../zig-cache"`（`HERE` 为生成时
   烘焙的字面量路径）——HOME 缺失的自足替代；
2. zig 的执行用**最小 PATH**（zig 目录 + `/usr/bin:/bin`），隔离共享
   ld shim 对原生探测的毒化；
3. 所有路径由配方（Python）在生成包装器时**烘焙为字面量**，不做命令替换，
   整个包装器单 `exec` 零 fork；
4. conan 2.29 注意：`self.run()` 无 `check=` 参数（非零退出用
   `ConanException` 捕获），环境按 profile 重建（无法靠外层 export 传入）。

## 禁则

禁止按表面错误安装 musl 头/改 sysroot——根因是环境面（缓存目录/PATH
shim），`env -i` 逐变量对照即可证伪；乱"修"会在下一次 conan 环境重建后复发。

## 与相邻条目的边界

- `DRAFT-below-ohos-unsigned-rust-toolchain`：预编译工具链的**签名 +
  运行库 SO 依赖**（本条只覆盖签名之后"跑起来"的环境面）。
- BadZipFile/codeload 无扩展名族（graph 已有 10 条）与 can't fork 资源族：
  已覆盖，本条不含；`LibCStdLibHeaderNotFound` / `ZIG_GLOBAL_CACHE_DIR` /
  `AppDataDirUnavailable` 在全库 0 命中。
