/* consumer.c — retro-gtk 的消费者测试（R34：真实调用被测包 API，非空壳打印）。
 *
 * 流程完全走 libretro-gtk 的公开 API：
 *   retro_core_new() → 连接 "video-output" 信号 → retro_core_boot()
 *   → retro_core_iteration()（同步跑一帧并取回视频）
 * 其中 retro-runner 进程、私有 GDBus IPC、memfd 共享帧缓冲都由被测包内部驱动；
 * 帧内容按 test_pattern.h 的契约逐像素复算校验，并对整帧做 FNV-1a 校验和。
 *
 * 成功时打印一行机器可读结果（供 test_ohos.sh 断言）：
 *   RETRO_GTK_OHOS_CONSUMER_OK frames=%u geometry=%ux%u fps=%.2f checksum=0x%08x
 * 失败时退出码非 0（g_assert / 显式 return 1）。
 */
#define RETRO_GTK_USE_UNSTABLE_API

#include <retro-gtk.h>

#include "test_pattern.h"

#include <gdk-pixbuf/gdk-pixbuf.h>
#include <glib.h>
#include <stdio.h>

static RetroPixdata *captured = NULL;
static guint frames = 0;

static void
on_video_output (RetroCore    *core,
                 RetroPixdata *pixdata,
                 gpointer      user_data)
{
  (void) core;
  (void) user_data;

  if (pixdata == NULL)
    return;

  if (captured != NULL)
    retro_pixdata_free (captured);

  captured = retro_pixdata_copy (pixdata);
  frames++;
}

static guint32
expected_checksum (unsigned frame)
{
  guint32 sum = 2166136261u;

  for (unsigned y = 0; y < TEST_HEIGHT; y++)
    for (unsigned x = 0; x < TEST_WIDTH; x++) {
      uint8_t r, g, b;

      test_rgb565_to_rgb8 (test_frame_pixel (frame, x, y), &r, &g, &b);
      sum = (sum ^ r) * 16777619u;
      sum = (sum ^ g) * 16777619u;
      sum = (sum ^ b) * 16777619u;
    }

  return sum;
}

static guint32
pixbuf_checksum (GdkPixbuf *pixbuf)
{
  const guchar *pixels = gdk_pixbuf_get_pixels (pixbuf);
  int rowstride = gdk_pixbuf_get_rowstride (pixbuf);
  int channels = gdk_pixbuf_get_n_channels (pixbuf);
  guint32 sum = 2166136261u;

  for (int y = 0; y < TEST_HEIGHT; y++)
    for (int x = 0; x < TEST_WIDTH; x++) {
      const guchar *p = pixels + y * rowstride + x * channels;

      sum = (sum ^ p[0]) * 16777619u;
      sum = (sum ^ p[1]) * 16777619u;
      sum = (sum ^ p[2]) * 16777619u;
    }

  return sum;
}

static void
check_sample_pixels (GdkPixbuf *pixbuf,
                     unsigned   frame)
{
  const struct { unsigned x, y; } samples[] = {
    { 0, 0 }, { TEST_WIDTH - 1, 0 }, { 0, TEST_HEIGHT - 1 },
    { TEST_WIDTH - 1, TEST_HEIGHT - 1 }, { TEST_WIDTH / 2, TEST_HEIGHT / 2 },
  };
  const guchar *pixels = gdk_pixbuf_get_pixels (pixbuf);
  int rowstride = gdk_pixbuf_get_rowstride (pixbuf);
  int channels = gdk_pixbuf_get_n_channels (pixbuf);

  for (gsize i = 0; i < G_N_ELEMENTS (samples); i++) {
    const guchar *p = pixels + samples[i].y * rowstride + samples[i].x * channels;
    uint16_t expected = test_frame_pixel (frame, samples[i].x, samples[i].y);
    uint16_t actual = test_rgb8_to_rgb565 (p[0], p[1], p[2]);

    if (actual != expected) {
      g_printerr ("FAIL: pixel (%u,%u) frame %u: expected 0x%04x, got 0x%04x\n",
                  samples[i].x, samples[i].y, frame, expected, actual);
      exit (1);
    }
  }
}

