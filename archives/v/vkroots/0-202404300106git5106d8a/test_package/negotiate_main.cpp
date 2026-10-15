// test_package/negotiate_main.cpp
//
// 完整消费者用例（端到端）：在 OHOS 上真实**运行** vkroots 生成的 layer 协商流程。
//
// 与「dlopen 外部 .so」的方式不同，本用例把 layer 定义与协商调用放在同一个可执行
// 文件内，因此不需要加载外部共享库、不需要 Vulkan loader、不需要 GPU —— 在 CI worker
// 的安全策略下也能实际执行（dlopen 本地新构建 .so 会被该策略拒绝，见 MANIFEST.yml）。
//
// 真实执行的功能/流程（非纯断言）：
//   1) 用 vkroots 公开 API 定义一个最小 layer（VKROOTS_DEFINE_LAYER_INTERFACES）
//   2) 按 vulkan/vk_layer.h 的契约构造 VkNegotiateLayerInterface
//   3) 调用 vkroots 生成的协商入口 vkNegotiateLoaderLayerInterfaceVersion
//   4) 校验返回 VK_SUCCESS 且交回的两个过程地址非空（证明 layer 接口运行期可用）
#include <vkroots.h>

#include <cstdio>

namespace ConsumerE2ELayer {

class VkDeviceOverrides {
public:
    static VkResult CreateImage(
        const vkroots::VkDeviceDispatch *pDispatch,
              VkDevice                   device,
        const VkImageCreateInfo         *pCreateInfo,
        const VkAllocationCallbacks     *pAllocator,
              VkImage                   *pImage) {
        return pDispatch->CreateImage(device, pCreateInfo, pAllocator, pImage);
    }
};

} // namespace ConsumerE2ELayer

VKROOTS_DEFINE_LAYER_INTERFACES(vkroots::NoOverrides,
                                vkroots::NoOverrides,
                                ConsumerE2ELayer::VkDeviceOverrides);

int main() {
    VkNegotiateLayerInterface nli{};
    nli.sType = LAYER_NEGOTIATE_INTERFACE_STRUCT;
    nli.pNext = nullptr;
    nli.loaderLayerInterfaceVersion = 2; // 请求 loader 接口 v2（vkroots 采用 v2 协商）

    const VkResult rc = vkNegotiateLoaderLayerInterfaceVersion(&nli);
    std::printf("[e2e] vkNegotiateLoaderLayerInterfaceVersion rc=%d (0=VK_SUCCESS)\n",
                static_cast<int>(rc));

    if (rc != VK_SUCCESS) {
        std::printf("FAIL: negotiation returned %d\n", static_cast<int>(rc));
        return 1;
    }
    if (nli.pfnGetInstanceProcAddr == nullptr || nli.pfnGetDeviceProcAddr == nullptr) {
        std::printf("FAIL: negotiation did not provide procs (gipa=%p gdpa=%p)\n",
                    reinterpret_cast<void *>(nli.pfnGetInstanceProcAddr),
                    reinterpret_cast<void *>(nli.pfnGetDeviceProcAddr));
        return 1;
    }

    std::printf("[e2e] pfnGetInstanceProcAddr=%p pfnGetDeviceProcAddr=%p\n",
                reinterpret_cast<void *>(nli.pfnGetInstanceProcAddr),
                reinterpret_cast<void *>(nli.pfnGetDeviceProcAddr));
    std::printf("OK: vkroots end-to-end negotiation passed\n");
    return 0;
}
