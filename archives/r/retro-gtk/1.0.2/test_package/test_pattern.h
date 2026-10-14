/* test_pattern.h — 假核心与消费者共享的帧内容契约。
 *
 * 两端口径必须一致：test_core.c 按 test_frame_pixel() 生成 RGB565 帧，
 * consumer.c 按同一期望值校验 libretro-gtk 传回来的 pixdata。这样"视频输出"
 * 链路（核心 → retro-runner → 共享内存帧缓冲 → RetroPixdata → GdkPixbuf）
 * 的字节内容就是可断言的确定性契约。
 */
#pragma once

#include <stdint.h>

#define TEST_WIDTH 320
#define TEST_HEIGHT 240
#define TEST_FPS 60.0
#define TEST_SAMPLE_RATE 30000.0

static inline uint16_t
test_pattern_pixel (unsigned x,
                    unsigned y)
{
  unsigned r = (x * 31u) / (TEST_WIDTH - 1);
  unsigned g = (y * 63u) / (TEST_HEIGHT - 1);
  unsigned b = (x + y) % 32u;

  return (uint16_t) ((r << 11) | (g << 5) | b);
}

/* 帧号进入蓝色分量低位：既保持可复算，又能断言"换帧确实生效"。 */
static inline uint16_t
test_frame_pixel (unsigned frame,
                  unsigned x,
                  unsigned y)
{
  uint16_t pixel = test_pattern_pixel (x, y);

  return (uint16_t) ((pixel & ~0x1fu) | ((pixel + frame) & 0x1fu));
}

/* RGB565 → RGB888 的位复制展开（gdk-pixbuf 对 565 的标准展开方式）。 */
static inline void
test_rgb565_to_rgb8 (uint16_t  pixel,
                     uint8_t  *r,
                     uint8_t  *g,
                     uint8_t  *b)
{
  unsigned r5 = (pixel >> 11) & 0x1f;
  unsigned g6 = (pixel >> 5) & 0x3f;
  unsigned b5 = pixel & 0x1f;

  *r = (uint8_t) ((r5 << 3) | (r5 >> 2));
  *g = (uint8_t) ((g6 << 2) | (g6 >> 4));
  *b = (uint8_t) ((b5 << 3) | (b5 >> 2));
}

/* RGB888 → RGB565 量化（用于把读回的像素与期望值按 565 精度比较，
   避免不同 GdkPixbuf 版本在展开时的舍入差异造成假失败）。 */
static inline uint16_t
test_rgb8_to_rgb565 (unsigned r,
                     unsigned g,
                     unsigned b)
{
  return (uint16_t) (((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3));
}
