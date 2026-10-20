# E2925 — meson monorepo 单组件适配（数据资源组件零编译复刻安装语义）

## 错误特征

在 meson monorepo 里适配单个子目录时，分两种失败面：

1. **兄弟组件依赖被拉入**（直接构建整仓）：
   ```
   meson.build:12:0: ERROR: Dependency "glib-2.0" not found, tried pkgconfig
   Program 'sassc' not found or not executable
   Run-time dependency gtk-update-icon-cache found: NO
   ```
2. **CI 环境无 meson**（配方里照搬 `meson setup`/`ninja install`）：
   ```
   /bin/sh: meson: command not found
   ERROR: conanfile.py: Error in build() method
   ```

## 触发条件

- 构建系统：meson，且仓库是 **monorepo**（顶层 `meson.build` 用多个 `option()` +
  `if get_option(...)` / `endif` + `subdir()` 组织多个组件）
- 阶段：configuration（`meson setup` 阶段解析依赖时）
- 目标组件是**纯数据/资源型**（声音主题、图标主题、字体包）：组件内没有
  `.c/.cpp/.rs` 等编译单元，meson 只做 `configure_file()` + `install_subdir()`
- 环境：CI worker 只有 conan + Python，没有 meson/ninja，也没有 sassc/glib 这些
  兄弟组件专用工具

## 根因分析

monorepo 的组件是**同层兄弟块**，顶层 `meson.build` 形如：

```meson
option('gnome-shell', type: 'boolean', value: true)
option('gtk',         type: 'boolean', value: true)
option('sounds',      type: 'boolean', value: true)

if get_option('gnome-shell')
  subdir('gnome-shell')
endif
if get_option('gtk')
  subdir('gtk')
endif
if get_option('sounds')
  subdir('sounds')
endif
```

`subdir()` 之间**没有隐式依赖传递**，但默认 `value: true` 意味着「不显式关闭就全建」。
因此适配 `sounds/` 时若直接 `meson setup <src>`，会先进入 `gtk/`、`gnome-shell/`，
这两块依赖 `sassc`、`glib-2.0`、`gtk-update-icon-cache`，在 CI 上必然 configuration 失败。

第二层根因：目标组件本身零编译。以 `sounds/meson.build` 为例，全文只有：

```meson
theme_dir = join_paths(get_option('prefix'), 'share', 'sounds', meson.project_name())
conf_data = configuration_data()
conf_data.set('ThemeName', meson.project_name())
configure_file(input : 'src/index.theme.in', output : 'index.theme',
               configuration : conf_data, install_dir: theme_dir)
install_subdir('src/stereo', install_dir: theme_dir)
```

即「模板变量替换 + 目录拷贝」。把它当成需要 meson 的构建，是把工具链依赖引进了
一个本该零依赖的交付物。

## 解决方案

### 推荐方案

**(1) 构建/验证期：只构建目标子目录**

```bash
meson setup build <src> --prefix=$PWD/stage \
      -Dgtk=false -Dgnome-shell=false -Dsounds=true
ninja -C build install
# → 实测 staging: share/sounds/Pop/{index.theme, stereo/**}，26 个文件、0 个符号链接
```

**(2) 交付期：不依赖 meson，用 Python 复刻安装语义**

- `configure_file()` → 读 `src/index.theme.in`，把 `@ThemeName@` 替换为项目名（`Pop`）
- `install_subdir('src/stereo', install_dir: theme_dir)` → 按目录树复制
- **follow_symlinks 语义**：上游 `install_subdir` 默认 `follow_symlinks=True`，
  4 个 `.oga` 别名链接在安装结果里是**实体文件**；配方复制后必须同样实体化，
  否则交付形态与上游不一致（在大小写不敏感或不支持链接的文件系统上更易出问题）

**(3) 等价性背书**：用 meson 实跑 staging 与 `${package_folder}` 做 `diff -r`，
无输出即逐字节一致；数据组件再叠加本体自检（条目数、`OggS` 魔数、无编译残留）。

### 禁止做法

- ❌ 配方 `build()` 里直接调 `meson setup` / `ninja install`：CI 无 meson，必红
- ❌ 直接 `cp -r src/stereo`：`index.theme` 的 `@ThemeName@` 不会被替换，别名也不会实体化
- ❌ 为了「能构建」而把 `-Dgtk=false` 改成给 CI 装 sassc/glib：把无关依赖引进交付链

## 验证

```bash
# 1) 上游实跑 staging（只开目标组件）
meson setup build <src> --prefix=$PWD/stage -Dgtk=false -Dgnome-shell=false -Dsounds=true
ninja -C build install

# 2) 配方产物 vs 上游 staging 逐字节对比（应无输出）
diff -r $PWD/stage/share/sounds/Pop <package_folder>/share/sounds/Pop ; echo EXIT=$?

# 3) 数据本体自检：条目数 + 容器魔数 + 无 ELF / 无源稿泄漏
```

实测（pop-sound 5.5.1.r7.g25ea85d）：`diff -r` EXIT=0，两侧 26 个文件聚合
`sha256=530161644a06d240ba3be9663fc3eb427f242b911ec130270b213a49400993ad`，
配方产物 26 文件 / 0 符号链接，与上游 meson 安装结果一致。

## 关联条目

- 相似：E1050（按实际交付布局断言，install_dir vs packaged path）
- 相似：E255（纯资源包配方形态：无编译、无 commands.json、符号链接处理）
- 原则：P013（平台限制必须降级而非绕过）——此处「降级」指用 Python 复刻安装语义而非硬塞工具链
