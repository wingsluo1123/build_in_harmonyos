# program_invocation_short_name 探测链需第三级 musl fallback(libinput 1.28.1 载体)

- **草稿 ID**: DRAFT-13400-libinput-1.28.1-musl-program-invocation-name-third-fallback
- **来源**: libinput/1.28.1 适配(积分赛依赖任务,PR 同分支提交)
- **分类**: meson / musl / glibc-extension / config-h
- **状态**: 随 PR #13400 提交(待 CI/审核)

## 问题 / 错误签名

- 上游 `meson.build` 对 glibc 全局 `program_invocation_short_name` 的探测只有两级:glibc 直供 → BSD `getprogname()`。
- musl(OHOS PC)两级皆不命中 → `config.h` 不定义该宏 → 编译 `tools/libinput-record.c`、`tools/ptraccel-debug.c` 时报 `use of undeclared identifier 'program_invocation_short_name'`(仅有的两个使用点,都在 usage() 输出)。

## 根因

1. `program_invocation_short_name` 是 **glibc 扩展**(errno.h 在 _GNU_SOURCE 下声明),POSIX/BSD 标准对应物是 `getprogname()`(BSD)/`__progname`(musl 提供 BSD 兼容变量,但无声明头)。
2. 上游探测链没有"两者皆无"的兜底分支:glibc 和 BSD 之外的平台(musl)静默漏定义。
3. 使用点只有 tools 的帮助输出,符号仅用于打印程序名——字面量兜底无功能损失。

## 最小修复方案

在 meson 层收敛(不逐文件 extern):

```meson
if not cc.has_header_symbol('errno.h', 'program_invocation_short_name', prefix : prefix)
    if cc.has_header_symbol('stdlib.h', 'getprogname')
        config_h.set('program_invocation_short_name', 'getprogname()')
    else
        # musl 两级皆无;仅 tools 的 usage() 使用,字面量即可
        config_h.set('program_invocation_short_name', '"libinput"')
    endif
endif
```

## 备选方案(仓库已有先例)

- **per-file 别名**(main 上 libinput 1.26.2 的做法):在使用文件内 `extern char *__progname;` + `#define program_invocation_short_name __progname`——语义等价且保留运行时程序名,适合使用点分散、无法在构建系统收敛的包;
- 两种方案任选;能改 meson/config.h 时构建系统层收敛更好。

## 实际验证结果

- 补丁对 Debian `1.28.1.orig.tar.gz` 解包树 `git apply --check` 通过;
- musl 兼容静态检查 43/43 通过(语法级);
- 实际交叉构建由 CI `conan create` 完成(随 PR 提交时待跑)。

## 适用范围

- musl 上构建、代码使用 `program_invocation_short_name`/`program_invocation_name` 且上游探测链缺兜底分支的包(libinput、consolation、eudev 系列在仓内多次复现);
- 探测链形态:has_header_symbol(errno.h) → has_header_symbol(getprogname) → ???

## 非适用边界

- 使用点在核心路径(非帮助输出)且程序名语义重要时,字面量兜底不够,应走 `__progname` 别名;
- glibc-only 包(不追求 musl 兼容)无需处理。

## 查重差异

- main 上 libinput 1.26.2 补丁用的是 per-file `__progname` 别名(见其 notes 问题 2);本条以 1.28.1 为载体补充**构建系统层第三级字面量兜底**方案,并记录两方案的取舍(收敛位置 vs 运行时语义)。

## 关联交付

- 本草稿与 `archives/l/libinput/1.28.1/**` 属同一交付范围(同 PR 关联,知识库扩展路径 B)。
