# E999 — OHOS loader 校验 .codesign 摘要：meson install 改写 .dynstr(RUNPATH) 使 lld 摘要失配 → dlopen Permission denied

## 错误特征

test_package 运行期 dlopen 失败：

```
libfprint/1.94.10 (test package): RUN: "./test_libfprint"
Error loading shared library libfprint-2.so.2
Error relocating ./test_libfprint: fp_context_new: symbol not found
```

或手动复现：

```
$ dlopen("libfprint-2.so.2")  # 已安装副本
dlopen: Permission denied
```

根因：OHOS loader 在 dlopen 时用 `.codesign` 段摘要（lld `-Wl,--code-sign` 链接时生成）校验当前文件内容。
OHOS 适配版 `meson install` 会把已安装副本 `.dynstr` 里的绝对构建路径（RUNPATH 形如
`/storage/.../.conan2/.../p/lib`）改写成 `'X'`，字节变了 → 摘要失配 → loader 拒绝加载。
`binary-sign-tool -selfSign` 重签同理会替换 lld 摘要。

## 触发条件

- 构建系统: meson（Conan MesonToolchain + Meson install 流程）
- 阶段: installation → runtime（test_package 执行 dlopen）

## 推荐方案

`package()` 中 `Meson(self).install()` 之后，从 meson build 树找回同名原始 `.so`
（walk `self.build_folder` 匹配 basename），`shutil.copy2` 覆盖包内被改写/重签的副本，
恢复 lld 生成的 `.codesign` 摘要（参考 `archives/l/libfprint/1.94.10/conanfile.py`
的 `_restore_pristine_shared_libraries`）：

```python
def package(self):
    Meson(self).install()
    self._restore_pristine_shared_libraries()  # 覆盖回 pristine .so
```

禁止用 `binary-sign-tool -selfSign` 重签：CI 在 release 阶段通过
`ci/artifacts/sign.sh` 统一签名，配方内重签只会破坏摘要。

## 验证

```bash
# 对比 build 树原始 .so 与包内 .so 字节（应仅在 .dynstr/RUNPATH 有差异 → 已恢复则无差异）
cmp build/.../libfprint-2.so.2 pkg/lib/libfprint-2.so.2
# conan create 后 test_package 运行不再报 dlopen Permission denied / symbol not found
```

## 关联条目

- 相关: 与「contents API 推送截断→空包」（DRAFT-libfprint-1.94.10-contents-api-truncated-conanfile-empty-package）为不同故障，勿混淆
