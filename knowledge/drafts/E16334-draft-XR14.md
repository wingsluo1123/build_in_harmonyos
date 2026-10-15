# E16334 — 消费者成功不能证明 Libtool 产物没有构建私有 RUNPATH

## 错误特征
Libtool 工程通过私有目录修复依赖 `.la` 的旧路径后，编译、安装和消费者都可能成功，安装库却仍保留该私有目录的 RUNPATH。若旧构建根仍在，迁移后的库也可能正常运行，因此还必须检查最终安装 ELF 的动态段。

本次实际反例是 libxrender/0.9.12.1 r005：共享、静态 Conan 构建均 RC 0，每种模式消费者 3/3、鸿蒙迁移测试 1/1，独立回读却发现共享库 RUNPATH 含有两次构建目录 `linker-view`。运行成功与交付元数据失败分别保留，没有改写历史结果。

## 触发条件
- 构建系统：Libtool；上游依赖接口接受普通 `-L/-l` 库。
- 阶段：链接、安装、签名和迁移验证。
- 依赖：已发布共享库的 `.la` 包含 `installed=yes` 与 `libdir`。

## 根因分析
`.la` 中 `installed=yes` 的含义仍然有效。把 `libdir` 改为私有副本目录只能解决旧路径，Libtool 随后仍会把新 `libdir` 加入依赖库的运行路径。上游 `ltmain.sh` 的 `-l` 查找顺序是在每个目录内先找 `.la`，再找实际共享库、静态库；同目录存在 `.la` 时，真实库文件不会阻止这项元数据传播。

## 解决方案

### 推荐方案
确认上游接受普通库链接后，私有搜索目录只放声明依赖的实际 `.so/.a`，保留普通 `-L/-l` 链接参数。检查最终安装 ELF 的动态段，随后对最终字节签名，并核对 SONAME 别名字节一致性。依次检查接口、实际制品、`.la` 元数据传播、安装 ELF、真实消费者和迁移后的 API；最后核验签名和依赖缓存完整性。

上游确实需要公开 `.la` 元数据、平台系统路径或插件语义时，应单独研究接口，不能照搬删除或清空所有 RPATH 的做法。

### 禁止做法
- 不改写共享 Conan 依赖缓存。
- 不把依赖 `.a` 的绝对路径塞入另一个 Libtool 静态归档。
- 不把消费者运行成功直接等同于 ELF 路径可迁移。

## 验证
```bash
llvm-readelf -d <installed-provider.so>
conan create <recipe> -pr:h=<native-host> -pr:b=<native-build> --build=<package>/*
```

修复后的 r006 使用相同官方源包和两份平台识别补丁，共享、静态 `conan create` 均 RC 0，消费者 3/3、鸿蒙测试 1/1，原始 `make check` RC 0。完整发布源只有两个 `Makefile.am`，均无注册测试，原始用例数为 0。新的鸿蒙测试和独立动态段回读均确认安装库无 RPATH/RUNPATH。原事务 15 份回执、30 条 WAL、唯一启动 1 次，释放后自有进程为零。

证据位于任务唯一根 `F:/HarmonyPC/wxwidgets-gui-delivery-20261014`：

- r005 `formal-artifact-readback.json`：共享库 SHA-256 `c654813295e59b2f8e08875a648e560db4155d66763ebdb72e9228100ac95821`，保留 producer RUNPATH。
- r006 `formal-artifact-readback.json`：共享库 SHA-256 `2d717c92545332b1db3bdf97c06d5b306225cb2872470fcf5a6cd46fbd9d1946`，无 RPATH/RUNPATH；RREV `003ed7e89c19ace5ad423a7ca154dd81`，PID `e647863c487673f3505fad09e4305079038bb22d`，PREV `0aca8285407905fccc4f3b3d9e09326d`。
- r006 `observed.json` 与 `snapshot-008.json`：原始结果、消费者字节哈希、不可变回执链和释放证据。
- r006 Conan 缓存归档 SHA-256 `65df9787983c9a4ca27f973bbca57d4681feef40ffa2253c1cebfd29532ca655`，562033 字节，独立二次回读一致。

## 关联条目与适用边界

这补充了 E236 的静态归档边界、E522 的递归私有 `.la` 方案及 E351/E544 草稿：私有 `.la` 修复后的运行成功仍可能伴随已安装共享库的 producer RUNPATH 泄漏。新增结论不证明 X server 图形操作、GTK/wxWidgets 全量验证或平台 CI 已通过。
