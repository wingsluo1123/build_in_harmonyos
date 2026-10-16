/*
 * test_consumer.c — trimadap 完整消费者端到端用例（HarmonyOS PC / aarch64）
 *
 * 【消费者场景】模拟真实部署形态：测序下机得到 gzip 压缩的 Illumina FASTQ，
 * 把 trimadap 作为流式过滤器接入数据处理管线（多线程 `-p 4`）修剪接头，
 * 再用下游消费者独立解析产出的 FASTQ 做校验；随后以 `-t 8` 跑一遍"真正剪切"
 * 的第二步流水线。这是一个跑通完整流程的消费者用例，而不是对 CLI 的零散断言。
 *
 * 【为什么算鸿蒙/PC 特有覆盖】本用例走的是 OHOS 目标平台独有或特有的路径：
 *   1) gzip 输入经 OHOS zlib（zlib/1.3.1 依赖）读写，验证 OHOS 上的 zlib 链接与 gzFile 路径；
 *   2) 多线程流式处理经 OHOS pthread / kthread.c 路径（-p 4）；
 *   3) 接头比对在 aarch64 上走的是本适配新增的标量内核（SSE2 是 x86 路径），
 *      因此该用例同时是 aarch64 标量内核的功能验收。
 *
 * 【输入构造】64 条读段，四类交替（长度与期望掩码均可精确推导）：
 *   cat0  82bp 随机插入片段 + 18bp 精确 3' 接头后缀   → 期望尾部 18 个 X
 *   cat1  100bp 纯随机（无接头对照）                   → 期望完全不变
 *   cat2  30bp 5' 通用接头后缀 + 70bp 随机插入片段     → 期望头部 30 个 X
 *   cat3  70bp 随机插入片段 + 12bp 3' 接头前缀         → 期望尾部 12 个 X
 * 随机序列由固定种子 LCG 生成，数据确定、可复现。
 *
 * 用法: ./test_consumer <trimadap-mt 绝对路径>
 */
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <zlib.h>

#define N_READS 64
#define MAX_SEQ 256
#define MAX_LINE 512

/* 上游 illumina.txt 中的 TruSeq 接头片段 */
#define AD3_FULL "AGATCGGAAGAGCACACG"                             /* 18 bp */
#define AD3_PART "AGATCGGAAGAG"                                   /* 12 bp */
#define AD5_30   "CTCTTTCCCTACACGACGCTCTTCCGATCT"                  /* 30 bp */

typedef struct {
	char name[32];
	char seq[MAX_SEQ];
	char insert[MAX_SEQ]; /* -t 剪切后应保留的插入片段 */
	int len;
	int insert_len;
	int cat;
} read_t;

static read_t g_reads[N_READS];
static unsigned int g_rng = 20261015u;

static unsigned int rng(void)
{
	g_rng = g_rng * 1664525u + 1013904223u;
	return g_rng;
}

static void rand_seq(char *dst, int n)
{
	int i;
	for (i = 0; i < n; ++i)
		dst[i] = "ACGT"[rng() % 4];
	dst[n] = 0;
}

static void make_reads(void)
{
	int i;
	for (i = 0; i < N_READS; ++i) {
		read_t *r = &g_reads[i];
		r->cat = i % 4;
		snprintf(r->name, sizeof(r->name), "read%03d", i);
		switch (r->cat) {
		case 0: /* 3' 精确接头后缀 */
			rand_seq(r->insert, 82);
			snprintf(r->seq, sizeof(r->seq), "%s%s", r->insert, AD3_FULL);
			break;
		case 1: /* 无接头对照 */
			rand_seq(r->insert, 100);
			snprintf(r->seq, sizeof(r->seq), "%s", r->insert);
			break;
		case 2: /* 5' 通用接头后缀 + 插入片段 */
			rand_seq(r->insert, 70);
			snprintf(r->seq, sizeof(r->seq), "%s%s", AD5_30, r->insert);
			break;
		default: /* 3' 接头前缀 */
			rand_seq(r->insert, 70);
			snprintf(r->seq, sizeof(r->seq), "%s%s", r->insert, AD3_PART);
			break;
		}
		r->len = (int)strlen(r->seq);
		r->insert_len = (int)strlen(r->insert);
	}
}

