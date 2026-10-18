# DRAFT-25001: 老 C 库 pth 线程包装层剥离——三层批量移植到 pthread

- 条目主题：依赖 pth（Portable Threads）包装库的 1990s C 代码移植到现代平台
  （OHOS 等无 pth 环境）的标准手法：头文件 / API / 构建三层同改。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：unicon 3.0.4；同范式适用于任何"系统 API 前缀映射薄包装库"。

## 错误特征
- 编译期：`fatal error: pth/pthread.h: No such file or directory`
- 链接期：`undefined reference to 'Pth_mutex_init'`、`cannot find -lpth`
- Makefile 中 `LIBS = ... -lpth` 指向不存在的库

## 根因
1. 1990s 代码用 pth 抽象线程，现代发行版与 OHOS 均不再提供 pth，制品仓也无此包——依赖链断裂。
2. pth 是 pthread 的**薄包装层**：API 与 pthread 一一对应仅前缀不同
   （`Pth_mutex_init` ≈ `pthread_mutex_init`，参数签名相同），包装层无独立语义。

## 修复（三层同改，缺一层都失败）
```bash
# ① 头文件层
sed -i 's|#include <pth/pthread.h>|#include <pthread.h>|' <files>
# ② API 层（前缀批量替换）
sed -i 's/Pth_/pthread_/g' <files>
# ③ 构建层：Makefile.in 摘除 -lpth
# 验证：三层各改后 grep 零残留
grep -rn "Pth_\|<pth/" --include='*.c' --include='*.h' .   # 必须无输出
make   # 全量复验
```

现代 libc 已含 pthread 符号（glibc 2.34+ 折叠进 libc；musl/OHOS 原生提供），
**无需补 `-lpthread`**（补了也是无害 no-op 库）。

## 适用判据与边界
- 适用：包装库源码是纯转发宏/内联、无额外状态机（API=系统 API 前缀映射）。
- 不适用：包装层有额外语义（如用户态线程调度、协程切换）——需逐 API 审查，
  不能机械替换。

## 验证（unicon 3.0.4 实证）
- 17 处 / 12 文件移植，grep 零残留；`make (all)` exit=0，7 产物全产出。
- 移植后第三方依赖清零（conanfile `requires` 为空）。
- consumer 进程内测试 + TCP 真并发测试全过。

## 关联
E407（pthread 相关 autotools 探测）、E507（pthread 符号能力探测）。
