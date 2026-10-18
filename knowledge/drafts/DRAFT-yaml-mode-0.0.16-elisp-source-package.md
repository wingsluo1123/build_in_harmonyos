# DRAFT:yaml-mode 0.0.16 —— elisp 单文件包的纯数据适配定式(不交付 .elc、ERT skipped、elisp 解析器第二实现)

## 背景

yaml-mode 0.0.16(Emacs 的 YAML major mode,canonical elisp 包)是单文件 elisp
包:主体 `yaml-mode.el`(18356 字节)+ ERT 测试 + 9 个 YAML 测试样例。上游
"构建"仅 `emacs --batch` 字节码编译生成 .elc;OHOS 无 emacs。

## 定式

1. **交付 .el 源文件,不交付 .elc**:.elc 与 emacs 版本绑定,跨环境交付本就
   不合适;目标环境按需 byte-compile。`test_layout.py` 把 `.elc` 列入构建产物
   拦截清单。
2. **布局**:Emacs site-lisp 约定 `share/emacs/site-lisp/<pkg>/<pkg>.el`,
   `package_info.resdirs` 指向该目录;消费者把目录加入 load-path 即用。
3. **上游 ERT 测试 skipped 申报**:上游 N 按实际申报(本例 4 个 ert-deftest),
   MANIFEST.yml 写明 skip_reason="emacs binary not available in OHOS CI
   environment"。
4. **rule12 消费用例 = elisp 解析器第二实现**(纯 Python,不依赖 emacs):
   - 版本头对账(`;; Version: x.y.z`)+ `(provide 'pkg)` 存在性;
   - 顶层形式解析:defcustom/defface/defun/defconst/defvar 清单+关键符号
     齐备(本例 36 个定义);
   - defconst 正则表提取:elisp→python 保守转换(`\( \) \| \b \s-` 子集,
     `\cX` 类别直接放弃并计数,不假装成功);
   - **真实消费**:用转换成功的正则对上游自带的 YAML 样例逐行做语法分类——
     即该 mode 的 font-lock 在每次 buffer 变更时的本职工作,不是纯断言。

## 实测

yaml-mode 0.0.16(commit 23395dfc 锚定;上游 0.0.14 起不打 tag,Debian 同锚):
本地 conan create 全链路真跑全绿,consumer 33 项+layout 39 项(含 .elc 拦截)。
适用范围:所有 elisp 单文件包(major-mode/minor-mode/extension)以及
"上游构建依赖目标环境特有解释器"的数据包。

## 关联

- 同类:installation-locale(数据包+第二实现消费)、distribution-gpg-keys
  (RFC 4880 第二实现消费)
- 坑:.elc 若误交付会被下游 emacs 加载失败;test-files 类上游样例应随包交付,
  作为第二实现的免费语料。
