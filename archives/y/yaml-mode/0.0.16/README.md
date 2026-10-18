# yaml-mode 0.0.16(OHOS PC 适配)

Emacs 的 YAML major mode——Emacs 用户编辑 YAML 的标准选择。
上游:<https://github.com/yoshiki/yaml-mode>(release 0.0.16,commit `23395dfc` 锚定)。

- **纯 elisp 数据包**:无编译(不交付与 emacs 版本绑定的 .elc 字节码)、零依赖、零补丁。
- 交付 `share/emacs/site-lisp/yaml-mode/yaml-mode.el`(load-path 约定,18356 字节)
  - 溯源(README/Changes/Makefile + 上游 9 个 YAML 测试样例)+ GPLv3 LICENSE。
- `build()` 做载荷清单闸门(14 文件逐项字节数+排序清单 sha256+主件内容指纹)。
- `test_package` 两级验证:消费者用例(纯 Python elisp 结构解析器+交付正则对上游
  YAML 样例的真实消费,不依赖 emacs)+ 布局自检;上游 ERT 测试依赖 emacs(CI 无
  emacs),按 skipped 申报,详见 `test_package/MANIFEST.yml`。

细节与实测记录见 `notes.md`。
