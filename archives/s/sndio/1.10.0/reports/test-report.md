# sndio 1.10.0 测试报告（HarmonyOS PC / OHOS arm64）

## 测试来源

- **上游测试：无**。`sndio-1.10.0.tar.gz`（108 文件）不含 `regress/`，也没有其他测试入口，因此不存在可跑的上游用例。
- **鸿蒙独有测试**：`test_package/`（CMake 消费者工程 + 契约测试程序 + 构建期校验），由 `conan create` 在包构建完成后执行。

## 实测结果（单次 `conan create`，退出码 0）

```
sndio/1.10.0@ohpcd/stable (test package): RESULT OK: 0 failure(s)
sndio/1.10.0@ohpcd/stable (test package): [ok] consumer program links and runs against libsndio
...
sndio/1.10.0@ohpcd/stable (test package): sndio: all HarmonyOS consumer tests passed
```

### A. 消费者程序（`test_package/test_sndio.c`，CMake 链接 `sndio::sndio`）

| 断言 | 结果 |
|------|------|
| 24 个公开入口符号全部解析（sio_* / sioctl_* / mio_*） | PASS（`-- 24/24 public entry points resolved`） |
| `sio_initpar()` 把全部参数置为 `~0u` 哨兵（`sio.c` 的 `memset(0xff)` 语义） | PASS |
| `sio_initpar()` 写入真实 `__magic` 标记 | PASS |
| `sio_open()` 对不存在设备返回 NULL | PASS |
| `sioctl_open()` 对不存在设备返回 NULL | PASS |
| `mio_open()` 对不存在设备返回 NULL | PASS |
| 公开 mode 常量与 `sndio.h` 一致（SIO_PLAY/REC、MIO_OUT/IN、SIOCTL_READ/WRITE） | PASS |

### B. 构建期包校验（`test_package/conanfile.py`，22 条 `[ok]`）

| 类别 | 校验内容 | 结果 |
|------|----------|------|
| 安装布局 | `include/sndio.h`、`lib/pkgconfig/sndio.pc`、`bin/{aucat,sndiod,sndioctl,midicat}` | 6/6 PASS |
| 共享库 | `libsndio.so`、`libsndio.so.7`、`libsndio.so.7.3` | 3/3 PASS |
| ELF 动态段 | 消费者 `DT_NEEDED = libsndio.so.7, libc.so`；无任何含 `/` 的条目 | PASS |
| ELF 动态段 | `libsndio.so.7.3` 的 `DT_SONAME = libsndio.so.7` | PASS |
| pkg-config | `sndio.pc` 可重定位（`prefix=${pcfiledir}/../..`）、`-lsndio` | PASS |
| 真实数据通路 | `aucat -n -e s16 -h raw -r 8000 -c 1 -i in.raw -o out.raw`：输出与输入**字节级完全一致**（16000 B → 16000 B），输出 RMS 实测 8000（输入方波 RMS 8000；阈值 > 7200） | PASS |
| pkg-config 元数据 | `sndio.pc`：`prefix=${pcfiledir}/../..`、`-lsndio`、`Version: 1.10.0`（自解析，不依赖 pkg-config 二进制） | PASS |
| 环境跳过 | `pkg-config --modversion`（worker 无该二进制）→ 显式 `SKIP:` 记录，不计入通过 | SKIP |
| CLI 执行 | `aucat`/`sndiod`/`sndioctl`/`midicat` 均可执行并打印 `usage: <tool>` | 4/4 PASS |

ELF 动态段由测试包内**纯 Python 解析**（读 ELF64 头 → `PT_DYNAMIC` → `DT_NEEDED`/`DT_SONAME`/`DT_STRTAB`），不依赖 `readelf`/`llvm-readelf` 是否存在于 worker。

## 未覆盖的部分（如实记录，未当作通过）

1. **需要活着的 `sndiod` 的路径**：沙箱无音频硬件，`sndiod -f` 只接受已存在的 sndio 设备，无法拉起守护进程；因此 `sio_open()` 真实设备播放/录音、`sndioctl` 调音量等路径无法执行。测试对这些路径断言"干净返回 NULL"，未标记为通过。
2. **`pkg-config --modversion`**：worker 上无 `pkg-config` 二进制，仅校验了 `sndio.pc` 内容（可重定位前缀 + `-lsndio`），版本查询打印 WARN 未验证。

## 构建证据

- `configure` 平台分支生效：编译命令含 `-D_GNU_SOURCE -DHAVE_SOCK_CLOEXEC -DHAVE_CLOCK_GETTIME`，链接含 `-Wl,-soname=libsndio.so.7`：

```
/data/service/hnp/bin/clang -L... -fPIC -shared -Wl,-soname=libsndio.so.7 -o libsndio.so.7.3 debug.o aucat.o ... clock_gettime.o -lm
```

- 三个补丁全部应用（日志逐条 `Apply patch (portability): ...`），配方内置断言 `_assert_patches_applied()` 防止 toybox `patch` 静默 no-op。
