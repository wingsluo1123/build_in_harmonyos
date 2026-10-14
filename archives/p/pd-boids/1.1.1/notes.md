# pd-boids 1.1.1 适配笔记

## 上游构成

`pd-boids_1.1.1.orig.tar.gz` 是 Pure Data 的鸟群/兽群模拟外部对象
**boids**（Eric Singer / A. Sier / Jasch），提供 `boids2d` 与 `boids3d`
两个类。使用上游**老式 Pd library template Makefile**，每个类产出一个
`<class>.pd_linux`。

## 构建

- **Pd API 头**：制品仓 `puredata/0.54.1` 是 *application*，不暴露 `m_pd.h`。
  配方在 `source()` 额外拉取同版本 `pure-data 0.54-1` 源码树，`-I` 指向其 `src`。
- **平台识别**：老式模板用 `uname -s` 判平台；OHOS 报 `HarmonyOS` 不匹配任何分支
  → `make` 命令行强制 `UNAME=Linux`（选中 `pd_linux` 扩展名与 `-shared` 链接旗标）。
- `CFLAGS` 在命令行整体给出：`-I<pd-api>/src -DPD -fPIC -O2 -w`。纯 C，零三方依赖。
- 构建产出 **2** 个 `.pd_linux`（`boids2d`、`boids3d`）。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/boids2d.pd_linux` | 2D 群集模拟 |
| `lib/pd-externals/boids3d.pd_linux` | 3D 群集模拟 |
| `lib/pd-externals/*-help.pd` | 帮助补丁 |
| `lib/pd-externals/boids-meta.pd` | 库元数据 |

## 测试

上游无自动化测试套件（只有帮助补丁）→ 上游 N=0。

消费者测试 `test_package/test_pd_boids.sh`（2 项断言）用**真机 OHOS `pd`** 无头
加载安装后的外部对象，读取两个类**确定性的参数 dump**（默认相邻数
`kNumNeighbors = 2`）：

- `[boids2d 4 0]` + `dump` → `neighbors 2`
- `[boids3d 4 0]` + `dump` → `neighbors 2`

真机 `conan create`：`CREATE_RC=0`，消费者 2/2。

> 备注：初始 boid 位置由随机数生成，故测试不校验位置输出，改用确定性的
> `dump` 参数报告；`pd` 用 `timeout 20` 结束。
