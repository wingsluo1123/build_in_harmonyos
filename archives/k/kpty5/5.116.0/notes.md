# kpty5 5.116.0 — adaptation notes

## What this software is

KPty is the KDE Frameworks 5 PTY (pseudo-terminal) library. It opens and owns a
pty master/slave pair (`KPty`), drives it through the Qt event loop
(`KPtyDevice`) and starts and supervises child processes attached to it
(`KPtyProcess`). The KF5 branch targets Qt5; this is not the Qt6-based `kpty`
6.x module.

## Dependencies (read from the upstream CMakeLists.txt)

| dependency | requirement | where |
|---|---|---|
| `ECM` | `find_package(ECM 5.116.0 NO_MODULE)`, REQUIRED | `CMakeLists.txt:8` |
| `Qt5 Core` | `find_package(Qt5 5.15.2 CONFIG REQUIRED Core)` | `CMakeLists.txt:30` |
| `KF5CoreAddons` | `find_package(... REQUIRED)` | `CMakeLists.txt:32` |
| `KF5I18n` | `find_package(... REQUIRED)` | `CMakeLists.txt:33` |
| `UTEMPTER` | `find_package(UTEMPTER)` — **optional** | `CMakeLists.txt:36` |
| `Qt5::Test` | autotests only | `autotests/CMakeLists.txt` |

`UTEMPTER` is left undetected: the OHOS sysroot ships no libutempter, so
`HAVE_UTEMPTER` stays off and KPty simply does not manage utmp entries through
an external helper.

## Obstacle 1 — the two Qt5 baselines (dependency graph)

`kpty 5.116.0` hard-requires **both** `KF5CoreAddons` and `KF5I18n`, and the
published KF5 5.116.0 packages are split across two different Qt5 revisions:

| pins | packages |
|---|---|
| `qt5-qtbase/5.15.2` (plain, `-no-widgets` stub) | `kcoreaddons5/5.116.0`, `kcodecs5`, `kimageformats5`, `kglobalaccel5`, `attica-kf5`, … (21 recipes) |
| `qt5-qtbase/5.15.2.2` (DBus/Widgets capable) | `kconfig5`, `kdbusaddons5`, `ki18n5`, `kwindowsystem5`, `qt5-qtdeclarative`, … (73 recipes) |

so the graph aborted with

    ERROR: Version conflict: Conflict between qt5-qtbase/5.15.2 and
    qt5-qtbase/5.15.2.2 in the graph.
    Conflict originates from ki18n5/5.116.0

**Resolution** — the pattern already established and documented by
`kjobwidgets5/5.116.0` for this exact conflict:

```python
self.requires("qt5-qtbase/5.15.2.2", force=True)
```

`force=True` (not `override=True`) unifies the graph while keeping
`qt5-qtbase` a consuming requirement so `package_folder` stays available in
`generate()`. Republishing `kcoreaddons5` against 5.15.2.2 would cascade into
all 21 recipes that pin it, so that route was not taken.

## Obstacle 2 — ki18n5's Gettext requirement

With the graph unified, configuration advanced to `ki18n5`'s
`KF5I18nConfig.cmake`, which includes `KF5I18nMacros.cmake` and runs
`find_package(Gettext)`. CMake's `FindGettext` only probes `PATH` for the tools
and Conan does not put them there at configure time:

    CMake Error: Could NOT find Gettext (missing: GETTEXT_MSGMERGE_EXECUTABLE)

Fixed by passing the executables from the gettext package explicitly
(`GETTEXT_MSGFMT_EXECUTABLE`, `GETTEXT_MSGMERGE_EXECUTABLE`) — the same remedy
`ki18n5/5.116.0` already uses for its own build.

## Obstacle 3 — the feature probes all report "not found"

`src/ConfigureChecks.cmake` drives a set of `check_function_exists` /
`check_include_files` / `check_struct_has_member` probes. **Every one of them
reports "not found" on this target** — including `termios.h` and `pty.h`, which
the OHOS sysroot demonstrably ships — because `CMAKE_SYSTEM_NAME` is the unknown
`HarmonyOS` ("System is unknown to cmake, create: Platform/HarmonyOS") and the
try_compile/link steps do not behave. With every `HAVE_*` at 0 the source takes
neither the `openpty()` path nor a fallback and dies on

    #error No method to open a PTY master detected.

The answers are supplied as cache variables instead; the `check_*` macros all
guard on `if(NOT DEFINED ...)` and therefore skip their probe once the value is
already in the cache. **Each value below was verified directly against the OHOS
sysroot**, and the decisive one — `openpty` — was compiled *and linked* with the
device compiler before being asserted:

