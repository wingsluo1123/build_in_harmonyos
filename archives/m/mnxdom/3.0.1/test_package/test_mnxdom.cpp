/*
 * mnxdom 3.0.1 — 消费者视角冒烟测试（OHOS/Conan 包）。
 *
 * 本程序真实调用被测库 API（R34），不依赖任何外部数据文件：
 *   1. 从零构建 MNX 文档：mnx 元数据 / global measures / part / layout / score
 *   2. 调用 validation::schemaValidate()，该路径经由 json-schema-validator
 *      校验内嵌于库中的 MNX JSON schema（证明传递依赖接线正确）
 *   3. doc.save() 落盘，再用 Document::create() 重新加载并再次校验
 *
 * 全部检查通过后返回 0，否则返回 1。
 */
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <string>

#include "mnxdom/mnxdom.h"

namespace {

int g_checks = 0;
int g_failures = 0;

void check(bool ok, const std::string& what)
{
    ++g_checks;
    if (ok) {
        std::cout << "ok   - " << what << std::endl;
    } else {
        ++g_failures;
        std::cerr << "FAIL - " << what << std::endl;
    }
}

std::filesystem::path workDir()
{
    const char* tmp = std::getenv("TMPDIR");
    std::filesystem::path dir =
        (tmp && *tmp) ? std::filesystem::path(tmp) : std::filesystem::temp_directory_path();
    dir /= "mnxdom-test-package";
    std::filesystem::create_directories(dir);
    return dir;
}

} // namespace

int main()
{
    using namespace mnx;

    // ── 1. 从零构建文档（Document 默认构造即补全必需子节点）──
    Document doc;
    check(static_cast<bool>(validation::schemaValidate(doc)),
          "fresh Document passes MNX schema validation");
    check(doc.mnx().version() > 0, "Document carries the MNX schema version");

    constexpr int kNumMeasures = 3;
    for (int i = 0; i < kNumMeasures; ++i) {
        auto measure = doc.global().measures().append();
        measure.set_id("m" + std::to_string(i + 1));
    }
    check(doc.global().measures().size() == static_cast<std::size_t>(kNumMeasures),
          "global measures appended");
    check(doc.global().measures()[0].id() == "m1", "measure id round trips");

    // ── 2. part + measures ──
    auto part = doc.parts().append();
    auto partMeasures = part.create_measures();
    partMeasures.append();
    check(doc.parts().size() == 1u, "part appended");
    check(static_cast<bool>(validation::schemaValidate(doc)),
          "document with a part passes schema validation");

    // ── 3. layout + staff ──
    auto layouts = doc.ensure_layouts();
    layouts.append();
    auto layout = layouts[0];
    layout.set_id("layout0");
    auto staff = layout.content().append<layout::Staff>();
    staff.set_symbol(LayoutSymbol::Bracket);
    check(staff.symbol() == LayoutSymbol::Bracket, "layout staff symbol round trips");

    // ── 4. score / page / system / layout change ──
    auto score = doc.ensure_scores().append("Full Score");
    auto page = score.ensure_pages().append();
    auto system = page.systems().append("m1");
    check(system.measure() == "m1", "system measure reference round trips");

    auto layoutChange = system.ensure_layoutChanges().append("layout0", "m2", FractionValue(3, 8));
    auto fraction = layoutChange.location().position().fraction();
    check(fraction.numerator() == 3u && fraction.denominator() == 8u,
          "fraction payload round trips");
    check(layoutChange.layout() == "layout0", "layout change references the layout");

    // ── 5. 组合后的文档仍需通过 schema 校验 ──
    check(static_cast<bool>(validation::schemaValidate(doc)),
          "composed document passes schema validation");

    // ── 6. 落盘 / 重新加载 ──
    const auto outFile = workDir() / "consumer-smoke.json";
    std::filesystem::remove(outFile);
    doc.save(outFile, 4);
    check(std::filesystem::exists(outFile) && std::filesystem::file_size(outFile) > 0,
          "doc.save() wrote a non-empty JSON file");

    auto reloaded = Document::create(outFile);
    check(reloaded.global().measures().size() == static_cast<std::size_t>(kNumMeasures),
          "reloaded document keeps the global measures");
    check(reloaded.parts().size() == 1u, "reloaded document keeps the part");
    check(static_cast<bool>(validation::schemaValidate(reloaded)),
          "reloaded document passes schema validation");

    std::cout << "mnxdom test_package: " << (g_checks - g_failures) << "/" << g_checks
              << " checks passed" << std::endl;
    return g_failures == 0 ? 0 : 1;
}
