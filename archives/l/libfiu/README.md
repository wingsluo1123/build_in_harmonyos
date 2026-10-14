# libfiu

## 简介
libfiu 是用户态故障注入（fault injection）C 库：用核心 API（`fiu_fail`/`fiu_return_on` 等）在代码中标记“失败点”，用控制 API（`fiu_enable`/`fiu_disable`/`fiu_enable_random` 等）在测试中启用或禁用这些失败点。附带 POSIX 预加载模块（无需改源码即可模拟 POSIX 失败）与 `fiu-run`/`fiu-ctrl`/`fiu-ls` 工具。上游以公有领域（BOLA-1.1）发布。

## OHOS 适配
- 纯 Makefile 项目（无 configure）：编译器、归档器从 Conan conf 获取，经 `make CC=... AR=... RANLIB=... -j1` 传入（R33/R9）
- 上游 Makefile 的 `PREFIX` 即最终安装前缀，`make PREFIX=<package_folder> install` 直装（该项目无 DESTDIR 语义，注意与 zlib 式 `DESTDIR` 区分）
- 上游测试 `make test` 在 build() 真实运行（C 测试 + Python 测试 + generated/collisions/utils 子套件），证据标记 `HMBS_UPSTREAM_TEST_RESULT` 由实际输出解析产生
- 非系统同名库，动态库与静态库同时保留（preload 预加载模块本质为共享对象，fiu-run 依赖它们）

## 依赖
- 无（仅系统 libc/pthread/libdl；Python 测试使用真机 python3，不进配方依赖）

## 功能验证
```c
#include <fiu.h>
#include <fiu-control.h>
fiu_init(0);
fiu_enable("no_free_space", 1, NULL, 0);
assert(fiu_fail("no_free_space") != 0);
fiu_disable("no_free_space");
assert(fiu_fail("no_free_space") == 0);
```

## 参考
- 官网: https://blitiri.com.ar/p/libfiu/
- 上游仓库: https://github.com/albertito/libfiu
