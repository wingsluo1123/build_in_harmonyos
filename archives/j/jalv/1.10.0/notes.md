# jalv 1.10.0 适配笔记

## 编译环境

- 构建系统: meson（上游）/ conanfile 直驱编译器两步法
- 编译日期: 2026-10-18
- 目标: OHOS PC aarch64（armv8），clang 工具链来自 SDK native/llvm
- 状态: published

## 编译步骤

meson 交叉没有「conan 一条命令建完」的稳定通道（`self.run` 内嵌 `$(pkg-config ...)`
子 shell 在沙箱里静默取空 flags，见 `skills/meson-cross-pkgconfig` 坑③），因此
`build()` 走两步法：

1. **generate**：用 ninja/meson 后端生成构建目录，pkg-config 的输出落盘成文件；
2. **compile**：Python 读回字面量 flags，直接调用交叉 clang/ninja 编译链接。

产物：`lib/jalv.so`（JACK 后端客户端库式宿主主体）与 `bin/jalv` 可执行文件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ERROR: Unknown option: "shared"` | 上游 meson_options.txt 无 `shared` 选项 | 用 `--default-library=shared` 全局开关（`invalid choice: 'false'` 同理，bool 映射到 shared/static） |
| 2 | `unable to find library -lzix` | 上游库实体名带版本后缀（实体为 `libzix-0`） | `-l` 前先 ls 依赖 lib 目录核实命名，按实体名链接 |
| 3 | meson install 重写 ELF 后执行报 `Operation not permitted` | OHOS 签名/属主映射（E046 族）：install 重写破坏了 ELF 代码签名 | 在 `package()` 里对重建产物重新签名（配方内固化该步骤） |
| 4 | 无音频服务器时启动即 SIGSEGV（rc=139） | `jalv_process_deactivate()` 在端口循环里无条件 `lilv_instance_connect_port(proc->instance, ...)`，而后端连接失败时 `instance` 仍为 NULL | 补 NULL 守卫补丁 `patches/0001-guard-null-instance-when-backend-open-failed.patch` |
| 5 | 端到端音频链路无法验证 | 本机 `jackd` 驱动目录被编译死为 `/lib/jack`（不存在且不可写），无法起 dummy server；且 `/tmp` 只读（日志须落 `~/tmp`） | 消费者测试改为验证真实 LV2 发现/加载链路 + 无服务时的优雅失败契约 |

## 源码修改

`patches/0001-guard-null-instance-when-backend-open-failed.patch`（367 B）：
`src/process_setup.c` 的 `jalv_process_deactivate()` 循环内为 `proc->instance`
加 NULL 守卫，只包住解引用、保留上游释放顺序（先 `lv2_evbuf_free` 再断端口）。
对应上游缺陷：失败路径解引用惰性初始化句柄。详见
`skills/runtime-service-absent-cleanup-guard`。

## 依赖版本

| 包 | 版本 | 说明 |
|----|------|------|
| lv2 | 1.18.11-git | 宿主契约头 |
| lilv | 0.28.0 | 插件发现/加载/状态 |
| sratom | 0.6.22 | lilv 状态序列化 |
| sord | 0.16.22 | URD 栈 |
| zix | 0.8.1-git.1 | 容器/语义工具（`sord` 钉版对齐） |
| suil | 0.10.26 | UI 承载 |
| jack | 1.9.22 | 唯一实际可用的音频后端（portaudio/19.7.0 在 OHOS 关闭了 ALSA/JACK/OSS 全部后端） |
| mda-lv2 | 1.2.12 | **仅 test_package** 的真实插件 bundle |

## 验证结果

```bash
# 干净无缓存环境完整流程
conan remove "jalv/*" -c
conan create archives/j/jalv/1.10.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# rc=0：补丁应用 1 次、上游 test/test_symap 通过、test_package 通过

# A/B（关闭 / 启用 NULL 守卫补丁）
# A 无补丁: test_package 失败 "crashed instead of failing gracefully ... rc=139"
# B 有补丁: Plugin: http://drobilla.net/plugins/mda/Delay
#           error: Failed to connect to audio system  → rc=1
```

## 交付物

| 文件 | 说明 |
|------|------|
| `library/lib/jalv.so` | 宿主主体（含内部 JACK 客户端） |
| `bin/jalv` | 可执行宿主前端 |

## 注意事项

- 运行期必须设置 `LV2_PATH`，且要指向 **bundle 的父目录**（指向 `foo.lv2` 自身会得到
  `load_dir_entry(): warning: Skipping non-directory ...`）。
- `-V` / `-h` 的退出码是 **81**（上游行为，非错误），测试断言应基于输出而非退出码。
- 无音频服务器时 `-i <uri>` 的期望退出码是 1 且打印 `Failed to connect to audio system`；
  若为 139 说明 NULL 守卫补丁未生效。
