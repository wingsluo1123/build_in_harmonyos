# yaml-mode 0.0.16 适配笔记(OHOS PC / aarch64)

## 包定位

`yaml-mode` 是 **Emacs 的 YAML major mode**(canonical elisp 包,
https://github.com/yoshiki/yaml-mode)——Emacs 用户编辑 YAML 的标准选择,
单文件包(主体 `yaml-mode.el`,18356 字节)。

上游版本锚定:**0.0.16 = merge commit `23395dfcf004c952850691b70e63f97f169596e8`**
(2023-10-03,"Merge pull request #109 from snogge/release-0.0.16")。上游自
0.0.14 起不再打 git tag(最后一个 tag 是 v0.0.13),0.0.14+ 只存在于 git 提交;
Debian 的 yaml-mode 0.0.16 同锚此提交。master HEAD(2026-08)的 yaml-mode.el
版本头同样是 0.0.16。

纯 elisp 数据包:**上游"构建"只是 emacs 字节码编译(--batch 生成 .elc)**,
OHOS 无 emacs,本包不编译、交付 .el 源文件(字节码由目标环境按需生成,
且 .elc 与 emacs 版本绑定,跨环境交付本就不合适)。

## 版本锚定

- 源 URL:`https://github.com/yoshiki/yaml-mode/archive/23395dfcf004c952850691b70e63f97f169596e8.tar.gz`
- sha256:`a3db35d89d9a45cde4a4bd22df8d08e62d8dc972046218532a46661d0ad0fe58`(23564 字节)
- yaml-mode.el:18356 字节,sha256 `5e19a87a7e6cc5f9e3f829888eedadef37041e8d30a2526ce07f08108ccb71a5`

## 载荷口径(三处常量必须同值同改)

交付清单 = **14 个文件显式清单**(conanfile.py 的 PAYLOAD_MANIFEST):

    share/emacs/site-lisp/yaml-mode/yaml-mode.el   数据本体(18356)
    share/doc/yaml-mode/upstream/README            溯源(1972)
    share/doc/yaml-mode/upstream/Changes           上游变更史(3930)
    share/doc/yaml-mode/upstream/Makefile          上游构建配方(812)
    share/doc/yaml-mode/upstream/test-files/*.yaml 上游 9 个测试样例(消费语料)
    licenses/LICENSE.txt                           GPLv3 全文(35149)

合计 62964 字节;排序清单 sha256 = `468bab40d95c19fcf752a8724f0fcabb7bf6e9bf2a95b79ce352c037dd057977`。
三处落点:`conanfile.py`(build() 闸门)、`test_package/consumer_ym.py`(布局路径)、
`test_package/test_layout.py`(自检对账)。

**.elc 明确不交付**:emacs 字节码与 emacs 版本绑定,且 OHOS 无 emacs——
test_layout.py 把 .elc 列入构建产物拦截。

## 上游测试与替代方案

上游 test/yaml-mode-test.el 含 **4 个 ert-deftest**(ERT 框架,依赖 emacs
batch 运行);CI 无 emacs,按 skipped 申报(MANIFEST.yml)。替代:consumer_ym.py
纯 Python 独立第二实现——elisp 顶层结构解析(36 个 def,关键符号齐备)+ defconst
正则表提取(elisp→python 保守转换,失败跳过计数)+ **用交付的正则对上游 9 个
YAML 样例逐行语法分类**(即 yaml-mode font-lock 的真实工作)。

## 交付边界

上游树里的 `.github/`、`.gitignore`、`.dir-locals.el`(开发配置)与 `test/`
(ERT 测试本体,依赖 emacs 运行)不交付;`test-files/*.yaml` 样例**随包交付**
在 doc/upstream/test-files/(消费者用例的真实语料)。

## 验证记录

- 本地:py_compile 全过;载荷清单口径由 tar 条目直算锁定;消费者解析器对
  交付 yaml-mode.el 实测(版本头/36 defs/正则提取/样例分类)。
- CI:conan create → build() 清单闸门 → test_package 两级用例。
