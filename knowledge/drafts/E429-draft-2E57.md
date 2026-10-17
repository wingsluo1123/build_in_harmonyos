# E429 — 判"有依赖"先扣掉仓库已有依赖；autotools 依赖的 include/库必须显式注入

## 错误特征
1. 用"零依赖"筛库 → 大量**本可直接适配**的候选被误杀（本轮实测：840 个 Debian 候选里，
   扣掉仓库已有依赖后仍有 41 个依赖全满足、其中 17 个是 C/C++ 构建；"零依赖"口径下只剩 2 个）。
2. autotools 工程编译时找不到依赖头，链接期又抓不到符号：
   ```
   src/argparse.c:186:10: fatal error: 'argp.h' file not found
   #include <argp.h>
   ```
   （链接期若把 `-largp` 放错位置，则是 `undefined reference to `argp_parse'` 或静默漏符号）
3. OHOS 上 configure 直接失败：
   ```
   configure: error: cannot guess build type; you must specify one
   ./config.status[760]: can't create ./confGbabpa/subs1.awk: Permission denied
   configure: error: could not setup config files machinery
   ```
4. 可选组件被静默跳过（本例 austinp）：
   ```
   checking for libunwind-ptrace.h... no
   not building austinp: missing libunwind
   ```
   —— 这是**上游既定行为**，不是适配缺陷；但要在清单里如实写清，不能当成"全部功能可用"。

## 触发条件
- 构建系统: autotools（本例；cmake/meson 的依赖注入机制不同）
- 阶段: configuration（判依赖、定范围）与 build（include/链接/三元组/umask）

## 根因分析
1. **"有依赖"只有相对仓库才有意义**：仓库已归档（或制品仓已发布）的依赖，适配时只需 `requires`
   引用，不构成阻塞。判依赖时必须先取全量已归档包名做差集。
2. **autotools 的依赖信息不会自动进编译行**：`AutotoolsToolchain` 生成 ≠ 依赖的 `cpp_info`
   自动进 `CFLAGS/CPPFLAGS`（实测 austin 编译行里只有 `-I. -I<src>`）。
3. **静态库在链接行有位置要求**：`LDFLAGS` 出现在目标文件之前 → `-largp` 放那里会漏符号；
   必须走 autoconf 的 `LIBS=`（落在链接行末尾）。
4. **config.guess 认不出 OHOS**：须显式给三元组。
5. **HMDFS 目录权限**：configure 的 `umask 077` 建临时目录会 `Permission denied`；而
   `autoreconf` 会**重新生成** `configure`，所以对 configure 的修补必须放在 autoreconf **之后**。

## 解决方案
1. **先扣仓库已有再做依赖判定**：
   ```bash
   git ls-tree -r --name-only main -- archives | grep manifest.yaml \
     | sed -E 's|^archives/[a-z0-9]/([^/]+)/.*|\1|' | sort -u > archived_names.txt
   ```
   依赖命中该名单（含 `lib*-dev` 归一化）即视为满足。
2. **显式注入依赖的 include/lib**：
   ```python
   for ref in ("argp-standalone", "libunwind"):
       dep = self.dependencies[ref]
       tc.extra_cflags.append("-I" + os.path.join(dep.package_folder, "include"))
       tc.extra_ldflags.append("-L" + os.path.join(dep.package_folder, "lib"))
   ```
3. **静态库用 `LIBS=`**：`tc.configure_args.append("LIBS=-largp")`（落在链接行末尾）。
4. **显式三元组**：`--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl`。
5. **改 configure 的 umask，且必须在 autoreconf 之后**：`umask 077` → `umask 022`
   （仓库 `archives/a/argp-standalone` 同款处理）。

### 禁止做法
- ❌ 把"有依赖"直接当淘汰理由（不核仓库已有）
- ❌ 只生成工具链就假定依赖 include/lib 已进编译行
- ❌ 把静态库放进 `LDFLAGS`
- ❌ 在 `autoreconf` **之前**改 `configure`（会被重新生成覆盖，等于白改）

## 验证
```bash
# 1) 依赖是否都在仓库
git ls-tree -r --name-only main -- archives | grep manifest.yaml | sed -E 's|^archives/[a-z0-9]/([^/]+)/.*|\1|' | sort -u | grep -E 'argp|libunwind'
# 2) 编译行里有没有依赖的 include（本库实测第一轮没有 → 必须显式注入）
grep -n 'argp.h\|-I.*argp' <构建日志>
# 3) 三元组与 umask
grep -n 'cannot guess build type' <配置日志> ; grep -n 'umask 077' configure
# 4) 可选组件如实记录
grep -n 'not building austinp' <配置日志>
```

## 关联条目
- 相关: E429（同一草稿 id 下的其它适配条目：平台清单版本 vs 真实上游版本 / 上游无测试时补测并摊开构成 /
  sdist 缺测试数据与依赖实证判定 / Conan 依赖遮蔽 / test_requires 的 test 上下文 / sdist 时间戳归一化 /
  console_scripts 入口落地）
