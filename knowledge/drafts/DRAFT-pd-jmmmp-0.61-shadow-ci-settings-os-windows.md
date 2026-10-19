# 精简 settings.yml 缺少 Windows 时，Conan 2 会让 `if self.settings.os == "Windows"` 抛 "Invalid setting 'Windows'"

- **草稿 ID**: DRAFT-pd-jmmmp-0.61-shadow-ci-settings-os-windows
- **来源**: pd-jmmmp 0.61 真机 shadow CI（第一次运行失败于 `automake/1.18` 的 `config_options`，补全 os 列表后通过）
- **分类**: conan / ci-harness / settings / ohos
- **状态**: 本地草稿（随 PR #16741 提交，未写正式索引）

## 问题 / 错误签名

影子 CI 第一次跑 `archives/p/pd-jmmmp/0.61` 时，包本身已经成功产出（141 个 `.pd` + 13 个 `.txt` + 38 张图），
失败发生在 `test_package` 的依赖图展开阶段：

```
puredata/0.56.5: Downloaded recipe revision 3bbec58bcd0dc08568ba4a7048fb6d9c
automake/1.18: Not found in local cache, looking in remotes...
automake/1.18: Downloaded recipe revision 65a7ba60030d238eb8bb32266391cfc5
ERROR: automake/1.18: Error in config_options() method, line 21
        if self.settings.os == "Windows":
        ConanException: Invalid setting 'Windows' is not a valid 'settings.os' value.
        Possible values are ['OHOS', 'Linux']
```

`CI` 的 `L1_RESULT` 因此记为 `fail: conan create failed`，并被提示误导为「依赖包未构建，请先提交依赖包的 PR」。

## 根因

1. **Conan 2 会校验 settings 比较的右值**。`self.settings.os == "Windows"` 不是纯字符串比较：
   Conan 要求当前 `settings.yml` 里定义了 `Windows` 这个取值，否则直接抛
   `Invalid setting`。所以即使 profile 是 `os=OHOS`，比较里的 `"Windows"` 也必须存在。
2. **影子 CI 手写了一份极简 settings.yml**，`os` 只声明 `OHOS` 与 `Linux`（目的是限制可选平台）。
   官方 CI 用的是完整 settings.yml，因此同一配方在官方 CI 正常、在本地影子 CI 必然失败。
3. **触发链与被适配库无关**：`pd-jmmmp` 的 `test_package` 依赖 `puredata/0.56.5`，后者的
   `build_requirements()` 引入 `automake/1.18`；`automake` 是 ConanCenter 式公开配方，带
   `os == "Windows"` 判断。任何 test_package 依赖 autotools 工具链的包都会踩到。

## 最小修复方案

隔离 `settings.yml` 保留官方完整 `os` 列表，只用 profile 约束目标平台：

```yaml
os:
    OHOS:
        version: ["6.0"]
    Linux:
    Windows:
        subsystem: [null, wsl]
    Macos:
    FreeBSD:
    Android:
    iOS:
    watchOS:
    tvOS:
    Emscripten:
    baremetal:
    SunOS:
    AIX:
    Arduino:
    VxWorks:
    QNX:
    Neutron:
    LynxOS:
```

实测：补全后同一包同一条命令得到
`Build Summary: Total: 1 / Success: 1 / Failed: 0`，
`L0/L1/L4/L5 pass`、`L2 skip`（无 bin/）。

## 排查路径（避免误判）

| 现象 | 易误判为 | 实际 |
|---|---|---|
| `automake/1.18 Error in config_options()` | 依赖包没发布 / 需要先提依赖 PR | harness 的 settings.yml 缺 `Windows` 取值 |
| `Invalid setting 'Windows'` 但 profile 显示 `os=OHOS` | profile 写错 | 比较右值校验，与 profile 无关 |
| 提示「请先提交依赖包的 PR」 | 依赖链阻塞 | `puredata/0.56.5` 早已发布（包 revision `a97a8157...` 正常下载） |

## 反例（不要做）

- **不要**为了通过而删掉 `test_package` 里的 `puredata` 依赖：那会把运行时验证（abstraction 能否在
  真机 Pd 里加载）整层删掉，只剩数据层，属于降低质量证据。
- **不要**去改 `automake` / `puredata` 的公共配方来规避这个比较：影响面远大于修 harness，
  而且官方 CI 并不需要这个修改。

## 附带前置（同次运行遇到的另一件事）

影子 CI 的 runner 用 heredoc 生成 clang wrapper，而 HarmonyOS 的 `/tmp` 是只读的：

```
run-ohos-shadow-ci-local.sh[39]: can't create temporary file /tmp/shXXXX.tmp: Read-only file system
```

在启动 runner **之前**把 `TMPDIR` / `TMP` / `TEMP` / `TMPPREFIX` 指向可写目录即可
（与《适配共性问题与首次真机启动避坑指南》第 13 条同源）。
