# 知识扩展查重与验证

基线：main `63c58108a49fbe646911540cb64956b7cbeccd2f`，2026-10-13。申请人chenicia（2301_79503900），队伍“天天开心”（用户确认）。两份成对草稿由当前ohc.graph.cmd_add草稿模式生成并补充真实证据，不修改正式图谱或索引，不自行分配正式编号。

| 草稿 | 关键词与相近条目 | 现有覆盖与新增范围 | 工具结果 |
|---|---|---|---|
| E429-draft-6C2A | gdk_screen_get_resolution、PANGO_SIZE_NEGATIVE、monitor 0x0；E463/E471/E527、headless Broadway示例草稿 | 旧条目为后端构建/工具或无显示分类；新增“已连接仍返回无效能力值”的几何与DPI组合诊断和真实GUI回归 | create，最近E471 0.20，E527 0.15，E240 0.13 |
| E429-draft-6C2B | Wrong JPEG library version、LIBJPEG_6.2、jpeg_CreateCompress、JPEG_LIB_VERSION；E157/E331/E028 | E157为版本检测脚本，E331为HMDFS符号链接，E028为系统库覆盖；新增builtin archive未选入shared的实际链接/动态符号/codec往返证据链 | create，最近E331 0.17，E157 0.14，E028 0.13 |

检索graph/doc/drafts；几何/DPI根因关键词无相同条目，JPEG版本宏命中E157并逐项比较，详见两份.md。机器相似度是辅助建议，最终通用性、编号、是否合并或独立入库由主编决定；不等于已获10分。

当前仓库parse_kv_file、required/known字段集合、category受控词表、regex编译、paired doc实际检查均通过，见knowledge-field-validation.json。draft-review原JSON包含质量及分数。正式graph validate CLI返回0，有既有覆盖/分类warnings，草稿不进入正式校验；没有改旧条目掩盖warnings。

独立子任务已提出并修正两处精度：geometry→screen仅单monitor；无效workarea→本monitor geometry不限单monitor。Pango约-117明确为按DPI比例推导，直接实测为DPI=-1、Pango critical和组合RED/GREEN。JPEG草稿明确只验证当前wxcore加载顺序，PNG仅调整同类链接位置，不宣称任意宿主无ELF符号抢占。

两份草稿均引用实际受控失败与最终消费者证据；这不是编造历史CI编号。同步本地知识库不等于官方入库。路径B拟申请一项贡献创新10分候选，测试框架/工具链验证不重复加分。
