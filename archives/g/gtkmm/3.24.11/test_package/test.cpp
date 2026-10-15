// test.cpp — gtkmm 3.24.11 消费者测试 (Conan L1, R34)
// 实质调用 gtkmm/gdkmm API 且不依赖显示服务器（OHOS 上 GTK+3 为 Broadway-only，
// gtk_init() 在无窗口环境下不可用——上游 15 个测试程序中只有 2 个注册为
// meson test()，其中一个 object_move 需要 gtk_init）。
// 本测试使用与上游 gdk_rgba_test 同款的无显示路径：Gdk::RGBA / Gdk::Rectangle
// 颜色与矩形运算 + sigc++-2.0 信号连接 + GType 注册（Gtk::Button）。
// 任一声明失败返回非 0。
#include <gtkmm.h>
#include <gdkmm.h>
#include <sigc++/sigc++.h>

#include <cstdio>

namespace {

int g_checks = 0;

bool check(bool condition, const char* what)
{
  ++g_checks;
  if (!condition)
    std::fprintf(stderr, "FAIL: %s\n", what);
  return condition;
}

void on_clicked()
{
  // 信号回调：仅验证 sigc++ 连接可用，不触发 UI。
}

} // namespace

int main()
{
  bool ok = true;

  // 0. 版本绑定：确认链接到的是 gtkmm-3.0 ABI（3.24.11）。
  ok &= check(GTKMM_MAJOR_VERSION == 3 && GTKMM_MINOR_VERSION == 24,
              "GTKMM_MAJOR/MINOR_VERSION == 3.24");
  ok &= check(GTKMM_MICRO_VERSION == 11, "GTKMM_MICRO_VERSION == 11");

  // 1. Gdk::RGBA —— 颜色构造 + 分量读取（gdkmm 公开 API，
  //    与上游 gdk_rgba_test 同路径，不依赖显示）。
  Gdk::RGBA rgba;
  rgba.set_rgba_u(0xFFFF, 0x0000, 0x0000, 0xFFFF);
  ok &= check(rgba.get_red_u() == 0xFFFF, "Gdk::RGBA red_u");
  ok &= check(rgba.get_green_u() == 0x0000, "Gdk::RGBA green_u");
  ok &= check(rgba.get_blue_u() == 0x0000, "Gdk::RGBA blue_u");
  ok &= check(rgba.get_alpha_u() == 0xFFFF, "Gdk::RGBA alpha_u");

  // 2. Gdk::Rectangle —— 矩形构造 + 尺寸 + 求交（gdkmm 公开 API，无显示依赖）。
  Gdk::Rectangle r1(0, 0, 100, 50);
  Gdk::Rectangle r2(50, 25, 100, 100);
  ok &= check(r1.get_x() == 0 && r1.get_y() == 0 && r1.get_width() == 100 &&
              r1.get_height() == 50, "Gdk::Rectangle geometry");
  Gdk::Rectangle inter = r1.intersect(r2);
  ok &= check(inter.get_width() == 50 && inter.get_height() == 25,
              "Gdk::Rectangle intersect");

  // 3. Gtkmm GType 包装层 —— 只做 GType 注册，不需要显示服务器。
  ok &= check(Gtk::Button::get_type() != 0, "Gtk::Button::get_type");
  ok &= check(g_type_is_a(Gtk::Button::get_type(), GTK_TYPE_WIDGET),
              "Gtk::Button is-a GtkWidget");

  // 4. sigc++-2.0 信号连接（libsigc-2.0 真实使用，ABI 与被测包一致）。
  sigc::signal<void()> sig;
  sigc::connection conn = sig.connect(sigc::ptr_fun(&on_clicked));
  ok &= check(conn.connected(), "sigc++-2.0 signal connection");
  sig.emit();
  conn.disconnect();

  std::printf("gtkmm-3.0 probe: checks=%d %s\n", g_checks, ok ? "PASS" : "FAIL");
  return ok ? 0 : 1;
}