int
main (int    argc,
      char **argv)
{
  g_autoptr(GError) error = NULL;
  RetroCore *core;
  GdkPixbuf *pixbuf;
  const gchar *core_path;
  gdouble fps;

  if (argc < 2) {
    g_printerr ("usage: %s <libretro-core.so>\n", argv[0]);

    return 2;
  }

  core_path = argv[1];

  /* RetroCore 拉起 retro-runner 时把 g_get_application_name() 作为进程参数
     （retro-runner 要求 argc>=3），因此使用方必须先设置应用名——上游由
     GTK/GApplication（或 g_test_init）顺带设置；纯 GLib 消费者需显式调用。 */
  g_set_application_name ("retro-gtk-ohos-consumer");

  core = retro_core_new (core_path);

  if (core == NULL) {
    g_printerr ("FAIL: retro_core_new() returned NULL\n");

    return 1;
  }

  g_signal_connect (core, "video-output", G_CALLBACK (on_video_output), NULL);

  retro_core_boot (core, &error);

  if (error != NULL) {
    g_printerr ("FAIL: retro_core_boot(): %s\n", error->message);

    return 1;
  }

  if (!retro_core_get_is_initiated (core)) {
    g_printerr ("FAIL: core is not initiated after boot\n");

    return 1;
  }

  if (retro_core_get_api_version (core) != 1) {
    g_printerr ("FAIL: core API version %u != 1\n",
                retro_core_get_api_version (core));

    return 1;
  }

  fps = retro_core_get_frames_per_second (core);
  if (fps < TEST_FPS - 0.01 || fps > TEST_FPS + 0.01) {
    g_printerr ("FAIL: frames per second %.4f != %.2f\n", fps, TEST_FPS);

    return 1;
  }

  /* 第一帧：核心的 retro_run() 把帧号推进到 1 */
  retro_core_iteration (core);

  if (frames != 1 || captured == NULL) {
    g_printerr ("FAIL: video-output not delivered (frames=%u)\n", frames);

    return 1;
  }

  if (retro_pixdata_get_width (captured) != TEST_WIDTH ||
      retro_pixdata_get_height (captured) != TEST_HEIGHT) {
    g_printerr ("FAIL: pixdata geometry %dx%d != %dx%d\n",
                retro_pixdata_get_width (captured),
                retro_pixdata_get_height (captured), TEST_WIDTH, TEST_HEIGHT);

    return 1;
  }

  pixbuf = retro_pixdata_to_pixbuf (captured);

  if (pixbuf == NULL) {
    g_printerr ("FAIL: retro_pixdata_to_pixbuf() returned NULL\n");

    return 1;
  }

  check_sample_pixels (pixbuf, 1);

  if (pixbuf_checksum (pixbuf) != expected_checksum (1)) {
    g_printerr ("FAIL: frame 1 checksum 0x%08x != expected 0x%08x\n",
                pixbuf_checksum (pixbuf), expected_checksum (1));

    return 1;
  }

  /* 再跑两帧：内容必须随帧号变化，且每帧仍与期望契约一致 */
  for (unsigned frame = 2; frame <= 3; frame++) {
    retro_core_iteration (core);

    g_object_unref (pixbuf);
    pixbuf = retro_pixdata_to_pixbuf (captured);

    if (pixbuf == NULL || pixbuf_checksum (pixbuf) != expected_checksum (frame)) {
      g_printerr ("FAIL: frame %u checksum mismatch\n", frame);

      return 1;
    }

    check_sample_pixels (pixbuf, frame);
  }

  if (frames != 3) {
    g_printerr ("FAIL: expected 3 video-output signals, got %u\n", frames);

    return 1;
  }

  printf ("RETRO_GTK_OHOS_CONSUMER_OK frames=%u geometry=%dx%d fps=%.2f "
          "frame=3 checksum=0x%08x\n",
          frames, TEST_WIDTH, TEST_HEIGHT, fps, pixbuf_checksum (pixbuf));

  g_object_unref (pixbuf);
  retro_pixdata_free (captured);
  retro_core_stop (core);
  g_object_unref (core);

  return 0;
}
