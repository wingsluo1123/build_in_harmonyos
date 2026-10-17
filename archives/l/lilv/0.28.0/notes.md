# lilv 0.28.0 适配笔记（OHOS PC aarch64）

## 上游形态
LV2 插件宿主库（drobilla，ISC），meson 构建，纯 C。下游消费者：jalv。
sha256 8dcb70adb5cf072335115a6b091f4113710bdc73abaadaa3f9e9c1e55957b149

## 依赖（R36 拓扑序：sratom 已先行适配 PR #15450）
sratom/0.6.22 + sord/0.16.22 + lv2/1.18.11-git（传递：serd/0.32.9、zix/0.8.x）
- 不显式钉 serd（sord 传递钉 0.32.9，显式钉版冲突实证同 sratom notes.md）

## meson 特性裁剪（探索期实测）
-Dbindings_py/cpp=disabled（无 python3/pybind11）、-Ddocs/-Dhtml/-Dsinglehtml=disabled、
-Dtests=disabled（离线三步法）、-Dlint=false、-Dtools=disabled、-Ddynmanifest=disabled。
--default-library=shared|static（上游无 shared 选项，sratom G2 同源实证）。

## 编译实测
[130/130] 零失败（含全部 21 个上游测试二进制）。

## 上游测试（R51 三步法，详见 reports/test-report.md）
21/21 实跑通过（LD_LIBRARY_PATH=build + conanrun 环境，逐用例 rc=0）。

## 消费者测试要点（test_package）
- fixture bundle 内嵌 test_package/fixture/consumer-test.lv2（manifest.ttl + plugin.ttl）；
- lilv.h 所有权陷阱：lilv_port_get_symbol 返回 const LilvNode* 由 port 持有，
  free 即 SIGSEGV（gdb ptrace 被沙箱拒，代码审查定位）；正确 API 两步取
  （get_port_by_index → port_get_symbol，0.28.0 无 plugin_get_symbol_by_index）；
- HMDFS 陷阱再现：meson install --destdir 落盘的 liblilv-0.so.0 软链接解析正常
  （readlink OK、head 出 ELF 魔数）但 dlopen 仍失败；改用 build 目录 ld 直出版
  （sha256 650d88a1... vs destdir 15523dc6...，内容不同——install 重写 RPATH）
  后加载成功。与 almanah 同源实证（HMDFS exec 由 ELF 内容决定）。

## conan-verify
见 reports/conan-verify-report.md（G0 "构建系统 unknown" / G4 "无法找到程序包 ID"
为门禁工具对 meson 直驱形态识别不全的告警，非阻断——G2 conan create 成功即实质
验证，同 sratom 口径）。
---

**编译结束**: 2026-10-12 18:20
**最终状态**: published
