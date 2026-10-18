# DRAFT-13619-lddtreepax-pax-utils-python-subpackage: lddtreepax 是 gentoo/pax-utils 的 Python 子包，不是独立上游

## 现象

任务目标库 `lddtreepax/1.3.9` 在 GitHub 上找不到同名的独立仓库；对 gentoo/pax-utils 整树做语言预检（R47）报 `mixed`（c:12, bash:5, python:1）。

## 根因

`lddtreepax` 是发行包子包名：gentoo/pax-utils 仓库里 `lddtree.py` 是 lddtree 的纯 Python 实现，
Alpine Linux 把它拆出重命名为 `lddtreepax`（noarch）。同一仓库还包含 C 工具（scanelf、lddtree C 版等），
属 `pax-utils` 子包——整树因此是多语言多工具项目。

## 处置

- 配方范围收窄到组件：`lddtree.py` + `tests/lddtree`，语言预检传 `--lang python --src <组件目录>` 后判定通过
- 兄弟子包另立配方（本仓 `archives/p/pax-utils/1.3.10` 覆盖 C 工具）
- 交付物命名跟发行包子包名（`lddtreepax`），源码坐标跟上游（pax-utils v1.3.9）

## 关联

- 任务 1783828906105（lddtreepax 1.3.9 OHOS 适配，2026-10-14）
- 档案：archives/l/lddtreepax/1.3.9
