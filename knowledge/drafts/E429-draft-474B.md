# E429 — musl 头与内核 uapi 头重复定义 sockaddr_storage；configure 的文档工具硬检查与 sbin 布局

## 错误特征
```
1) OHOS 上编译 C 项目时（musl + sysroot 的 linux 头）：
   .../sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'
   struct sockaddr_storage { ... }
   .../sysroot/usr/include/sys/socket.h:377:8: note: previous definition is here
2) configure 阶段被文档工具挡住：
   checking for asciidoc... no
   configure: error: "asciidoc not found"
3) 装完包里找不到期望的产物：
   [FAIL] 缺少可执行产物：<pkg>/bin/madwimax        （上游是 sbin_PROGRAMS）
```

## 触发条件
- 平台: musl（OHOS）+ 内核 uapi 头（sysroot 的 `linux/*.h`）
- 阶段: build（编译）与 configure、package（布局）

## 根因分析
1. **musl 头与 uapi 头的重复定义**：上游 `src/tap_dev.c` 的 include 顺序是
   `<sys/socket.h>` → `<linux/if.h>` → `linux/socket.h`，两边都定义 `sockaddr_storage`。
   **关键**：musl 侧 `sys/socket.h:376` 是 `#ifndef __MUSL__` 包裹 —— 平台把这处交给了内核头。
2. **文档工具硬检查**：`configure.ac` 里 `AC_MSG_ERROR(["asciidoc not found"])`；同处
   `AC_ARG_WITH(man-pages)` 提供了 `--without-man-pages`。
3. **sbin 布局**：上游 `sbin_PROGRAMS = madwimax`，与仓库命令声明约定的 `bin/` 不一致。

## 解决方案
1. **一个 -D 解决头冲突**（不改上游源码）：
   ```python
   tc.extra_defines.append("__MUSL__")     # musl 不再自定义 sockaddr_storage，只剩内核头那份
   ```
   > 通则：遇到"musl 头 + linux uapi 头"的重复定义，**先看 musl 侧有没有 `__MUSL__`/`__DEFINED_*`
   > 守卫**；有守卫就加宏，没必要去改上游的 include 顺序。
2. **关掉文档生成**：
   ```python
   tc.configure_args.append("--without-man-pages")
   ```
3. **包内布局自己兜底**：`package()` 里 `make install` 之后再显式拷一次
   ```python
   shutil.copy2(<built exe>, <package>/bin/<name>)   # chmod 755
   ```

### 禁止做法
- ❌ 为头冲突去改上游 include 顺序（能加守卫宏就别动源码）
- ❌ 为了 asciidoc 去装文档工具链（文档非适配必需品，先找 `--without-*` 开关）
- ❌ 假定 `make install` 一定落到 `bin/`（按上游 Makefile.am 的 *_PROGRAMS 判断）

## 验证
```bash
grep -n '__MUSL__\|__DEFINED' <sysroot>/usr/include/sys/socket.h     # 确认守卫存在
grep -rn '#include <linux/' src/ | head                             # 谁会带出 uapi 头
grep -n 'AC_MSG_ERROR' configure.ac | head                          # configure 的硬检查点
ls <pkg>/bin <pkg>/sbin                                             # 产物落点
<exe> --help ; <exe> --version                                      # 真跑断言
```

## 关联条目
- 相关: E429（同一草稿 id 下的其它适配条目：conan 下 CMake 工程四处目标名/路径不匹配 /
  上游 CMake 假定系统路径与 SKIP_RPATH / 脚本式工具入口打包三坑 / 平台清单版本 vs 真实上游版本 /
  上游无测试时补测并摊开构成 / 判依赖先扣仓库已有 等）
