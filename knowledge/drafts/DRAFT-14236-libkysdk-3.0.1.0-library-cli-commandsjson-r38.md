# DRAFT-14236-libkysdk-3.0.1.0-library-cli-commandsjson-r38

**library 包（`package_type="library"`）附带 CLI 工具（`cpp_info.bindirs=["bin"]`）同样触发 L0k/R38 —— E424 的 application 案例之外的库包变体**

- **实例**: libkysdk/3.0.1.0（PR #14236，构建 #84447 / #84726）
- **状态**: draft（草稿，待合入评估）

## 错误签名

```
[step] L0k: Checking commands.json for CLI tools (R38)...
[fail] L0k: CLI tool detected but commands.json missing (R38)
[fail] libkysdk/3.0.1.0 — L0 quality gate failed: commands_json_r38
```

## 根因

L0k/R38 的 CLI 判定**不依赖 `package_type`**：`ci/conan/detect_bindirs.py` 解析到非空 `cpp_info.bindirs`（或 conanfile 存在 `RUNTIME DESTINATION bin` / `package_type="application"`）即判定为 CLI 工具包，随后要求软件级 `archives/<字母>/<包名>/commands.json` 存在，且校验：

1. JSON 合法；
2. `type == "tool"`；
3. `name` 包含包名；
4. `versions` 包含当前版本号。

libkysdk 是 library 包（`package_type = "library"`），但交付 4 个 CLI（`kconf2` / `conf2-compile` / `conf2-sync-system` / `conf2-sync-session`），`package_info()` 中声明 `self.cpp_info.bindirs = ["bin"]` → 触发 R38。

**关键陷阱**：本地工作区曾创建合规的 `archives/l/libkysdk/commands.json`，但未 `git add` 提交推送 → 本地 CI 全绿（`[ok] commands.json valid (type=tool)`）、PR CI 在 L0 gate 报 `commands_json_r38`。**"本地过、PR 挂"的根因是文件未入库**，不是本地/远端环境差异。

## 推荐方案（与 E424 同法）

在**软件级目录**（版本目录的上一级）创建 `archives/l/libkysdk/commands.json`：

```json
{
  "name": "libkysdk",
  "description": "Kylin SDK 基础库：日志/配置/定时器/工具集/跳表容器/GSettings 封装/埋点诊断 + conf2 配置同步 CLI",
  "homepage": "https://gitee.com/openkylin/libkysdk-base",
  "type": "tool",
  "versions": {
    "3.0.1.0": {
      "ref": "libkysdk/3.0.1.0",
      "binary": false
    }
  }
}
```

要点：

- `type` 必须为 `tool`；
- `name` 必须包含包名 `libkysdk`；
- `versions` 必须包含 `3.0.1.0`；
- **创建后必须提交并推送回 PR 分支**，否则本尰绿、PR 挂。

## 验证命令

```sh
CI_PACKAGES="archives/l/libkysdk/3.0.1.0" CI_BRANCH="feat/libkysdk-3.0.1.0" zsh ci/conan/build_and_test.sh
```

## 禁止策略

1. 把 `commands.json` 放到版本目录 `archives/l/libkysdk/3.0.1.0/commands.json` —— R38 检查的是软件级目录；
2. 创建后不提交推送 —— PR CI 依旧失败；
3. 为绕 R38 删除 `bindirs` 声明 —— 丢失 CLI 交付，且 test_package/交付物受影响。

## 关联

- `similar_to`: E424（pico-sdk，`package_type="application"` 案例）、E255（资源型数据包）
- `principles`: P016
