# DRAFT: --disable-nls 不消除守卫外的 i18n 调用——g_libintl_* UNDEF 使消费者链接失败，应守卫调用点而非注入 libintl DSO

## 现象

libxfce4util 4.20.0：`--disable-nls` 下 `conan create` 编出 `libxfce4util.so.7` 毫无告警，
失败出现在消费者（test_package）链接阶段（CI run3 日志 704-713 行）：

```
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: g_libintl_bindtextdomain
>>> referenced by .../p/lib/libxfce4util.so
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: g_libintl_textdomain
>>> referenced by .../p/lib/libxfce4util.so
clang-15: error: linker command failed with exit code 1
```

第一轮误修（把 glib 包内 libintl DSO 绝对路径塞进 LDFLAGS）把失败点前移到 configure
（CI run4 日志 210-218 行）：

```
checking whether we are cross compiling... configure: error: cannot run C compiled programs.
ConanException: Error 77 while executing
```

## 根因

三因叠加的因果链：

1. **上游语义**：`AM_GNU_GETTEXT([external])` 的 `--disable-nls` 只是令 `ENABLE_NLS` 不
   定义、不链 libintl——**不移除源码里的 i18n 调用**。本库 `xfce-i18n.c:168-181` 与
   `libxfce4util-private.c:56-63` 把 `bindtextdomain / bind_textdomain_codeset / textdomain`
   调用写在 `#ifdef ENABLE_NLS` 之外。
2. **头文件重绑**：conan 依赖 glib 时，其 proxy-libintl 的 `libintl.h` 把
   `bindtextdomain/textdomain/dgettext` 宏重定义为 `g_libintl_*`；实现 DSO 在 glib 包
   `lib/` 内，而上游 `LIBADD` 的 `$(INTLLIBS)` 为空——编译后 `.so` 的 UND 符号表里留下
   `g_libintl_*`，库自身 `-shared` 链接允许未定义符号，**缺陷潜伏**。
3. **失败点**：消费者用 lld（默认 `--no-allow-shlib-undefined`）链接时才爆（run3）。

误修为何更糟：绝对路径 `.so` 进入**每一个 configure conftest** 的链接行；conftest 运行时
按 SONAME 找不到 `libintl.so.8` → `cannot run C compiled programs`（error 77）→ configure
误判交叉编译级联出错（run4）——正中 P-AUTOTOOLS-002"conftest 必须能正常执行"。且该路径
只补本库链接行，**消费者链接行依旧定位不到供给 DSO，闭包不完备**。

## 族内三形态 dedup 对照（同族必读）

都是"OHOS 无 libc libintl 平台上 gettext 头/宏的形态差"，但形态互斥，修复方向不同：

| # | 形态 | 触发组合 | UNDEF 符号 | 首报点 | 条目 |
|---|------|----------|-----------|--------|------|
| 1 | **调用点裸露 + proxy 头重绑**（本条） | `--disable-nls` + 调用在 `ENABLE_NLS` 守卫外 + 依赖 glib proxy-libintl 头 | `g_libintl_bindtextdomain / g_libintl_textdomain` | 消费者链接（lld --no-allow-shlib-undefined） | 本条（libxfce4util 4.20.0） |
| 2 | **守卫内回退宏集不全** | NLS 关 + `#else` 分支漏 `bind_textdomain_codeset` 宏 + 调用点也在守卫外 | `bind_textdomain_codeset`（无 g_ 前缀，未重绑） | 消费者链接 | DRAFT-nls-off-incomplete-i18n-stub-undefined-shlib-symbol（libexif-gtk 0.5.0） |
| 3 | **不关 NLS 的头供给缺口** | NLS 开/默认 + sysroot `libintl.h` 空 stub 无 gettext/dgettext 声明 | ——（编译期报声明缺失，非链接期 UNDEF） | 编译期 | DRAFT-appstream-1.2.0-ohos-gettext-proxy-libintl-header（appstream；该条 id 字段为拟编 E5xx，文件名如左） |

图条目近似对照：E015（`libintl_dgettext`/`dgettext` 未链 -lintl）、E027
（`libintl_gettext/libintl_bindtextdomain` 前缀系）、E142（运行期 `g_libintl_dgettext:
symbol not found`，relocate 阶段）。与 E142 同符号族但不同 phase：本条在**消费者链接期**
被 `--no-allow-shlib-undefined` 拦下，E142 在**运行期** relocate 才炸——链接期拦截意味着
失败面=全部消费者，必须在库侧修。

