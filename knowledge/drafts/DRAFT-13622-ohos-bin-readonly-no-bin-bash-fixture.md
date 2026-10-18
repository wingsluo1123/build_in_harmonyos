# DRAFT-13622-ohos-bin-readonly-no-bin-bash-fixture: OHOS /bin 只读且无 /bin/bash，fixture 依赖的上游测试空跑

## 现象

lddtree-py 上游用例 `lddtree.py /bin/bash | grep -i 'none'` 在 OHOS 上 raw PASS，但输出为空——
`/bin/bash` 不存在（`test -x /bin/bash` 失败），且 `/bin` 只读无法补 fixture。

## 环境事实

- `/bin` 只读，无 bash（bash 位于 `~/.harmonybrew/bin/bash`）
- `/usr/bin/env` 是 toybox 符号链接（功能可用）
- `/tmp` 只读 → 临时文件一律放工作目录（如 `_analysis/`）
- toybox 限制：`cat -A` 不支持，`whoami`/`id` 不可用

## 处置

1. 上游测试 fixture 先做存在性预检，缺失即记空跑（E363 边界，与 pax-utils/1.3.10 notes 同类记录）
2. 修复等价探针：真实 ELF 输入（`/bin/sh`）+ 设备 python3 + conanrunenv，验证工具本体
3. R51 申报表如实申报 raw 结果与空跑原因，不粉饰

## 关联

- 任务 1783828906105（lddtreepax 1.3.9，2026-10-14）
- 档案：archives/p/pax-utils/1.3.10/notes.md（同类 E363 记录）
