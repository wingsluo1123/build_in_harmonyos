# 运行期服务缺失时的清理路径空指针崩溃（audio/display/service host）

> 关联：`skills/runtime-service-absent-cleanup-guard` · 样例库：`archives/j/jalv/1.10.0`

## 1. 现象

在**没有运行期服务**的目标机上跑宿主/客户端程序，本应打印
`Failed to connect to audio system` 之类的错误后退出，实际却：

```text
$ LV2_PATH=<mda.lv2 父目录> jalv -i http://drobilla.net/plugins/mda/Delay
Plugin: http://drobilla.net/plugins/mda/Delay
error: Failed to connect to audio system
$ echo $?
139            # SIGSEGV，而不是 1
```

构建期完全无感：`conan create` 成功、上游单元测试 `test/symap` 通过、`jalv -V`
正常；只有「真实插件 + 真实初始化流程 + 缺服务」三条件同时成立才复现。

## 2. 根因

`src/process_setup.c` 的失败清理函数：

```c
for (uint32_t i = 0U; i < proc->num_ports; ++i) {
  lv2_evbuf_free(proc->ports[i].evbuf);
  lilv_instance_connect_port(proc->instance, i, NULL);  /* instance == NULL */
  proc->ports[i].evbuf = NULL;
}
```

而 `jalv_open()` 的顺序是「先建端口（`jalv_create_ports()`，`num_ports > 0`），
后连后端（`jalv_backend_open()`）」：后端连接失败直接 `return -6`，此时
`process.instance` 从未被赋值（一直 NULL），但端口数组已存在 → 清理循环必然
解引用 NULL。

分类：不是平台缺陷，也不是依赖缺陷，而是**上游失败路径缺守卫**，只是恰好只有
在「目标平台没有该服务」时才暴露。

## 3. 排除性实验（判定归属时必做）

| 实验 | 结果 | 说明 |
|------|------|------|
| 仅调用 `jack_client_open()`（连不上）后退出 | rc=0 | 不是 libjack 静态析构 / 依赖问题 |
| 无效插件 URI（`jalv_open` 早退，不进端口循环） | rc=1 优雅 | 崩溃窗口在「端口已建 + 句柄未建」之间 |
| 有效插件 + 无 JACK 服务器 | rc=139 | 复现 |
| 有效插件 + NULL 守卫补丁 | rc=1 + 错误文案 | 修复确认 |

另外本机 `jackd` 因驱动目录被编译死为 `/lib/jack`（不可写、不存在）无法起
dummy server，所以「有音频服务器」这一支无法在 CI 复现 —— 测试因此用
`timeout 20` 兜底，把 `rc=124` 视为「服务存在、运行正常」。

## 4. 处理策略

**首选：清理路径 NULL 守卫补丁**（`templates/0001-guard-lazy-handle-cleanup.patch.tmpl`）

```c
    lv2_evbuf_free(proc->ports[i].evbuf);
    proc->ports[i].evbuf = NULL;
    if (proc->instance) {                      /* 只守卫解引用 */
      lilv_instance_connect_port(proc->instance, i, NULL);
    }
```

三条铁律：守卫只包住解引用、保留上游释放顺序、禁止 `if (!h) return;` 提前返回。

**配套：测试必须区分崩溃与优雅失败**（`templates/test_package-graceful-failure.py.tmpl`）

- `rc == 139` 单独断言失败（这是回归守卫）；
- `rc == 1` 断言 `Failed to connect to ...` 文案；
- `rc == 124`（有服务时跑满超时）视为通过；
- 必须加载**真实第三方消费对象**（本例 mda-lv2 的真实插件 bundle），不许空壳断言。

**兜底：`env_unsupported` 标记** —— 服务在目标平台根本不存在、补丁后程序也没有
任何实用功能时，标记不可用比「能编译但一跑就崩」诚实。

## 5. 检测

```sh
# L1 源码：清理函数里无守卫解引用惰性句柄
python3 skills/runtime-service-absent-cleanup-guard/scripts/detect_absent_service_crash.py \
    scan --src <源码根>

# L2 运行期：服务缺失特征 + 崩溃特征同时出现才归因本类
python3 skills/runtime-service-absent-cleanup-guard/scripts/detect_absent_service_crash.py \
    runtime --run "<bin> <args>" --timeout 20
python3 skills/runtime-service-absent-cleanup-guard/scripts/detect_absent_service_crash.py \
    runtime --log host.txt --rc 139
```

## 6. 适用与不适用

- **适用**：音频宿主（JACK/ALSA/PipeWire）、显示客户端（X11/Wayland）、
  系统服务客户端（DBus），且目标平台确实不提供该服务、程序本应优雅退出。
- **不适用**：崩溃在正常路径（普通内存缺陷）；只是退出码非零而无崩溃
  （`jalv -V/-h` 返回 81 就是上游行为，不需要补丁）；程序在目标环境根本没有
  可用功能（走 `env_unsupported`）。

## 7. 实测证据（jalv 1.10.0）

| 组 | 配置 | 结果 |
|----|------|------|
| A | 无补丁 + test_package | 失败：`crashed instead of failing gracefully when no audio server is available ... rc=139` |
| B | 加 `patches/0001-guard-null-instance-when-backend-open-failed.patch` | 全绿：`Plugin: <uri>` + `Failed to connect to audio system` + rc=1 |
| 干净环境 | `conan remove "jalv/*" -c` 并清 build/source 目录后重跑 | 全绿（补丁应用 1 次，`test/symap` 通过，test_package 通过） |

## 8. 已知边界

- L1 是形态启发式，跨函数句柄、宏包裹循环、`goto` 清理标签会漏，必须靠 L2 兜底与人工确认。
- L2 依赖英文特征串；非英文日志需扩展 `SERVICE_ABSENT_PATTERNS`。
- 本条目只覆盖「失败路径崩溃」，不解决「服务缺失导致功能不可用」的产品级问题。
