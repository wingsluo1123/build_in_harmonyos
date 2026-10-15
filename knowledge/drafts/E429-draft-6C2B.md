# 共享包装库内置 codec 与系统 codec 的链接选择（草稿）

日期：2026-10-12；实例：wxwidgets-gtk3/3.2.10.1，GTK3/libjpeg-turbo 与 wx bundled JPEG。路径 B 候选，是否独立入库或补充既有条目由主编判断。

## 现象与根因

共享库能构建、初始化 wxApp，JPEG 保存却报 `Wrong JPEG library version: library is 62, caller expects 90`。包缺失并非原因：GTK 依赖图已有 libjpeg-turbo，wx 也构建了 libwxjpeg.a。wxcore 的链接项先列 toolkit `-ljpeg/-lturbojpeg`，后列 builtin archive；前者已满足未定义符号，归档实现没有被选入。头文件编译版本90与实际实现62不匹配，原产物 `jpeg_CreateCompress/Decompress@LIBJPEG_6.2` 为可观察证据。

## 修复和可推广诊断

依次确认实际被编译头文件的版本宏、归档符号、最终链接命令顺序和shared动态符号。不能因CMake缓存写builtin就假定实现已经进入shared库。0004对 wxBUILD_SHARED 且 wxUSE_LIBJPEG/PNG=builtin 的 wxcore，将选中归档前置到 toolkit 依赖前，保留上游后续依赖链接；非shared和system codec不进入该修改。

输入是明确的codec选择与实际link列表；输出是与编译头一致的实现和可用编解码。可推广到 GUI、图像/压缩包装共享库混用 bundled archive 与系统依赖的场景。不要改JPEG_LIB_VERSION骗过结构尺寸检查，不删除依赖或用桩替代codec。若设计支持统一使用system codec，可以同时调整头/实现，但需独立验证API和依赖版本，不能仅改运行宏。

## 验证与限制

保持16×16真实图片编码/解码及尺寸检查：旧installed shared包RED退出1，记录JPEG版本冲突；包含0004的trial库GREEN退出0，输出JPEG roundtrip OK。trial nm -D不再显示对jpeg_Create*的LIBJPEG_6.2未定义导入。最终Conan包及正式W3记录另列archives/w/wxwidgets-gtk3/3.2.10.1/reports/validation-summary.md，不继承trial成功。

该修法只验证当前 wxcore 符号选择与加载顺序，尚未证明任意GTK宿主先以RTLD_GLOBAL加载系统JPEG后再载wx插件也安全。PNG仅调整相同链接位置，JPEG是本次实际ABI冲突复现对象；不声称所有格式或所有动态符号冲突均已解决。TIFF/多监视器等与此根因无关。

## 查重与新增内容

查重基线main63c58108a49fbe646911540cb64956b7cbeccd2f。检索 `Wrong JPEG library version`、`LIBJPEG_6.2`、`jpeg_CreateCompress` 无同根因；`JPEG_LIB_VERSION`命中E157，其内容为cpp缺失时版本检测脚本失败及JPEG_VER配置，未覆盖共享链接先满足符号导致builtin archive未入选。新增的是“选择值→实际链接→动态符号→真实codec往返”证据链与限定修法，而非重复E157版本检测或一般依赖缺失知识。

相似度工具结果与人工裁定见reports/knowledge-review.md。此处没有伪造历史CI失败；失败来自受控真机复现。