查重检索词与范围：`g_libintl|bindtextdomain|proxy-libintl` 于 `knowledge/graph`（命中
E015/E027/E142，phase/符号形态差异如上）与 `knowledge/drafts`（命中形态 2/3 两条，组合
条件与 UNDEF 符号不同）；`build-chain-pitfalls.md` 链接闭包节提供 lld 三定律框架但无本
形态；经验仓 main `xapp-2.8.9-libintl-lld-search-order` 是同符号族的"经验检索条目"（非
B 申报面），其绝对路径范式被本条 forbid 收敛边界为 meson-only。

## 修复（rec）

以最小源码补丁给守卫外的调用点补 `#ifdef ENABLE_NLS`（本库实例 =
`patches/0004-disable-nls-i18n-guards.patch`，xfce-i18n.c 与 libxfce4util-private.c 两处）：

- 与上游"禁 NLS 即无 i18n"的构建语义一致（等价于上游在启用 NLS 时宏自然展开的行为）；
- `.so` 不再携带 UNDEF `g_libintl_*`，**对全部下游消费者一次完备**（而非逐个消费者补救）；
- 补丁最小、可解释、可重复应用，按 P-PATCH-001 落 `patches/` 目录，不 sed 生成文件。

## 退路（fallback）

仅当确需运行期 gettext（NLS 必须开，或守卫补丁被上游拒绝）：补全 libintl 供给链——启用
NLS 并把 glib 的 libintl DSO 纳入本包 `lib/` 随包分发（安装期重签，满足 P-PACK-001），或
复用已发布的 gettext 运行时包，并重验下游 `--no-allow-shlib-undefined` 闭包。代价（诚实
权衡）：包变重、libintl 供给跨库重复、ELF 变更面扩大（重签/升级/兼容矩阵）——仅作退路。

## 禁止（forbid）

1. **绝对路径注入 libintl DSO**（`LDFLAGS="<glib-pkg>/lib/libintl.so.8 ..."`）。原因与后果
   见根因 (误修反噬)：conftest 全灭（error 77）+ 闭包仍不完备。经验仓 xapp/libido3 的
   绝对路径范式据此修正边界：**meson-only**（meson 无 autotools conftest 语义，不受本
   禁令约束）。
2. **`#ifdef __OHOS__` 包 i18n 调用点**。要消除的是"`--disable-nls` 下调用裸露"这一构建
   语义，不是平台差异；非 OHOS 平台关 NLS 同样炸，且上游无该宏、引入无上游语义分支——
   可移植性假修复 + 上游同步长期冲突。

## 自包含验证探针

conan create 之后，任何新 shell 可跑（`<p>`=package_folder；工具链在 /data/service/hnp/bin）：

```sh
# 1) .so UNDEF 探针：修复前命中 g_libintl_bindtextdomain/g_libintl_textdomain，修复后为空
/data/service/hnp/bin/llvm-nm -D --undefined-only <p>/lib/libxfce4util.so.7 | grep g_libintl

# 2) 最小消费者链接复现（不依赖本 run 任何文件）：
printf 'int main(void){return 0;}\n' > /tmp/t.c
/data/service/hnp/bin/clang /tmp/t.c -L<p>/lib -lxfce4util \
  -lglib-2.0 -lgobject-2.0 -lgio-2.0 -o /tmp/t
# 修复前：ld.lld: error: undefined reference due to --no-allow-shlib-undefined:
#         g_libintl_textdomain >>> referenced by <p>/lib/libxfce4util.so
# 修复后：exit 0
```

本 run 实测：修复前两探针分别命中/复现（run3）；0004 守卫后探针 1 输出为空、探针 2
通过，消费者三用例与 kiosk 冒烟在 CI run8 全绿。

## 证据索引（run 内审计用，探针不依赖）

- run3 失败：`logs/ci-run3.log:704-713`（lld UNDEF 双符号）
- run4 误修反噬：`logs/ci-run4.log:210-218`（cannot run C compiled programs，Error 77）
- 调用点：tarball `libxfce4util/xfce-i18n.c:168-181`、`libxfce4util/libxfce4util-private.c:56-63`
- 修复：`patches/0004-disable-nls-i18n-guards.patch`；决策记录：`notes.md` 问题表 #6/#7
