# /dev/shm 占满时 conan 并行下载秒退：报的是 "No space left on device"，但磁盘还有一切

对应知识草稿：`knowledge/drafts/gdcm-3.0.24-devshm-enospc-conan-download-pool.kv`
来源：gdcm 3.0.24 适配（分支 `feat/gdcm-3.0.24`）本地 W3 首次 `conan create`。

## 命中场景

在设备上跑任何 `conan create` / `conan install` / `conan upload`，命令**几秒钟内**退出，
没进 source、没进 build。日志形如：

```
Downloading binary packages in 20 parallel threads...
Traceback (most recent call last):
  ...
  File ".../conans/client/download/download.py", line .., in _download_bulk
    pool = ThreadPool(len(downloads), ..., )
  File ".../multiprocessing/pool.py", line .., in __init__
  File ".../multiprocessing/managers.py" ...
OSError: [Errno 28] No space left on device
```

## 为什么容易误判

`Errno 28` 字面就是 ENOSPC，第一反应是"缓存盘满了"。实测排除了这个解释：

```
df -h <数据盘>          # 仍有数百 GB 可用
```

真凶是 **CPython 的 POSIX 信号量实现落在 `/dev/shm`**：`ThreadPool` 构造要
`SimpleQueue → ctx.Lock() → _multiprocessing.SemLock`，也就是 `sem_open()`；本机
`/dev/shm` 是 1 GB tmpfs 且已被占满，`sem_open` 直接 ENOSPC。所以磁盘空间与报错无关，
决定成败的是 `/dev/shm` 的剩余 inode/块。

另一个陷阱：把 `TMPDIR` 改到可写大目录**没用**——信号量不走 TMPDIR。

```bash
df -h /dev/shm                                     # Use% 100% → 命中
python3 -c "import multiprocessing as mp; mp.Lock(); print('ok')"   # OSError 28 → 命中
ls /dev/shm                                        # 沙箱下 Permission denied
```

最后一条决定了这条路在沙箱里走不通：**清不掉**。`/dev/shm` 里的对象属于别的进程，
本沙箱既列不出也不能删。所以只能让 conan 不创建线程池。

## 正确绕法

`_download_bulk()` 在 `parallel == 0` 时走串行分支（直接 `for node in downloads`），
不创建 `ThreadPool`，因此不再需要任何信号量：

```bash
conan create archives/g/gdcm/3.0.24 -cc core.download:parallel=0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="gdcm/*"
```

改完之后构建正常启动（gdcm 全量构建 + 上游 ctest 一路跑到尾），代价只是依赖
下载从并行变串行，对总时长没有可测影响（构建本身十几分钟量级）。

## 两个必须记住的写法坑

| 写法 | 后果 |
|------|------|
| `conan create ... -c core.download:parallel=0` | `ERROR: [conf] 'core.*' configurations are not allowed in profiles` —— `-c` 是 profile conf，`core.*` 被显式拒绝 |
| `conan -cc core.download:parallel=0 create ...` | `'-cc' is not a Conan command` —— `-cc` 不是顶层选项，必须挂在**子命令之后** |

两种失败都长得像"这个 conf 不支持"，容易顺势去改配方、删缓存、甚至换构建路线——
都不必。唯一正确形态是 `conan <子命令> ... -cc core.download:parallel=0`。

## 适用面与边界

- **本地设备环境问题，不是配方问题**。CI worker 的 `/dev/shm` 正常，无此现象；
  所以**不要**把这个 conf 写进 profile、`global.conf` 或任何随 PR 提交的文件里，
  也不要因此给 `conandata.yml` 填 `file://` 路径（同类"本地环境泄漏"教训）。
  知识草稿里 `rec_impl: ci-env-only` 就是这个意思。
- 任何在此设备上调 `multiprocessing.pool` 的 Python 工具都会撞同一面墙，
  先跑上面那两行 `verification_cmd` 确认。
- 兜底方案：先 `conan download <ref>` 把依赖二进制单独拉进缓存，让批量下载的
  `downloads` 列表为空、`_download_bulk` 直接 return，效果等价。
