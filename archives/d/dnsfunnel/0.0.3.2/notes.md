# dnsfunnel 0.0.3.2 适配笔记

## 编译环境
- 构建系统: skarnet 自有 configure + GNU make（非 autotools、非 cmake）
- 编译日期: 2026-10-08
- 编译器: clang 15.0.4（OHOS SDK，`/data/service/hnp/bin/clang`）
- 状态: built

## 编译步骤

上游是 skarnet 家族的自有 configure，命令与 skalibs/s6-dns 同族：

```sh
./configure --prefix=<package folder> --disable-shared \
  --with-sysdeps=<skalibs>/lib/skalibs/sysdeps \
  --with-include=<skalibs>/include --with-include=<s6-dns>/include \
  --with-lib=<skalibs>/lib --with-lib=<s6-dns>/lib
make -j1
make install
```

其中 `<skalibs>` / `<s6-dns>` 是 conan 包目录（`self.dependencies["skalibs"].package_folder`
与 `self.dependencies["s6-dns"].package_folder`），`<package folder>` 即本包
`package_folder`。skarnet configure 不是标准 autotools，**不使用** Conan 的
`AutotoolsToolchain`；CC/CFLAGS 由 `env="conanbuild"` 提供（configure 自身会依次探测
CC、`${cross}gcc`、`${cross}clang`，conanbuild 把 OHOS clang 目录放在 PATH 首位）。
OHOS clang 无默认 sysroot，configure 的链接探测找不到 CRT 启动对象，因此在调用前把
`--sysroot=<ohos-sdk>/native/sysroot` 注入 `LDFLAGS`（与 skalibs 配方同一处理）。

手工分步实测（Step 2，源码 `.work` 目录，同一组依赖包目录）：

| 步骤 | 退出码 |
|---|---|
| `./configure` | 0 |
| `make -j2` | 0 |
| `make install` | 0 |
| `make check` | 0（上游 `TEST_BINS` 为空，实际循环 0 项） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 本机直连 `skarnet.org` 取源失败：HTTPS `OpenSSL SSL_connect: SSL_ERROR_SYSCALL in connection to skarnet.org:443`、HTTP `Recv failure: Connection reset by peer` | 端点对本机出口不可达（同刻 `deb.debian.org` 200，非本机网络全断） | 先用 skarnet.org 的公开镜像站取得发布归档做**内容核对**；正式源码 URL 采用上游官方 GitHub 镜像 `skarnet/dnsfunnel`（上游页面自己列出该地址），CI 对 GitHub URL 自带镜像 fallback |
| 2 | 台账只登记依赖 skalibs | 源码 `#include <s6-dns/...>`、`package/deps.mak` 链 `-ls6dns -lskarnet` | 配方 `requirements()` 同时声明 `skalibs/2.15.1.0` 与 `s6-dns/2.4.1.0`（两者均已在 ohpcd 发布且有可用二进制） |
| 3 | conan-init 模板按 autotools 生成配方（`AutotoolsToolchain` + `package_type=library`） | 模板不识别 skarnet 自有 configure | 改写为 skarnet 同族写法：直接调用 configure/make，`package_type="application"`（只装两个可执行文件，无人链接本包） |
| 4 | `s6-dns` 自身配方是 `package_type="application"`，其 `cpp_info` 不会传给消费者 | Conan 对 application 类型包不暴露 cpp_info | 依赖不走 cpp_info，直接用 `self.dependencies[...].package_folder` 拼 `--with-include/--with-lib/--with-sysdeps` |
| 5 | 上游 `make check` 不执行任何用例 | `package/targets.mak` 的 `TEST_BINS` 为空、`src/tests/` 目录不存在 | 按 `N_static=0` 口径交付：上游测试三行全 0 并附清点证据，测试面全部由 `test_package` 消费者测试承担 |

## 源码核对

- 采用的源码 URL：`https://github.com/skarnet/dnsfunnel/archive/refs/tags/v0.0.3.2.tar.gz`
  （33016 字节，sha256 `a9f3d1749ebd02116437dea913afc06949e918f656c30e052edd34d298f9698f`）
