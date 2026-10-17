/* WhySynth 20170701 — DSSI 插件消费者测试（真机准宿主）。
 *
 * 不满足于「dlopen 成功 / 符号存在」：本程序按 DSSI 宿主的最小流程把插件
 * 真的跑起来，并对**音频输出**下断言：
 *
 *   1. dlopen 装好的 lib/dssi/whysynth.so（鸿蒙上必须带 .codesign，否则
 *      dlopen 直接 Permission denied）
 *   2. 取 ladspa_descriptor / dssi_descriptor，核对元信息
 *      （UniqueID 2187、Label "WhySynth"、198 个端口、端口 0/1 是音频输出、
 *       其余是控制输入）
 *   3. instantiate(44100) —— 这一步会走 sampleset_init()，
 *      里面就有 PadSynth 的 fftwf_plan_r2r_1d()（即 libfftw3f 的实际使用）
 *   4. connect_port 接满全部端口（控制口初值取自各端口声明的合法范围，
 *      见下方注释），再 select_program(0,0) 让插件把内建 "friendly patch"
 *      写回宿主缓冲区（DSSI 端口往返），据此断言它确实写入了参数
 *      （而不是把宿主的初值原样留着）
 *   5. activate + run_synth(NOTEON) 渲染 0.5 秒，断言输出**不是静音**
 *      且全部有限（无 NaN/Inf）
 *   6. 再发 NOTEON 之外的一个 NOTEOFF 渲染一段，断言同样有限
 *   7. deactivate / cleanup / dlclose
 *
 * 判据说明：静音断言不是「跑通了」的弱信号 —— 它证明事件处理、声部分配、
 * 振荡器/包络/效果整条 DSP 链路真的产出了信号；如果插件只是能加载，
 * 输出会恒为 0 而测试失败。
 */

#include <dlfcn.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <dssi.h>   /* 内含 <alsa/seq_event.h>；同时给出 LADSPA/ DSSI 描述符 */

#ifndef TARGET_SO
#error "TARGET_SO must be defined (path of the installed whysynth plugin)"
#endif

#define SAMPLE_RATE   44100
#define BLOCK_FRAMES  (SAMPLE_RATE / 2)   /* 0.5 秒 */
#define EXPECT_PORTS  198
#define EXPECT_UNIQUE 2187

static int checks = 0;
static int failures = 0;

static void expect(int condition, const char *what)
{
    ++checks;
    if (condition) {
        printf("  ok   %s\n", what);
    } else {
        ++failures;
        printf("  FAIL %s\n", what);
    }
}

static int all_finite(const float *buf, unsigned long n)
{
    unsigned long i;
    for (i = 0; i < n; ++i) {
        if (!isfinite(buf[i])) {
            return 0;
        }
    }
    return 1;
}

static float peak(const float *buf, unsigned long n)
{
    unsigned long i;
    float p = 0.0f;
    for (i = 0; i < n; ++i) {
        float a = fabsf(buf[i]);
        if (a > p) {
            p = a;
        }
    }
    return p;
}

static void fill_event(snd_seq_event_t *ev, int type, int key, int velocity)
{
    memset(ev, 0, sizeof(*ev));
    ev->type = (snd_seq_event_type_t)type;
    ev->time.tick = 0;
    ev->data.note.channel = 0;
    ev->data.note.note = key;
    ev->data.note.velocity = velocity;
}

