# DRAFT: Conan MesonToolchain 的 libexecdir=bin 归并（retro-gtk 1.0.2 实测）

## 现象

上游 `retro-runner/meson.build` 用 `install_dir: libexecdir` 安装内部 helper，
`meson install` 却把它装到了 `<pkg>/bin/retro-runner`；同时
`RETRO_RUNNER_PATH` 常量（上游为 `libexecdir / 'retro-runner'`）跟着变成
`/bin/retro-runner`。

## 根因

`conan create` 生成的 machine file 里：

```ini
[project options]
bindir = 'bin'
sbindir = 'bin'
libexecdir = 'bin'      # ← Conan MesonToolchain 的默认归并
```

Conan 2 的 `MesonToolchain` 默认把 `bindir/sbindir/libexecdir` 全部归并为 `bin`，
以便包内布局简单。对"库 + 内部 helper"这类上游布局，会带来三个连带影响：
helper 落 bin/、编译期路径常量与实际安装位置不一致、以及"库包内含 bin/ 可执行"
让 CLI/tool 门禁（commands.json 要求）语义不清。

## 修复

```python
tc.project_options["libexecdir"] = "libexec"   # 还原上游安装语义
```

并把 helper 的定位方式写进 notes/README（本包：`libexec/retro-runner`，运行期可用
`RETRO_RUNNER_PATH` 覆盖）；`package_type = "shared-library"`、`cpp_info.bindirs = []`，
明确不把它当 PATH 工具声明。

## 验证

- 默认配置：`find <pkg> -name retro-runner` → `bin/retro-runner`（错误位置）
- 显式 `-Dlibexecdir=libexec`：→ `libexec/retro-runner`，包内 `.codesign` 重签后
  可被 `RetroCore` 拉起（test_package 的消费者测试在设备上实测通过）。
