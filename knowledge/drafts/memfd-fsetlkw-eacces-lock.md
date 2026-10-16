# DRAFT: memfd fcntl 锁限制（OHOS）

## 现象

软件启动即 FATAL，报错形如：

```
Error Cannot create lock - Permission denied (13)
```

PHP 8.5.8 (CGI SAPI) 首个实证；CLI SAPI 不触发（其 opcache 默认开关为 0）。

## 根因

OHOS 内核未实现 memfd 匿名文件上的 POSIX 记录锁：

```python
# 精确复现（python3）
import os, fcntl, struct
fd = os.memfd_create("test")                                  # 成功
lk = struct.pack('hhqqi', fcntl.F_WRLCK, 0, 0, 1, 0)
fcntl.fcntl(fd, fcntl.F_SETLKW, lk)
# → OSError: [Errno 13] Permission denied
```

对照：HMDFS 普通文件上 `flock` 与 `F_SETLK/F_SETLKW` 均正常——
差异面是**锁目标为 memfd**，不是锁调用本身。

PHP OPcache 锁初始化（`zend_shared_alloc.c`）在 Linux 系目标优先走
`memfd_create`（`HAVE_MEMFD_CREATE`），拿 fd 后 `F_SETLKW` 失败即
`zend_accel_error_noreturn`。

## 修复

1. **源码补丁**（首选）：关默认值——
   `archives/p/php/8.5.8/patches/0005-opcache-disable-by-default-on-ohos.patch`
   将 `opcache.enable` 默认 "1"→"0"，保留显式 `-d opcache.enable=1` 能力。
2. **二进制等价修复**（制品层）：ini entry 的 `default_value` 指针重定向到
   已存在的 "0" 字符串（8 字节等长，重签）。
3. **不可禁用的锁**：改走普通文件锁路径（HMDFS 支持 flock/fcntl），跳过
   memfd 分支。

## 排查信号

- 二进制 `strings` 同时含 `memfd_create` 与 `fcntl` 锁；
- 运行报 `Cannot create lock`；
- ini 的 lock 路径/`TMPDIR` 调整均无效（锁不走文件系统）。

## 验收要点

必须覆盖非 CLI SAPI：PHP 案例中 CLI 60 项深测全过而 `php-cgi` 开箱即崩；
上游测试套件中带 `--INI-- opcache.enable=1` 段的测试会如实暴露该缺陷
（修复后此类测试仍失败属预期，需在 notes 声明为平台限制）。

## 关联

- 配方修复：build_in_harmonyos `archives/p/php/8.5.8/`（0005 补丁）
- 上游源码：`ext/opcache/zend_shared_alloc.c:98`（memfd_create 优先路径）、
  `ext/opcache/zend_accelerator_module.c:286`（ini 默认值）
