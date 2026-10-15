# DRAFT-2670 — glib 跨代际依赖图冲突：override 统一到低版 glib/2.84.0.1.1（按制品仓已发二进制世代选向）

> 状态：草稿（来自 gnome-recipes 2.0.4 适配，task_id=2670）

## 问题

配方依赖图解析时报 glib 版本冲突：

```
Version conflict: gtk/3.24.43 -> glib/2.84.0.1.1,
while libgoa/3.58.1 -> glib/2.88.3
```

（json-glib、gnome-autoar 同样钉 glib/2.88.3，图上两条 glib 钉法
只差小版本代际，默认二段解析不收敛。）

## 根因

OHOS 制品仓里 GNOME 各库按自身上游节奏建立配方，对 glib 的
`requires` 钉在不同 GLib 2.x 小版本（2.84.x / 2.88.x 并存）。
Conan 默认不做跨 requires 的一致性升级——每个包声明自己的
钉法，冲突就显式报出来。

## 方向判定：不看 ABI 论证，看制品仓二进制的世代分布

GLib 2.x 系列 ABI 向后兼容，单看这条，「向上统一到 2.88.3」
似乎总是安全解。但平台制品仓的现实是**二进制按世代发布**：

- gtk3 全栈（gtk/3.24.43、atk、gdk-pixbuf、pango、gspell、
  libsoup、harfbuzz、libpng、libtiff…）的已发二进制全部构建于
  glib/2.84.x + zlib/1.3.1.1 世代；
- glib/2.88.3 + zlib/1.3.2 世代目前只有 libgoa/json-glib/
  gnome-autoar 等少量二进制，gtk3 栈一个都没有。

向上统一会把图上 13 个已发二进制全部作废（package_id 随依赖
代际变化），触发整栈源码构建；实测（gnome-recipes 2.0.4 首轮）
该路径在 libpng 处就死于老配方直接 exec 脚本（OHOS Error 126）。
向下统一则保留全部已发二进制，代价 = 把 libgoa/json-glib/
gnome-autoar 钉回 glib 2.84 世代，其中 libgoa 需单节点源码重编。

**决策规则 = 先查 ohpcd 上各候选世代二进制的存在性，再定
override 方向；ABI 兼容性只在同世代内做验证。**

## 方案

Conan 2 允许根 override 覆盖依赖声明的硬 pin（实测 Overrides
表：`"glib/2.88.3": ["glib/2.84.0.1.1#5a9bdf1a…"]`，无冲突无告警）：

```python
self.requires("glib/2.84.0.1.1", override=True,
              options={"shared": True},
              transitive_headers=True, transitive_libs=True)
...
self.requires("zlib/1.3.1.1", override=True,
              transitive_headers=True, transitive_libs=True)
```

配合同世代三件套版本：json-glib/1.10.6.1、gnome-autoar/0.4.5
（gnome-autoar-0.pc 名称不变）；glib 2.84 公开 pkg-config 闭包
显式列入：pcre2/10.45、libffi/3.4.4、graphite2/1.3.14、
xz/5.6.2（对齐 activity-log 0.9.7 先例）。libgoa/3.58.1 保留
上游版本，源码重编（meson 接受 glib 2.84，实测 95 目标构建 +
打包全绿）。

**组件命名代沟**：两代 glib 配方连 cpp_info 组件命名都不同——2.84
世代带后缀（glib-2.0/gio-2.0/gobject-2.0…），2.88 世代改裸名
（glib/gio/gobject…）。按 2.88 写的消费者（libgoa 的
`cpp_info.requires = ["glib::glib", "glib::gio"]`）向下统一后会让
PkgConfigDeps 中止（"Component 'glib::gio' not found in 'glib'
package requirement"）。修法=generate() 在 PkgConfigDeps 前对依赖
cpp_info.requires 做双向 -2.0 运行期归一（依赖对象在 generate()
中是活引用，改写对生成器可见；最小探针实测 libgoa 的 goa-1.0.pc
随即生成 `Requires: glib-2.0 gio-2.0`）。

配套 generate() 内 glib pkg-config 修补（别名、Requires 变量、
python 工具变量）见主配方。

## 验证

- gnome-recipes 2.0.4（task 2670，2026-10-14）：
  - 图解析：24 Cache + 13 Download + 仅 libgoa Missing，无告警；
  - libgoa/3.58.1 真机源码构建通过（依赖 glib/2.84.0.1.1）；
  - 真机 conan-verify 八门禁结果见主配方 notes.md。

## 适用边界

- 依赖链同时出现「已发二进制钉低版 glib」与「新库钉高版 glib」
  的应用；
- 判定前提是已实测 ohpcd 两个世代的二进制存在性；
- 若两个世代都有完整二进制，优先选择与业务主链（如 gtk3）
  一致的世代；
- 不适用于 major 代际跳跃（GLib 2→3 无 ABI 保证）。

## 查重差异

- 与「有 commands.json 工具包须同步 versions 登记」（R38）、
  「版本递增铁律」（R37）不重叠：那两条是版本发布面规则，
  本条是依赖图收敛面；
- 与单纯「依赖缺件」类草稿互补：缺件的修法是补包/移植，
  本条是包都在、但钉法冲突时的收敛策略。

## 关联交付

- 本草稿与 `archives/g/gnome-recipes/2.0.4/**` 同属一次交付
  （conanfile.py requirements 段 + generate() pkg-config 修补链）。
- 正式 E 编号由知识库主编审核后分配。
