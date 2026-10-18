# E429 — TUI/数据类工具交付的两个要点

以 **visidata 3.1.1**（终端表格数据浏览器）的适配为例。

## 要点 1：测试环境的 TMPDIR 要按属主挑

```
E   OSError: The temporary directory ... is not owned by the current user.
```

pytest 的 `tmp_path` 会校验"临时目录属主 == 当前用户"，而 HMDFS 上构建目录属主是映射后的另一 uid。
按属主挑选可写 `TMPDIR`（专用临时挂载点优先，如 `/data/storage/el2/base/cache`），并清掉
`XDG_CACHE_HOME` / `XDG_CONFIG_HOME` / `XDG_DATA_HOME`——否则会绕过用例 monkeypatch 的 `HOME`。

## 要点 2：TUI 工具也能做"真实数据链路"校验

全屏界面不能交互，但**上游常提供批处理入口**。visidata 支持：

```bash
vd -b -o out.csv in.csv     # 批处理：读入 → 处理 → 导出
```

于是消费者校验可以真正驱动一次往返，而不是只跑 `--version`：

```python
run([vd, "-b", "-o", outcsv, csvp], env)
assert "foo" in open(outcsv).read()
```

> 只断言"命令存在 + 版本号"等于没验证 —— 交付物"能启动但不能干活"的问题，要到用户真正使用才暴露。

## 附带：`entry_points` 与 `scripts=` 并存时两条都要装

visidata 既有 `console_scripts`（`visidata=visidata.main:vd_cli`），也把 `bin/vd`、`bin/vd2to3.vdx`
作为 `scripts=` 发布。配方需要：按 entry_points 生成启动脚本 **+** 复制实体脚本并 `chmod 755`
（不要依赖 `pip --target` 的落盘位置）。

## 禁止做法

- ❌ TUI 工具只断言版本号/文件存在（`forbid_1`）。
