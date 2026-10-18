# DRAFT-25002: 手写 configure+Makefile.in 老包的 Conan custom 配方五件套

- 条目主题：老手写构建系统（configure 为手工 shell 脚本、Makefile.in 硬编码
  工具链，非 autoconf/cmake/meson）在 OHOS 上用 Conan custom 配方的完整手法，
  重点覆盖 **install/data-install 分裂陷阱**（漏跑 = 空数据目录假成功）。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：unicon 3.0.4；同范式适用于所有手写 Makefile.in 老包。

## 错误特征
- 编译期：`g++: No such file or directory` / `gcc: command not found`
  （OHOS 只有 clang/clang++，Makefile.in 硬编码 gcc/g++）
- 运行期（假成功）：编译链接全绿，但包内数据目录存在却为空
  （`Couldn't access .../dict/pinyin.map` 一类断言失败）

## 根因
1. 手写 Makefile.in 的 `install` 目标依赖闭包不完整：`install: all` 只装库，
   数据走独立的 `data-install` 目标，头文件干脆不装——老包极常见。
2. `conan create` 绿只代表 build() 成功，**不代表 package() 产物完整**；
   数据缺失要到 test_package 运行断言才暴露。

## 修复（五件套）
```python
# ① 补丁层：Makefile.in 的 CC/CXX 环境变量化（R33：取自 conanbuild 环境）
# ② build()
def build(self):
    self.run(f"./configure --prefix={self.package_folder}")
    self.run("make")
    self.run("make -C unicon ccedata gbdata big5data")  # 补跑数据生成目标
# ③ package()——关键：核对上游 install 是否分裂出数据目标
def package(self):
    self.run("make install")
    self.run("make data-install")      # install 分裂时必跑，否则数据目录全空
    copy(self, "*.h", src=.../include, dst=.../include)  # ④ 老包常不装头文件
# ⑤ package_info：libdirs 指非标准路径 + 纯库形态摘可执行（免 R38）
```

## 诊断口诀
`conan create` 绿但 test_package 运行断言挂 →
先 `conan cache path <ref>` 后 `ls -R` 查包内数据/头文件是否齐全
→ 再回头核上游 install 目标的依赖闭包（`grep -A20 '^install' Makefile*`）。

## 验证（unicon 3.0.4 实证）
- 首轮 conan-verify G2 失败：包内 `lib/unicon/modules/cce/dict/` 为空
  （pinyin.map 缺失，consumer test 断言挂）。
- 根因：上游根 Makefile `install` 与 `data-install` 是独立目标，配方漏跑后者。
- 补 `make data-install` 后 G0-G4 + L2/L4/L5 全门禁通过（consumer test 实证
  pinyin.map 入包）。
- 44 补丁、`make (all)` exit=0、7 产物、第三方依赖清零。

## 关联
E097（bearssl 自定义 Makefile 无 configure）、E156（fbida 非标准 configure）、
E108（patch Makefile.in install 规则）、E041（绕过 autotools）。