/* 以 gzip 写出 FASTQ（真实下机数据形态；同时验证 OHOS 上的 zlib） */
static int write_fastq_gz(const char *path)
{
	gzFile fp = gzopen(path, "wb");
	int i, j;
	if (fp == NULL) {
		fprintf(stderr, "无法创建 gzip FASTQ: %s\n", path);
		return -1;
	}
	for (i = 0; i < N_READS; ++i) {
		const read_t *r = &g_reads[i];
		gzprintf(fp, "@%s\n%s\n+\n", r->name, r->seq);
		for (j = 0; j < r->len; ++j)
			gzputc(fp, 'I');
		gzputc(fp, '\n');
	}
	if (gzclose(fp) != Z_OK) {
		fprintf(stderr, "gzip FASTQ 收尾失败: %s\n", path);
		return -1;
	}
	return 0;
}

/* 真实执行被测二进制：fork + execv（不依赖 /bin/sh），stdout/stderr 落文件 */
static int run_tool(const char *binary, const char *in, const char *out,
		    const char *err, int use_trim)
{
	pid_t pid;
	int status = 0, fd_out, fd_err;
	char *args[8];
	int n = 0;

	args[n++] = (char *)binary;
	if (use_trim) {
		args[n++] = "-t";
		args[n++] = "8";
	} else {
		args[n++] = "-p";
		args[n++] = "4";
	}
	args[n++] = (char *)in;
	args[n] = NULL;

	fd_out = open(out, O_WRONLY | O_CREAT | O_TRUNC, 0644);
	fd_err = open(err, O_WRONLY | O_CREAT | O_TRUNC, 0644);
	if (fd_out < 0 || fd_err < 0) {
		fprintf(stderr, "无法打开输出文件\n");
		return -1;
	}

	pid = fork();
	if (pid < 0) {
		fprintf(stderr, "fork 失败\n");
		return -1;
	}
	if (pid == 0) {
		dup2(fd_out, STDOUT_FILENO);
		dup2(fd_err, STDERR_FILENO);
		close(fd_out);
		close(fd_err);
		execv(binary, args);
		fprintf(stderr, "execv 失败: %s\n", binary);
		_exit(127);
	}
	close(fd_out);
	close(fd_err);
	if (waitpid(pid, &status, 0) < 0)
		return -1;
	if (!WIFEXITED(status))
		return -1;
	return WEXITSTATUS(status);
}

/* 下游消费者：独立解析产出的 FASTQ */
static int load_fastq(const char *path, read_t *out, int max)
{
	FILE *fp = fopen(path, "r");
	char line[MAX_LINE];
	int n = 0;
	if (fp == NULL) {
		fprintf(stderr, "无法读取产出 FASTQ: %s\n", path);
		return -1;
	}
	while (fgets(line, sizeof(line), fp) != NULL) {
		size_t l = strlen(line);
		read_t *r;
		if (l && line[l - 1] == '\n')
			line[--l] = 0;
		if (line[0] != '@')
			continue;
		if (n >= max)
			break;
		r = &out[n];
		snprintf(r->name, sizeof(r->name), "%s", line + 1);
		if (fgets(line, sizeof(line), fp) == NULL)
			break;
		l = strlen(line);
		if (l && line[l - 1] == '\n')
			line[--l] = 0;
		snprintf(r->seq, sizeof(r->seq), "%s", line);
		r->len = (int)l;
		if (fgets(line, sizeof(line), fp) == NULL) /* + 行 */
			break;
		if (fgets(line, sizeof(line), fp) == NULL) /* 质量串 */
			break;
		l = strlen(line);
		if (l && line[l - 1] == '\n')
			line[--l] = 0;
		if ((int)l != r->len) {
			fprintf(stderr, "%s: 质量串长度 %zu 与序列 %d 不一致\n",
				r->name, l, r->len);
			fclose(fp);
			return -1;
		}
		++n;
	}
	fclose(fp);
	return n;
}

