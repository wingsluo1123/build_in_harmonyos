// KB-NO-OPENGL 样例消费者：真调用被测包 API（非空壳断言）。
// 关键语义：门控 GL 代码后，无 GL 环境下的行为必须与「从未有 GL」一致——
// 即 prepareFrame() 保持默认 Upscaling 策略，且不触碰任何 GL 符号。
#include <noopengldemo/renderer.h>

#include <cstdio>

int main()
{
    noopengldemo::Renderer renderer;

    if (!renderer.prepareFrame()) {
        std::printf("FAIL: prepareFrame() returned false in a no-GL build\n");
        return 1;
    }

    if (renderer.scaling() != noopengldemo::Renderer::TextureScaling::Upscaling) {
        std::printf("FAIL: no-GL build must keep the Upscaling strategy\n");
        return 1;
    }

    std::printf("OK: no-GL build keeps the default scaling strategy (GL path skipped)\n");
    return 0;
}
