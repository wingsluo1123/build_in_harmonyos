// 消费者视角测试（R34：必须实质调用被测包 API）：
//   1) 编译期校验 lsp-r3d-iface 版本宏；
//   2) 运行期实调 builtin.h 的 Factory 注册/枚举机制 —— 这是本包除纯类型定义外
//      唯一的运行期逻辑（Factory 构造时注册、析构时摘链、enumerate 顺序遍历），
//      可真实验证静态库产物可用；
//   3) 顺带校验 backend_metadata_t/factory_t 结构布局在头文件与库之间一致
//      （消费者自定义 factory 传给库内 enumerate 后取回指针应保持同一地址）。
#include <lsp-plug.in/r3d/iface/backend.h>
#include <lsp-plug.in/r3d/iface/builtin.h>
#include <lsp-plug.in/r3d/iface/factory.h>
#include <lsp-plug.in/r3d/iface/types.h>
#include <lsp-plug.in/r3d/iface/version.h>

#include <cstdio>
#include <cstdlib>

#if (LSP_R3D_IFACE_MAJOR != 1) || (LSP_R3D_IFACE_MINOR != 0) || (LSP_R3D_IFACE_MICRO != 31)
#error "lsp-r3d-iface version mismatch: expected 1.0.31"
#endif

namespace
{
    using namespace lsp;
    // r3d 的类型/枚举/工厂都在 lsp::r3d 命名空间
    using namespace lsp::r3d;

    int                 metadata_calls   = 0;
    int                 create_calls     = 0;
    backend_t           sink_backend;

    const backend_metadata_t *probe_metadata(factory_t *_this, size_t id)
    {
        ++metadata_calls;
        // 本用例只提供 0 号后端：其余 id 一律返回 NULL（上游契约）
        return (id == 0) ? reinterpret_cast<const backend_metadata_t *>(_this) : NULL;
    }

    backend_t *probe_create(factory_t *_this, size_t id)
    {
        ++create_calls;
        return (id == 0) ? &sink_backend : NULL;
    }

    factory_t           probe_factory =
    {
        &probe_metadata,
        &probe_create
    };

    // 通过上游宏注册（等价于静态构造期注册）
    LSP_R3D_BUILTIN_FACTORY(probe_registration, &probe_factory)

    int count_factories()
    {
        int                 n = 0;
        for (r3d::Factory *f = r3d::Factory::list(); f != NULL; f = f->next())
            ++n;
        return n;
    }
} /* namespace */

int main()
{
    std::printf("lsp-r3d-iface %d.%d.%d\n",
        LSP_R3D_IFACE_MAJOR, LSP_R3D_IFACE_MINOR, LSP_R3D_IFACE_MICRO);

    // 枚举契约：本用例注册的 factory 位于索引 0，1 号起为 NULL
    factory_t *got = r3d::Factory::enumerate(0);
    if (got != &probe_factory)
    {
        std::printf("FAIL: enumerate(0) returned %p, expected %p\n",
            static_cast<void *>(got), static_cast<void *>(&probe_factory));
        return 1;
    }
    if (r3d::Factory::enumerate(1) != NULL)
    {
        std::printf("FAIL: enumerate(1) should be NULL\n");
        return 2;
    }

    // 通过枚举到的 factory 实调 metadata/create（真实走函数指针表）
    const backend_metadata_t *md = got->metadata(got, 0);
    if (md != reinterpret_cast<const backend_metadata_t *>(got))
        return 3;
    if (got->metadata(got, 1) != NULL)
        return 4;
    if (got->create(got, 0) != &sink_backend)
        return 5;
    if (got->create(got, 1) != NULL)
        return 6;
    if (metadata_calls != 2 || create_calls != 2)
    {
        std::printf("FAIL: call counts metadata=%d create=%d\n", metadata_calls, create_calls);
        return 7;
    }

    // 注册链表非空且包含本用例注册的 factory
    if (count_factories() < 1)
        return 8;

    // 结构布局自洽：枚举值与上游头文件一致（消费者与库对同一布局编译）
    if (static_cast<int>(WND_HANDLE_X11) != 1 || static_cast<int>(PIXEL_RGBA) != 0)
        return 9;

    std::puts("consumer checks passed");
    return 0;
}