int main(void)
{
    void *handle;
    LADSPA_Descriptor *(*get_ladspa)(unsigned long);
    const DSSI_Descriptor *(*get_dssi)(unsigned long);
    const DSSI_Descriptor *dssi;
    LADSPA_Descriptor *ladspa;
    LADSPA_Handle instance;
    unsigned long i;
    unsigned long changed = 0;
    float *left = NULL, *right = NULL, *control = NULL;
    float before[EXPECT_PORTS];
    float first_peak, second_peak;

    printf("== whysynth DSSI plugin consumer test ==\n");
    printf("TARGET_SO=%s\n", TARGET_SO);

    handle = dlopen(TARGET_SO, RTLD_NOW);
    if (!handle) {
        printf("  FAIL dlopen(%s): %s\n", TARGET_SO, dlerror());
        printf("RESULT FAIL dlopen  (%d checks, %d failures)\n", ++checks, ++failures);
        return 1;
    }
    expect(1, "dlopen(plugin)");

    get_ladspa = (LADSPA_Descriptor *(*)(unsigned long))dlsym(handle, "ladspa_descriptor");
    get_dssi = (const DSSI_Descriptor *(*)(unsigned long))dlsym(handle, "dssi_descriptor");
    expect(get_ladspa != NULL, "dlsym(ladspa_descriptor)");
    expect(get_dssi != NULL, "dlsym(dssi_descriptor)");
    if (!get_ladspa || !get_dssi) {
        goto out;
    }

    ladspa = get_ladspa(0);
    expect(ladspa != NULL, "ladspa_descriptor(0) != NULL");
    if (!ladspa) {
        goto out;
    }
    expect(ladspa->UniqueID == EXPECT_UNIQUE, "LADSPA UniqueID == 2187");
    expect(ladspa->Label != NULL && strcmp(ladspa->Label, "WhySynth") == 0,
           "LADSPA Label == \"WhySynth\"");
    expect(ladspa->PortCount == EXPECT_PORTS, "PortCount == 198");
    expect(ladspa->instantiate && ladspa->connect_port && ladspa->activate
           && ladspa->run && ladspa->cleanup, "LADSPA vtable complete");

    /* 端口布局：0/1 音频输出，2..197 控制输入 */
    expect(LADSPA_IS_PORT_OUTPUT(ladspa->PortDescriptors[0])
           && LADSPA_IS_PORT_AUDIO(ladspa->PortDescriptors[0]),
           "port 0 is audio output");
    expect(LADSPA_IS_PORT_OUTPUT(ladspa->PortDescriptors[1])
           && LADSPA_IS_PORT_AUDIO(ladspa->PortDescriptors[1]),
           "port 1 is audio output");
    {
        int inputs_ok = 1;
        for (i = 2; i < ladspa->PortCount; ++i) {
            if (!LADSPA_IS_PORT_INPUT(ladspa->PortDescriptors[i])
                || !LADSPA_IS_PORT_CONTROL(ladspa->PortDescriptors[i])) {
                printf("       port %lu is not a control input (desc=0x%x)\n",
                       i, ladspa->PortDescriptors[i]);
                inputs_ok = 0;
                break;
            }
        }
        expect(inputs_ok, "ports 2..197 are control inputs");
    }

    dssi = get_dssi(0);
    expect(dssi != NULL, "dssi_descriptor(0) != NULL");
    if (!dssi) {
        goto out;
    }
    expect(dssi->DSSI_API_Version == 1, "DSSI_API_Version == 1");
    expect(dssi->LADSPA_Plugin == ladspa, "DSSI descriptor refers to the same LADSPA plugin");
    expect(dssi->run_synth != NULL, "DSSI run_synth present");
    expect(dssi->configure != NULL, "DSSI configure present");
    expect(dssi->get_program != NULL && dssi->select_program != NULL,
           "DSSI program interface present");

    instance = ladspa->instantiate(ladspa, SAMPLE_RATE);
    expect(instance != NULL, "instantiate(44100) != NULL");
    if (!instance) {
        goto out;
    }

    left = (float *)calloc(BLOCK_FRAMES, sizeof(float));
    right = (float *)calloc(BLOCK_FRAMES, sizeof(float));
    control = (float *)calloc(EXPECT_PORTS, sizeof(float));
    if (!left || !right || !control) {
        printf("  FAIL out of memory for port buffers\n");
        ++checks;
        ++failures;
        goto cleanup_instance;
    }

    /* 控制端口的初值必须落在端口声明的取值范围内。
     *
     * 这里原来用 -12345.0f 当"哨兵"，好让 select_program() 写回默认参数时
     * 能被检测出来；但 -12345 对**每一个**端口都是越界值，而 LADSPA/DSSI 宿主
     * 只会把控制端口设在声明范围之内。实测（真机 SIGSEGV，Signal 11）后果：
     * 第 197 号端口 "Tuning"（声明范围 415.3..466.2 Hz）**不是 patch 参数**，
     * select_program() 不写它，于是哨兵值一路留到 DSP，被 whysynth 直接当频率用：
     *     whysynth_voice_render.c:2612
     *         voice->current_pitch *= synth->pitch_bend * *(synth->tuning);
     *     whysynth_voice_render.c:2641
     *         oscillator(..., deltat * osc1_omega);      -> w0 = tuning / 44100
     * 于是 w0 = -12345/44100 = -0.279932（实测值），相位累加器 pos 向负方向一路
     * 跑下去（`if (pos >= 1.0f) pos -= 1.0f;` 对负数永不触发），
     * padsynth.c:612 的 `sine_wave[i + 4]`（i = lrintf(pos*1024) ≈ -5.5e5）
     * 越界读取，直接段错误。
     *
     * 上游在这条路径上不做钳位，宿主本来也不该给越界值，所以这是**测试激励非法**，
     * 不是移植缺陷：照 LADSPA 约定，宿主可以给端口设任何**合法**值。改成按端口
     * 声明的下界取值（未声明下界的取 0.0f）——正对应"宿主把控制数组清零、再按各
     * 端口的声明范围夹到合法值"这一真实情形；全部合法，且与 friendly patch 的默认
     * 值普遍不同，仍然能检出 select_program() 有没有把默认参数写回宿主。
     */
    for (i = 2; i < EXPECT_PORTS; ++i) {
        const LADSPA_PortRangeHint *hint = &ladspa->PortRangeHints[i];
        control[i] = (hint->HintDescriptor & LADSPA_HINT_BOUNDED_BELOW)
                     ? hint->LowerBound : 0.0f;
    }
    control[0] = control[1] = 0.0f;   /* 音频输出口，未连接，留个确定值 */
    ladspa->connect_port(instance, 0, left);
    ladspa->connect_port(instance, 1, right);
    for (i = 2; i < EXPECT_PORTS; ++i) {
        ladspa->connect_port(instance, i, &control[i]);
    }

    memcpy(before, control, sizeof(before));
    dssi->select_program(instance, 0, 0);
    for (i = 2; i < EXPECT_PORTS; ++i) {
        if (control[i] != before[i]) {
            ++changed;
        }
    }
    printf("       select_program(0,0) wrote %lu of %d control ports\n",
           changed, EXPECT_PORTS - 2);
    expect(changed > 100, "select_program() pushed the default patch into the host ports");

    /* DSSI configure：越界值必须返回错误消息（见 y_synth_handle_polyphony） */
    expect(dssi->configure(instance, "polyphony", "8") == NULL,
           "configure(polyphony=8) accepted");
    expect(dssi->configure(instance, "polyphony", "999") != NULL,
           "configure(polyphony=999) rejected with a message");

    ladspa->activate(instance);

    {
        snd_seq_event_t ev;
        fill_event(&ev, SND_SEQ_EVENT_NOTEON, 69, 100);   /* A4, mezzoforte */
        dssi->run_synth(instance, BLOCK_FRAMES, &ev, 1);
    }
    first_peak = peak(left, BLOCK_FRAMES);
    printf("       note-on block peak = %.6f\n", first_peak);
    expect(all_finite(left, BLOCK_FRAMES) && all_finite(right, BLOCK_FRAMES),
           "note-on block is finite (no NaN/Inf)");
    expect(first_peak > 1e-4f, "note-on block is not silent (peak > 1e-4)");

    {
        snd_seq_event_t ev;
        fill_event(&ev, SND_SEQ_EVENT_NOTEOFF, 69, 0);
        dssi->run_synth(instance, BLOCK_FRAMES, &ev, 1);
    }
    second_peak = peak(left, BLOCK_FRAMES);
    printf("       note-off block peak = %.6f\n", second_peak);
    expect(all_finite(left, BLOCK_FRAMES) && all_finite(right, BLOCK_FRAMES),
           "note-off block is finite (no NaN/Inf)");

    ladspa->deactivate(instance);
    expect(1, "deactivate() returned");

cleanup_instance:
    free(left);
    free(right);
    free(control);
    ladspa->cleanup(instance);
    expect(1, "cleanup() returned");

out:
    dlclose(handle);

    printf("RESULT %s  (%d checks, %d failures)\n",
           failures == 0 ? "PASS" : "FAIL", checks, failures);
    return failures == 0 ? 0 : 1;
}
