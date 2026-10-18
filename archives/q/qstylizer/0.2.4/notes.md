# qstylizer 0.2.4：保留 QSS 字面值中的分号

固定来源：PyPI qstylizer 0.2.4 sdist；SHA256 `4880991d912c9837454832e8e2b58d60b66848d8c4a7cf57ed544fd68b91a23a`。
上游：https://github.com/blambright/qstylizer 。MIT。此 Python 运行时库没有可执行入口，不需要 Qt GUI 运行器；测试范围为 QSS 文本构造及解析，未验证 Qt 渲染。

## 问题和最小修复

正常输入 `QLabel { qproperty-text: "left;right"; }` 在原版中变成 `"leftright"`。`parser.parse` 已通过 tinycss2 区分声明及值，但 `StyleRule._sanitize_value` 又对值进行全局 `replace(";", "")`，因此损坏 QString、URL 或转义中的分号。

补丁只改变值清理：使用已有运行时依赖 tinycss2 判断尾部 token 是否是顶层 `literal ;`，只移除连续声明终止符，保留原文本及尾部空白。引号/URL/转义中的分号属于 string、url 或 ident token，不能删除。不增加解析框架，不改原 suite/fixtures。

## 依赖和运行

Conan 运行时依赖为 `python/3.12.9#d8eda770878152bea40b42db9f7024cd`，目标实际构建与交付消费者已确认供应。Python 依赖按准确官方纯 Python wheel 安装至包内 `lib/python`：tinycss2 1.4.0、inflection 0.5.1、webencodings 0.5.1。URL/SHA256 在 conandata.yml 中逐一固定，随 wheel 保留各 dist-info 许可与元数据。

原上游 suite 使用 pytest 7.4.4、pytest-mock 3.16.0，及其固定传递依赖。原声明中的 pytest-catchlog 是旧插件；本轮 suite 未使用 catchlog fixture，pytest 7 自带日志功能，保留原测试文件且实际原 suite 72 项通过，没有改写 fixture 或伪造 mocker。测试工具只用于 build-tools，不随运行时包交付。

`conan create . -pr:h <已核 OHOS profile> -pr:b <已核 profile> --build=missing` 在 build 中运行原 suite 和新增回归，test_package 使用交付包完成 1 个消费者流程。可选 `QSTYLIZER_INPUTS` 指向固定 sdist/wheels 私有目录；所有本地输入仍校验官方 SHA256。没有设置该变量时使用 conandata 官方地址。

## 已验证及待验证

本机 CPython 3.11：原 suite 修复前后均 72/72；新增 7 项修复前 6 失败/1 通过，修复后 7/7；已安装布局消费者 1/1、8 条断言。原始结果在作者 ENTRY 引用的 evidence/ 目录。

OHOS/HongMeng Kernel 1.12.0 aarch64、Python 3.12.9、Conan 2.29.1：原 suite 72/72，新增回归7/7，交付包消费者1流程/8断言通过；Conan Verify PASS。完整W3已通过：L0、L1、L1e负向验证、L4、L5 PASS；L2因无bin目录SKIP。旧G0b及KC2/KC5失败保留，私有运行目录采用官方ad0c1a73中的build_and_test.sh与knowledge_check.sh修正后，由未修改的FinishPipeline.step35_local_ci实际执行并生成.ci-result.json。没有重放完整finish，不宣称其整体终态。独立W4及R3受影响复核通过；AtomCode、本PR官方CI和提审待完成。平台任务标记 cpp，实际软件为 Python；按项目现有人工 Python 语言入口裁决执行，不修改任务标签。


## 官方补丁生成与行尾边界

H1原refresh-patch曾因dry-run失败而保留手工补丁，虽然rc0，不能视作R3成功。原始失败保留。sdist原style.py及受测文件均为CRLF，官方生成器read_text产生LF上下文；在既有Ubuntu/GNU patch环境复现了相同dry-run失败。

本次在私有host镜像仅将原始/修复style.py行尾CRLF规范化为LF，真实执行未修改的官方 `ohc-run.py refresh-patch --auto qstylizer 0.2.4`，成功生成 `patches/0001-qstylizer-style.py.patch`，SHA256 `b5063d18d82d41c5aceb4797d32cdf1550ff7593a6f0392b3fdb8b08b4ccc980`。GNU dry-run及实际回放均通过，回放源码与OHOS受测源码经相同行尾规范化后逐字节相等；其他源码不变。固定sdist、目标原始源码及先前失败原件未改。作者将conandata/manifest引用准确改为该实际生成文件，strip仍为1。

这是补丁生成来源及序列化变化，未更改Python行为，未另行重跑独立suite；W3必要create执行另记。新补丁已由目标Conan patch_ng实际应用，raw style.py SHA256仍为afa8f8af1a3e6ef80c86c9f1d68fd8fe9e56564246d64efbe662ddcec6bcf926，与原受测字节相同，其他源码不变。新export RREV为aa7d0eaedeaf3d3d0372668fb262cfd3；完整W3结果及实际包引用见test-report.md。
