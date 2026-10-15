# DRAFT-libfprint-1.94.10-json-glib-dep-codesign-symbol-not-found

> Contributor: gcw_eQ4VpLdf | Status: Draft | Updated: 2026-10-12
> Source: libfprint 1.94.10 HarmonyOS PC 适配（PR #14631, CI #85262 test_package 运行期）
> 领域：conan / runtime / codesign / ohos-platform / dependency

## 背景

libfprint 1.94.10 在 CI #85262（CI-011）上编译 113/113 目标全部成功，但 test_package
运行期失败：

```text
Error loading shared library libjson-glib-1.0.so.0: (needed by .../gusbaf0db42b6c067/p/lib/libgusb.so.2)
Error relocating .../libgusb.so.2: json_object_has_member: symbol not found
```

libfprint 通过 gusb 依赖 json-glib。本地 conan create 全绿（test_package 输出
"OHOS: FpContext OK"），但 CI 同配方失败——**本地绿 ≠ CI 绿**。

## 错误签名

```text
Error loading shared library libjson-glib-1.0.so.0: (needed by .../libgusb.so.2)
Error relocating .../libgusb.so.2: json_object_has_member: symbol not found
```

## 根因

E999 同根因作用于**已发布依赖包**：

1. OHOS loader 在 dlopen 时校验 `.codesign` 摘要（lld `-Wl,--code-sign`）与当前文件内容一致；
2. json-glib/1.10.6 发布时其 `libjson-glib-1.0.so.0` 被 OHOS 适配的 `meson install` 改写
   （.dynstr 中 RUNPATH 绝对路径被替换为 'X'），摘要失配；
3. 消费者（libfprint → gusb → json-glib）运行期加载 libgusb.so.2 时需 libjson-glib-1.0.so.0，
   loader 拒绝加载 → 报 "Error loading shared library" 并级联 "symbol not found"。

**为什么本地绿 CI 红**：本地曾手工修复 json-glib 缓存包（用构建树原始 .so 替换
`p/json-*/p/lib` 及 `d/conan_package.tgz` 内的损坏副本，见 E999-draft-856F）；CI 每次从
ohpcd 下载远端包。决定性验证：远端下载 .so 的 sha256 为 `b6fcccb9…`，本地修复版为
`facbae90…`，**不一致**——远端包仍是损坏版。

## 修复方案（推荐：重新上传修复版依赖包）

对 json-glib 配方应用 E999 的恢复方案，重新上传：

```python
# json-glib 配方 package()：meson install 后从构建树恢复 pristine .so
# （walk self.build_folder 找同 basename，shutil.copy2 覆盖 p/lib 及 d/conan_package.tgz）
conan upload json-glib/1.10.6 -r=ohpcd
```

libfprint 侧无需改——依赖链自动取到新包。若已有修复版（json-glib/1.10.6.1 已 built），
可 override：

```python
self.requires("json-glib/1.10.6.1", override=True)   # 或 CI --build=json-glib/*
```

## 禁止做法

- ❌ 仅本地修缓存/改本地 .so 而不重新上传远端包，就声称修复——CI 依旧下载损坏包，属伪造通过
- ❌ 删除/绕过 test_package 的 json-glib 加载路径以掩盖 symbol not found——掩盖真实依赖损坏

## 验证

```bash
# 判远端包损坏：
conan download json-glib/1.10.6:<package_id> -r=ohpcd   # 用全新 CONAN_HOME
sha256sum .../libjson-glib-1.0.so.0                      # ≠ 本地修复版 facbae90… 即损坏
# 判修复：重新上传后，CI test_package 运行期不再报 symbol not found
```

## 关联条目

- 根因: E999（meson install 改写 .dynstr → codesign 摘要失配 → loader 拒绝）
- 相关: E999-draft-856F（同根因；libfprint 自身 .so 的恢复方案）
- 相关: DRAFT-libfprint-1.94.10-meson-eagain-unknown-compiler-worker（同 PR 的另一失败层：
  CI worker 瞬时 EAGAIN）