| probe | value | evidence |
|---|---|---|
| `HAVE_PTY_H` | 1 | `sysroot/usr/include/pty.h` exists |
| `HAVE_TERMIOS_H` | 1 | `sysroot/usr/include/termios.h` exists |
| `openpty_in_libc`, `HAVE_OPENPTY` | 1 | `openpty` declared in `pty.h`; probe using it compiles+links (rc=0) |
| `HAVE_POSIX_OPENPT`, `HAVE_GRANTPT`, `HAVE_UNLOCKPT`, `HAVE_PTSNAME` | 1 | declared in `stdlib.h` |
| `HAVE_TCGETATTR`, `HAVE_TCSETATTR` | 1 | declared in `termios.h` |
| `revoke`, `getpt`, `_getpty` | 0 | absent from the sysroot |
| `login`, `logout` | 0 | absent from the sysroot |
| `HAVE_UTMPX` | 0 | `getutxent` absent |
| `HAVE_TERMIO_H`, `HAVE_UTIL_H`, `HAVE_LIBUTIL_H`, `HAVE_SYS_STROPTS_H`, `HAVE_SYS_FILIO_H` | 0 | headers absent |

This is the same class of workaround as the SONAME flags the sibling KF5
recipes set, for the same "HarmonyOS is not a CMake platform" reason.

## Obstacle 4 — source-level portability (`patches/0001-ohos-portability.patch`)

Five fixes: the first four in `src/kpty.cpp`, the fifth in `src/kptydevice.cpp`.

1. **Qt headers.** `kpty.cpp` uses `QFile`/`QFileInfo` but only reached them
   through transitive includes from `kpty_p.h`, which includes just
   `QByteArray`/`QString`. This Qt5 build does not provide them transitively, so
   they are included directly.
2. **`QString::sprintf`** is gone from this Qt5 configuration; the two call
   sites become `QString::asprintf`.
3. **bare `endl`** is gone; it becomes `Qt::endl`.
4. **utmp session bookkeeping.** The OHOS `utmp.h` is a **stub**:
   `_PATH_WTMP` is `"/dev/null/wtmp"`, and it declares `pututline`/`getutent`
   but neither `updwtmp` nor `getutline`. `KPty::login()`/`logout()` only reach
   those two symbols when the platform has **neither** the utmpx API
   (`HAVE_UTMPX`) **nor** `login()`/`logout()` (`HAVE_LOGIN`), so both function
   bodies are enclosed in `#if !HAVE_UTMPX && !HAVE_LOGIN` … `#else` … `#endif`
   and excluded at compile time on OHOS. On glibc `HAVE_UTMPX` is 1 and the
   original utmpx path (`pututxline`/`updwtmpx`) is used unchanged.

   A note for whoever revisits this: an earlier revision of the patch put a bare
   `return;` behind the guard instead of enclosing the body. That is a *runtime*
   guard — the rest of the function is still compiled, so `updwtmp`/`getutline`
   were still referenced and the build still failed. Compile-time exclusion
   requires the `#if/#else` to wrap the code.

5. **`_k_canRead()`'s queue-length ioctl.** This one is why every upstream case
   failed. `KPtyDevicePrivate::_k_canRead()` sized its read from
   `ioctl(masterFd, PTY_BYTES_AVAILABLE, &available)` and only read *inside*
   `if (!ioctl(...))`:

   ```cpp
   int available;                                     // uninitialised
   if (!::ioctl(q->masterFd(), PTY_BYTES_AVAILABLE, (char *)&available)) {
       ... read into readBuffer ...
   }
   if (!readBytes) {                 // still 0
       readNotifier->setEnabled(false);   // notifier off for good
       Q_EMIT q->readEof();               // reported as EOF
       return false;
   }
   ```

   HarmonyOS **denies the queue-length ioctls on the pty master** — and answers
   them on the slave — so the guarded read never executed and every activation
   of the read notifier was reported as end-of-file. Measured on the device with
   a scratch program (`openpty()` pair, child attached to the slave, ioctls run
   on both ends):

   | ioctl | on master | on slave |
   |---|---|---|
   | `TIOCINQ` (0x541b) | `-1` EACCES | `0` |
   | `FIONREAD` (same 0x541b) | `-1` EACCES | `0` |
   | `TIOCOUTQ` (0x5411) | `-1` EACCES | `-1` EACCES |
   | `TIOCGWINSZ` (0x5413) | `0` | `0` |
   | `TCGETS` (0x5401) | `0` | `0` |
   | `TIOCGPTN` (0x80045430) | `0` | `-1` ENOTTY |

   `read()` on the master returns the queued data normally (`select()` says
   readable and `read()` then returned `first\n` / `second\n` in the same run),
   so the ioctl is only a sizing hint. The patch inverts the guard: on ioctl
   failure it asks for `CHUNKSIZE` and reads anyway. The master is `O_NONBLOCK`
   (`finishOpen()` sets it), so the read returns whatever is queued and
   `readBuffer.unreserve(available - readBytes)` releases the surplus. Where the
   ioctl works, nothing changes — including the closed-slave case, which
   legitimately reads zero bytes and still reports `readEof`.

   How this was pinned down: the failing run's log showed
   `log == "<|$\n<<"` for `test_pty_signals` — a `readEof` with **no** data and
   no `readyRead` at all — plus `0 bytes available, waiting` before a
   `waitForReadyRead(5000)` that returned false. `waitForReadyRead()` cannot
   succeed once the notifier is disabled, because `doWait()` loops on
   `readNotifier->isEnabled()`. The child side had already been proven correct
   (slave fd open, `TIOCSCTTY` errno 0, `dup2` to 0/1/2 done, and after
   `KProcess::setupChildProcess()` `/proc/self/fd/0..2` are the pty), which left
   the parent's read path as the only candidate.

