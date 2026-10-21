# visidata

终端里的表格数据浏览器：打开 csv/tsv/json/xlsx/sqlite 等文件后可以分页浏览、排序、筛选、透视、绘图，
并把结果另存；支持按键宏与插件。
上游：<https://github.com/saulpw/visidata>

| 版本 | 说明 |
|------|------|
| [3.1.1](3.1.1/notes.md) | 当前适配版本（HarmonyOS PC / ohos-aarch64） |

## 这个包提供什么

- `bin/visidata` —— 主入口（`visidata --version` → `saul.pw/VisiData v3.1.1`）
- `bin/vd`、`bin/vd2to3.vdx` —— 上游发布的两个脚本
- `python/visidata/` —— 核心模块与随包依赖（python-dateutil、importlib-metadata）

## 适配要点（细节见 3.1.1/notes.md）

1. **入口两条都要处理**：上游既有 `console_scripts`（`visidata=visidata.main:vd_cli`），
   也把 `bin/vd` 作为 `scripts=` 发布 → 配方按 entry_points 生成启动脚本 + 复制实体脚本并补可执行位。
2. **上游 37 个用例真跑**：`visidata/tests/` → 本地 `37 passed`（**37/37，100%**）。
3. **消费者校验带真实数据链路**：离线 CSV 经 `vd -b -o` 批处理导出，而不是只跑 `--version`。
