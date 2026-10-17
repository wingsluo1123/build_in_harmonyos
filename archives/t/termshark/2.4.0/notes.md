# termshark 2.4.0 适配笔记

## 软件概况

- **上游**：https://github.com/gcla/termshark （Go，module `github.com/gcla/termshark/v2`）
- **用途**：tshark 的 Wireshark 风格终端 UI —— 在终端里交互式分析网络流量（抓包、过滤、Follow Stream、解码）
- **技术形态**：**Go CLI**（`./cmd/termshark`），go.mod 要求 go >= 1.13；依赖约 35 个较老的 Go 模块
- **运行期依赖（关键）**：**`tshark` 可执行文件** —— termshark 通过 exec tshark 完成所有协议解析，缺失则拒绝启动（`utils.go:202`：`Could not find tshark in your PATH. The tshark binary is required to run termshark.`）
- **许可证**：MIT

## 构建策略

复用本批已发布的 `archives/t/termsvg/0.11.0` / `archives/t/termshot/0.6.1` Go 配方骨架（源自 `archives/a/addchain/0.4.0`）：

```bash
GOOS=linux GOARCH=arm64 CGO_ENABLED=0 GOTOOLCHAIN=local \
  go build -trimpath -o <workspace>/link-out/termshark ./cmd/termshark
```

依赖解析：约 35 个较老 Go 模块经 `GOPROXY=https://goproxy.cn,direct` 全部解析成功（实测）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go SDK 不可执行（`Permission denied`） | OHOS 拒绝 exec 未签名 ELF；且签名会重置执行位 | `binary-sign-tool` 签名 SDK 全部 ELF + 签名后显式 `chmod 755`（+ 容错：非本用户所有文件 chmod 会 EPERM，已用 try/except） |
| 2 | Go 工具链/CI 缺失 | CI 无 go bootstrap，制品仓无 `go/*` | 配方自举 go1.26.0（多源 URL + sha256） |
| 3 | `go: no such tool "vet"` | 一次性环境异常（该 tool 实际已签名且可直接执行） | 清理 workspace 后重跑即正常 |
| 4 | 上游 3 个包测试失败（TestFolders / TestFields1 / TestCF1） | 上游测试会 exec `tshark`；而**依赖的 bindirs 只进消费者 runenv，不进本 build 进程** | build 里显式把 tshark 的 bin 加到 PATH、其**完整 lib 闭包**加到 LD_LIBRARY_PATH |
| 5 | `Error loading shared library libgcrypt.so.20` | 只注入了 tshark 自己的 lib/，而它是共享库型应用，还需 glib/libgcrypt/libgpg-error/libxml2/zstd/brotli | 遍历全部依赖的 `lib/` 目录注入（实测后 TestFolders/TestFields1 均通过） |
| 6 | test_package 报 `Could not find tshark in your PATH` | `test()` 只传了自己生成的 env 脚本，丢了 Conan 聚合的 conanrun | 显式定位 tshark 的 package_folder 并导出 `TERMSHARK_TSHARK_BIN` |
| 7 | test_package 报 `libpython3.12.so.1.0: libintl_gettext: symbol not found`（Error 127） | 把整个 conanrun 的 `LD_LIBRARY_PATH` 套到**测试进程自身** → 毒化了与本任务无关的解释器（外来 libintl 覆盖） | **不再向测试进程套 conanrun**；改为导出普通变量 `TERMSHARK_TSHARK_BIN` / `TERMSHARK_LIB_DIRS`，仅在测试脚本内为 termshark/tshark **子进程**构造隔离 env |
| 8 | `TypeError: expected str... not NoneType` | `generate()` 里 `os.path.join(dep.package_folder, ...)` 先于 None 守卫执行（部分依赖 package_folder 为 None） | 把 `if not dep.package_folder: continue` 前置 |
| 9 | HMDFS 链接风险（E051） | Go linker 对输出文件 mmap | 链接输出放 `/data/storage/el2/base/haps/entry/files/termshark-conan-go/<ver>/link-out` |

## 运行期能力核验（真机 2026-10-12）

- `termshark --help` → 正常输出 banner 与 `-i/-r/-w/-Y/-f/-d/-D` 等完整选项
- `termshark --version` → **真实 exec tshark** 并输出 `TShark (Wireshark) 4.6.7 (Git commit b439fb7b47a9).`
- `tshark -r 1.pcap -c 2`（包内随附的 upstream 夹具）→ 真实解析出 TLSv1.2 报文
- `llvm-readelf -h` → ELF64 / AArch64

## 上游测试结果（如实记录）

```
go test -count=1 ./...  →  12 个包 ok  /  1 个包失败
```

- **通过的 12 个包**：含此前因缺 tshark 而失败的 `pkg/pcap`、`pkg/fields`、根包等（注入 tshark 后真实运行）。
- **失败的 1 个包**：`pkg/shark` 的 `TestCF1`：
  - 现象：期望 `"Absolute time"`，实际 `"Absolute time                      \t_ws.col.abs_time"`。
  - 根因：`pkg/shark/columnformat.go:257` 用 `regexp.MustCompile("\\s+")` 做 2 段切分，而 **tshark 4.x 的 `tshark -G column-formats` 输出 3 列**（token / 长名 / 字段名），导致 `Name` 吞掉尾随填充与字段名。
  - **判定为上游用例对新版外部工具的陈旧**：`columnformat.go` 的上游 `master` 分支代码与本地 `v2.4.0` 逐字节一致，即上游自己也未修。
  - 处理：**不修改上游断言、不伪造通过**，如实记录为 12 ok / 1 fail。

## 验证结果

```bash
conan create archives/t/termshark/2.4.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

- 包创建成功：`termshark/2.4.0`（`EXIT=0`）
- 上游测试：`go test ./...` → 12 ok / 1 fail（TestCF1，上游陈旧，见上）
- test_package 6 项实质断言全 PASS：
  - 二进制存在于包内
  - tshark 在构造的子进程中可解析（`TERMSHARK_TSHARK_BIN`）
  - `--help` 含 banner 与 `-i/-r/-w/-Y/-f`
  - `--version` **真实 exec tshark** 并输出真实 TShark 4.6.7 banner
  - tshark 对**包内随附 pcap**（2360 字节，upstream 夹具）真实解析出报文
  - aarch64 ELF 架构校验

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | Go 配方：工具链自举+签名、非 hmdfs 链接、tshark 完整 lib 闭包注入上游测试 |
| `conandata.yml` | 官方 GitHub tag 源 + sha256（与 Homebrew formula `949c7186…` 一致） |
| `commands.json` | R38 可执行文件声明（含 tshark 运行期依赖说明） |
| `test_package/` | R34 实质验证（真实二进制 + tshark 委派 + 真 pcap 解析；环境隔离注入） |
| `manifest.yaml` | status: built，含上游测试如实记录 |

## 注意事项

- **不要向测试进程套整个 conanrun 的 LD_LIBRARY_PATH**：会毒化无关进程（本任务实测 libpython 崩溃）。应导出普通变量、只给子进程构造 env。
- 共享库型命令依赖（tshark）需要**完整 lib 闭包**，仅加其自身 lib/ 不够。
- Go SDK 签名后务必 `chmod 755`，否则报错与"缺签名"完全一样，易误判。
---

**编译结束**: 2026-10-13 04:33
**最终状态**: built
