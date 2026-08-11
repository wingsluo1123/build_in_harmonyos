# acf-lib-lua5.3 0.11.1 适配笔记

## 编译环境
- 构建系统: custom (纯 Lua 文件复制安装)
- 编译日期: 2026-08-11
- 状态: built

## 软件说明
acf-lib-lua5.3 是 Alpine Configuration Framework 的 Lua 5.3 标准模块库，纯 Lua 实现（无 C 扩展），包含 8 个模块：apk.lua / date.lua / db.lua / format.lua / fs.lua / html.lua / processinfo.lua / validator.lua。安装到 `share/lua/5.3/acf/` 并在 `share/lua/5.3/` 根复制兼容性副本。

## 构建步骤
1. 下载上游源码 acf-lib-v0.11.1.tar.gz（GitLab archive API，SHA256: 95e3658eab121358c800d1ca02764a3b55bf52a813694c27e74fe73533014a8e）
2. 应用补丁 0001-lua53-compat-legacy-apis.patch 修复 format.lua 中 Lua 5.1 时代 API（getfenv/string.gfind，Lua 5.2+ 已移除）
3. conan create 构建 acf-lib-lua5.3/0.11.1@ohpcd/stable，纯 Lua 模块复制安装

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lua/5.3.0 依赖不可达 | 制品仓 ohpcd remote 无 lua 5.3.x 系列，ConanCenter 在项目 CI 中被禁用；归档中 lua 5.3.x 仅有 5.3.6（源码构建方式，无 Conan 配方） | 子任务为 lua/5.3.6 补写 Conan 配方并 conan create 发布到本地 cache；acf-lib-lua5.3 改用 lua/5.3.6 作依赖 |
| 2 | lua/5.3.6 recipe 在 cache 缺裸版本 ref | 子任务用 `--user=ohpcd --channel=stable` 导出，只缓存带 user/channel 的 ref；acf-lib-lua5.3 的 `self.requires("lua/5.3.6")` 需裸版本 ref | 用不带 user/channel 的 `conan create` 重新导出 lua/5.3.6，产生裸版本 ref |
| 3 | format.lua 含 Lua 5.1 时代 API | format.lua:216 `getfenv(3)`（Lua 5.2 移除）、format.lua:217 `string.gfind`（Lua 5.1 移除，5.0 已废弃别名） | 补丁 0001-lua53-compat-legacy-apis.patch：用 `debug.getinfo(3,"f").func` + `_ENV`/`_G` 替换 `getfenv(3)`，用 `string.gmatch` 替换 `string.gfind` |
| 4 | 补丁解析失败 "patch stream is incomplete" | 初版补丁末尾缺少换行符 | 用 git diff 重新生成补丁，确保末尾换行 |
| 5 | 补丁路径 "work/format.lua" 不匹配 | git diff 带了 work/ 前缀（临时仓库目录名） | 修正补丁路径为 `a/format.lua` / `b/format.lua`（Conan strip_root 后源码在根目录） |

## 源码修改
- `format.lua`：`expand_bash_syntax_vars` 函数中 `getfenv(3)` → `debug.getinfo(3,"f").func` + `_ENV`/`_G`，`string.gfind` → `string.gmatch`（补丁：0001-lua53-compat-legacy-apis.patch）

## 依赖版本
- lua/5.3.6（制品仓本地 cache，源码构建方式，Conan 配方由子任务补写）

## 验证结果
```bash
conan create archives/a/acf-lib-lua5.3/0.11.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# 结果: test package PASS
#   PASS: packaged Lua modules invoked
#   PASS: invalid IPv4 and port rejected
```

## 上游测试说明
acf-lib 0.11.1 上游无独立测试套件（Alpine aports 声明 `options="!check"`，注释 "no test suite"）。源码无 test 目录、test 脚本、test/check make 目标。test_package 用 C 嵌入 Lua 5.3 解释器加载 4 个真实打包模块（format/html/validator + 兼容性 format），调用 10 个断言验证核心 API（format.dostounix / parse_lines、html.html_escape / url_encode、validator.is_ipv4 / is_port、兼容性 require('format')）。
---

**编译结束**: 2026-08-11 19:15
**最终状态**: built
