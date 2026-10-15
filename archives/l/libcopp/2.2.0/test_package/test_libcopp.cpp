// Conan test_package — libcopp 2.2.0
//
// 真实执行一次协程上下文切换：create -> start ->（runner 内 yield）-> resume ->
// 取返回码。这条路径**必须**经过打包进来的 fcontext 汇编（arm64/aapcs/elf/gas），
// 因此它同时验证了「打包产物里确实是 arm64 上下文切换汇编、且能在 OHOS 上真的切换」。
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include <libcopp/coroutine/coroutine_context_container.h>

class probe_runner {
 public:
  int operator()(void*) {
    copp::coroutine_context_default* self = copp::this_coroutine::get<copp::coroutine_context_default>();
    if (nullptr == self) {
      std::fputs("LIBCOPP_TEST FAIL: this_coroutine::get returned null\n", stderr);
      std::exit(2);
    }
    std::fputs("LIBCOPP_STEP inside-runner\n", stdout);
    std::fflush(stdout);
    self->yield();
    std::fputs("LIBCOPP_STEP resumed\n", stdout);
    std::fflush(stdout);
    return 42;
  }
};

int main() {
  copp::coroutine_context_default::ptr_t co = copp::coroutine_context_default::create(probe_runner());
  if (!co) {
    std::fputs("LIBCOPP_TEST FAIL: create returned null\n", stderr);
    return 2;
  }
  std::fputs("LIBCOPP_STEP created\n", stdout);
  std::fflush(stdout);

  co->start();
  std::fputs("LIBCOPP_STEP started-and-yielded\n", stdout);
  std::fflush(stdout);

  co->resume();
  std::fputs("LIBCOPP_STEP finished\n", stdout);
  std::fflush(stdout);

  int ret = co->get_ret_code();
  if (42 != ret) {
    std::fprintf(stderr, "LIBCOPP_TEST FAIL: ret_code=%d expect=42\n", ret);
    return 3;
  }

  std::fputs("LIBCOPP_TEST PASSED\n", stdout);
  return 0;
}
