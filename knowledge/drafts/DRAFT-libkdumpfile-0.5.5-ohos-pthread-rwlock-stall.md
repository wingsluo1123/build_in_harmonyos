# OHOS/musl 上 libkdumpfile 打开 dump 的 pthread rwlock 放锁-重取模式导致 FUTEX 永久挂起

## 问题
libkdumpfile 0.5.5 在 OHOS（musl libc）上，所有需要 `kdump_open_fdset` 打开 dump 的上游测试
（diskdump/elf/lkcd/sadump/multixlat/sys-xlat/xlatmap/zero/early 共 76 项）全部在读取阶段永久挂起：
父 sh 脚本 wchan=do_rt_sigsuspend、子进程 checkattr/dumpdata wchan=FUTEX。未打开 dump 的 116 项
（xlat/addrxlat/addrmap 纯 addrxlat_step_trans）全部通过——通过/失败边界恰好是"是否打开 dump"。

## 根因
- `src/kdumpfile/context.c:75/78` 初始化 `shared->lock`（rwlock）与 `cache_lock`（mutex）；
- `src/kdumpfile/open.c:480-482/512-514` 的 `uts_name_from_init_uts_ns()`/`update_linux_utsname()`
  采用「持锁 -> rwlock_unlock -> get_symbol_val（其回调 sym_value 内部 rdlock 同一把 shared->lock）
  -> rwlock_wrlock 重取」的放锁-重取模式；
- musl 的 `pthread_rwlock_rdlock` 为 tryrdlock→a_spin 自旋→__timedwait（_rw_lock futex），读者-写者
  唤醒顺序与 glibc 不同；同线程经回调重入同一 rwlock 时进入永久等待。
- `src/addrxlat/` 零锁（get_symbol_val 的 pure 翻译不取锁），故 116 项不受影响。

## 隔离实验（A/B 对照，决定性证据）
| 配置 | 结果 |
|---|---|
| A 默认（USE_PTHREAD=1, pthread_rwlock） | 76 项中挂起（wchan=do_rt_sigsuspend/FUTEX） |
| B `./configure --without-pthread`（锁退化空实现） | 9/9 代表入口全部通过 |
| C rwlock→普通 mutex 降级（USE_PTHREAD=1） | 仍挂起（排除 rwlock 语义本身） |
| D rwlock→PTHREAD_MUTEX_RECURSIVE 递归互斥 | 5/5 代表入口全过，multiread/thread-errstr 也过 |

## 修复（E029/E248 同族平台适配，走 conandata 声明补丁）
`src/threads.h` 将 `rwlock_*` 退化为递归互斥锁：`typedef pthread_mutex_t rwlock_t`；
`rwlock_rdlock=rwlock_wrlock=pthread_mutex_lock`；`rwlock_unlock=pthread_mutex_unlock`；
`rwlock_init` 用 `PTHREAD_MUTEX_RECURSIVE` 属性。保留互斥语义、消除 musl rwlock 唤醒顺序依赖，
无平台条件宏、USE_PTHREAD 保持打开。

## 验证
- 交付配置（递归互斥 + 收敛 8 补丁 + zlib）`make check`：`# TOTAL=206 / # PASS=206 / # FAIL=0 /
  # ERROR=0 / # SKIP=0`，exit 0（主日志 sha256 357c0617）；上游 205 项全部真实通过且更强
  （zlib 条件测试 diskdump-basic-zlib 也通过）；
- `conan-verify` G1-G4/L1/L2/L4/L5 全过、`finish` W2/W3（JC/L0/L1/L2 pass）；
- 鸿蒙特有测试 r04-ohos-test 新鲜运行 RUN_RC=0。

## 适用边界
- `src/kdumpfile` 含 pthread rwlock/mutex 的 Autotools C 库在 musl/OHOS 上读取类路径挂起通用；
- 递归互斥使读读不并行（吞吐降低、正确性保持），线程安全在本平台未做并发压测验证。

## 反例与限制
- `src/addrxlat` 零锁路径、纯翻译测试不受影响；
- 直接 pthread_create/join 的 `tests/multiread.c`、`tests/thread-errstr.c` 不受 USE_PTHREAD 影响，
  递归互斥修复后亦真实通过（multiread rc=0）。
