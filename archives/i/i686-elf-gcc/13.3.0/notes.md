# i686-elf-gcc 13.3.0 适配笔记

## 编译环境
- 构建系统: autotools (GCC configure + make)
- 编译日期: 2026-07-18
- 编译器: clang/clang++ (15.0)
- 平台: aarch64-unknown-linux-ohos (HarmonyOS PC, arm64)
- 状态: built

## 源码信息
- 源码: GCC 13.3.0
- 下载地址: https://mirrors.tuna.tsinghua.edu.cn/gnu/gcc/gcc-13.3.0/gcc-13.3.0.tar.xz
- SHA256: 0845e9621c9543a13f484e94584a49ffc0129970e9914624235fc1d061a0c083

## 前置依赖（in-tree）
GCC 编译需要 GMP、MPFR、MPC、ISL 数学库。采用 in-tree 方式：通过 conandata.yml
声明 prerequisites，在 build() 方法中调用 `_download_prerequisites()` 下载到源码树
并创建符号链接（gmp→gmp-6.2.1, mpfr→mpfr-4.1.0, mpc→mpc-1.2.1, isl→isl-0.24）。
GCC 的 configure 脚本会自动发现源码树内的符号链接，无需 `--with-gmp` 等硬编码路径。

| 依赖 | 版本 | 下载地址 |
|------|------|----------|
| GMP | 6.2.1 | https://gcc.gnu.org/pub/gcc/infrastructure/gmp-6.2.1.tar.bz2 |
| MPFR | 4.1.0 | https://gcc.gnu.org/pub/gcc/infrastructure/mpfr-4.1.0.tar.bz2 |
| MPC | 1.2.1 | https://gcc.gnu.org/pub/gcc/infrastructure/mpc-1.2.1.tar.gz |
| ISL | 0.24 | https://gcc.gnu.org/pub/gcc/infrastructure/isl-0.24.tar.bz2 |

## 编译步骤

1. 下载 GCC 13.3.0 源码（清华镜像）
2. 调用 `_download_prerequisites()` 下载 GMP/MPFR/MPC/ISL 到源码树并创建符号链接
3. 修改所有 configure 脚本中的 umask 077 为 umask 022（解决 HMDFS 权限问题）
4. 修复 libiberty/config.in：添加缺失的 HAVE_LIMITS_H, HAVE_SPAWN_H 等宏定义
5. 执行 configure（out-of-tree 构建）：
   ```
   ./configure --target=i686-elf \
     --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
     --prefix=/ --without-headers --enable-languages=c,c++ \
     --disable-nls --disable-werror --disable-multilib \
     --disable-libssp --disable-libquadmath --disable-libgomp \
     --disable-plugin --disable-libstdc++-v3 \
     --with-gnu-as --with-gnu-ld
   ```
6. 执行 make：`make -j1`
7. 执行安装：`make install DESTDIR=<package_folder>`

> **R33 合规**：不使用 `--with-gmp`/`--with-mpfr`/`--with-mpc` 硬编码路径，
> 而是通过 in-tree prerequisites 方式让 GCC configure 自动发现。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | MPC 未安装 | 系统未预装 MPC 库 | 使用 in-tree prerequisites 方式，从 conandata.yml 下载 MPC 1.2.1 到源码树 |
| 2 | HMDFS mkfifo 不支持 | HMDFS 文件系统不支持 mkfifo，make -j2 jobserver 无法创建管道 | 使用 `make -j1` 串行编译 |
| 3 | RTLD_NOW/RTLD_GLOBAL 未定义 | HarmonyOS dlfcn.h 不定义 RTLD_NOW 和 RTLD_GLOBAL 宏，plugin 机制依赖这些宏 | 添加 `--disable-plugin` configure 选项 |
| 4 | libstdc++-v3 configure 失败 | 裸机目标 i686-elf 无法运行 configure 测试程序（try_compile/try_run 失败） | 添加 `--disable-libstdc++-v3` configure 选项 |
| 5 | config.guess 不识别 OHOS | GCC 源码的 config.guess 不包含 HarmonyOS/OHOS 检测分支 | 使用 `--build=aarch64-unknown-linux-gnu` 绕过（与 binutils 相同策略） |
| 6 | make -j2 jobserver 失败 | HMDFS 不支持 mkfifo，GNU make jobserver 无法创建 FIFO 管道 | 使用 `make -j1` 替代 `make -j2` |

## 产物列表

安装到 package 目录的可执行文件：
- i686-elf-gcc — C 交叉编译器
- i686-elf-g++ — C++ 交叉编译器
- i686-elf-c++ — C++ 交叉编译器（符号链接）
- i686-elf-cpp — 预处理器
- i686-elf-gcc-13.3.0 — 版本化名称
- i686-elf-gcc-ar — LTO ar 包装器
- i686-elf-gcc-nm — LTO nm 包装器
- i686-elf-gcc-ranlib — LTO ranlib 包装器

## 验证结果

```bash
i686-elf-gcc --version    # gcc (GCC) 13.3.0
i686-elf-g++ --version   # g++ (GCC) 13.3.0
```

## make check

make check 因时间限制和交叉编译裸机目标限制跳过（GCC 测试套件需要 dejagnu 且
耗时极长，裸机目标无法运行测试程序）。

## 注意事项

- **R33 合规**：不使用 `--with-gmp`/`--with-mpfr`/`--with-mpc` 硬编码路径，使用 in-tree prerequisites
- HMDFS 文件系统限制导致必须使用 `make -j1`
- HarmonyOS 缺少 RTLD_NOW/RTLD_GLOBAL 宏定义，必须 `--disable-plugin`
- 裸机目标 i686-elf 无法运行 configure 测试程序，必须 `--disable-libstdc++-v3`
- config.guess 不识别 OHOS，使用 `--build=aarch64-unknown-linux-gnu` 绕过
- 所有 configure 脚本都需要修改 umask 077→022（HMDFS 权限问题）
- libiberty/config.in 需要手动添加缺失的 HAVE_* 宏定义

---

**编译结束**: 2026-07-18
**最终状态**: built
