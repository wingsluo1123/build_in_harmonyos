# visidata 3.1.1 适配说明（HarmonyOS PC / ohos-aarch64）

## 1) 身份与源

- 上游：`https://github.com/saulpw/visidata`（版本 **3.1.1**，与平台清单一致）
- 源：PyPI sdist `visidata-3.1.1.tar.gz`（平台 pip 镜像直链），sha256
  `8c4484158f0851e4887e595542bd65bdd991de9c20652b442b3fd9742ce8b031`，13,166,704 字节，317 个文件
- 它做什么：终端里的表格数据浏览器 —— 打开 csv/tsv/json/xlsx/sqlite 等文件后可以分页浏览、排序、
  筛选、透视、绘图，并把结果另存；支持按键宏与插件，适合无 GUI 环境直接处理数据。

## 2) 构建与安装

```
pip install --target <包>/python python-dateutil importlib-metadata
pip install --no-deps --target <包>/python .
# 按 entry_points visidata=visidata.main:vd_cli 生成 <包>/bin/visidata
# 复制上游 scripts：bin/vd、bin/vd2to3.vdx → <包>/bin
```

产物：`bin/{visidata, vd, vd2to3.vdx}`、`python/visidata/` + 随包依赖、`licenses/LICENSE.gpl3`。

## 3) 测试环境的两处适配（不改上游用例）

1. **按属主挑选 TMPDIR** —— pytest 的 `tmp_path` 校验"属主 == 当前用户"，HMDFS 上构建目录属主不同；
2. **清 `XDG_CACHE_HOME`/`XDG_CONFIG_HOME`/`XDG_DATA_HOME` 并补 `/system/bin` 到 PATH** ——
   避免用例的 HOME monkeypatch 被绕过、并让用例能 spawn 系统命令。

## 4) 测试

- **上游用例（真跑）**：`visidata/tests/` → 本地 `37 passed`（**37/37，100%**），用例内容未改。
- **消费者校验**：`test_package/check_visidata.py` **6 项**（全部离线）→
  `checks=6 fails=0 skips=0 / RESULT: PASS`，含 `visidata --version` 真跑与一次
  **真实批处理**（离线 CSV 经 `vd -b -o` 导出，输出含 foo/bar）。

## 5) 实测（本地 conan create）

`rc=0`；上游 `37 passed`；消费者 6/6 通过。
