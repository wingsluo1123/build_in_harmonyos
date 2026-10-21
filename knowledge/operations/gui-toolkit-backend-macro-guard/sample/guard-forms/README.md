# 守卫形态矩阵（离线回归样例）

锁定检测器「什么算后端宏守卫、什么不算」的判定口径。每个子目录一个最小 C 文件，
`check.sh` 逐目录跑检测器并断言 `exit code` 与 `hard` 计数。**不需要 GTK / conan / 网络**，
任何环境都能跑：

```sh
./check.sh            # 静默模式：每例一行 PASS/FAIL
./check.sh --verbose  # 失败/成功都打印检测器完整输出
```

## 算守卫（WARN `backend-header-guarded`，脚本 exit 0）

| 目录 | 形态 |
|---|---|
| `01-ifdefined/` | `#if defined(GDK_WINDOWING_X11)` |
| `02-ifdef/` | `#ifdef GDK_WINDOWING_X11` —— 工具包自身写法（`gtk/gtkplug.h:34` 同款） |
| `03-elifdefined/` | `#elif defined(GDK_WINDOWING_X11)`（多后端 `#if`/`#elif` 链） |

## 不算守卫（HARD `backend-header-unguarded`，脚本 exit 1）

| 目录 | 形态 | 为什么不算 |
|---|---|---|
| `04-ifndef/` | `#ifndef GDK_WINDOWING_X11` | 语义相反：代码只在宏**未定义**时编译，正是 broadway-only 平台必炸的写法 |
| `05-not-defined/` | `#if !defined(GDK_WINDOWING_X11)` | 同上 |
| `06-unguarded/` | 无任何守卫 | 基线：无条件 include 后端专用头 |
| `07-platform-macro/` | `#ifdef __OHOS__` | 平台名不是工具包发布的后端宏（另有 WARN `platform-macro-guard`）；同一份源码在其它 broadway/Wayland-only 平台照样坏 |

## 为什么单列这份矩阵

`#ifdef` 与 `#if defined(...)` 语义等价、被 GTK 自身大量使用（`gtk/gtkplug.h`、
`gtk/gtksocket.h`），但只认后者的实现会把「已经正确守卫」的源码误判成 HARD 假阳性，
把人引向一个不存在的越界问题。反向地，把 `#ifndef`/`!defined` 一并当成「已守卫」，
则会把真正会炸的写法放过——两头都要钉住，所以正反形态都在本矩阵里。
