# termshot 0.6.1 适配笔记

## 软件概况

- **上游**：https://github.com/homeport/termshot （Go，module `github.com/homeport/termshot`）
- **用途**：在**真实伪终端**中执行命令，捕获其输出（含 ANSI 颜色与文本修饰）并渲染成仿真终端窗口样式的截图（PNG/JPEG）
- **技术形态**：**Go CLI**（`./cmd/termshot`），go.mod 要求 go >= 1.24.0
- **许可证**：MIT

## 构建策略

直接复用 2026-10-12 同批发布的 `archives/t/termsvg/0.11.0` 骨架（Go 工具链自举 + 签名 + 非 hmdfs 链接），其本身源自 `archives/a/addchain/0.4.0`。

```bash
GOOS=linux GOARCH=arm64 CGO_ENABLED=0 GOTOOLCHAIN=local \
  go build -trimpath -o <workspace>/link-out/termshot ./cmd/termshot
```

**cgo 判定（重要）**：termshot 的依赖含 `fogleman/gg` 与 `golang/freetype`，看似需要 cgo；实测其字体栅格化与 PNG/JPEG 编解码走纯 Go 的 `golang.org/x/image` 后端，`CGO_ENABLED=0` 可完整构建出静态二进制并在 OHOS 直接运行（真机实测）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go SDK 下载后可执行位丢失（`-rw-rw-r--`），exec 报 `can't execute: Permission denied` | 本次签名循环只做了 `sign + mv`，遗漏 `chmod 755`；与「缺 .codesign」的报错**表象完全相同**，极易误判 | 签名后显式 `chmod 755`（`_sign_go_sdk_if_ohos` 内每个 ELF 签完即设权限） |
| 2 | `_sign_elf_if_ohos` 抛 `PermissionError: [Errno 13]` on chmod | 手工实验曾在 workspace 留下**其他 uid 所有**的已签名文件；`go build` 因缓存/未重链走到「已签名」分支，对该文件 chmod 触发 EPERM | ① chmod 改为 try/except 容错（文件已签名，权限非致命）；② 清理手工实验残留 link-out/sign-tmp 后重跑 |
| 3 | 上游 `internal/ptexec` 的 "should run with fixed terminal size" 失败：`failed to get size: inappropriate ioctl for device` | `exec.go:175` 通过 `pty.GetsizeFull(os.Stdout)` 取终端尺寸；conan 构建环境的 stdout 是**管道**（非 tty）→ ioctl 返回 ENOTTY。注意：**平台 pty 本身没问题**（C 探针实测 master/slave 上 TIOCGWINSZ/TIOCSWINSZ 均成功，row=24/col=80 可读写） | 上游 `exec.go:179-186` 自带 `isCI()` 回退路径（CI=true 时以 80x25 兜底，再应用请求的 rows/cols）。配方在上游 `go test` 环境注入 `CI=true` 走**官方**路径；实测 3/3 Specs 真实通过（`stty size` == `12 40`），未跳过、未削弱任何断言 |
| 4 | HMDFS 链接风险（E051） | Go linker 对输出文件 mmap，hmdfs 不支持 | 链接输出放 `/data/storage/el2/base/haps/entry/files/termshot-conan-go/<ver>/link-out`，完成后再拷回 build_folder |
| 5 | `go test` 的 `*.test` 二进制无法 exec | 未签名 ELF；0 用例执行 | `go test -exec <wrapper>`，wrapper 在 exec 前对测试二进制签名 |

## 运行期能力核验（真机 2026-10-12）

- `termshot --version` → `termshot version (development)`（上游无版本变量，未注入）
- `termshot --help` → 正常输出用法与 pty 说明
- `termshot -f out.png -- echo "hello from termshot"` → **成功**，产出 **16,319 字节 PNG，837x425 像素**
- `llvm-readelf -h` → ELF64 / AArch64

## 验证结果

```bash
conan create archives/t/termshot/0.6.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

- 包创建成功：`termshot/0.6.1`（`EXIT=0`）
- 上游测试：`go test -count=1 ./...` → **2 个包 ok / 0 fail**
- test_package 9 条断言全 PASS（归入 5 个验证项：二进制可用 / 真 pty 截图为真 PNG / 尺寸 / ANSI 红色像素 / aarch64 ELF）：
  - 二进制存在于包内
  - `--help` 含用法/pty 说明、`--version` 可运行
  - 真实命令经真伪终端产出真实截图（16,319 字节）
  - 有效 PNG（837x425）魔数与尺寸校验
  - aarch64 ELF 架构校验

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | Go 配方：工具链自举+签名、非 hmdfs 链接、签名后 chmod 容错、CI=true 上游测试回退 |
| `conandata.yml` | 官方 GitHub tag 源 + sha256 |
| `commands.json` | R38 可执行文件声明 |
| `test_package/` | R34 实质验证（真实二进制驱动 + PNG 尺寸/魔数断言） |
| `manifest.yaml` | status: built |

## 注意事项

- `OHOS_GO_WORKDIR` 可覆盖 Go 工作区根目录（默认为 `/data/storage/el2/base/haps/entry/files/termshot-conan-go`）。
- CI 环境下 `go test` 需 `CI=true`（上游 isCI 契约），否则 ptexec 固定尺寸用例在非 tty 下会失败。
- 与 termsvg 的差异：termsvg 注入了 ldflags 版本号（上游有 `main.version` 变量），termshot 上游无版本变量，不做注入。
---

**编译结束**: 2026-10-13 04:32
**最终状态**: built
