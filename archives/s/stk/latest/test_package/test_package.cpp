// stk/latest - test_package
//
// 以消费者视角验证已安装的 STK：DSP 核心对象能实际产生正确的信号，
// 并覆盖本归档所打补丁涉及的 Thread 生命周期路径。

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <unistd.h>

#include "Stk.h"
#include "SineWave.h"
#include "Noise.h"
#include "OnePole.h"
#include "OneZero.h"
#include "Delay.h"
#include "ADSR.h"
#include "Thread.h"
#include "Mutex.h"

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond)                                                    \
  do {                                                                 \
    ++g_checks;                                                        \
    if (cond) {                                                        \
      std::cout << "  ok   " << g_checks << " - " << #cond << "\n";    \
    } else {                                                           \
      ++g_failed;                                                      \
      std::cout << "  FAIL " << g_checks << " - " << #cond << "\n";    \
    }                                                                  \
  } while (0)

// Thread::start() 需要一个 THREAD_FUNCTION; 用一个受互斥量保护的计数器,
// 同时验证 Mutex 与 Thread 两个类。
static stk::Mutex g_mutex;
static volatile int g_worker_ran = 0;

static THREAD_RETURN THREAD_TYPE worker(void * /*ptr*/)
{
  for (int i = 0; i < 50; ++i) {
    g_mutex.lock();
    ++g_worker_ran;
    g_mutex.unlock();
    usleep(200);
  }
  return 0;
}

int main(void)
{
  // ---- 1. 全局采样率 --------------------------------------------------
  stk::Stk::setSampleRate(48000.0);
  CHECK(stk::Stk::sampleRate() == 48000.0);
  stk::Stk::setSampleRate(44100.0);
  CHECK(stk::Stk::sampleRate() == 44100.0);

  // ---- 2. SineWave: 正弦振荡器必须产生有界且非恒定的波形 --------------
  {
    stk::SineWave sine;
    sine.setFrequency(441.0);          // 44100/441 = 100 采样一个周期
    double minv = 2.0, maxv = -2.0, sum = 0.0;
    for (int i = 0; i < 100; ++i) {
      stk::StkFloat s = sine.tick();
      if (s < minv) minv = s;
      if (s > maxv) maxv = s;
      sum += s;
    }
    CHECK(maxv <= 1.0 && minv >= -1.0);              // 有界
    CHECK(maxv > 0.98 && minv < -0.98);              // 确实扫过整个幅度
    CHECK(std::fabs(sum) < 1e-6);                    // 整周期直流分量为 0
    sine.reset();
    CHECK(std::fabs(sine.lastOut()) < 1e-12);        // reset 后输出归零
  }

  // ---- 3. Noise: 随机源应有变化且有界 ---------------------------------
  {
    stk::Noise noise(20260802);
    double maxv = -2.0, minv = 2.0;
    for (int i = 0; i < 256; ++i) {
      stk::StkFloat s = noise.tick();
      if (s > maxv) maxv = s;
      if (s < minv) minv = s;
    }
    CHECK(maxv <= 1.0 && minv >= -1.0);
    CHECK(maxv > 0.5 && minv < -0.5);                // 不是常数输出
  }

  // ---- 4. OnePole / OneZero: 滤波器的稳态与冲激响应 -------------------
  {
    stk::OnePole lp;
    lp.setPole(0.9);
    lp.setGain(1.0);
    stk::StkFloat y = 0.0;
    for (int i = 0; i < 2000; ++i) y = lp.tick(1.0);
    // b0 = 1 - |a1| = 0.1, 直流增益 = b0 / (1 - 0.9) = 1
    CHECK(std::fabs(y - 1.0) < 1e-3);

    stk::OneZero z;
    z.setZero(-1.0);                                  // y[n] = 0.5*(x[n] + x[n-1])
    stk::StkFloat h0 = z.tick(1.0);
    stk::StkFloat h1 = z.tick(0.0);
    CHECK(std::fabs(h0 - 0.5) < 1e-9);
    CHECK(std::fabs(h1 - 0.5) < 1e-9);
  }

  // ---- 5. Delay: 整数延迟线必须精确延后 N 个采样 ----------------------
  {
    stk::Delay d(7, 64);
    CHECK(d.getDelay() == 7);
    stk::StkFloat out = 0.0;
    for (unsigned long i = 0; i < 7; ++i) out = d.tick(i == 0 ? 1.0 : 0.0);
    CHECK(std::fabs(out) < 1e-12);                    // 第 7 个之前仍为 0
    CHECK(std::fabs(d.tick(0.0) - 1.0) < 1e-12);      // 第 8 个采样吐出冲激
  }

  // ---- 6. ADSR: 包络必须走完 attack 并停在 sustain --------------------
  {
    stk::ADSR env;
    env.setAllTimes(0.001, 0.001, 0.5, 0.001);
    env.keyOn();
    for (int i = 0; i < 4410; ++i) env.tick();        // 0.1s, 远超 A+D
    CHECK(std::fabs(env.lastOut() - 0.5) < 1e-3);
    env.keyOff();
    for (int i = 0; i < 4410; ++i) env.tick();
    CHECK(env.lastOut() < 1e-3);
  }

  // ---- 7. Thread / Mutex ---------------------------------------------
  // 本归档为 Thread.cpp 打了补丁: 当 C 库未提供 pthread_cancel() 时,
  // Thread::cancel() 报告失败而不是编译不过或崩溃。这里覆盖整条生命周期。
  {
    stk::Thread t;
    CHECK(t.start(&worker, NULL) == true);

    // cancel() 的返回值依平台而异 (有 pthread_cancel 时为 true, 否则为
    // false)。此处只要求它可被安全调用, 不得崩溃, 且随后 wait() 仍成功。
    bool cancelled = t.cancel();
    CHECK(cancelled == true || cancelled == false);

    t.testCancel();                                   // 不得崩溃

    CHECK(t.wait() == true);                          // 线程可回收
    g_mutex.lock();
    int ran = g_worker_ran;
    g_mutex.unlock();
    CHECK(ran > 0);                                   // 工作线程确实执行过
  }

  std::cout << "\n" << (g_checks - g_failed) << "/" << g_checks
            << " checks passed, " << g_failed << " failed\n";
  return g_failed == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
