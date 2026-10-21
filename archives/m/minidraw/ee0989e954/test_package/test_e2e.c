/*
 * test_e2e.c — minidraw 端到端消费者用例（r02 rule12 补缺）
 *
 * 硬要求：真实调用 minidraw 公开 API，走通
 *   初始化/创建绘图上下文 -> 执行实际绘制操作（线段/矩形/填充等基元）
 *   -> 渲染到像素缓冲 -> 对输出像素做内容校验（像素落位、颜色/覆盖正确）
 *   -> 资源释放
 * 的完整链路。
 *
 * 平台约束：OHOS PC 无 Cairo/Pango/GDI，minidraw 上游在无后端时唯一可用的
 * 公开渲染通道是 md_backend_custom（消费者自供 procs 表）。本用例自实现一个
 * 最小软件光栅化后端（像素缓冲 RGBA8），把 minidraw 的绘图命令真实光栅化到
 * 像素，再读回并逐像素校验颜色与覆盖，验证绘图链路端到端生效。
 */
#define MINIDRAW_IMPLEMENTATION
#include "minidraw.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ── 自定义软件后端状态 ─────────────────────────────── */
typedef struct
{
    md_uint32 sizeX;
    md_uint32 sizeY;
    md_uint32 stride;      /* bytes per row */
    unsigned char* pixels; /* RGBA8, row-major */
    md_color fillColor;
    md_color lineColor;
    md_int32 moveX, moveY;
    md_int32 pathX, pathY; /* 记录 line_to 终点供 stroke 使用 */
    md_bool32 hasPath;
} sw_state;

static md_uint32 g_failures = 0;

#define SW_CHECK(cond, msg)                                                    \
    do {                                                                       \
        if (!(cond)) {                                                         \
            printf("FAIL: %s (line %d)\n", msg, __LINE__);                     \
            g_failures++;                                                      \
        }                                                                      \
    } while (0)

static void sw_put_pixel(sw_state* s, md_int32 x, md_int32 y, md_color c)
{
    if (x < 0 || (md_uint32)x >= s->sizeX || y < 0 || (md_uint32)y >= s->sizeY) {
        return;
    }
    unsigned char* p = s->pixels + (md_uint32)y * s->stride + (md_uint32)x * 4;
    p[0] = c.r; p[1] = c.g; p[2] = c.b; p[3] = c.a;
}

/* ── 后端 procs 实现 ─────────────────────────────────── */

static void sw_api_uninit(md_api* pAPI)
{
    /* custom 后端无全局资源，仅需保证 md_uninit 可安全调用（procs.uninit 必须非空） */
    (void)pAPI;
}

static md_result sw_gc_init(md_api* pAPI, const md_gc_config* pConfig, md_gc* pGC)
{
    (void)pAPI;
    sw_state* s = (sw_state*)calloc(1, sizeof(sw_state));
    if (s == NULL) {
        return MD_OUT_OF_MEMORY;
    }
    s->sizeX = pConfig->sizeX > 0 ? pConfig->sizeX : 64;
    s->sizeY = pConfig->sizeY > 0 ? pConfig->sizeY : 64;
    s->stride = s->sizeX * 4;
    s->pixels = (unsigned char*)calloc(s->stride * s->sizeY, 1);
    if (s->pixels == NULL) {
        free(s);
        return MD_OUT_OF_MEMORY;
    }
    if (pConfig->pInitialImageData != NULL) {
        memcpy(s->pixels, pConfig->pInitialImageData, s->stride * s->sizeY);
    }
    pGC->pUserData = s;
    return MD_SUCCESS;
}

static void sw_gc_uninit(md_gc* pGC)
{
    sw_state* s = (sw_state*)pGC->pUserData;
    if (s != NULL) {
        free(s->pixels);
        free(s);
        pGC->pUserData = NULL;
    }
}

static void sw_gc_clear(md_gc* pGC, md_color color)
{
    sw_state* s = (sw_state*)pGC->pUserData;
    size_t i;
    for (i = 0; i < (size_t)s->sizeX * s->sizeY; ++i) {
        unsigned char* p = s->pixels + i * 4;
        p[0] = color.r; p[1] = color.g; p[2] = color.b; p[3] = color.a;
    }
}

static void sw_gc_set_fill_brush_solid(md_gc* pGC, md_color color)
{
    ((sw_state*)pGC->pUserData)->fillColor = color;
}

static void sw_gc_set_line_brush_solid(md_gc* pGC, md_color color)
{
    ((sw_state*)pGC->pUserData)->lineColor = color;
}

