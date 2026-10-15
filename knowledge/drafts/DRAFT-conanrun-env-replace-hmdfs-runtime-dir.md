# draft-conanrun-env-replace-hmdfs-runtime-dir

## 问题

qtbase test_package 在 HarmonyOS 共享存储上运行时，QStandardPaths 的
RuntimeLocation 用例无法通过：

```
QStandardPaths: runtime directory '/storage/Users/currentUser/runtime-20020085'
  is not owned by UID 20020085, but a directory permissions 0771 owned by UID 20001006
[FAIL] Runtime directory; expected=usable path with a numeric UID fallback; actual=not matched
[FAIL] system: exit=35, expected=0
```

同一症状的另一形态：`Failed to create wl_display` / `Could not ensure
runtime directory`（Wayland 需要运行时目录）。

## 根因：两个互相独立的陷阱叠加

### ① conan 的 `env="conanrun"` 是整表替换，不是追加

test_package 的 `test()` 用 `env="conanrun"` 执行测试驱动时，宿主环境被
**整体替换**——在外层 shell 里 `export XDG_RUNTIME_DIR=...` 根本到不了
测试进程。QStandardPaths 随后退而扫描 `$HOME`、`/tmp` 下**已存在的陈旧
目录**，拿到一个不属于当前用户的路径。

### ② hmdfs 共享存储上，目录属主 UID 是固定值

hmdfs（`/storage/Users` 下的 FUSE 型共享存储）上**任何新建目录的
`st_uid` 恒为 20001006**（共享存储服务账号），无论哪个 UID 创建的。以
uid 20020085 运行的测试进程永远无法满足 Qt 的运行时目录检查（属主 ==
当前 UID 且权限 0700）——`mkdir`+`chmod` 无济于事，所有真实文件系统
路径（/、/data/local/tmp 不可达、/dev/shm 不可用）全部撞墙，exit=35。

## 修法：测试层修复，真实文件系统上保持 FAIL 语义

### 1. 运行时目录在 conanfile 里创建，并走**命令行前缀**注入

```python
# test_package/conanfile.py（test() 内）
xdg = os.path.join(self.build_folder, "runtime-dir")
os.makedirs(xdg, exist_ok=True)
# env="conanrun" 会丢弃继承变量，必须放在命令行上：
command = ["env", f"XDG_RUNTIME_DIR={xdg}"] + command
```

### 2. 测试驱动对属主不匹配的文件系统**降级 SKIP**（不是跳过检查）

```python
# run_tests.py
xdg_eff = os.environ.get("XDG_RUNTIME_DIR") or <numeric-uid fallback 探测>
if os.stat(xdg_eff).st_uid != os.getuid():
    # 共享存储型文件系统：属主恒为服务 UID，检查不可满足 → 降级 SKIP，
    # 给出明确原因；CI/真机文件系统上检查照常生效，坏了照样 FAIL。
    print("[SKIP] system: runtime dir ownership unsatisfiable on "
          "shared-storage-style filesystem", flush=True)
```

要点：**不要特判 hmdfs 的 UID 值**——判据是不变量
（`st_uid != getuid()`），对任何"目录属主固定"的文件系统都成立。

## 判据小结

| 现象 | 结论 |
|---|---|
| 外层 export 的变量测试进程里没有 | conan `env="conanrun"` 是整表替换；要传就用 `env VAR=... ` **命令行前缀** |
| hmdfs 上目录属主永远是 20001006 | 共享存储服务 UID 固定；属主检查在此类 FS 上不可满足，按不变量（`st_uid != getuid()`）降级 SKIP |
| `QStandardPaths: runtime directory ... is not owned by UID` | 上面两条叠加的典型输出；别 chmod——属主不是 chmod 能改的 |
| 为什么不直接豁免 | 真实文件系统（CI/真机）上检查会通过、用例仍然真跑真断言；SKIP 只发生在"结构上不可能通过"的共享存储形态 |