- 交叉核对的上游发布归档：`dnsfunnel-0.0.3.2.tar.gz`
  （28935 字节，sha256 `aa44a1680a5cba44bf23315661a3328c918ab83ffdd25a13e262ef21ed81a10b`，
  与上游随包发布的 `.sha256` 文件逐字节一致，`gzip -t` 通过，55 个成员）
- 两包解包逐文件对比：内容完全相同，差异仅为 GitHub 归档多 `.gitignore`、
  发布归档多三个空目录（`src/include/`、`src/include-local/`、`src/dnsfunnel/deps-lib/`，
  git 不跟踪空目录；`configure` 会自行创建所需目录）

## 源码修改

无补丁（`patches: []`）。

## 依赖版本

- `skalibs/2.15.1.0`（ohpcd 已发布，精确 `conan install --build=never` 取到二进制）
- `s6-dns/2.4.1.0`（ohpcd 已发布，精确 `conan install --build=never` 取到二进制）

## 验证结果

```text
上游测试用例统计: 静态 0 / 实跑 0 / 跳过 0（上游 TEST_BINS 为空、src/tests 不存在）
消费者测试 (test_package/test.sh): 5 条断言，全部通过（2026-10-08 本机实测，2.5s）
  [ok] dnsfunneld usage 路径（退出码 100）
  [ok] dnsfunnel-translate 生成缓存列表 caches（回环地址按默认规则剔除）
  [ok] dnsfunnel-translate 缺输入路径（退出码 111）
  [ok] dnsfunneld 绑定 127.0.0.1:<port> 并发出 -1 就绪信号
  [ok] 端到端转发：example.com 经 127.0.0.1:<port> 返回 2 条 A 记录
```

端到端转发断言的两个细节：

- **就绪信号**：`dnsfunneld -1` 在绑定成功并完成初始化后向上游 stdout 写一个换行，
  测试据此判定「已监听」，比固定 sleep 可靠。
- **查询工具**：`dnsfunneld` 的 `sanitize_and_new()` 要求 `arcount == 0`（`hdr.counts.nr`
  为 0），带 EDNS0 OPT 记录的查询会被**静默丢弃**，因此断言必须用 `dig +noedns`
  （实测：默认 dig 超时、`+noedns` 16ms 返回 2 条 A 记录）。这是上游实现选择，
  不是平台差异。
- **外网依赖**：转发断言先用 `dig +noedns @9.9.9.9` 做探针；探针不可达时测试显式打印
  `[skip] 外网 DNS 探针不可达，端到端转发断言未执行（监听/就绪断言已通过）` 并继续，
  监听/就绪/usage/缓存列表四条断言在任何网络条件下都强制执行。

Step 2 手工编译四步退出码均为 0（见上表）；`make install` 产物：

| 文件 | 说明 |
|---|---|
| `bin/dnsfunneld` | 本地 DNS 转发守护（绑定 127.0.0.1，转发到缓存列表） |
| `bin/dnsfunnel-translate` | 从 resolv.conf 生成缓存列表 |
| `include/dnsfunnel/config.h` | 构建期生成的配置头 |

## 注意事项

- `dnsfunneld` 默认绑定 `127.0.0.1:53`（特权端口），无权限运行时会报
  `unable to bind on ip 127.0.0.1 port 53: Permission denied` —— 这是上游设计行为，
  不是适配缺陷；消费者测试改用 `-p <高位端口>` + `-R ""`（关闭 chroot）验证真实转发链路。
- `dnsfunneld` 的默认 root 是 `/run/dnsfunnel/root`，进程会 `chdir + chroot` 到该目录
  并从 `./caches` 读缓存列表；该目录在本平台不存在，因此测试与部署都必须显式 `-R ""`
  或先建好 root 目录。
- 本包是**薄前端**，机制面（异步 DNS 解析、缓存）在 `s6-dns` 与 `skalibs`。
---

**编译结束**: 2026-10-08 15:07
**最终状态**: built
