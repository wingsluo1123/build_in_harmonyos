// test_package/test_layer.cpp
//
// 真实消费者测试：用 vkroots 的公开 API 定义一个最小 Vulkan layer。
// 本文件不是空壳——它使用了 vkroots 的核心接口：
//   * vkroots.h 头文件本身（VKROOTS_VERSION_* 版本宏）
//   * vkroots::VkDeviceDispatch（dispatch 表类型）
//   * vkroots::NoOverrides（未覆盖层的占位类型）
//   * VKROOTS_DEFINE_LAYER_INTERFACES 宏（生成 layer 的对外入口）
// 编译产物是可被 Vulkan loader 加载的模块；若被测包缺失，编译必然失败
// （CI L1e 破坏性反向验证：移走 include/ 后本文件无法编译）。
#include <vkroots.h>

#include <cstdio>

// 版本宏来自被测头文件——若头文件未正确安装/被替换，此处编译期即失败
static_assert(VKROOTS_VERSION_MAJOR == 0, "unexpected vkroots major version");

namespace ConsumerTestLayer {

class VkDeviceOverrides {
public:
    static VkResult CreateImage(
        const vkroots::VkDeviceDispatch *pDispatch,
              VkDevice                   device,
        const VkImageCreateInfo         *pCreateInfo,
        const VkAllocationCallbacks     *pAllocator,
              VkImage                   *pImage) {
        std::printf("vkroots consumer test layer: intercepting vkCreateImage\n");
        return pDispatch->CreateImage(device, pCreateInfo, pAllocator, pImage);
    }
};

} // namespace ConsumerTestLayer

// 生成 layer 的对外入口（vkNegotiateLoaderLayerInterfaceVersion 等）
VKROOTS_DEFINE_LAYER_INTERFACES(vkroots::NoOverrides,
                                vkroots::NoOverrides,
                                ConsumerTestLayer::VkDeviceOverrides);
