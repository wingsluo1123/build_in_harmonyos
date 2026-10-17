// apt-pkg 2.7.14 — test_package 消费者测试（真实调用 libapt-pkg API）
//
// 覆盖 R34 要求：
//   * 调用真实公共 API：pkgInitConfig / pkgInitSystem / pkgCacheFile / debVS / _error
//   * 含鸿蒙（OHOS）特有断言：__OHOS__ 分支验证 APT::Architecture == "arm64"
//     （依赖 0009 补丁内嵌的 dpkg 架构表；无 /usr/share/dpkg 也能正确映射）
//
// 编译：C++17；链接 libapt-pkg（静态）+ 各 conan 依赖库。
#include <apt-pkg/cachefile.h>
#include <apt-pkg/configuration.h>
#include <apt-pkg/debversion.h>
#include <apt-pkg/error.h>
#include <apt-pkg/init.h>
#include <apt-pkg/pkgsystem.h>
#include <apt-pkg/strutl.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <unistd.h>

static int failures = 0;

#define CHECK(cond, msg)                                                            \
   do {                                                                             \
      if (cond) {                                                                   \
         std::printf("  [PASS] %s\n", msg);                                         \
      } else {                                                                      \
         std::printf("  [FAIL] %s\n", msg);                                         \
         ++failures;                                                                \
      }                                                                             \
   } while (0)

int main(int argc, char **argv)
{
   (void)argc; (void)argv;
   std::printf("apt-pkg test_package consumer test\n");

   // ── 1. 配置初始化（真实 API） ──────────────────────────────
   bool ok = pkgInitConfig(*_config);
   CHECK(ok, "pkgInitConfig() 成功");

   std::string arch = _config->Find("APT::Architecture");
   CHECK(!arch.empty(), "APT::Architecture 非空");
   std::printf("       APT::Architecture = \"%s\"\n", arch.c_str());

#ifdef __OHOS__
   // ── 鸿蒙特有断言：OHOS 交叉目标为 aarch64，应映射为 deb 架构 "arm64" ──
   // 验证 0009 补丁内嵌的 dpkg 架构表在无 /usr/share/dpkg 时仍生效。
   CHECK(arch == "arm64", "__OHOS__: APT::Architecture 映射为 arm64 (内嵌架构表)");
   std::printf("       __OHOS__ defined, host arch check executed\n");
#else
   std::printf("       (非 OHOS 平台，跳过 arm64 特有断言)\n");
#endif

   // ── 2. 包系统初始化（真实 API，上游原貌） ─────────────────────
   // 上游 pkgInitSystem(Configuration&, pkgSystem *&Sys) 第二参数是“指针的
   // 引用”；apt-get/apt-cache 等二进制都直接把全局 _system 传入，函数内部
   // Sys = pkgSystem::GlobalList[I] 经引用写回全局 _system。若传局部变量，
   // 全局 _system 仍为 0，随后 pkgCacheFile 全链路会在 pkgcachegen.cc
   // MakeStatusCache() 里 _system->AddStatusFiles() 空指针 SIGSEGV
   // （实测 probe5：BuildCaches+0xcc）。故此处必须传全局 _system。
   ok = pkgInitSystem(*_config, _system);
   CHECK(ok, "pkgInitSystem() 成功");
   CHECK(_system != nullptr, "pkgInitSystem 设置全局 _system");
   if (_system != nullptr)
   {
      std::string label = _system->Label != nullptr ? _system->Label : "";
      CHECK(!label.empty(), "pkgSystem::Label 非空");
      std::printf("       system label = \"%s\"\n", label.c_str());
   }

   // ── 3. 版本比较（真实 API：debVS） ─────────────────────────
   CHECK(debVS.CmpVersion("1.0-1", "1.0.1") < 0, "debVS: 1.0-1 < 1.0.1");
   CHECK(debVS.CmpVersion("1.0.1", "1.0-1") > 0, "debVS: 1.0.1 > 1.0-1");
   CHECK(debVS.CmpVersion("1:2.0", "10") > 0, "debVS: 1:2.0 > 10 (epoch 生效)");
   CHECK(debVS.CmpVersion("1.0", "1.0") == 0, "debVS: 1.0 == 1.0");

   // ── 4. 字符串工具（真实 API） ──────────────────────────────
   CHECK(APT::String::Strip("  hello  ") == "hello", "String::Strip 去除空白");

   // ── 5. 缓存文件（真实 API：pkgCacheFile 全链路） ────────────
   // 构造一个空 dpkg status 文件，让缓存生成链路真实跑一遍：
   // pkgCacheFile::GetPkgCache() -> BuildCaches -> pkgCacheGenerator
   std::string tmpdir = "/storage/Users/currentUser";
   std::string status = tmpdir + "/apt-testpkg-status.XXXXXX";
   char *statusbuf = new char[status.size() + 1];
   std::snprintf(statusbuf, status.size() + 1, "%s", status.c_str());
   int fd = mkstemp(statusbuf);
   CHECK(fd >= 0, "mkstemp 创建空 status 文件");
   if (fd >= 0)
   {
      close(fd);
      _config->Set("Dir::State::status", statusbuf);
      // 把 cache/lists/sources 指到可写临时目录，避免触碰 OHOS 只读 rootfs
      _config->Set("Dir::Cache", tmpdir + "/apt-testpkg-cache/");
      _config->Set("Dir::State::lists", tmpdir + "/apt-testpkg-lists/");
      _config->Set("Dir::Etc::sourcelist", "/dev/null");
      _config->Set("Dir::Etc::sourceparts", "/dev/null");
      // 清理可能的遗留 cache，避免旧缓存干扰
      pkgCacheFile::RemoveCaches();

      pkgCacheFile Cache;
      pkgCache *C = Cache.GetPkgCache();
      CHECK(C != nullptr, "pkgCacheFile::GetPkgCache() 构建出缓存");
      if (C != nullptr)
      {
         std::printf("       cache Header.PackageCount = %u\n",
                     static_cast<unsigned>(C->HeaderP->PackageCount));
         CHECK(C->HeaderP->PackageCount == 0u, "空 status 文件 => 0 个包");
      }
      else
      {
         std::printf("       (GetPkgCache 失败，错误栈: %d 条)\n",
                     _error->PendingError() ? 1 : 0);
      }
      pkgCacheFile::RemoveCaches();
      std::remove(statusbuf);
   }
   delete[] statusbuf;

   // ── 6. 错误栈清理验证 ─────────────────────────────────────
   _error->Discard();

   std::printf("apt-pkg test_package: %s (%d failures)\n",
               failures == 0 ? "OK" : "FAILED", failures);
   return failures == 0 ? 0 : 1;
}
