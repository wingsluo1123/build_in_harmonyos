// test_juce — HarmonyOS 消费者验证程序
// 仅使用 juce 包安装/导出的公开头文件与公开 API (juce::String), 编译链接并运行,
// 验证第三方使用者能否在 OHOS 目标上调用 JUCE 公开 API 并得到可观察结果。
#include <juce_core/juce_core.h>

int main()
{
    juce::String s ("Hello, HarmonyOS JUCE!");
    juce::String upper = s.toUpperCase();

    // 公开 API 调用: String::toUpperCase + String::contains, 结果可观察
    const bool ok = upper.contains ("HARMONYOS") && upper.contains ("JUCE");
    juce::Logger::outputDebugString (upper);

    return ok ? 0 : 1;
}
