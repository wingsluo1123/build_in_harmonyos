# abiword-plugin-openwriter 3.0.8 适配笔记（OHOS PC）

## 上游情况

- **仓库**:`https://gitlab.gnome.org/World/AbiWord` (mirror: github.com/AbiWord/abiword)
- **版本**:3.0.8 (2026-02-18 release)
- **插件位置**:`plugins/openwriter/`(主源码的子目录,**不是独立仓库**)
- **上游协议**:GPL-2.0-or-later

### 为什么单独归档

abiword-plugin-openwriter 在 Alpine Linux、NetBSD pkgsrc 等发行版中是独立打包的
（虽然源码来自 AbiWord 主包）。我们的项目采用"一个第三方库一个归档目录"的约定，
所以把它从 AbiWord 主源码里"虚拟"拆出来。

## 待办

- [ ] 获取 AbiWord 3.0.8 release tarball，验证 sha256
- [ ] 解压后提取 `plugins/openwriter/` 子目录作为单独归档输入
- [ ] 调研 openwriter 的运行时依赖（abiword/glib/libxml2/pango/fribidi/libgsf/...）
- [ ] 写 conanfile.py（autotools 配方）
- [ ] 写 test_package（CMake 消费者测试，验证 openwriter 关键 API）
- [ ] OHOS HNP worker 交叉编译验证
- [ ] qemu-aarch64-static 烟雾测试
- [ ] 真机回归测试（需要远程协作 — 见团队方案）
- [ ] 提 PR

## 参考

- 上游 release notes: <https://gitlab.gnome.org/World/AbiWord/-/tags/release-3.0.8>
- Alpine 打包:<https://pkgs.alpinelinux.org/package/v3.24/community/x86_64/abiword-plugin-openwriter>
- PIDGIN 适配参考:<archives/p/pidgin/2.14.14/>

## 远程真机协作

真机调试需要通过 **hdc over TCP + Tailscale + DevEco Studio 远程 endpoint** 方案（团队统一）。
