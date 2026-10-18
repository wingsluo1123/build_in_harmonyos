# DRAFT-13623-conan-virtualrunenv-dotest-sfx-dollar0: VirtualRunEnv 导出名与上游 dotest 脚本的 $0 依赖

## 现象

在 conan build() 内复现上游 meson 测试执行时，两个细节会踩坑：
1. 环境脚本导出名是 `conanrunenv-release-armv8.sh`（来自 VirtualRunEnv，大写 E）
2. 上游 `tests/lddtree/dotest-py` 依赖同目录 `lib.sh`，其定位逻辑用 `${0%/*}`

## 根因

- Conan 2.29 `conan.tools.env` 的 RunEnv 导出名按 VirtualRunEnv 命名规则生成
- `dotest-sfx`/`lib.sh` 用 `$0` 推导自身所在目录：`$0` 无路径（PATH 查找命中）时 `${0%/*}` 退化为整个词，
  lib.sh 定位失败

## 处置

```bash
# build() 内：
bash -c 'source conanrun*.sh && cd tests/lddtree && bash ./dotest-py'
#                ^^^^^^^^^^^^ 通配兼容导出名        ^^^^^^^^^^^^^^ 带 ./ 保证 $0 含路径
```

## 关联

- 任务 1783828906105（lddtreepax 1.3.9，2026-10-14），探针日志 _analysis/lddtreepax-1.3.9/15-*.log
