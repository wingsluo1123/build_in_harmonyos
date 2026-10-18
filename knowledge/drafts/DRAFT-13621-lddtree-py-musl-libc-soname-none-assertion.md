# DRAFT-13621-lddtree-py-musl-libc-soname-none-assertion: lddtree.py 的 musl None 输出命中上游 glibc-only 负向断言

## 现象

修复等价探针（python3 + pyelftools + 真实 `/bin/sh`）下，上游用例 lddtree-py FAIL：
`grep -i 'none'` 命中输出行 `libc.so => None`。

## 根因

两层：
1. **musl 布局**：OHOS/musl 下 `/bin/sh` 的 NEEDED `libc.so` 没有可解析的 soname 链（无 libc.so.6 之类实体文件），
   lddtree.py:649 对无法解析的库打印 `None`——上游算法的平台边界，工具本身 rc=0、树结构正确。
2. **上游断言盲区**：`lddtree.py /bin/bash | grep -i 'none'` 是负向断言（期望无 None 行），按 glibc 布局书写；
   上游 alpine/musl CI 是 `-Dtests=false`，musl 路径从未被测过。

## 处置

- 判定非适配缺陷 → 不修改上游断言、不 hack 源码
- 真实行为由 test_package 5 条正向断言覆盖（存在性/shebang/显式路径执行/真实 ELF 树结构/溯源）
- notes.md R51 表如实申报：raw 结果 + 空跑说明 + 探针 FAIL 根因

## 关联

- 任务 1783828906105（lddtreepax 1.3.9，2026-10-14），探针日志 _analysis/lddtreepax-1.3.9/16,17-*.log
