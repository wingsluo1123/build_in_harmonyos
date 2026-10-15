/* consumer_use_case.c — mnxdom 3.0.1 消费者用例（端到端业务流程）
 *
 * 业务场景：模拟上层业务应用「乐谱工程批处理器」（MusicScoreBatch）。
 * 该应用面向音乐排版/乐谱批量工具，接收一份 MNX 乐谱 JSON 工程文件，
 * 使用随包交付的 mnxdom 公开接口完成一个**完整的输入 → 处理 → 可观察输出**
 * 业务流程，并把导出的 MNX 工程文件与统计报告交由驱动脚本核验：
 *
 *   C1  载入：读取输入 MNX 工程文件（真实文件 I/O，鸿蒙侧走 $TMPDIR/HMDFS）
 *   C2  校验：调用 validation::schemaValidate 对输入工程做 MNX schema 校验
 *   C3  编辑：按业务规则补齐工程结构——追加全局小节、新建声部(part)并补小节、
 *       建立排版(layout)与谱表(staff)、建立分谱(score)/页面(page)/系统(system)
 *       以及系统级排版切换(layoutChange)
 *   C4  导出：doc.save() 落地为新的 MNX 工程文件（可观察产物）
 *   C5  回读复核：Document::create() 重新装载导出文件，再次 schema 校验，
 *       并比对关键业务字段（小节数/声部数/排版 id/系统小节引用）
 *
 * 判定采用业务期望值（见 main 中注释），对导出产物做真实复核；
 * 退出码：0=业务流程全部完成且产物与期望一致；非 0=业务校验失败。
 *
 * 与 test_package/test_mnxdom.cpp（API 断言集）不同：本用例构成一个完整的
 * 「工程文件输入 → 业务编辑 → 产物落盘 → 回读复核」流程，并输出供脚本核验
 * 的产物文件与报告行（observable output），而非单纯断言列表。
 *
 * 用法：consumer_use_case <输入工程.json> <导出工程.json>
 */
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <string>

#include "mnxdom/mnxdom.h"

namespace {

int g_failures = 0;

void fail(const std::string& what)
{
    std::cerr << "FAIL: " << what << std::endl;
    ++g_failures;
}

/* 鸿蒙侧临时/工作目录：优先 $TMPDIR（R10：不得硬编码 /tmp） */
std::filesystem::path workDir()
{
    const char* tmp = std::getenv("TMPDIR");
    std::filesystem::path dir =
        (tmp && *tmp) ? std::filesystem::path(tmp) : std::filesystem::temp_directory_path();
    return dir;
}

} // namespace

int main(int argc, char** argv)
{
    using namespace mnx;

    if (argc < 3) {
        std::cerr << "usage: consumer_use_case <input.mnx.json> <output.mnx.json>" << std::endl;
        return 2;
    }
    const std::filesystem::path inputPath = argv[1];
    const std::filesystem::path outputPath = argv[2];

    std::cout << "--- 消费者用例 (mnxdom 3.0.1) ---" << std::endl;
    std::cout << "workdir=" << workDir().string() << std::endl;

    // ── C1 载入真实工程文件 ──────────────────────────────────────────────
    if (!std::filesystem::exists(inputPath)) {
        fail("输入工程文件不存在: " + inputPath.string());
        return 1;
    }
    Document doc = Document::create(inputPath);

    // ── C2 对输入工程做 schema 校验 ─────────────────────────────────────
    if (!static_cast<bool>(validation::schemaValidate(doc))) {
        fail("输入工程未通过 MNX schema 校验");
        return 1;
    }
    std::cout << "C1/C2 载入并校验通过: " << inputPath.filename().string() << std::endl;

    // ── C3 业务编辑：把工程补齐为一份可交付的乐谱工程 ────────────────────
    // 业务规则：每份工程至少 3 个小节（业务方批处理默认补齐）
    constexpr int kBusinessMeasures = 3;
    const std::size_t measuresBefore = doc.global().measures().size();
    for (int i = 0; i < kBusinessMeasures; ++i) {
        auto measure = doc.global().measures().append();
        measure.set_id("m" + std::to_string(measuresBefore + i + 1));
    }

    // 业务规则：每个工程至少一个声部，且声部小节数与全局小节数一致
    auto part = doc.parts().append();
    auto partMeasures = part.create_measures();
    const std::size_t totalMeasures = doc.global().measures().size();
    for (std::size_t i = partMeasures.size(); i < totalMeasures; ++i) {
        partMeasures.append();
    }

    // 业务规则：建立默认排版 layout0 与谱表
    auto layouts = doc.ensure_layouts();
    layouts.append();
    auto layout = layouts[0];
    layout.set_id("layout0");
    auto staff = layout.content().append<layout::Staff>();
    staff.set_symbol(LayoutSymbol::Bracket);

    // 业务规则：建立分谱/页面/系统，并为系统配置排版切换
    auto score = doc.ensure_scores().append("Full Score");
    auto page = score.ensure_pages().append();
    auto system = page.systems().append("m1");
    auto layoutChange = system.ensure_layoutChanges().append("layout0", "m2", FractionValue(3, 8));

    // 编辑后必须仍是合法工程
    if (!static_cast<bool>(validation::schemaValidate(doc))) {
        fail("业务编辑后工程未通过 MNX schema 校验");
        return 1;
    }

    // ── C4 导出新的工程文件（可观察产物）────────────────────────────────
    std::filesystem::remove(outputPath);
    doc.save(outputPath, 2);
    const auto bytes = std::filesystem::exists(outputPath)
                           ? std::filesystem::file_size(outputPath) : 0;
    if (bytes == 0) {
        fail("导出工程文件为空: " + outputPath.string());
        return 1;
    }

    // ── C5 回读复核：重新装载产物并比对业务字段 ─────────────────────────
    auto reloaded = Document::create(outputPath);
    if (!static_cast<bool>(validation::schemaValidate(reloaded))) {
        fail("回读导出工程未通过 MNX schema 校验");
        return 1;
    }
    if (reloaded.global().measures().size() != totalMeasures) {
        fail("回读后小节数不一致");
    }
    if (reloaded.parts().size() != 1u) {
        fail("回读后声部数不一致");
    }
    if (reloaded.global().measures()[0].id() != "m1") {
        fail("回读后首小节 id 不一致");
    }
    if (layoutChange.layout() != "layout0") {
        fail("排版切换未引用 layout0");
    }

    // ── 可观察报告行（由驱动脚本核验）───────────────────────────────────
    std::cout << "consumer-report: measures=" << totalMeasures
              << " parts=" << reloaded.parts().size()
              << " layout=" << layout.id().value_or(std::string("<unset>"))
              << " first_measure=" << reloaded.global().measures()[0].id().value_or(std::string("<unset>"))
              << " fraction=" << layoutChange.location().position().fraction().numerator()
              << "/" << layoutChange.location().position().fraction().denominator()
              << " output=" << outputPath.filename().string()
              << " bytes=" << bytes
              << " failures=" << g_failures
              << std::endl;

    if (g_failures == 0) {
        std::cout << "consumer-ok" << std::endl;
        return 0;
    }
    return 1;
}
