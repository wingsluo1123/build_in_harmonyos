# chayang

逐渐降低屏幕亮度（grace period），可用于在锁屏前留出缓冲时间（`chayang && swaylock`）。
单文件 C11 的 wlroots / `zwlr-layer-shell` Wayland 客户端。

- 主页: https://git.sr.ht/~emersion/chayang
- 许可证: MIT
- 构建系统: meson (C11)

## 版本

| 版本 | 状态 | 构建日期 |
|------|------|----------|
| 0.1.0 | built | 2026-10-16 |

## 依赖

wayland/1.24.0 · wayland-protocols/1.36 · libffi/3.4.4（构建工具 meson/1.11.0）

## 适配要点

- **ELF 必须签名（E077）**：鸿蒙只执行带有效 `.codesign` 的 ELF；meson 安装期会就地改写 ELF（把 RUNPATH 的构建机绝对路径替换为占位符），
  使该段失效，导致安装后的 `bin/chayang` 执行被拒
  （`Operation not permitted`）。配方在 `package()` 末尾用
  `binary-sign-tool sign -selfSign 1` 重新签名。
- **wayland-scanner 必须静态重建**：`wayland` 包自带的 scanner 有两个独立缺陷——`.codesign`
  被 meson 安装期的 ELF 改写作废，且 DT_NEEDED 内嵌构建机 Conan 缓存绝对路径
  （libexpat.so，本机不存在）并缺 `libxml2.so.16`。配方从 wayland 1.24.0 源码编译一个
  只依赖 libc 的静态 scanner 供 `dependency('wayland-scanner', native: true)` 使用。
- pkg-config 修补：制品仓 `wayland-client.pc`（prefix `/`）与 `wayland-protocols.pc`
  （prefix 为构建机缓存路径）需复制改写 prefix 后置顶 PKG_CONFIG_PATH。
- `Requires.private: libffi` 会被 `pkg-config --cflags` 解析，故把 libffi 提升为直接 requires。
- 上游无测试套件（`meson test` → `No tests defined.`）；消费者测试 9 条断言
  （产物 6 + 真实运行 3）全部通过。

## 构建 / 验证

```bash
conan create archives/c/chayang/0.1.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

## 使用

```bash
chayang -h          # usage: chayang [-d seconds]
chayang && swaylock # 3 秒渐暗后锁屏（-d 可调整秒数）
```

详细配方见 `0.1.0/`。
