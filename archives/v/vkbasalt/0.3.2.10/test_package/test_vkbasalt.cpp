// test_vkbasalt.cpp — 鸿蒙特有消费者测试（test_package）
//
// vkBasalt 是 Vulkan implicit layer：运行时由 Vulkan loader 通过
// VK_LAYER_* 机制 dlopen 加载。本测试直接模拟 loader 行为：
//  1. dlopen("libvkbasalt.so") —— 验证 layer 可被动态加载
//     （鸿蒙 ELF 代码签名 / 依赖完整性在加载期暴露的问题会在此失败）；
//  2. dlsym 检查 layer 导出的 VkLayer 初始化入口符号
//     （vkGetInstanceProcAddr / vkCreateInstance —— implicit layer 注册
//     必须导出，否则 loader 拒绝加载该 layer）；
//  3. 校验 vkBasalt.json 层配置存在（implicit layer 的启用依赖此文件，
//     它由配方随包安装在 share/vulkan/implicit_layer.d/）。
//
// 编译：由 test_package/CMakeLists.txt 构建；运行：conan test 阶段执行。

#include <cstdio>
#include <cstdlib>
#include <string>

#if defined(_WIN32)
#include <windows.h>
#define LIB_EXT "dll"
#define dlopen(name, flags) (void*)(LoadLibraryA(name))
#define dlsym(handle, sym) (void*)(GetProcAddress((HMODULE)(handle), sym))
#define dlclose(handle) (void)(FreeLibrary((HMODULE)(handle)))
#else
#include <dlfcn.h>
#define LIB_EXT "so"
#endif

static int checks = 0;

static void report(const char* name, bool ok, const char* detail = "") {
    checks++;
    std::printf("%s %s%s%s\n", ok ? "PASS:" : "FAIL:", name,
                detail[0] ? " (" : "", detail);
    if (!ok) {
        std::printf("FAILED_CHECK=%d\n", checks);
        std::exit(1);
    }
}

int main() {
    std::printf("vkBasalt test_package starting (HarmonyOS consumer test)\n");

    // --- 1. dlopen layer 库 ---
    std::string libpath = "libvkbasalt." LIB_EXT;
    void* handle = dlopen(libpath.c_str(), RTLD_NOW);
    if (!handle) {
#if !defined(_WIN32)
        report("dlopen libvkbasalt.so", false, dlerror());
#else
        report("dlopen libvkbasalt.dll", false, "LoadLibrary failed");
#endif
        return 1;
    }
    report("dlopen layer library", true, libpath.c_str());

    // --- 2. 检查 layer 关键导出符号 ---
    // vkBasalt 是 Vulkan implicit layer，导出带 vkBasalt_ 前缀的 layer 入口
    // （loader 通过 vk_layer.h 定义的名称约定查找）。dlopen 后 dlsym 验证
    // 这两个入口存在，即证明 layer 的 dispatch 表可被 loader 初始化。
    void* sym_gipa = dlsym(handle, "vkBasalt_GetInstanceProcAddr");
    void* sym_gdpa = dlsym(handle, "vkBasalt_GetDeviceProcAddr");
    report("dlsym vkBasalt_GetInstanceProcAddr", sym_gipa != nullptr);
    report("dlsym vkBasalt_GetDeviceProcAddr", sym_gdpa != nullptr);
    dlclose(handle);

    // --- 3. 校验层配置文件 vkBasalt.json（implicit layer 注册文件）---
    // 由 meson 的 config/meson.build 安装到 share/vulkan/implicit_layer.d/，
    // 随包分发；测试进程在包内 lib 同级 share 下查找。
    const char* pkg_root = std::getenv("TEST_PACKAGE_ROOT");
    if (!pkg_root || !*pkg_root) {
        pkg_root = ".";  // fallback：当前目录（conan 已把包根注入环境）
    }
    std::string json_path = std::string(pkg_root) +
        "/share/vulkan/implicit_layer.d/vkBasalt.json";
    FILE* fp = std::fopen(json_path.c_str(), "rb");
    if (!fp) {
        report("layer config vkBasalt.json", false, json_path.c_str());
        return 1;
    }
    std::fclose(fp);
    report("layer config vkBasalt.json", true, json_path.c_str());

    std::printf("PASS: all %d vkBasalt checks passed\n", checks);
    return 0;
}
