# DRAFT-10862: musl 的 tmpfile() 静态缓冲区把 TMPDIR 截断为 7 字符，临时文件落到只读前缀 → open EACCES (errno=13)

- **来源**：sox_ng 14.8.0.1 适配（2026-10-13）
- **领域**：libc 差异（glibc → musl/OHOS）× 临时文件处理
- **邻近但不同**：DRAFT-10005（musl strtol EINVAL，同 musl 主题不同根因）；DRAFT-10767（HMDFS tmp Permission denied，同权限主题不同机制）

## 现象

鸿蒙 PC 真机上 `make check`（8svx/gain 效果相关格式往返用例）报：

```
can't open channel output file
```

C 探针实证（`TMPDIR=/storage/Users/currentUser/tmp`，31 字符）：

| 操作 | 结果 |
|------|------|
| `tmpfile()` 实际使用的路径 | `/storag/fileXXXXXX`（TMPDIR 被截断为 7 字符） |
| `open("/storag/fileXXXXXX")` | EACCES (errno=13) |
| `open("/storage/Users/currentUser/tmp/fileXXXXXX")` | 正常 |

glibc 开发机上无任何编译错误（glibc 的 `tmpfile()` 正确遵循 TMPDIR），完全不可复现 —— 只在 OHOS 真机运行时暴露。

## 根因

OHOS musl libc 的 `tmpfile()` 实现基于定长静态缓冲区
`sizeof("/tmp/fileXXXXXX")` = 16 字节：只取 `TMPDIR` 的前 **7 个字符**
（16 − 8(fileXXXXXX) − 1(NUL) = 7），再拼接 mkstemp 随机后缀。
TMPDIR 超过 7 字符时，路径落到不存在的前缀下（本机 `/storag` 落在
只读 erofs 根目录），open 即 EACCES。

sox_ng 中建临时文件的效果链为 `lsx_tmpfile() → tmpfile()`，
8svx/gain 均走该路径。

## 修复（纯 C，无平台宏，glibc 行为不变）

非 WIN32 路径不调用 `tmpfile()`，改用**完整 TMPDIR** 构造临时目录
（4096 字节静态缓冲、仅初始化一次、未设置回退 /tmp、长度自检），
再交给 sox_ng 现有的"mkstemp + 关闭即删"tmpfile 模拟逻辑
（后缀 `/libSoX.tmp.XXXXXX`）。实际补丁（0004）：

```c
#ifndef _WIN32
  /*
  tmpfile() on some libc implementations (e.g. musl, as used by
  OpenHarmony PC) truncates the TMPDIR value to a short static buffer, so a
  long TMPDIR (such as /storage/Users/currentUser/tmp) produces a bogus path
  under the read-only root directory and tmpfile() fails with EACCES. Use
  the emulated mkstemp path below with the full TMPDIR value instead.
  */
  if (!path)
  {
    static char default_path[4096] = "";
    if (default_path[0] == 0)
    {
      char const * tmpdir = getenv("TMPDIR");
      if (tmpdir && tmpdir[0] && strlen(tmpdir) < sizeof(default_path) - 1)
        strcpy(default_path, tmpdir);
      else
        strcpy(default_path, "/tmp");
    }
    path = default_path;
  }
#endif
```

要点：

1. 缓冲按完整 TMPDIR 定容（4096 ≥ PATH_MAX），不复用 16 字节定长缓冲；
2. `#ifndef _WIN32` + `getenv("TMPDIR")` 运行时探测，不用 `__OHOS__`
   宏 —— glibc 语义相同（遵循 TMPDIR），行为不变，R8 合规；
3. static 仅初始化一次（幂等、避免竞争）；`strlen < sizeof-1` 检查
   防溢出（超长回退 /tmp）；
4. 注释表述 "some libc implementations"，不点名单一平台。

## 排查口诀

> OHOS 上"Linux 正常、一涉及临时文件就报 can't open / EACCES"，且
> 日志/探针显示路径被截断为 7 字符 —— 基本就是本条。先用独立 C 探针
> 验证 TMPDIR 处理，不要怀疑目录权限。

## 三段式证据链（本条已实测）

| 步骤 | 状态 | 结果 |
|------|------|------|
| 未打补丁 | make check 失败 | 8svx/gain 往返 "can't open channel output file"（tmpfile EACCES） |
| C 探针 | 根因确认 | 截断路径 `/storag/fileXXXXXX` EACCES errno=13；直接 open 同目录正常 → 路径截断而非目录权限 |
| 打完整 TMPDIR + mkstemp 模拟补丁 | 通过 | `make check` 退出码 0：src 168 ok + check.sh 74 OK + 2 VOID（上游标记），0 失败 |

反向验证：去掉补丁后 make check 失败复现，确认测试对补丁敏感。

## 适用范围

- 所有在 OHOS 上调用 `tmpfile()` 且 TMPDIR 长于 7 字符的程序
- 带效果链的音频工具（sox/sox_ng 的 8svx/gain 等）及一切基于临时文件的效果链
- 任何假定 `tmpfile()` 遵循 `TMPDIR` 的代码（musl 实现违反该假定）

## 关联文件

- `archives/s/sox_ng/14.8.0.1/patches/0004-src-libsox_i.c.patch`（`lsx_tmpfile` 非 WIN32 分支）
- `archives/s/sox_ng/14.8.0.1/notes.md`（踩坑与解决 §2，含探针实证）
- 本地日志：`/storage/Users/currentUser/tmp/sox_ng-14.8.0.1.make-check-release.log`