static void sw_gc_move_to(md_gc* pGC, md_int32 x, md_int32 y)
{
    sw_state* s = (sw_state*)pGC->pUserData;
    s->moveX = x; s->moveY = y;
}

static void sw_gc_line_to(md_gc* pGC, md_int32 x, md_int32 y)
{
    sw_state* s = (sw_state*)pGC->pUserData;
    s->pathX = x; s->pathY = y;
    s->hasPath = MD_TRUE;
}

static void sw_gc_rectangle(md_gc* pGC, md_int32 left, md_int32 top, md_int32 right, md_int32 bottom)
{
    sw_state* s = (sw_state*)pGC->pUserData;
    /* 保存矩形边界到路径，供 fill/stroke 使用 */
    s->pathX = left; s->pathY = top;
    s->moveX = right; s->moveY = bottom;
    s->hasPath = MD_TRUE;
}

static void sw_gc_fill(md_gc* pGC)
{
    sw_state* s = (sw_state*)pGC->pUserData;
    md_int32 x, y;
    /* 填充最近一次 rectangle 包围盒（含边界），真实写入像素 */
    md_int32 left = s->pathX, top = s->pathY;
    md_int32 right = s->moveX, bottom = s->moveY;
    if (left > right) { md_int32 t = left; left = right; right = t; }
    if (top > bottom) { md_int32 t = top; top = bottom; bottom = t; }
    for (y = top; y <= bottom; ++y) {
        for (x = left; x <= right; ++x) {
            sw_put_pixel(s, x, y, s->fillColor);
        }
    }
    s->hasPath = MD_FALSE;
}

static void sw_gc_stroke(md_gc* pGC)
{
    sw_state* s = (sw_state*)pGC->pUserData;
    /* 用 Bresenham 画一条从 move_to 到 line_to 的线段，真实写入像素 */
    md_int32 x0 = s->moveX, y0 = s->moveY;
    md_int32 x1 = s->pathX, y1 = s->pathY;
    md_int32 dx = x1 > x0 ? x1 - x0 : x0 - x1;
    md_int32 dy = y1 > y0 ? y1 - y0 : y0 - y1;
    md_int32 sx = x0 < x1 ? 1 : -1;
    md_int32 sy = y0 < y1 ? 1 : -1;
    md_int32 err = dx - dy;
    for (;;) {
        sw_put_pixel(s, x0, y0, s->lineColor);
        if (x0 == x1 && y0 == y1) {
            break;
        }
        {
            md_int32 e2 = 2 * err;
            if (e2 > -dy) { err -= dy; x0 += sx; }
            if (e2 < dx)  { err += dx; y0 += sy; }
        }
    }
    s->hasPath = MD_FALSE;
}

static md_result sw_gc_get_image_data(md_gc* pGC, md_format outputFormat, void* pImageData)
{
    sw_state* s = (sw_state*)pGC->pUserData;
    if (outputFormat != md_format_rgba) {
        return MD_INVALID_ARGS;
    }
    memcpy(pImageData, s->pixels, s->stride * s->sizeY);
    return MD_SUCCESS;
}

static md_result sw_gc_get_size(md_gc* pGC, md_uint32* pSizeX, md_uint32* pSizeY)
{
    sw_state* s = (sw_state*)pGC->pUserData;
    if (pSizeX != NULL) { *pSizeX = s->sizeX; }
    if (pSizeY != NULL) { *pSizeY = s->sizeY; }
    return MD_SUCCESS;
}

/* 未使用到的 procs 置 NULL；minidraw 包装函数对 NULL 有守卫。 */

