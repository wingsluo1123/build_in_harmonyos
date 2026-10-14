/* test_core.c — 供 test_package 使用的假 Libretro 核心（自写，非上游 retro-dummy 拷贝）。
 *
 * 它实现完整的 Libretro v1 核心入口（retro-runner 会逐个 dlsym 这 21 个符号），
 * 声明 RGB565 像素格式与 320x240@60fps 的 av_info，并按 test_pattern.h 的确定性
 * 图案填充帧缓冲——这样 libretro-gtk 的视频输出链路可以被逐字节断言。
 */
#include "libretro_abi.h"
#include "test_pattern.h"

#include <string.h>

static retro_environment_t environment_cb;
static retro_video_refresh_t video_cb;
static retro_audio_sample_t audio_cb;
static retro_audio_sample_batch_t audio_batch_cb;
static retro_input_poll_t input_poll_cb;
static retro_input_state_t input_state_cb;

static enum retro_pixel_format pixel_format = RETRO_PIXEL_FORMAT_RGB565;
static unsigned frame_number = 0;
static uint16_t frame_buffer[TEST_WIDTH * TEST_HEIGHT];

static void
fill_frame (unsigned frame)
{
  for (unsigned y = 0; y < TEST_HEIGHT; y++)
    for (unsigned x = 0; x < TEST_WIDTH; x++)
      frame_buffer[y * TEST_WIDTH + x] = test_frame_pixel (frame, x, y);
}

unsigned
retro_api_version (void)
{
  return RETRO_API_VERSION;
}

void
retro_get_system_info (struct retro_system_info *info)
{
  memset (info, 0, sizeof (*info));
  info->library_name = "retro-gtk-ohos-test-core";
  info->library_version = "1.0";
  info->valid_extensions = "";
  info->need_fullpath = false;
  info->block_extract = false;
}

void
retro_get_system_av_info (struct retro_system_av_info *info)
{
  info->geometry.base_width = TEST_WIDTH;
  info->geometry.base_height = TEST_HEIGHT;
  info->geometry.max_width = TEST_WIDTH;
  info->geometry.max_height = TEST_HEIGHT;
  info->geometry.aspect_ratio = (float) TEST_WIDTH / (float) TEST_HEIGHT;
  info->timing.fps = TEST_FPS;
  info->timing.sample_rate = TEST_SAMPLE_RATE;
}

void
retro_set_controller_port_device (unsigned port,
                                  unsigned device)
{
  (void) port;
  (void) device;
}

void
retro_set_environment (retro_environment_t cb)
{
  environment_cb = cb;

  if (environment_cb != NULL)
    environment_cb (RETRO_ENVIRONMENT_SET_PIXEL_FORMAT, &pixel_format);
}

void
retro_set_video_refresh (retro_video_refresh_t cb)
{
  video_cb = cb;
}

void
retro_set_audio_sample (retro_audio_sample_t cb)
{
  audio_cb = cb;
}

void
retro_set_audio_sample_batch (retro_audio_sample_batch_t cb)
{
  audio_batch_cb = cb;
}

void
retro_set_input_poll (retro_input_poll_t cb)
{
  input_poll_cb = cb;
}

void
retro_set_input_state (retro_input_state_t cb)
{
  input_state_cb = cb;
}

void
retro_init (void)
{
  frame_number = 0;
  fill_frame (frame_number);
}

void
retro_deinit (void)
{
}

void
retro_reset (void)
{
  frame_number = 0;
  fill_frame (frame_number);
}

bool
retro_load_game (const struct retro_game_info *game)
{
  (void) game;

  return true;
}

void
retro_unload_game (void)
{
}

unsigned
retro_get_region (void)
{
  return RETRO_REGION_NTSC;
}

void
retro_run (void)
{
  frame_number++;

  /* 每帧重建（帧号进入蓝色低位），再按 Libretro 契约把整帧交给前端 */
  fill_frame (frame_number);

  if (input_poll_cb != NULL)
    input_poll_cb ();

  if (video_cb != NULL)
    video_cb (frame_buffer, TEST_WIDTH, TEST_HEIGHT,
              TEST_WIDTH * sizeof (uint16_t));

  if (audio_batch_cb != NULL) {
    static const int16_t silence[2] = { 0, 0 };

    audio_batch_cb (silence, 1);
  } else if (audio_cb != NULL) {
    audio_cb (0, 0);
  }

  (void) input_state_cb;
}

size_t
retro_serialize_size (void)
{
  return 0;
}

bool
retro_serialize (void   *data,
                 size_t  size)
{
  (void) data;
  (void) size;

  return false;
}

bool
retro_unserialize (const void *data,
                   size_t      size)
{
  (void) data;
  (void) size;

  return false;
}

void *
retro_get_memory_data (unsigned id)
{
  (void) id;

  return NULL;
}

size_t
retro_get_memory_size (unsigned id)
{
  (void) id;

  return 0;
}
