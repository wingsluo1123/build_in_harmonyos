# SKILL: 运行期服务缺失导致清理路径崩溃的检测与守卫（runtime-service-absent-cleanup-guard）

> 版本 1.0.0 · 适用 OHOS PC（aarch64）三方应用/宿主适配流程 · Conan 2.x + 上游 C/C++
> 定位：把「程序在目标平台找不到它依赖的运行期服务（音频服务器 / 显示服务 /
> DBus）→ 失败清理路径解引用未初始化句柄 → SIGSEGV」这一类**只在目标环境
> 暴露、构建期完全看不出来**的缺陷，压缩成「一次检测 + 一个守卫补丁 + 一条
> 测试断言」。jalv 1.10.0 实测落地。

## 1. 一句话说明

上游程序把「连接运行期服务」放在初始化中段，把 `instance/client/display`
这类句柄留成惰性初始化；一旦服务缺失，它走保底清理函数，而清理函数常常
**在循环里无条件解引用该句柄** → 本应打印 `Failed to connect to ...` 退出，
实际 SIGSEGV（rc=139）。本 SKILL 做三件事：

1. **识别**：两通道检测——L1 源码通道扫「清理函数里无守卫解引用惰性句柄」，
   L2 运行期通道要求「服务缺失特征 + 崩溃特征同时出现」才归因本类；
2. **给策略**：NULL 守卫补丁模板 + test_package「优雅失败」断言模板，并明确
   什么时候该改用 `env_unsupported` 标记而不是打补丁；
3. **可复现**：`tests/repro_absent_service_crash.sh` A/B 双向验证（无守卫必崩 /
   有守卫必优雅），输出 `ABSENT_SERVICE_CRASH_REPRODUCED=yes` →
   `GUARD_CONFIRMED=yes` → `REPRO_SCRIPT_EFFECTIVE=yes`。

## 2. 问题机理（jalv 1.10.0 实测）

```
jalv_open()
  ├─ jalv_create_ports()        # 端口结构建立 → num_ports > 0
  └─ jalv_backend_open()        # 连 JACK；失败 → return -6，process.instance 仍为 NULL
        ↓ 失败清理
jalv_close() → jalv_process_deactivate()
  └─ for (i < num_ports) lilv_instance_connect_port(proc->instance, i, NULL);
                                       ^^^^^^^^^^^^ NULL → SIGSEGV
```

关键三点：

| 观察 | 含义 |
|------|------|
| 构建期零症状，只在**运行**时暴露 | 交叉编译/单测都发现不了，必须靠消费者测试跑真流程 |
| 崩溃只出现在**失败路径** | 有音频服务器时程序正常；CI 恰恰没有服务器 → 100% 命中 |
| 上游语义本身是合理的 | 缺的是「句柄可能还没建」的守卫，属可小改的上游缺陷，宜补丁而非放弃 |

对照实验（本机实测，用于排除「是依赖的问题」）：

| 实验 | 结果 | 结论 |
|------|------|------|
| 仅 `jack_client_open()` 失败后退出（不涉及 jalv 清理） | rc=0 | 不是 libjack 的静态析构问题 |
| 无效插件 URI（`jalv_open` 早退，不经过端口循环） | rc=1 优雅 | 崩溃属于「端口已建 + 句柄未建」这段窗口 |
| 真实插件 + 无音频服务器 | **rc=139** | 复现本类缺陷 |
| 真实插件 + 守卫补丁后 | **rc=1 + `Failed to connect to audio system`** | 策略有效 |

## 3. 适用范围

### 3.1 适用

| 场景 | 典型包 |
|------|--------|
| 音频宿主/客户端：需要 JACK/ALSA/PipeWire 服务器或声卡 | jalv、zynaddsubfx 类宿主、zita-* 工具 |
| 显示客户端：需要 X11/Wayland 服务 | GUI 前端、`DISPLAY` 依赖型工具 |
| 服务客户端：需要 DBus/systemd 等系统服务 | 会话/权限类工具 |

判据（同时满足）：目标平台**确实没有**该服务；程序在缺少服务时应能打印错误
退出；实际却以 rc=139/134 结束；且 L1 在清理函数里命中无守卫循环。

### 3.2 不适用（改用其它策略）

| 情况 | 正确做法 |
|------|----------|
| 程序**根本无法**在目标环境提供任何功能（纯依赖缺失） | 不下发二进制或标 `env_unsupported`，不要为了「能跑」而打一堆桩 |
| 崩溃发生在正常路径（不是失败清理） | 属普通内存缺陷，按常规补丁修，不要套本 SKILL 的「环境缺失」叙事 |
| 只是退出码非零（如 1/81）但无崩溃 | 不需要补丁；写成测试断言即可（jalv 的 `-V/-h` 就是 81） |
| 有服务时也必须能跑（CI 有服务） | 测试要同时接受 rc=1（无服务）与 timeout（有服务），见模板 |

## 4. 识别：两通道

### L1 源码通道（建配方前 / 打完容器后都可跑）

