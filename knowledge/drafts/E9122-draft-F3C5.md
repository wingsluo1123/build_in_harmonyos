# E9122 — 上游 configure 用 command -v ed 决定安装名：产物名随构建机环境漂移

## 错误特征

同一份源码在不同构建机上装出的可执行文件名不同（`ed` 或 `oed`）；消费者按 `ed` 调用失败，
或打包清单/文档记录的名字与实际产物不一致。构建日志本身不报错，属静默漂移。

## 触发条件

- 构建系统: 手写 POSIX sh `configure`（非 autoconf、非 cmake）
- 阶段: configure（产物名决策）、install（落盘）

## 根因分析

`configure:146-150`：

```sh
if [ ! -x "$(command -v ed)" ] ; then
	prog="ed"
else
	prog="oed"
fi
```

产物名取决于构建机 PATH 中是否已存在 `ed`。因此产物名不可复现：CI 容器与开发机上
可能得到不同名字，消费者按名字调用会失败，制品校验也会不一致。

## 解决方案

### 推荐方案

配置阶段显式指定产物名（上游已支持该开关）：

```sh
./configure --program-name=ed
```

使安装名与构建机 PATH 解耦。

### 禁止做法

- ❌ 在 CI 中往 PATH 里增删一个 `ed` 来"碰"出期望的名字 —— 依赖环境、脆弱且不可复现；
- ❌ 安装后 `mv` 改名 —— 安装脚本与 man 页仍指向旧名，且绕过上游 install 逻辑。

## 验证

```bash
./configure --program-name=ed && grep -E '^prog' Makefile   # 期望: prog= ed
```

## 关联条目

- 相关: E9121
