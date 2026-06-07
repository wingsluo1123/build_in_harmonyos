# E098 — ninja 链接静态库时 toybox sh 的 rm 命令不可用

## 错误特征
编译 meson 项目时，ninja 在链接静态库阶段失败：

```
FAILED: [code=127] src/util/libvirt_util.a
rm -f src/util/libvirt_util.a && /path/to/llvm-ar csrDT src/util/libvirt_util.a ...
/bin/sh: rm: inaccessible or not found
```

## 触发条件
- 构建系统: meson/ninja
- 阶段: compilation（静态库链接）
- 平台: OpenHarmony（使用 toybox sh）

## 根因分析
ninja 在链接静态库时生成的命令行包含 `rm -f xxx.a && llvm-ar csrDT xxx.a ...`，
使用 `/bin/sh` 执行。在 OpenHarmony 的 HMDFS 环境下，toybox sh 的 rm 命令
可能因权限或路径问题而无法执行（permission denied/inaccessible），导致
静态库创建失败。

## 解决方案

### 推荐方案（手动 workaround）
1. 手动创建静态库文件：
   ```bash
   cd builddir
   /data/service/hnp/bin/ar csrDT src/util/libvirt_util.a src/util/libvirt_util.a.p/*.o
   ```
2. 继续编译：
   ```bash
   ninja -j1
   ```

### 回退方案（修改构建系统）
创建 meson native file，指定静态库链接器配置：
```ini
[binaries]
ar = '/data/service/hnp/bin/ar'  # 使用 GNU ar，避免 llvm-ar 的 rm 问题
```

### 禁止做法
- ❌ 创建 rm 软链接（`ln -s /usr/bin/rm toybox-rm`）
- ❌ 设置 rm alias（`alias rm='/usr/bin/rm'`）
- ❌ 修改 `/bin/sh` 的 PATH 环境变量

**原因**: 这些做法会污染构建环境，可能导致其他软件的构建命令混乱。

## 验证
```bash
# 检查是否是 HMDFS/toybox 限制
ls -la /bin/sh /usr/bin/rm

# 手动验证 ar 命令是否可用
cd builddir
/data/service/hnp/bin/ar csrDT test.a src/util/libvirt_util.a.p/*.o
ls -la test.a
```

## 关联条目
- 相似: E002（/tmp 只读），E046（chmod 不生效）
- 平台限制: HMDFS 软链接限制