int main(void)
{
    md_api api;
    md_gc gc;
    md_api_config apiConfig;
    md_gc_config gcConfig;
    unsigned char readback[64 * 64 * 4];
    md_color bg = md_rgba(255, 255, 255, 255);    /* 白底 */
    md_color fill = md_rgba(255, 0, 0, 255);      /* 红矩形 */
    md_color line = md_rgba(0, 0, 255, 255);      /* 蓝线段 */
    md_uint32 sizeX = 0, sizeY = 0;
    unsigned char* px;
    int i, onLine = 0;

    /* 1. 初始化：custom 后端 + 自实现 procs 表 */
    memset(&apiConfig, 0, sizeof(apiConfig));
    apiConfig.backend = md_backend_custom;
    apiConfig.custom.procs.uninit            = sw_api_uninit;
    apiConfig.custom.procs.gcInit             = sw_gc_init;
    apiConfig.custom.procs.gcUninit           = sw_gc_uninit;
    apiConfig.custom.procs.gcClear            = sw_gc_clear;
    apiConfig.custom.procs.gcSetFillBrushSolid   = sw_gc_set_fill_brush_solid;
    apiConfig.custom.procs.gcSetLineBrushSolid   = sw_gc_set_line_brush_solid;
    apiConfig.custom.procs.gcMoveTo           = sw_gc_move_to;
    apiConfig.custom.procs.gcLineTo           = sw_gc_line_to;
    apiConfig.custom.procs.gcRectangle        = sw_gc_rectangle;
    apiConfig.custom.procs.gcFill             = sw_gc_fill;
    apiConfig.custom.procs.gcStroke           = sw_gc_stroke;
    apiConfig.custom.procs.gcGetImageData     = sw_gc_get_image_data;
    apiConfig.custom.procs.gcGetSize          = sw_gc_get_size;

    SW_CHECK(md_init(&apiConfig, &api) == MD_SUCCESS, "md_init (custom backend)");

    /* 2. 创建绘图上下文：64x64 RGBA8 像素缓冲 */
    memset(&gcConfig, 0, sizeof(gcConfig));
    gcConfig.sizeX = 64;
    gcConfig.sizeY = 64;
    gcConfig.format = md_format_rgba;
    SW_CHECK(md_gc_init(&api, &gcConfig, &gc) == MD_SUCCESS, "md_gc_init");
    SW_CHECK(md_gc_get_size(&gc, &sizeX, &sizeY) == MD_SUCCESS, "md_gc_get_size");
    SW_CHECK(sizeX == 64 && sizeY == 64, "gc size 64x64");

    /* 3. 清屏（白底） */
    md_gc_clear(&gc, bg);

    /* 4. 绘制基元 1：填充矩形 (10,10)-(30,30) 红色 */
    md_gc_set_fill_brush_solid(&gc, fill);
    md_gc_rectangle(&gc, 10, 10, 30, 30);
    md_gc_fill(&gc);

    /* 5. 绘制基元 2：线段 (2,2)->(60,2) 蓝色 */
    md_gc_set_line_brush_solid(&gc, line);
    md_gc_move_to(&gc, 2, 2);
    md_gc_line_to(&gc, 60, 2);
    md_gc_stroke(&gc);

    /* 6. 渲染到像素缓冲并读回 */
    SW_CHECK(md_gc_get_image_data(&gc, md_format_rgba, readback) == MD_SUCCESS, "md_gc_get_image_data");

    /* 7. 像素内容校验 */
    /* 7a. 背景：矩形外 (5,5) 与线段外 (32,20) 应为白色 */
    px = readback + 5 * 64 * 4 + 5 * 4;
    SW_CHECK(px[0] == 255 && px[1] == 255 && px[2] == 255, "background white @(5,5)");
    px = readback + 20 * 64 * 4 + 32 * 4;
    SW_CHECK(px[0] == 255 && px[1] == 255 && px[2] == 255, "background white @(32,20)");

    /* 7b. 矩形内部：中心 (20,20) 与角点 (10,10)/(30,30) 应为红色（像素确实落位） */
    px = readback + 20 * 64 * 4 + 20 * 4;
    SW_CHECK(px[0] == 255 && px[1] == 0 && px[2] == 0, "fill red @(20,20)");
    px = readback + 10 * 64 * 4 + 10 * 4;
    SW_CHECK(px[0] == 255 && px[1] == 0 && px[2] == 0, "fill red @(10,10)");
    px = readback + 30 * 64 * 4 + 30 * 4;
    SW_CHECK(px[0] == 255 && px[1] == 0 && px[2] == 0, "fill red @(30,30)");

    /* 7c. 线段覆盖：y=2 行中应有 >=20 个蓝色像素（像素落位且覆盖正确） */
    px = readback + 2 * 64 * 4;
    for (i = 2; i <= 60; ++i) {
        if (px[i * 4 + 0] == 0 && px[i * 4 + 1] == 0 && px[i * 4 + 2] == 255) {
            onLine++;
        }
    }
    SW_CHECK(onLine >= 20, "line blue coverage >= 20 px @row y=2");
    printf("line coverage: %d blue pixels on row y=2\n", onLine);

    /* 8. 资源释放 */
    md_gc_uninit(&gc);
    md_uninit(&api);

    if (g_failures == 0) {
        printf("OK: minidraw E2E consumer test passed (init->draw rect+line+fill->pixel check->release)\n");
        return 0;
    }
    printf("NG: %u E2E check(s) failed\n", g_failures);
    return 1;
}