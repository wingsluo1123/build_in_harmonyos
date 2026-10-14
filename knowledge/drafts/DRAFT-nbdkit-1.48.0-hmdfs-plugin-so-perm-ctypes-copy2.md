# test_package 消费者 ctypes.CDLL 加载插件 .so 权限问题（HMDFS + copy2 EPERM）

## 问题

nbdkit 1.48.0 R01 的 test_package 用 Python `ctypes.CDLL` 直接加载安装目录下的
插件 `nbdkit-example1-plugin.so`。本地验证通过，但远端 CI 的
`conan create` 在 test_package `test()` 第 73 行失败：

```
OSError: Error loading shared library .../lib/nbdkit/plugins/nbdkit-example1-plugin.so: Permission denied
```

## 根因

1. **HMDFS 权限位归一化**：HarmonyOS HMDFS 将文件权限归一化为 owner+group
   （实测插件 .so 为 `770`，other 无读/执行位），且 **chmod 试图补 other 位不生效**
   （实测 `chmod 755 → 770`、`chmod 644 → 660`）。CI worker 用户若不属于文件的
   owner/group，`open(2)` 即 EACCES → `dlopen` Permission denied。
   本地用户属于 group `file_manager`（uid 20020101 ∈ 1006），故本地可加载。
2. **shutil.copy2 在 HMDFS 上触发 EPERM**：若先用 `copy2` 把插件复制到临时路径
   再加载，复制元数据（权限位）本身报
   `PermissionError: [Errno 1] Operation not permitted`。

## 方案

1. **打包源头修正**：`conanfile.py package()` 遍历 `package_folder` 归一化权限——
   `.so`/`.a`/`bin/` 下文件 `chmod 775`，其余 `664`（HMDFS 下尽力而为）。
2. **test_package 改用用户可写路径 + C dlopen**：
   - 用 `shutil.copyfile`（仅复制内容，**不用 copy2**）把插件复制到
     `tempfile.mkdtemp(dir=$TMPDIR)` 用户可写目录，显式 `chmod 744`；
   - 编译 C 消费者（test.c，公开 plugin ABI dlopen 断言）并对复制路径运行，
     与本地 harmonyos_special_test 验证方式一致。

```python
# conanfile.py package()
import os
for root, dirs, files in os.walk(self.package_folder):
    for f in files:
        p = os.path.join(root, f)
        try:
            os.chmod(p, 0o775 if (f.endswith(".so") or f.endswith(".a") or "/bin/" in p) else 0o664)
        except OSError:
            pass

# test_package test()
work = tempfile.mkdtemp(prefix="pkg-tp-", dir=os.environ.get("TMPDIR", None))
shutil.copyfile(example, os.path.join(work, "plugin.so"))   # 不能 copy2
os.chmod(os.path.join(work, "plugin.so"), 0o744)
self.run(f'"{cc}" -o "{consumer}" "{test_c}" -ldl')
self.run(f'"{consumer}" "{os.path.join(work, "plugin.so")}"', env="conanrun")
```

## 验证

- 修复前：CI `ctypes.CDLL(plugin.so)` → Permission denied；本地 `copy2` → EPERM。
- 修复后：`conan create` test_package 通过
  （C dlopen consumer 输出 `consumer loaded plugin: name=example1 struct_size=384`，
  `nbdkit 1.48.0 consumer validation PASSED`）。
- 本地重跑 harmonyos_special_test（C dlopen）6 断言全 PASS（log sha 2b330a49…）。

## 适用边界 / 反例

- **适用**：任何 test_package/消费者需要 dlopen 安装在 HMDFS 目录下的
  `.so`（插件、扩展、动态模块）且 CI 用户可能不属于文件 group 的场景。
- **反例 / 不适用**：
  1. E212 场景：hmmac 安全标签阻止用户路径 dlopen（方案是装 hnp 标签路径，
     禁 chmod，与本候选不同）；
  2. 本地同组用户直接加载 770 .so 可过（不能据此判定 CI 也可过）；
  3. 纯链接型（静态 .a）不涉及 dlopen 权限。

## 查重差异（七轴）

| 轴 | 结论 |
|----|------|
| exact_duplicate | 否（无同签名条目） |
| causal_duplicate | 否（E212 归因 hmmac 标签，本候选归因 Unix 权限位 + HMDFS 归一化 + copy2 EPERM） |
| trigger_overlap | 部分（E212/E143 同为 dlopen .so Permission denied） |
| solution_overlap | 部分（E212=装 hnp 路径勿 chmod；本候选=copyfile 到用户路径 + C dlopen） |
| combination_novelty | 是（copy2 EPERM + 770 权限位 + ctypes→C dlopen 迁移三要素） |
| boundary_novelty | 是（copyfile 可、copy2 必 EPERM；other 位 chmod 无效） |
| test_migration_novelty | 是（conan-verify G2 可复现，可迁移其他含 dlopen 模块的包） |

## 关联

- 产生库：nbdkit 1.48.0（archives/n/nbdkit/1.48.0，R02）
- 相关条目：E212、E143、E045；同库另一草稿 DRAFT-nbdkit-1.48.0-application-autotools-module-shared-conflict