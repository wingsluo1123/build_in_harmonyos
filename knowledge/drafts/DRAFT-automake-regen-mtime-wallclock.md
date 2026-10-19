# DRAFT-automake-regen-mtime-wallclock：autotools maintainer-mode 重生成的 mtime 归一化基准与覆盖不变量

- 条目主题：配方式"全树 mtime 归一化"防 automake 重生成的完整不变量——**覆盖全树（含 dist 期重打戳的任意树文件）+ 墙钟基准 + 依赖序重触生成物**；固定 epoch 对该不变量没有结构性防护。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：gdl 3.40.0（案例）；规则泛化到一切在无 automake 设备上由配方做 mtime 归一化的 autotools dist 包。
- similar_to：**E248**（同 error_signature 异触发器）；邻族 E069/E041/E071（不同机理）。

## 错误特征（与 E248 同签名）

```
missing: line 81: automake-1.16: command not found
WARNING: 'automake-1.16' is missing on your system.
make[3]: *** [Makefile:506: <src>/docs/reference/Makefile.in] Error 127
```

## 根因（修正后机理，勿写成无条件律）

1. **maintainer-mode 重生成规则的前置可含任意树文件**。案例 gdl-3.40.0 全树唯一此类规则：
   `docs/reference/Makefile:505`
   `$(srcdir)/Makefile.in: $(srcdir)/Makefile.am $(top_srcdir)/gtk-doc.make $(am__configure_deps)`
   规则体的 `for dep in $?; do case '$(am__configure_deps)' in *$$dep*) am--refresh…esac; done`
   对不在 am__configure_deps 内的新前置一律落空，直接落到 `$(AUTOMAKE)` fallback（configure
   类前置才会走 am--refresh/config.status 路径）——这是 gtk-doc.make 类文件特殊性的机制根源。
2. **失败 = 覆盖不全 + 基准偏低 二者叠加**：配方归一化漏掉 gtk-doc.make（dist 期重打戳的
   非生成树文件），且归一化基准早于其上游 mtime → Makefile.in 被归一化得比该前置还旧 →
   regen 被触发 → 设备无 automake → 127。**不要写成"固定 epoch 必败"的无条件律**：探针
   证明"全树覆盖 + 依赖序"的固定 epoch 同样不触发；固定 epoch 的真实缺陷是既不预知
   tarball mtime 上限、也不强制覆盖，两条失守其一即触发（墙钟天然满足"基准 ≥ 全树最大 mtime"）。
3. **pristine tarball 本身有序**（gdl 实测：Makefile.in 1630012431 > gtk-doc.make
   1630012421 > Makefile.am 1540236964；configure 1630012430 > aclocal.m4 1630012429）：
   裸解包不触发 regen，倒挂是配方自己的归一化造出来的——与 enchant 2.8.2 的"解包倒挂"
   不同源，勿混写。
4. **与 E248 的关系**：error_signature 同族，但触发器不同——E248 是 apply_conandata_patches
   的 hunk 顺序致 `.am` 新于 `.in`（补丁触及 Makefile 文件）；本条的补丁只动 `configure`，
   触发器是配方归一化的覆盖/基准问题。**E248 的单文件对齐法（把 .in 对齐到 .am）对本触发器
   无效甚至有害（对齐后离 gtk-doc.make 更远）**。

## 实败证据（案例）

- gdl 3.40.0 create round-2：`local-create-r2.log:1462-1473`（`missing automake-1.16` →
  `command not found` → `WARNING …` → `docs/reference/Makefile.in Error 127` → 连锁 Error 2）。
  失败轮配方已有归一化（同轮日志有 `[ok] autotools mtimes normalized`）——即"覆盖不全 +
  基准偏低"形态；失败仅出现在 docs/reference（全树唯一 gtk-doc.make 前置规则所在）。
- round-1 是配方 `name` 错误轮（`conanfile didn't specify name`），从未构建，与本条无关。
- 墙钟+依赖序修复后 r3/r4/CI run2/run3 全绿；run3 缓存树实测 mtime 序
  gtk-doc.make < Makefile.in < build Makefile 全部正确。

## 修复（rec）

```python
# build() 内顺序：apply_conandata_patches → umask 修改 → _fix_autotools_mtimes()
now = time.time()
for root, dirs, files in os.walk(src):        # 1) 全树 touch 到 T（覆盖含 gtk-doc.make）
    for name in files + dirs:
        os.utime(os.path.join(root, name), (now, now))
# 2) 依赖序重触生成物
aclocal.m4        -> now+2
configure         -> now+3
config.h.in       -> now+4
**/Makefile.in    -> now+5
aux 脚本           -> now+6
```

## verification_cmd（自包含合成探针，全新 shell 可复现）

```sh
D=$(mktemp -d) && cd "$D" || exit 1
printf '#!/bin/sh\necho "automake-1.16: command not found" >&2\nexit 127\n' > missing
chmod +x missing
: > Makefile.am && : > gtk-doc.make
cat > Makefile.in <<'MK'
all: all-am
all-am: ;
Makefile.in: Makefile.am gtk-doc.make
	@./missing automake-1.16 --gnu docs/Makefile
MK
touch -d @1000000200 Makefile.am gtk-doc.make   # dist 期重打戳的前置
touch -d @1000000100 Makefile.in                # 归一化把它放得更早（覆盖漏了 gtk-doc.make）
make -f Makefile.in Makefile.in >/dev/null 2>&1; RC1=$?   # 期望 2：$(AUTOMAKE) fallback → 127
touch -d @2000000000 Makefile.am gtk-doc.make
touch -d @2000000005 Makefile.in                # 修复不变量：.in 新于全部前置
make -f Makefile.in Makefile.in >/dev/null 2>&1; RC2=$?   # 期望 0
[ "$RC1" -eq 2 ] && [ "$RC2" -eq 0 ] && echo PROBE_PASS || echo PROBE_FAIL
```

注意：不要拿 pristine 解包树做第一步验证（tarball 有序，会得出相反结论）；也不要在已配置
构建树上朴素 `touch gtk-doc.make && make`（build-dir Makefile 新鲜时再生链不问津，
config.status 陈旧时会走全局 recheck 掩盖）——自包含合成探针是唯一稳定复现路径。

## 拒稿预演（同签名重复申报？）

E248 已收录同 error_signature 条目，但 trigger/rec 均不同（patch 序 vs 归一化覆盖/基准；
单文件对齐 vs 墙钟+依赖序全树规则），且 E248 rec 对本触发器无效（见上）。复发面由 GNOME
gtk-doc 时代 dist 形态 + 平台无 automake 恒定保证，非单库个例。

## 关联

E248（同签名：patch 序倒挂/单文件对齐法）、E069（编译 automake 循环依赖）、E041/E071
（automake 版本不匹配/bypass-autotools-env）——均为邻族异机理。principles：P010、P014。
