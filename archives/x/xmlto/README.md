# xmlto 0.0.29 — HarmonyOS PC 适配

## 软件信息

| 字段 | 值 |
|------|-----|
| 名称 | xmlto |
| 版本 | 0.0.29 |
| 类型 | 命令行工具 (CLI) |
| 许可证 | GPL-2.0-or-later |
| 上游仓库 | https://pagure.io/xmlto |
| 描述 | XSL 工具链前端 — 将 XML 文档按指定格式（html/pdf/ps/txt/man 等）应用 XSL 样式表完成转换 |

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| （无 conan 依赖） | — | 纯脚本 + 单个 C 程序；运行期依赖系统 `bash`/`getopt`/`xmllint`/`xsltproc` |

## 适配说明

xmlto 由两部分构成：`xmlto`（bash 脚本，XSL 工具链前端）与 `xmlif`（C 程序，XML 条件处理）。
唯一需要编译的是 `xmlif.c`；`xmlto` 本身由 `configure` 从 `xmlto.in` 生成。

### OHOS 适配要点

1. **tarball 无预生成 `configure`**：构建前先 `autoreconf -fiv`（需环境提供 automake）
2. **configure 的 rm 探测受限**：设置 `ACCEPT_INFERIOR_RM_PROGRAM=yes` 绕过
3. **safe-bin rm shim 导致 make 阶段 EXIT trap 失败**（本地 WorkBuddy 沙箱特有）：
   构建脚本改为直接调用 `clang` 编译 `xmlif.c`，CI 环境无此问题
4. **xmlto 脚本 shebang**：生成的脚本 shebang 指向构建机的绝对 bash 路径，
   打包时改写为 `#!/usr/bin/env bash` 并确保 `0755`
5. **零源码补丁**：不修改上游源码

### 构建命令

```bash
autoreconf -fiv
./configure --prefix=<pkg> --bindir=<pkg>/bin --sbindir=<pkg>/bin \
            --libdir=<pkg>/lib --includedir=<pkg>/include --datarootdir=<pkg>/share
clang -DHAVE_CONFIG_H -I<src> -DNDEBUG -O3 -c -o xmlif/xmlif.o xmlif/xmlif.c
clang -o xmlif/xmlif xmlif/xmlif.o
```

## 验证结果

- conan create: ✅ PASS（日志含真实构建段，退出码 0）
- conan-verify: ✅ PASS (G0/G1/G2/G3/G4 + L2/L4/L5)
- W3 本地 CI: ✅ PASS (L0/L1/L2/L4/L5)
- 上游测试: ✅ PASS (xmlif 8/8)
- test_package: ✅ PASS（鸿蒙特有非断言测试 + 端到端消费者用例）

## 测试

### 上游测试

上游入口为 `xmlif/test/run-test`（`make check` 无可执行目标）。共 8 个用例：
`no-condition`、`unrelated-condition`、`html`、`pdf`、`ps`、`foo`、`baz`、`bar`，
与上游 `result-*` 期望逐字节比对。**实测 8/8 通过**（`reports/upstream-test.log`）。

### 适配后测试（test_package）

`test_package/consumer_test.sh`，全部基于退出码判定，不使用断言：

A. **鸿蒙特有非断言测试** —— 原生 ELF 与动态依赖闭包加载
   - `readelf -h xmlif`：OHOS aarch64 原生 ELF
   - `readelf -d xmlif`：DT_NEEDED 闭包含 `libc.so`
   - 原生执行 `xmlif`：闭包在本机真实加载

B. **端到端消费者用例（构造输入 → 真实执行 → 产出 → 校验内容）**
   - B1 `xmlto -x style.xsl --skip-validation -o out html doc.xml`：校验 HTML 产物内容
   - B2 `xmlif` 条件过滤：与上游期望输出逐字节比对

## 使用方式

```bash
xmlto html document.xml              # 转换为 HTML
xmlto -o outdir pdf document.xml     # 转换为 PDF（需 passivetex）
xmlto -x custom.xsl --skip-validation html doc.xml   # 指定样式表
xmlif condition=html < input.xml     # XML 条件处理
xmlto --version
```

## PR 信息

- 分支：`feat/xmlto-0.0.29`
- 状态：built