```sh
python3 skills/runtime-service-absent-cleanup-guard/scripts/detect_absent_service_crash.py \
    scan --src <上游源码根>
# 命中则: ABSENT_SERVICE_CLEANUP_CANDIDATE=yes + HIT=path:line:detail
```

扫描逻辑：只在 `*cleanup|close|deactivate|destroy|free|shutdown|teardown|release*`
命名的函数体内，找 `for/while` 循环里对 `…->instance|client|handle|display|conn…`
的调用，且循环窗口内没有对应 `if (…handle…)` / `assert(…handle…)` 守卫。

### L2 运行期通道

```sh
# 直接跑（输出自动落文件，绝不接管道）
python3 .../detect_absent_service_crash.py runtime --run "<binary> <args>" --timeout 20

# 或解析已有日志
python3 .../detect_absent_service_crash.py runtime --log host.txt --rc 139
```

判定：**服务缺失特征**（`Failed to connect to audio system` / `Cannot connect to
server` / `cannot open display` / `Connection refused` …）与**崩溃特征**
（`Segmentation fault` / `core dumped` / rc=139）同时出现才判 `yes`。只有连接
失败 = 正常优雅失败（不需要补丁）；只有崩溃 = 另一类问题。

## 5. 处理策略

### 5.1 首选：清理路径 NULL 守卫补丁

抄 `templates/0001-guard-lazy-handle-cleanup.patch.tmpl`。要点：

- 守卫只包住「解引用」本身，**保留上游释放顺序**（先释放 evbuf 再断开端口）；
- 不要 `if (!handle) return;` 提前返回 —— 会跳过后续释放，泄漏；
- `@@` 行数计数必须精确，生成后 `git apply --check` 复验（toybox patch 对
  计数错误会静默 no-op）。

### 5.2 配套：消费者测试必须区分「崩溃」与「优雅失败」

抄 `templates/test_package-graceful-failure.py.tmpl`。核心三条：

1. 真的加载一个第三方真实对象（jalv 用 mda-lv2 的真实插件 bundle），不许空壳；
2. `rc == 139` 单独断言为失败，不许用 `rc != 0` 一把抓；
3. 给超时兜底：`rc == 1`（无服务，断言错误文案）/ `rc == 124`（有服务，跑满了
   算通过），其余退出码都算失败。

### 5.3 兜底：`env_unsupported` 标记

服务在目标平台根本不存在、且补丁后程序也无任何实用功能时，不要硬塞补丁：
在归档里标记 `env_unsupported` 并写明触发条件与替代方案，比「能编译但一跑就
崩」诚实。

## 6. 限制与边界

- L1 是**形态启发式**，不是语义分析：跨函数传递的句柄、宏包裹的循环、
  `goto` 清理标签都会漏，需 L2 兜底；命中也可能误报（有守卫但写法在窗口外），
  必须人工确认。
- L2 依赖日志特征串，非英文输出或自定义日志前缀需在脚本里补 `SERVICE_ABSENT_PATTERNS`。
- 本 SKILL 只解决「失败路径崩溃」，不解决「服务缺失导致功能不可用」的产品级问题。
- 与 `meson-cross-pkgconfig` 互补：那个管**构建期**交叉坑，这个管**运行期**
  环境缺失；两者常在同一个包上先后出现（jalv 两个都踩了）。

## 7. 复现与自检

```sh
sh skills/runtime-service-absent-cleanup-guard/tests/repro_absent_service_crash.sh [输出目录]
python3 -m pytest skills/runtime-service-absent-cleanup-guard/tests/test_detect_absent_service_crash.py
```

脚本不依赖任何本地绝对路径（`CC`/`SKILL_DIR`/`SIGN_TOOL` 均可用环境变量覆盖），
被测进程输出一律重定向到文件以规避 SIGPIPE。

## 8. 实测证据

| 轮次 | 命令/场景 | 结果 |
|------|-----------|------|
| A（关策略） | `conan create archives/j/jalv/1.10.0`（无补丁）+ test_package | test_package 断言失败：`crashed instead of failing gracefully ... rc=139` |
| B（开策略） | 同上 + `patches/0001-guard-null-instance-when-backend-open-failed.patch` | 全绿；`Plugin: http://drobilla.net/plugins/mda/Delay` + `Failed to connect to audio system` + rc=1 |
| 干净环境 | `conan remove "jalv/*" -c` + 清 `p/` 后重跑 | 全绿（补丁应用 1 次，上游 `test_symap` 通过，消费者测试通过） |

## 9. 资产清单

| 文件 | 作用 |
|------|------|
| `scripts/detect_absent_service_crash.py` | 两通道检测（L1 源码 / L2 运行期） |
| `templates/0001-guard-lazy-handle-cleanup.patch.tmpl` | NULL 守卫补丁模板 |
| `templates/test_package-graceful-failure.py.tmpl` | 优雅失败断言模板 |
| `samples/graceful_cleanup_demo.c` | 自包含最小样例（无三方依赖） |
| `tests/repro_absent_service_crash.sh` | A/B 复现与检测器自校验 |
| `tests/test_detect_absent_service_crash.py` | 检测器单测 |
