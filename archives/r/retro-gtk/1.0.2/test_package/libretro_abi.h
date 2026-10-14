/* libretro_abi.h — 本 test_package 用的最小 Libretro ABI 声明（自写头部，非上游
 * libretro.h 拷贝）。
 *
 * 只声明假核心（test_core.c）与 libretro-gtk 的 retro-runner 之间真正交换的
 * 结构体、回调类型与环境命令；字段顺序严格对应 Libretro API v1 ABI。
 */
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define RETRO_API_VERSION 1

/* 环境命令（只列本测试用到的） */
#define RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY 9
#define RETRO_ENVIRONMENT_SET_PIXEL_FORMAT 10
#define RETRO_ENVIRONMENT_SET_SUPPORT_NO_GAME 18

enum retro_pixel_format {
  RETRO_PIXEL_FORMAT_0RGB1555 = 0,
  RETRO_PIXEL_FORMAT_XRGB8888 = 1,
  RETRO_PIXEL_FORMAT_RGB565 = 2,
};

enum retro_region {
  RETRO_REGION_NTSC = 0,
  RETRO_REGION_PAL = 1,
};

struct retro_game_geometry {
  unsigned base_width;
  unsigned base_height;
  unsigned max_width;
  unsigned max_height;
  float aspect_ratio;
};

struct retro_system_timing {
  double fps;
  double sample_rate;
};

struct retro_system_av_info {
  struct retro_game_geometry geometry;
  struct retro_system_timing timing;
};

struct retro_system_info {
  const char *library_name;
  const char *library_version;
  const char *valid_extensions;
  bool need_fullpath;
  bool block_extract;
};

struct retro_game_info {
  const char *path;
  const void *data;
  size_t size;
  const char *meta;
};

typedef bool (*retro_environment_t) (unsigned cmd, void *data);
typedef void (*retro_video_refresh_t) (const void *data,
                                       unsigned    width,
                                       unsigned    height,
                                       size_t      pitch);
typedef void (*retro_audio_sample_t) (int16_t left,
                                      int16_t right);
typedef size_t (*retro_audio_sample_batch_t) (const int16_t *data,
                                              size_t         frames);
typedef void (*retro_input_poll_t) (void);
typedef int16_t (*retro_input_state_t) (unsigned port,
                                        unsigned device,
                                        unsigned index,
                                        unsigned id);

/* 核心导出入口（retro-runner 逐个 dlsym 这 21 个符号） */
void retro_init (void);
void retro_deinit (void);
unsigned retro_api_version (void);
void retro_get_system_info (struct retro_system_info *info);
void retro_get_system_av_info (struct retro_system_av_info *info);
void retro_set_controller_port_device (unsigned port, unsigned device);
void retro_set_environment (retro_environment_t cb);
void retro_set_video_refresh (retro_video_refresh_t cb);
void retro_set_audio_sample (retro_audio_sample_t cb);
void retro_set_audio_sample_batch (retro_audio_sample_batch_t cb);
void retro_set_input_poll (retro_input_poll_t cb);
void retro_set_input_state (retro_input_state_t cb);
void retro_reset (void);
void retro_run (void);
size_t retro_serialize_size (void);
bool retro_serialize (void *data, size_t size);
bool retro_unserialize (const void *data, size_t size);
bool retro_load_game (const struct retro_game_info *game);
void retro_unload_game (void);
void *retro_get_memory_data (unsigned id);
size_t retro_get_memory_size (unsigned id);
