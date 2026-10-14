# sratom 0.6.22 适配笔记（OHOS PC aarch64）

## 上游形态
LV2 Atom ↔ Turtle RDF 序列化小库（drobilla，ISC），meson 构建，纯 C。
源：https://download.drobilla.net/sratom-0.6.22.tar.xz
sha256 0209b7d0f22c96abb416722ed735b0933be47931ecff4aa4b26ded7760b4f252

## 依赖（全部制品仓已发布）
sord/0.16.22 + lv2/1.18.11-git（传递：serd/0.32.9、zix/0.8.x）

## 依赖图决策（R35/R36 记录）
- **不显式钉 serd**：sord/0.16.22 传递钉 serd/0.32.9；显式 requires serd/0.32.10
  会精确版本互斥（conan 2 Version conflict，实测）。去钉版后图自动收敛到 0.32.9
  （同 jalv/ocp 实证的同族问题同解法）。
- serd 0.32.9 与上游 sratom 0.6.22 要求兼容（sratom 未钉 serd 精确版）。

## meson 交叉构建（探索期实测，配方 build() 固化）
- cross file：c/llvm-ar/pkg-config，linux-aarch64，needs_exe_wrapper=true；
- **meson_options.txt 无 shared 选项**（G2 实测 "Unknown option: shared"）——库形态用
  `--default-library=shared|static` 全局开关表达（取值映射 true→shared / false→static，
  meson 拒绝 true/false 字面量）；
- -Ddocs/-Dhtml/-Dsinglehtml=disabled（无 doc 工具链）、-Dtests=disabled（配方纯净，
  上游测试走离线三步法）、-Dlint=false；
- PKG_CONFIG_PATH 指 PkgConfigDeps 生成目录（lv2/serd-0/sord-0/zix-0.pc 齐备）。

## conan-verify G2 修复循环（5 轮，逐轮实证）
1. test_package 手工聚合 -I 漏 lv2 → lv2 的包缓存 p/ 目录未落盘（只有 d/e/es，
   download --only-recipe 不落二进制）→ `conan install --build=never` 落盘后解决；
2. test_package 自写聚合对 lv2 布局不稳 → 改 PkgConfigDeps 生成 lv2.pc（需在
   test_package requires 显式声明 lv2——仅靠传递依赖不生成 .pc）；
3. 嵌套 `"$(PKG_CONFIG_PATH=... pkg-config ...)"` 子 shell 展开在沙箱不稳 →
   **两步法**：pkg-config 输出落盘文件，Python 读回字面量 flags 拼编译命令；
4. 硬编码兜底 `-lzix` 报 unable to find——zix 库文件名是 libzix-0，.pc 已带
   -lzix-0，勿追加（教训：兜底库假设必须先 ls 库目录核实命名）。

## 上游测试（R51 三步法，详见 reports/test-report.md）
- 清点：test/meson.build 注册 trip/write（suite=unit）+ headers 探针（单列）；
- 实跑：2/2 通过（trip 输出 "All tests passed."，write 为上游设计的警告路径验证
  rc=0），探针 rc=0；
- 消费者测试实测：Int32 往返 body 字节级全等；Object 属性数 2、label String 无损、
  x 经 sratom 的 xsd:int 映射回读 atom:Int 2026（字节 EA 07 00 00 实证）。

## conan-verify
G1/G2/G3 + L2/L4/L5 全绿（reports/conan-verify-report.md；G0 "构建系统 unknown" 与
G4 "无法找到程序包 ID" 为门禁工具对 meson 直驱形态识别不全的告警，非阻断——G2
conan create 成功即实质验证）。
