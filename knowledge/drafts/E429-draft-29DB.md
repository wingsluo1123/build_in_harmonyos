# E429 — 在 conan 的 out-of-source 布局下接入上游 autotools 测试（5 处坑 + SKIP/makeinfo 语义）

## 错误特征
```
1) make: *** No rule to make target 'check'.  Stop.            （在源码目录跑）
2) shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not supported
   make[3]: *** [Makefile:2403: test-suite.log] Error 1        （automake 驱动在本沙箱跑不了）
3) 从构建目录 Makefile 只解析出 2 个测试名（实际 18 个）；名字还带 test_xxx$(EXEEXT)
4) Error relocating <build>/test_lsp_python: json_tokener_get_error: symbol not found   （rc=127）
   FAIL: mkdtemp / FAIL: cannot open /tmp/xwpe_chktest/...     （/tmp 只读 → abort rc=-6）
5) build-aux/missing: line 85: makeinfo: command not found → docs/xxx.info Error 127（make/check/install 都会）
```

## 触发条件
- 构建系统: conan + 上游 autotools（`check_PROGRAMS`/`TESTS`）
- 阶段: testing（接入上游自带测试）

## 根因分析
1. **out-of-source**：源码目录没有 Makefile → 必须在构建目录编译/运行测试程序。
2. **automake 的 `check-TESTS` 驱动**依赖 `getcwd()` 在构建子目录上的行为，受限文件系统上会直接失败。
3. **名单解析**：`check_PROGRAMS` 跨多行；`m.end()` 后第一项是空串（不滤空行就只读第一行）；名字带
   `$(EXEEXT)`。
4. **运行条件**：automake 在 `make check` 时会导出 `srcdir`/`builddir` 等；直跑必须自己补。
   `LD_LIBRARY_PATH` 不补会被环境里同名但不完整的库遮蔽；`TMPDIR` 指到只读目录会让 `mkdtemp` 失败。
5. **语义**：`exit 77` = SKIP（不是失败）；缺 texinfo 时 info 文档规则会中断 make（三处都会）。

## 解决方案
```python
# ① 名单解析：滤空行 + 处理续行 + 剥变量
m = re.search(r"^check_PROGRAMS\s*=\s*(.+)$", txt, re.M)
lines = [m.group(1)]
rest = [l for l in txt[m.end():].splitlines() if l.strip()]      # ← 必须滤空行
i = 0
while lines[-1].rstrip().endswith("\\") and i < len(rest):
    lines.append(rest[i]); i += 1
names = [re.sub(r"\$\([A-Za-z_]+\)", "", n).strip() for n in " ".join(l.rstrip().rstrip("\\") for l in lines).split()]

# ② 在构建目录编译，逐个直跑（绕开 check-TESTS 驱动）
subprocess.run(["make", "-j1", "MAKEINFO=true"] + names, cwd=build_folder)

# ③ 运行条件自己补
tenv = dict(os.environ)
tenv["LD_LIBRARY_PATH"] = "<每个依赖的 package_folder>/lib:" + tenv.get("LD_LIBRARY_PATH", "")
tenv["TMPDIR"] = "<构建目录下一个可写目录>"
tenv.update({"srcdir": src, "abs_srcdir": src, "top_srcdir": src, "abs_top_srcdir": src,
             "builddir": build, "abs_builddir": build, "top_builddir": build, "abs_top_builddir": build})
subprocess.run([exe], cwd=src, env=tenv)     # cwd 用源码根：上游用相对路径打开数据文件

# ④ 统计语义
#    rc==0 → 通过；rc==77 → 跳过（SKIP，打印原因）；其它 → 失败

# ⑤ makeinfo：make / make check / make install 三处都传 MAKEINFO=true
```

### 禁止做法
- ❌ 在源码目录跑 `make check`（out-of-source 下必然 "No rule to make target"）
- ❌ 把 `exit 77` 当失败（那是 automake 约定的 SKIP；也不该反过来当通过，要如实记录原因）
- ❌ 只加 `<building>/lib` 到 LD_LIBRARY_PATH 却漏了依赖的 lib 目录（会被环境同名库遮蔽）
- ❌ 为了绕过只读 /tmp 就删掉用例（应做可移植性修正：写死的 `/tmp/...` → 相对路径）

## 验证
```bash
grep -n 'check_PROGRAMS' <build>/Makefile | head -3        # 名单形态
<build>/<test-binary> ; echo rc=$?                         # 0=通过 77=跳过 其它=失败
```

## 关联条目
- 相关: E429（同一草稿 id 下的其它适配条目：conan 下 CMake 工程四处目标名/路径不匹配 / meson 在 CI 下
  Unknown linker / musl 与内核 uapi 头冲突 / 脚本式工具入口打包三坑 / 上游无测试时补测并摊开构成 等）
