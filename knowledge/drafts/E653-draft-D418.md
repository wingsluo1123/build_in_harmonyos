# E653（草稿）— 上游 Makefile 的 `all` 目标用 nroff 预排版手册页，OHOS CI 工具链没有 nroff

> 草稿（DRAFT）— 来自 cascade 1.4 HarmonyOS PC (aarch64) 适配的真实实践，与 `.kv` 配对。

## 错误特征

无 nroff 的环境上的典型输出（示意；本机有 nroff，未在本机复现）：

```
nroff -man cascade.1 > cascade.0
/bin/sh: nroff: command not found
make: *** [Makefile:NN: cascade.0] Error 127
```

本机 x86 runner 装有 nroff，该报错在本地构建中**不会出现**；它只在没有 nroff 的 CI/设备工具链上出现，
所以是“本地 conan create 绿、CI 红”的典型来源。依据：仓内 `wiggle/1.3` 配方记录
“default `all` target also renders `wiggle.man` via `nroff`, which is not part of the toolchain”，
`trurl/0.16.1` 同样跳过依赖 cd2nroff 的手册页。

## 触发条件

- 构建系统：autotools（autoconf 2.13 的老 configure）/ 手写 Makefile
- 阶段：`make`（默认 `all`）与 `make install`（`install.man` 依赖 `cascade.0`）
- 项目类型：sh/perl/awk 脚本类、BSD 风格老项目，手册页源（`.1`）随包分发并在构建时预排版成 cat1 页

## 根因分析

cascade 1.4 的 `Makefile.in`：

```make
all:: cascade
all:: cascade.0
cascade.0: cascade.1
	rm -f cascade.0
	nroff -man cascade.1 > cascade.0
install.man:: cascade.0
	$(INSTALL_DATA) $(srcdir)/cascade.0 $(mandir)/cat1/cascade.1
	$(INSTALL_DATA) $(srcdir)/cascade.1 $(mandir)/man1/cascade.1
```

默认 `make`、`make install` 都传递依赖 nroff。手册页是纯文档，与脚本功能无关，却能让整个构建失败。

## 解决方案

### 推荐方案

build() 只构建产物目标；package() 用细分安装目标，等价于 `make install` 去掉 `install.man`，
roff 源页用 `copy()` 补装：

```python
def build(self):
    self.run(f'AWK=awk ./configure --prefix="{self.package_folder}" '
             f'--mandir="{self.package_folder}/share/man"', cwd=self.source_folder)
    self.run("make cascade", cwd=self.source_folder)          # 不跑 all，不触发 nroff

def package(self):
    self.run("make installdirs install.bin install.examples install.docs install.lisp",
             cwd=self.source_folder)
    copy(self, "cascade.1", src=self.source_folder,
         dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
    os.rmdir(os.path.join(self.package_folder, "share", "man", "cat1"))  # installdirs 建的空目录
```

### 回退方案

没有细分目标可用时，用 conandata 补丁把规则改成 `cp cascade.1 cascade.0`（补丁中不得出现 `__OHOS__`）。

### 禁止做法

- ❌ 为手册页给配方加 `tool_requires("groff/…")`、`heirloom-doctools` 或在构建机 `apt/brew install groff`：
  依赖面扩大、依赖未必已发布，PF4 依赖闸会拦。
- ❌ `touch cascade.0` 之类用空文件冒充预排版结果：安装出空 cat1 页，掩盖问题。

## 验证

```bash
grep -nE 'nroff|groff|mandoc' Makefile.in Makefile.am Makefile 2>/dev/null   # 找规则
conan create archives/c/cascade/1.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# build 日志只有 `make cascade`；包内 share/man/man1/cascade.1 存在、无 cat1；test_package 24/24 通过
```

## 与已有条目的关系

- `E038`（groff 1.23 的 nroff 配置宏不兼容）：那条是 **man-db 已有 nroff 但配置宏不兼容**；本条是 **构建机根本没有 nroff**，
  处置是不让构建依赖它。
- `E289`（`install-man` 找不到 `.1` 源文件）：缺的是手册页**源文件**；本条缺的是**排版工具**。
- `E402`（toybox gzip 不认识选项导致 man 页压缩失败）：同属“手册页步骤拖死构建”的一族，工具与报错不同。

## 关联条目

- 相关：E038、E289、E402；仓内先例 `archives/w/wiggle/1.3`、`archives/t/trurl/0.16.1`
