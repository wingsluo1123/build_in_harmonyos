# E432 — OHOS CI worker 进程争用：测试阶段 `fork(2)` EAGAIN（瞬时）

## 错误特征

```
…/run_upstream_tests.sh: fork: retry: Resource temporarily unavailable
```

- 子进程（node/mocha 等）**没有产出任何日志**（因为根本没 fork 成功）。
- 紧随其后的同类命令常常成功（如默认电池 fork 失败、`leaks.js` 立刻成功）。

> 与 E165/E430 区分：那些是 **exec/shebang** 失败（子进程能启动但脚本/解释器不可执行）；
> 本条连 fork 都没成功。

## 触发条件

- 阶段: testing（或 build 的密集子进程阶段）
- 环境: OHOS CI worker（进程/资源瞬时紧张）

## 根因分析

`bash` 启动子进程时 `fork(2)` 返回 `EAGAIN`（RLIMIT_NPROC / 瞬时资源紧张），
bash 打印 `fork: retry: Resource temporarily unavailable`。属**瞬时**资源争用，
本地开发机一般无此限制，故本地 W3 / 离线 `conan create` 不复现。

## 解决方案

### 推荐方案

对有子进程的测试/构建调用做**有界重试**，且仅针对瞬时特征：

```sh
for attempt in 1 2 3; do
    "$NODE" "$MOCHA" … >"$log" 2>&1 && return 0
    rc=$?
    if [ ! -s "$log" ] || grep -qE "Resource temporarily unavailable|cannot fork|Cannot allocate memory" "$log"; then
        sleep $((attempt * 10)); continue
    fi
    return "$rc"          # 真实失败：不重试
done
```

并降低进程 churn（如 `npm install --ignore-scripts`）。

### 禁止做法

- ❌ 对所有非零退出都重试（会掩盖真实测试失败）。
- ❌ 把该失败归因为「源码编译错误」去改源码。

## 验证

```bash
# 观察子进程日志是否为空 + bash 是否报 fork: retry；重试后成功即为瞬时
```

## 关联条目

- 相关: E430（make 直接 exec shebang 脚本失败 → 显式 bash）
- 相关: E431（hnp node.org `bin/npm` 残缺 stub）
