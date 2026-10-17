# 原生验证报告

- 目标：HarmonyOS PC/aarch64，SDK clang 15，Release。
- 官方源码 SHA256：`e42cc098f7b8a6051c4f79a99b55162d467098aba60f69649bdc7583f0734b57`。
- `conan create`：**RC=0**。
- 上游：**84/84 CTest 组，0 失败**，168.2 秒；包含 SSL、archive、MQI、线程、GC、引擎。
- 消费者：**29/29 Prolog + 1/1 C embedding = 30/30**。
- 原始上游测试源文件未修改；没有 ctest 排除项。
- 无界面配置的六个可选扩展组未启用，范围见 notes。
- 静态声明 4035 条/221 文件（含未启用目录 366 条），与组数分别记录。
- 原生完整 create 日志 SHA256：`e7d1df394f0a6eb4355583916dd89d0da3aea633ff35b4e0df50cad27d797957`。
- 迁移验证：复制包的版本、资源定位、GMP、SSL/archive 加载与线程 1000 次循环通过。
- 原始运行日志由本次任务保存，CI 会从同一配方重新构建并运行全部注册测试。

## 安装 ELF 检查

逐个检查 50 个 ELF 的安装 RPATH，均为相对 ORIGIN 路径；
每个安装 ELF 的 SHA256 均与对应构建 ELF 相同，安装未改变已签名字节。
系统同名依赖未作为共享库链接；外部 libarchive 的传递依赖由 Conan 提供。

| 文件 | RPATH/RUNPATH | NEEDED |
|---|---|---|
| `bin/swipl` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `bin/swipl-ld` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libc.so` |
| `bin/swipl-win` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/archive4pl.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libarchive.so.13, libc.so` |
| `lib/swipl/lib/aarch64-ohos/cgi.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/crypt.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/crypto4pl.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/double_metaphone.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/files.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/hashstream.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/http_stream.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/inclpr.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/isub.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/json.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/libedit4pl.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/libswipl.so.10.0.2` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libc.so` |
| `lib/swipl/lib/aarch64-ohos/mallocinfo.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/md54pl.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/memfile.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/ntriples.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/pcre4pl.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/pdt_console.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/porter_stem.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/process.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/prolog_stream.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/protobufs.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/rdf_db.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/readutil.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/redis4pl.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/rlimit.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/sched.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/sgml2pl.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/sha4pl.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/snowball.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/socket.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/ssl4pl.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/streaminfo.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/sweep-module.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/syslog.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/table.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/tex.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/time.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/turtle.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/uid.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/unicode4pl.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/unix.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/uri.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/websocket.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/yaml4pl.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
| `lib/swipl/lib/aarch64-ohos/zlib4pl.so` | `$ORIGIN:$ORIGIN/../lib/swipl/lib/aarch64-ohos` | `libswipl.so.10, libc.so` |
