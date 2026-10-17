# DRAFT — 共享库型命令依赖：运行时闭包只注入子进程，测试进程自身绝不套整个 runenv

> 拟提升编号：E554（最终编号由知识库主编确认）
> 来源：termshark 2.4.0 适配（2026-10-13，鸿蒙 PC 真实机）

## 错误特征

```
# 注入不足：只加了 tshark 自己的 lib/
Error loading shared library libgcrypt.so.20: (needed by .../libwireshark.so.19)
Error relocating .../libwireshark.so.19: gcry_control: symbol not found

# 上游测试里 exec tshark 但没注入 PATH
exec: "tshark": executable file not found in $PATH
exit status 127

# 注入过度：把整个 conanrun 套到测试进程自身
Error relocating /data/service/hnp/python.org/python_3.12/lib/libpython3.12.so.1.0: libintl_gettext: symbol not found
Error relocating /data/service/hnp/python.org/python_3.12/lib/libpython3.12.so.1.0: libintl_dgettext: symbol not found
...
ConanException: Error 127 while executing
```

## 场景

可执行包 A（termshark）在运行期 **exec** 另一个共享库型可执行依赖 B（tshark）。
B 是 `package_type="application"`，暴露 `bindirs=["bin"]` / `libdirs=["lib"]`，
且它自身依赖一整条共享库闭包。

```
tshark 的 DT_NEEDED：
  libc++_shared.so
  libwireshark.so.19      ──┐
  libwiretap.so.16         ├─ 这些又需要 libglib-2.0.so / libgio-2.0.so /
  libwsutil.so.17         ──┘   libgobject-2.0.so / libgcrypt.so.20 / libxml2.so.16 / ...
```

## 两个方向相反的错误

### 错误一：注入不足

| 现象 | 根因 |
|------|------|
| `libgcrypt.so.20` 加载失败 | 只把 tshark **自己**的 `lib/` 加进 LD_LIBRARY_PATH，缺整条闭包 |
| `exec: "tshark": executable file not found` | **依赖的 bindirs 只进消费者的 runenv，不进 A 的 build 进程**——A 的上游测试里 `exec.Command("tshark")` 自然找不到 |

### 错误二：注入过度（更隐蔽）

把整个 `conanrun` 的 `LD_LIBRARY_PATH` 套到**测试进程自身**：

```
self.run(f'"{sys.executable}" "{test_script}"', env=["termshark_test_env", "conanrun"])
```

结果：路径列表里的外部 `libintl` 被加载，`libpython3.12.so.1.0` 报
`libintl_gettext: symbol not found`，消费者测试 **exit 127 死在启动阶段**——
被测功能一行都没跑到，且报错完全指向错误方向。

## 解决方案

**配方侧**：把依赖的 bin/lib 以**普通环境变量**导出（只做事实陈述，不污染任何
进程默认环境）：

```python
def generate(self):
    env = Environment()
    deps = self.dependencies
    env.define("TERMSHARK_PACKAGE_ROOT",
               deps[self.tested_reference_str.split("/")[0]].package_folder)
    tshark_bin = os.path.join(deps["tshark"].package_folder, "bin")
    env.define("TERMSHARK_TSHARK_BIN", tshark_bin)

    # 完整闭包：遍历**全部**依赖的 lib 目录
    lib_dirs, seen = [], []
    for dep in deps.values():
        if not dep.package_folder:      # ⭐ 前置 None 守卫，否则 TypeError
            continue
        libdir = os.path.join(dep.package_folder, "lib")
        if os.path.isdir(libdir) and libdir not in seen:
            seen.append(libdir); lib_dirs.append(libdir)
    env.define("TERMSHARK_LIB_DIRS", os.pathsep.join(lib_dirs))
    env.vars(self).save_script("termshark_test_env")
```

**测试侧**：在脚本内为**子进程**构造 env，测试进程自身保持原样：

```python
def build_child_env():
    env = dict(os.environ)
    bin_ = os.environ.get("TERMSHARK_TSHARK_BIN", "")
    if bin_:
        env["PATH"] = bin_ + os.pathsep + env.get("PATH", "")
    libs = [d for d in os.environ.get("TERMSHARK_LIB_DIRS", "").split(os.pathsep) if d]
    if libs:
        env["LD_LIBRARY_PATH"] = os.pathsep.join(libs + ...)
    return env

child_env = build_child_env()
subprocess.run([termshark, "--version"], env=child_env, ...)   # 只给子进程
subprocess.run(["tshark", "-r", pcap, "-c", "2"], env=child_env, ...)
```

**注意**：`self.run()` 只传 `env=["termshark_test_env"]`，**不要**加 `"conanrun"`。

**A 的上游测试**若需 exec B（termshark 的 `utils.go` 调 tshark），同样在
`_run_upstream_tests` 里显式注入 B 的 bin + 完整 lib 闭包。

## 验证

真机实测（termshark 2.4.0）：

| 检查 | 结果 |
|------|------|
| `termshark --help` | banner + `-i/-r/-w/-Y/-f` 齐全 |
| `termshark --version` | **真实 exec tshark** → `TShark (Wireshark) 4.6.7` |
| `tshark -r 1.pcap -c 2` | 真实解出 TLSv1.2 报文 |
| 二进制架构 | ELF64 / AArch64 |
| 消费者测试 | 6 项断言全 PASS，`conan create` exit_code=0 |

## 推广价值

覆盖所有"exec 另一个可执行"的可执行包：

- termshark → tshark
- snakeviz → python
- wireshark → dumpcap
- git → 页面器（less）、diff 工具（diff-highlight）

以及一切共享库型命令依赖的消费者测试。核心原则一句话：
**运行时闭包的作用域是子进程，不是测试进程自己。**
