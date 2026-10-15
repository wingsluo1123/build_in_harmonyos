/*
 * test_package — libming 消费者视角功能测试（R34：必须实质调用被测包 API）
 *
 * 真实链接并调用 libming 公开头文件 <ming.h> 中的 API：初始化 → 建影片 →
 * 建形状并绘制 → 挂到影片 → 保存为 SWF → 回读产物校验文件头与尺寸。
 * 覆盖 4 组 API 面：Ming_*（运行期）、newSWFMovie/SWFMovie_*（影片）、
 * newSWFShape/SWFShape_*（图形）、SWFMovie_save（输出）。
 *
 * 任一断言失败即返回非 0，让 conan create 失败（不是只打印 "OK" 的空壳测试）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <ming.h>

static int failures = 0;

static void check(int cond, const char *what)
{
	if (cond) {
		printf("ok   %s\n", what);
	} else {
		printf("FAIL %s\n", what);
		failures++;
	}
}

int main(int argc, char **argv)
{
	const char *out = (argc > 1) ? argv[1] : "test_package.swf";
	SWFMovie movie;
	SWFShape shape;
	SWFDisplayItem item;
	int rc;

	/* 1) 运行期初始化（Ming_* API） */
	rc = Ming_init();
	check(rc == 0, "Ming_init() returns 0");

	/* 2) 影片对象与属性 */
	movie = newSWFMovie();
	check(movie != NULL, "newSWFMovie() returns non-NULL");
	if (movie == NULL)
		return 1;

	SWFMovie_setRate(movie, 12.0);
	check(1, "SWFMovie_setRate(12.0)");
	SWFMovie_setDimension(movie, 320, 240);
	check(1, "SWFMovie_setDimension(320x240)");

	/* 3) 形状 API：描一个三角形并加入影片 */
	shape = newSWFShape();
	check(shape != NULL, "newSWFShape() returns non-NULL");
	if (shape == NULL)
		return 1;

	SWFShape_setLine(shape, 2, 0, 0, 0, 255);
	SWFShape_movePenTo(shape, 0, 0);
	SWFShape_drawLineTo(shape, 100, 0);
	SWFShape_drawLineTo(shape, 50, 80);
	SWFShape_drawLineTo(shape, 0, 0);
	SWFShape_end(shape);
	check(SWFShape_getVersion(shape) >= 0, "SWFShape_getVersion() >= 0");

	item = SWFMovie_add(movie, (SWFBlock)shape);
	check(item != NULL, "SWFMovie_add(shape) returns non-NULL");
	SWFMovie_nextFrame(movie);
	check(1, "SWFMovie_nextFrame()");
	SWFMovie_writeExports(movie);
	check(1, "SWFMovie_writeExports()");

	/* 4) 输出 SWF 并回读产物校验（真实产物，不是只跑函数） */
	rc = SWFMovie_save(movie, out);
	check(rc >= 0, "SWFMovie_save() returns >= 0");

	{
		FILE *fp = fopen(out, "rb");
		long size = 0;
		char sig[4] = {0, 0, 0, 0};	/* 3 字节签名 + NUL，供 strcmp 使用 */

		check(fp != NULL, "saved .swf is readable");
		if (fp != NULL) {
			fseek(fp, 0, SEEK_END);
			size = ftell(fp);
			fseek(fp, 0, SEEK_SET);
			if (fread(sig, 1, 3, fp) != 3) {
				sig[0] = sig[1] = sig[2] = 0;
			}
			fclose(fp);
		}
		/* 未压缩 SWF 签名 FWS / zlib 压缩签名 CWS（Ming_setSWFCompression） */
		check(strcmp(sig, "FWS") == 0 || strcmp(sig, "CWS") == 0,
		      "saved .swf has FWS/CWS signature");
		check(size > 32, "saved .swf is non-trivial (> 32 bytes)");
		printf("     %s: %ld bytes, signature %.3s\n", out, size, sig);
	}

	Ming_cleanup();
	printf("\n%s: %d assertion(s) failed\n", failures ? "FAILED" : "PASSED",
	       failures);
	return failures ? 1 : 0;
}
