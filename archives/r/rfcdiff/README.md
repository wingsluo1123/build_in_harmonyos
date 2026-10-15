# rfcdiff

rfcdiff 比较两份 Internet-Draft / RFC 文本，先剥掉每页的页眉页脚再做差异，输出更干净的结果。
单文件 bash 脚本（内嵌 awk），支持四种输出：

- 并排 HTML（默认，`--html`）
- 左边距带变更条的文本（`--chbars`）
- 普通 diff（`--diff`）
- 分页 wdiff / 带颜色的 HTML wdiff（`--wdiff` / `--hwdiff`，需要 `wdiff`）

- 上游：https://github.com/ietf-tools/rfcdiff （tag `1.49`）
- 许可证：GPL-2.0-or-later

## 交付内容

- `bin/rfcdiff`：上游脚本，应用了 1 个鸿蒙适配补丁（见下）
- `share/doc/rfcdiff/README.md`：上游文档
- `licenses/LICENSE`：许可证正文

## 使用

```sh
rfcdiff draft-foo-00.txt draft-foo-01.txt             # 生成 draft-foo-01-from-00.html
rfcdiff --chbars --stdout old.txt new.txt             # 变更条文本输出到标准输出
rfcdiff --diff --stdout old.txt new.txt               # 普通 diff
rfcdiff --keep old.txt new.txt                        # 保留临时工作文件（位于 $TMPDIR）
```

## 运行时依赖

`bash`、`awk`、`diff`、`sed`、`grep`、`tr`、`tar` —— 操作系统自带工具，不是 Conan 包，
所以配方没有 `requires`。可选：`wdiff`（词级差异，缺失时自动回退内置着色）、
`wget`（参数为 http/ftp URL 时）、浏览器（`--browse`）。

## HarmonyOS 适配

单个补丁 `patches/0001-rfcdiff.patch`，三处各一行改动：

1. **shebang → `/data/service/hnp/bin/bash`**（E165）：鸿蒙没有 `/bin/bash`。
2. **工作目录 → `${TMPDIR:-/tmp}/rfcdiff-$$`**（E002）：鸿蒙 `/tmp` 只读，上游硬编码 `/tmp` 会在
   任何输出模式下报 `Failed to create temporary directory`。
3. **`--keep` 分支 `cd /tmp` → `cd "${workdir%/*}"`**：保留现场时在工作目录旁打包。

## 测试

上游发布树（tag 1.49）只有 `LICENSE`、`README.md`、`rfcdiff`，没有任何测试（N = 0）。
`test_package/` 补充：

| 来源 | 用例数 | 说明 |
|------|--------|------|
| `test_rfcdiff.sh` | 10 | 对合成 Internet-Draft 运行包内 rfcdiff，逐字节校验各输出模式 |
| `test_rfcdiff_ohos.sh` | 5 | 鸿蒙特有：shebang、经 OHOS bash 运行、`$TMPDIR` 落点/清理/报错语义 |

详见版本目录的 `notes.md`。

## 版本

| 版本 | 制品引用 | 上游版本 | 状态 |
|------|----------|----------|------|
| 1.49 | `rfcdiff/1.49` | 1.49 | built |