## Device quirks around running the suite

Two things had to be handled to get the five cases executing and passing:

1. **`test_pty_basic` cannot pass here.** The case starts bash *inside* the pty
   and compares the pty output verbatim, and this device's bash always writes a
   getcwd complaint as it starts:

       shell-init: error retrieving current directory: getcwd: cannot access
       parent directories: <errno>

   That was measured from four working directories - the build tree,
   `/storage/Users/currentUser/tmp`, the test home, and a mirrored copy of the
   build tree on `/data` - and with every errno text (`Not supported`,
   `Permission denied`, `No error information`), so it is not a permissions or
   path problem: bash does this, `sh` does not. Running the binary elsewhere does
   not help either - its `DT_NEEDED` carries the *relative* path
   `../bin/libKF5Pty.so`, so it is only loadable from its own directory (a
   symlinked cwd and a mirrored tree were both tried).

   The recipe therefore runs the suite through ctest as before and accepts this
   one case ONLY when the actual output is exactly that single line followed by
   the expected payload - the pty round trip has to have produced
   `1: test\r\n2: test\r\n`. The case is recorded as environment-blocked, not
   as a pass, and the other four cases must still each report PASS.

2. **A closed slave reports EIO, not a zero-length queue.** Upstream never reads
   in that case: its `ioctl(TIOCINQ)` succeeds with 0 and the zero-length read
   returns 0, which the EOF branch catches. With the ioctl denied the read is a
   real one and returns -1/EIO, which the error branch would swallow - the
   `readEof` signal would never fire and `test_pty_signals` would lose its
   trailing `|` marker. EIO is mapped to end-of-file; any other errno still goes
   to the error branch.
## Upstream test audit

**Enumeration.** `autotests/CMakeLists.txt` registers exactly one CTest entry:

    add_test(NAME kptyprocesstest COMMAND kptyprocesstest)

driven by `QTEST_MAIN(KPtyProcessTest)` at `kptyprocesstest.cpp:219`.
`kptyprocesstest.cpp/.h` is the only test source in the tree.

**Counting real cases, not runners.** `QTest` executes every slot declared
under `private Q_SLOTS:`. In `kptyprocesstest.h` those are exactly:

| # | case |
|---|---|
| 1 | `test_pty_basic` |
| 2 | `test_pty_signals` |
| 3 | `test_ctty` |
| 4 | `test_shared_pty` |
| 5 | `test_suspend_pty` |
| | **total upstream = 5** |

The five `public Q_SLOTS` in the same header (`slotReadyRead`, `slotDoRead`,
`slotReadEof`, `slotBytesWritten`, `slotStep`) are **signal handlers used by
`test_pty_signals`, not test cases** — Qt Test only collects `private Q_SLOTS`,
so they are correctly excluded from the count of 5.

There is no other test entry point: no `tests/` directory, no second CTest
registration, and no other `QTEST_*_MAIN` macro anywhere in the tree.

A pty is a kernel facility, so these cases can only be executed on the device.

## Status

Numbers from the actual device run are recorded in `manifest.yaml`.

## CI / 复审状态记录（2026-10-04）

- 本配方本身无需再改；此前 pc-pr-review 的 FAIL（rule1 标题前缀 / rule6 AI 检视 / rule7 CI）
  已逐一处理：标题改为【积分赛】前缀、AI 检视 ✅ 通过、CI 仅剩基础设施阻塞。
- Worker 侧 SSH bridge 多次 `Connection refused: 111`（#70104 / #71250 / #71435），
  属共享 Worker 池基础设施故障，非本配方编译问题；CI 恢复后按流程 /rebuild 即可。
