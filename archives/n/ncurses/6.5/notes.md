# ncurses 6.5 适配笔记 — HarmonyOS PC (aarch64)

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-08-07
- 编译器: clang/clang++ (aarch64-unknown-linux-ohos, /data/service/hnp/bin/clang)
- 状态: built (conan-verify 八门禁通过; 制品仓 remote 访问受限未上传)
- Conan: 2.29.1 (OHOS 适配版), profile: ci/conan/profiles/ohos-aarch64

## 编译步骤

1. 初始化编译环境:
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build ncurses 6.5 --url=https://invisible-mirror.net/archives/ncurses/ncurses-6.5.tar.gz
   ```

2. 平台补丁 (配方 build() 内联 sed 实现):
   - **E160**: config.guess 注入 `HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl` (uname -s 返回 HarmonyOS)
   - config.sub 注入 `ohos*` / `linux-ohos*` 匹配
   - **as_expr=false**: 绕过 /usr/bin/expr 对 BRE 交替 `\|` 的 bug

3. configure (静态编译 — R26 系统同名库强制静态):
   ```bash
   TMPDIR=<可写目录> /system/bin/sh ./configure --prefix=/ \
     --without-shared --with-normal \
     --without-debug --without-ada --without-manpages --without-cxx-binding \
     --enable-widec --enable-overwrite
   ```
   验证: "checking if you want to build shared libraries... no"

4. 编译: `make -j1` (必须 -j1: -jN 的 make jobserver mkfifo 在 HMDFS 报 Operation not permitted)

5. 安装: `make install DESTDIR=<package_folder>` (--prefix=/ + DESTDIR staging)

6. 测试: `make check` → 输出 "The test-programs are interactive" (交互式测试, 无头环境自动跳过, 退出码 0)

7. Conan 配方: `conan-init` → `conan-verify` (G0-G4+L2/L4/L5 八门禁通过)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识引用 |
|---|------|------|----------|----------|
| 1 | config.guess: unable to guess system type | uname -s=HarmonyOS 不在 config.guess 已知系统 | sed 注入 HarmonyOS→Linux/musl 分支 | E160 |
| 2 | 子目录 Makefile 变量行乱码 (top_srcdir/srcdir/prefix 等, 含 "kk" 高字节垃圾, 每次运行不同) | /usr/bin/expr 对 BRE 交替 `\|` 模式返回垃圾, config.status 计算 ac_dir/ac_top_srcdir 出错 | configure 中 as_expr="expr"→"false", 强制 echo\|sed fallback | (新, 见草稿) |
| 3 | config.status: can't create .../csXXXX/out: Permission denied | HMDFS UID 映射: umask 077 建的 0700 目录 owner 映射为 20001006, 进程实际 20020100 不可写 | 移除 configure 中 `umask 077 && mktemp/mkdir` 的 umask 077; TMPDIR 指向预创建可写目录 | E011 |
| 4 | make -jN: jobserver mkfifo: Operation not permitted | GNU make 并发 jobserver 用 mkfifo, HMDFS 不支持 | 全部使用 -j1 | (已有模式) |
| 5 | make install: No rule to make target 'install' | autotools.install() 在 conan 默认 cwd (build-release, 无 Makefile) 运行 | package() 显式 cwd=source_folder | — |
| 6 | config.guess dummy.c: Permission denied (2 条警告) | config.guess 尝试在 TMPDIR 建测试文件, 同样 UID 映射问题 | 非致命, config.guess fallback 输出 aarch64-unknown-linux-musl | E011 |

## 源码修改

无独立补丁文件 — 配方 conanfile.py build() 内联 sed 实现 (config.guess/config.sub/configure)。
这是探索性编译模式 (R3: 不生成 .patch, 源码修改记录于 notes + 配方内)。

## 依赖版本

- 无外部 Conan 依赖 (W0: ncurses 独立)
- 工具链: clang 15.0.4 (OHOS SDK 26.0.0.18)
- make: GNU Make 4.4.1

## 验证结果

```bash
# 静态库 (无 .so — R26)
$ file lib/libncursesw.a
libncursesw.a: ar archive
$ ar t lib/libncursesw.a | head
hardscroll.o hashmap.o lib_addch.o ...

# 工具静态链接 ncurses (readelf 仅依赖 libc.so)
$ readelf -d bin/tic | grep NEEDED
Shared library: [libc.so]

# test_package (实质调用 ncurses API — R34)
$ ./test_ncurses
ncurses 6.5 OK (curses_version=ncurses 6.5.20240427)

# conan-verify
$ ohc-run.py conan-verify ncurses 6.5
✅ 配方验证通过: ncurses 6.5 (G0-G4+L2/L4/L5)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (静态编译 + HMDFS 修复内联) |
| conandata.yml | 官方源 + sha256 |
| test_package/ | test.c (curses_version + tputs) + conanfile + CMakeLists + MANIFEST.yml |
| manifest.yaml | 版本元数据 (status: built) |
| reports/conan-verify-report.md | conan-verify 报告 |

## 注意事项

- **R26/R4**: ncurses 是系统同名库, 禁止 .so 动态库 (污染 /lib /lib64 致系统崩溃)。配方 generate() 显式 `--without-shared`。
- 制品仓 remote 访问受限 ("system acceleration policy not enabled"), 未执行 conan upload。
- 远端 feat/ncurses-6.5 为他人工作 (2026-07-31 提交), 本分支 (feat/ncurses-6.5-2E1D3D81) 独立实现, 参考其适配思路但配方独立编写 (新增 as_expr/Makefile 乱码修复)。
