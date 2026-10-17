# 处理策略：以 meson 选项守卫 `subdir('help')`，默认关闭 yelp 帮助页

## 1. 问题本质

GNOME 系 meson 项目用 `gnome.yelp()` 生成帮助页。该函数在构建期对每个语言调用
**itstool** 合并 DocBook/HTML 的翻译片段：

```meson
# help/meson.build（上游原样）
gnome.yelp('parlatype',
  sources: [...],
  media: [...],
)
```

itstool 在本仓 OHOS 构建环境里**装了但不可用**：

| 观察 | 证据 |
|---|---|
| itstool 是 python 脚本，shebang 指向构建机上不存在的解释器 | `head -1 $(command -v itstool)` → `#!/data/service/hnp/bin/python3 -s`；该路径在本机不存在 |
| 即使绕过 shebang，python 侧还缺 libxml2 绑定 | `python3 -c 'import libxml2'` → `ModuleNotFoundError: No module named 'libxml2'` |
| meson 运行它时拿到 126 | ninja 输出 `code=126`（command found but not executable / interpreter missing） |

因此**只要 `subdir('help')` 被执行，构建必然失败**，且失败点在 help 子目录，
与库本身的编译无关。

## 2. 策略：补丁加一个默认关闭的 meson 选项

不改上游源码语义，只把「帮助页」变成可选构建项。

**改动 1 — `meson_options.txt` 增加选项（默认 false）：**

```diff
+option('help',
+  type: 'boolean',
+  value: false,
+  description: 'build the yelp help pages (needs a working itstool)',
+)
```

**改动 2 — `meson.build` 用选项守卫子目录：**

```diff
-subdir('help')
+if get_option('help')
+  subdir('help')
+endif
```

**为什么默认 false 而不是默认 true + 命令行传参：**

- conan 的 `Meson.configure()` **只接受 `reconfigure` 参数，没有 `args`**，无法在
  recipe 里直接追加 `-Dhelp=false`；改工程选项只能落到 native file 的
  `[project options]`（`MesonToolchain.project_options`），而 toybox/HMDFS 环境下
  多一层间接就多一层失败面。
- 默认 false 与上游「帮助页是可选文档」的语义一致；需要帮助页的宿主显式
  `-Dhelp=true` 即可找回（本仓 CI/制品仓场景不需要）。
- 该形态与仓库既有实践同构：`ghex/46.0` 用
  `0001-meson-disable-help-and-icon-cache.patch` 同样在 meson 层禁用 help。

## 3. 补丁模板（可直接复用）

> 下例文件名为**模板示例**；本包实际交付为
> `patches/0001-meson.build.patch` 与 `patches/0002-meson_options.txt.patch`
> （内容与本模板等价，`meson_options.txt` 侧的实际 option 描述见该补丁）。
> 照抄时请把 `patch_file` 改成你自己的实际文件名。

`patches/0001-guard-help-subdir.patch`：

```diff
--- a/meson.build
+++ b/meson.build
@@
-subdir('help')
+if get_option('help')
+  subdir('help')
+endif
```

`patches/0002-add-help-option.patch`：

```diff
--- a/meson_options.txt
+++ b/meson_options.txt
@@
+option('help',
+  type: 'boolean',
+  value: false,
+  description: 'build the yelp help pages (needs a working itstool)',
+)
```

`conandata.yml` 声明（`patch_type: portability`，说明 itstool 在本环境不可用）：

```yaml
patches:
  "4.3":
    - patch_file: "patches/0001-guard-help-subdir.patch"
      patch_description: "guard the yelp help pages behind the help option: itstool is packaged for the host as a python script whose interpreter and libxml2 binding are not available there"
      patch_type: "portability"
    - patch_file: "patches/0002-add-help-option.patch"
      patch_description: "add the help build option used to disable the yelp help pages"
      patch_type: "portability"
```

## 4. 备选方案与取舍

| 方案 | 结论 |
|---|---|
| **本方案**：meson 选项守卫（默认关） | ✅ 采用。不动源码语义、可在任意宿主重开、与 ghex 实践同构 |
| 不引入 itstool（去掉 `tool_requires`） | ❌ 更早失败：meson 在 `gnome.yelp()` 处直接报 `Program 'itstool' not found`，仍是硬失败 |
| 直接删掉 `help/` 目录或删除 `subdir('help')` | ⚠️ 可行但改动面大、patch 会随上游文件变动失效；选项守卫的 patch 上下文更稳定 |
| 用 `PATH` 屏蔽 itstool / 伪造 itstool 桩 | ❌ 不可靠：meson 在 configure 期做 `find_program` 且 yelp 目标要真产物；桩函数产出空文件仍可能在后续 install 阶段暴露 |
| 打 `__OHOS__` 平台宏守卫 | ❌ 违反 R8：patches/ 默认禁止平台宏；且该问题与平台宏无关，是「工具链缺失」，用构建选项表达才正确 |

## 5. 适用范围与判断口径

**适用**：所有用 `gnome.yelp()` 的 meson 项目（GNOME/GTK 栈：应用、面板、设置等）。
识别脚本 `detect-gnome-yelp-itstool.sh` 覆盖源码特征（`gnome.yelp(` / `subdir('help')`）
+ 环境特征（itstool 缺失或不可用）+ 日志特征（`code=126` 等）。

**不适用**：非 meson 构建（autotools 的 `--disable-help` 自有开关）、itstool 可用的宿主。

**是否属于 R40「深度适配不完整」**：不属于。帮助页是**最终用户文档**，LC_MESSAGES
翻译（msgfmt 路径）仍然照常构建并随包发布（本包 `share/locale/*/LC_MESSAGES/*.mo`
实测存在），库与应用功能不受影响——禁用的是 yelp 帮助页文档目标。

## 6. 与相邻知识的关系

| 已有条目/草稿 | 与本策略的区别 |
|---|---|
| `knowledge/drafts/DRAFT-appstream-1.2.0-ohos-meson-itstool-join-optional.kv` | 那条讲的是 **meson i18n 模块 `i18n.itstool_join()`**（metainfo XML 翻译合并）在 itstool 缺失时报错，处方是 `find_program(required: false)` 降级；本策略面对的是 **`gnome.yelp()` 帮助页**目标，且 itstool「存在但不可执行（126）」，无法靠 `required:false` 降级——只能把整个 help 子目录变成可选 |
| `E471` / `E527`（无显示器测试分类） | 讲的是 `meson test` 用例在无 X11/Wayland 时的跳过与归类，与构建期的 itstool 无关 |
| `E444`（GTK4/meson 适配） | GTK4 依赖链与 pkgconfig 归一化，不含 yelp/itstool 分支 |
