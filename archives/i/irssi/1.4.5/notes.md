# irssi 1.4.5 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-10
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 1. 安装依赖（cmd-pkgs预编译包）
curl -fsSL .../install.sh | sh -s -- glib 2.88.0
curl -fsSL .../install.sh | sh -s -- openssl 3.5.6
curl -fsSL .../install.sh | sh -s -- ncurses 6.4
curl -fsSL .../install.sh | sh -s -- pcre2 10.40

# 2. Meson 配置
meson setup builddir --prefix=$DEFAULT_PREFIX \
  -Dwith-perl=no \
  -Denable-true-color=yes \
  -Dstatic-dependency=yes

# 3. 编译
ninja -C builddir -j2

# 4. 安装
DESTDIR=$TEST_PREFIX ninja -C builddir install

# 5. 测试
ninja -C builddir test
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess不识别HarmonyOS (autotools) | E007 | 改用meson构建系统，无需patch config.guess/config.sub |
| 2 | autotools config.status创建临时文件失败 | HMDFS限制，config.status在当前目录创建临时子目录时Permission denied | 改用meson构建系统 |
| 3 | Perl模块编译失败 | HarmonyOS Perl不完整 | 使用 `-Dwith-perl=no` 禁用 |
| 4 | glib需要pcre2 | glib依赖pcre2 | 安装pcre2 10.40 cmd-pkgs预编译包 |
| 5 | test-796失败 | getpwuid_r()不支持非系统UID (E051) | 平台限制，非irssi bug |

## 源码修改

无源码修改。meson构建系统无需平台补丁。

## 依赖版本

- glib 2.88.0 (cmd-pkgs预编译)
- openssl 3.5.6 (cmd-pkgs预编译)
- ncurses 6.4 (cmd-pkgs预编译)
- pcre2 10.40 (cmd-pkgs预编译)

## 验证结果

```bash
$ irssi --version
irssi 1.4.5 (20231003 1405)
```

测试结果：4/5 通过（test-796因平台限制失败）

## 注意事项

- 使用meson而非autotools，因为autotools的config.status在HMDFS上无法创建临时文件
- ncurses cmd-pkgs预编译包缺少头文件，但meson通过cc.find_library可直接检测到libncursesw.a
- irssi源码自带terminfo-core.c，当HAVE_TERM_H未定义时会自行声明setupterm/tputs等函数

---

**编译结束**: 2026-08-10 03:11
**最终状态**: built
