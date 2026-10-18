# swift-toolchain-ohos — 软件级目录（★ 预备件，未落 archives/）

本目录对应 **`archives/s/swift-toolchain-ohos/`**（软件级）。

```text
archives/s/swift-toolchain-ohos/
├── commands.json     ← R38 / CI L0k：type="tool"、name 一致、versions["6.0.3"].ref、binary:false
├── manifest.yaml     ← 软件级 manifest（ARCHIVE-SPEC v2.0）；CI L0e / PF3 要求它存在且非空
├── README.md         ← 本档
└── 6.0.3/            ← 版本级：conanfile.py / conandata.yml / notes.md / patches/ / test_package/
```

## 软件简介

OHOS 自建 **Swift 6.0.3 工具链**最小集，作为 `tool_requires` 供 Foundation / swiftPM
等下游配方在竞赛 CI（无系统 Swift）中构建使用。
**路径 B（贡献创新）：平台基础设施包**，同族先例 `archives/r/rust-toolchain/1.97.1`。

## 为什么需要验收方裁定（PENDING-P2）

rust 有官方 dist tarball 可下载；**OHOS 的 Swift 工具链是我们自建的，上游没有对应发行物**。
载荷（189,124,959 B / `922277ac…`）既不能进仓（PF2 / JC2 / JC3），
又没有官方 URL 可指（PF7 / R39）⇒ 托管位置需裁定。

详见 `6.0.3/notes.md` 的 PENDING-P2 清单。

> ★ 本目录是 **`$Q101/prep/crate/` 下的预备件**：本轮不写目标仓库，
> 落地动作等 P2 答复（常设项 **0-129**：预备件与落地件物理分离）。
