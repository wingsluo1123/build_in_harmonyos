# ocp — Open Cubic Player

Open Cubic Player（OCP）是一款历史悠久的模块音乐 / Tracker 播放器，支持 MOD/S3M/XM/IT、
Adlib/SB、SID、MIDI 等多种音源与格式，提供 curses 全屏界面与键盘快捷操作。

- 上游仓库：<https://github.com/mywave82/opencubicplayer>
- 本项目适配版本：**3.3.1**（HarmonyOS PC / aarch64-linux-ohos）
- 配方：`conanfile.py`（Autotools，`package_type = application`，产物 `bin/ocp`）

## 适配要点

1. **Autotools 三元组**：教 `build-aux/config.guess`、`build-aux/config.sub` 识别
   `aarch64-unknown-linux-ohos`（补丁 `0001`），不使用 `--build/--host` 绕过（E007）。
2. **configure 临时目录**：`configure` 的 `mktemp -d` 分支在 HMDFS 上产生的目录
   （`drwx--S---`）构建器不可写，回落 `mkdir` 路径（补丁 `0002`）。
3. **测试 scratch 目录**：上游测试硬编码 `/tmp`，而 HarmonyOS 的 `/tmp` 为只读挂载
   （知识条目 E002），改为构建树内可写目录（补丁 `0003`）。
4. **源码必须取 release 资产**：只有 GitHub release 资产内含 vendored 解码器子模块
   （`playtimidity`、`playqoa`、`playsid` 等），codeload 的 git tag 归档会缺目录导致
   `configure` 直接失败。

## 依赖

ncurses、zlib、bzip2、mad、libogg、libvorbis、flac、libpng、libjpeg-turbo、
game-music-emu、alsa-lib、libdiscid、cjson、ancient；构建期 `tool_requires xa/2.4.1`。

## 验证

- `conan create`（`ocp/3.3.1@ohpcd/stable`）：包创建成功，消费者测试 1/1 通过。
- W3 本地 CI 模拟：`setup.sh` + `build_and_test.sh` 全部通过（`.ci-result.json` exit_code=0）。
- 上游测试：可运行用例 9/9 通过；`mdb-test` 残留（上游 Makefile 链接缺陷，见
  `3.3.1/notes.md` 与 `3.3.1/reports/test-report.md`）。