/* ---------------------------------------------------------------- 断言框架 */
static int g_pass, g_fail;

static void ok(const char *what)
{
	++g_pass;
	printf("  ok   : %s\n", what);
}

static void bad(const char *what, const char *detail)
{
	++g_fail;
	printf("  FAIL : %s\n", what);
	if (detail != NULL)
		printf("         %s\n", detail);
}

int main(int argc, char **argv)
{
	const char *binary, *work = "consumer-work";
	char in[MAX_LINE], out1[MAX_LINE], out2[MAX_LINE], err1[MAX_LINE], err2[MAX_LINE];
	static read_t got[N_READS];
	int rc1, rc2, n1, n2, i, j, bad_len = 0, bad_fidelity = 0, bad_mask = 0;
	int mask_ok[4];

	if (argc < 2) {
		fprintf(stderr, "用法: %s <trimadap-mt 路径>\n", argv[0]);
		return 2;
	}
	binary = argv[1];
	if (argc > 2)
		work = argv[2];

	if (mkdir(work, 0755) != 0 && access(work, F_OK) != 0) {
		fprintf(stderr, "无法创建工作目录: %s\n", work);
		return 2;
	}

	snprintf(in, sizeof(in), "%s/illumina-run.fq.gz", work);
	snprintf(out1, sizeof(out1), "%s/trimmed-mask.fq", work);
	snprintf(out2, sizeof(out2), "%s/trimmed-cut.fq", work);
	snprintf(err1, sizeof(err1), "%s/stage1.err", work);
	snprintf(err2, sizeof(err2), "%s/stage2.err", work);

	make_reads();

	printf("trimadap 消费者端到端用例（%d 条读段，gzip 输入）\n", N_READS);

	/* 流程 ①：下机 gzip FASTQ → 多线程流式修剪（掩码）→ 下游解析 */
	if (write_fastq_gz(in) != 0) {
		bad("生成 gzip FASTQ 输入", in);
		return 1;
	}
	ok("生成 gzip 压缩 FASTQ 输入（经 OHOS zlib）");

	rc1 = run_tool(binary, in, out1, err1, 0);
	if (rc1 != 0) {
		bad("流程① trimadap -p 4 退出码为 0", err1);
	} else {
		ok("流程① trimadap -p 4（多线程 gzip 流式）退出码为 0");
	}

	n1 = load_fastq(out1, got, N_READS);
	if (n1 != N_READS) {
		char d[128];
		snprintf(d, sizeof(d), "产出记录数 %d，期望 %d", n1, N_READS);
		bad("流程① 产出记录数与输入一致", d);
		return 1;
	}
	ok("流程① 产出记录数与输入一致（下游消费者独立解析）");

	mask_ok[0] = mask_ok[1] = mask_ok[2] = mask_ok[3] = 1;
	for (i = 0; i < N_READS; ++i) {
		const read_t *src = &g_reads[i];
		const read_t *dst = &got[i];
		int expect_x = 0, x_at_head = 0, fx, lx;

		if (strcmp(src->name, dst->name) != 0) {
			bad("记录顺序/名称与输入一致", dst->name);
			return 1;
		}
		if (src->len != dst->len) {
			bad_len = 1;
			continue;
		}
		/* 非 X 区必须与输入逐字节一致 */
		for (j = 0; j < src->len; ++j)
			if (dst->seq[j] != 'X' && dst->seq[j] != src->seq[j]) {
				bad_fidelity = 1;
				break;
			}
		/* X 区必须连续且贴合某一端 */
		fx = -1;
		for (j = 0; j < dst->len; ++j)
			if (dst->seq[j] == 'X') {
				fx = j;
				break;
			}
		if (fx >= 0) {
			lx = fx;
			for (j = fx; j < dst->len; ++j)
				if (dst->seq[j] == 'X')
					lx = j;
			for (j = fx; j <= lx; ++j)
				if (dst->seq[j] != 'X')
					bad_mask = 1;
			if (!(fx == 0 || lx == dst->len - 1))
				bad_mask = 1;
			if (fx == 0 && lx == 29)
				x_at_head = 1;
			expect_x = lx - fx + 1;
		}
		/* 分类期望 */
		switch (src->cat) {
		case 0:
			if (expect_x != 18 || x_at_head)
				mask_ok[0] = 0;
			break;
		case 1:
			if (expect_x != 0)
				mask_ok[1] = 0;
			break;
		case 2:
			if (expect_x != 30 || !x_at_head)
				mask_ok[2] = 0;
			break;
		default:
			if (expect_x != 12 || x_at_head)
				mask_ok[3] = 0;
			break;
		}
	}
	if (bad_len)
		bad("流程① 输出长度与输入一致", "存在长度改变的读段");
	else
		ok("流程① 输出长度与输入一致");
	if (bad_fidelity)
		bad("流程① 非掩码区与输入逐字节一致", "存在被改写的碱基");
	else
		ok("流程① 非掩码区与输入逐字节一致");
	if (bad_mask)
		bad("流程① 掩码区连续且贴合读段某一端", "存在游离/不连续的 X");
	else
		ok("流程① 掩码区连续且贴合读段某一端");

	if (mask_ok[0])
		ok("流程① 3' 精确接头后缀被整段掩码（18 bp，16 条读段）");
	else
		bad("流程① 3' 精确接头后缀被整段掩码", "掩码长度/位置与期望不符");
	if (mask_ok[1])
		ok("流程① 无接头对照读段完全不变（16 条读段）");
	else
		bad("流程① 无接头对照读段完全不变", "对照读段被误修剪");
	if (mask_ok[2])
		ok("流程① 5' 通用接头被整段掩码（30 bp，16 条读段）");
	else
		bad("流程① 5' 通用接头被整段掩码", "掩码长度/位置与期望不符");
	if (mask_ok[3])
		ok("流程① 3' 接头前缀被掩码（12 bp，16 条读段）");
	else
		bad("流程① 3' 接头前缀被掩码", "掩码长度/位置与期望不符");

	/* 流程 ②：第二步"真正剪切"（-t 8），产出可直接下游使用的插入片段 */
	rc2 = run_tool(binary, in, out2, err2, 1);
	if (rc2 != 0) {
		bad("流程② trimadap -t 8 退出码为 0", err2);
	} else {
		ok("流程② trimadap -t 8（剪切模式）退出码为 0");
	}
	n2 = load_fastq(out2, got, N_READS);
	if (n2 != N_READS) {
		char d[128];
		snprintf(d, sizeof(d), "产出记录数 %d，期望 %d", n2, N_READS);
		bad("流程② 产出记录数与输入一致", d);
	} else {
		ok("流程② 产出记录数与输入一致");
	}
	{
		int bad_ins = 0;
		for (i = 0; i < n2 && i < N_READS; ++i)
			if (strcmp(got[i].seq, g_reads[i].insert) != 0)
				bad_ins = 1;
		if (bad_ins)
			bad("流程② 每条读段精确等于已知插入片段", "存在与期望插入片段不符的输出");
		else
			ok("流程② 每条读段精确等于已知插入片段（下游可直接使用）");
	}

	printf("\ntrimadap consumer e2e: %d passed, %d failed\n", g_pass, g_fail);
	return g_fail == 0 ? 0 : 1;
}
