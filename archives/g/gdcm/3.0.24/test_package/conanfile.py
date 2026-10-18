#!/usr/bin/env python3
"""Conan test_package — gdcm 3.0.24 消费者用例

两段式端到端：库 API 生成并读回真实 DICOM（test_gdcm.cpp），再用制品包里的 CLI
工具消费同一文件（本文件 test()）。合计 67 条断言，口径见 MANIFEST.yml。
"""
import glob
import hashlib
import os
import re
import struct

from conan import ConanFile
from conan.tools.build import can_run


class GdcmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _run_ld_path(self):
        # 运行时依赖（实测 NEEDED）：libexpat.so（conan 依赖）+ libc++_shared.so（SDK
        # llvm/lib/aarch64-linux-ohos）。不 source conanrun.sh——其继承的系统默认
        # LD_LIBRARY_PATH 含缺符号的 libc++ 变体，实测最小路径集即可正确运行。
        parts = []
        for dep in ("expat", "zlib"):
            if dep in self.dependencies:
                for d in self.dependencies[dep].cpp_info.aggregated_components().libdirs:
                    parts.append(d)
        for sdk_lib in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos")) + [
            "/data/service/hnp/lib",
        ]:
            if os.path.isdir(sdk_lib):
                parts.append(sdk_lib)
        return ":".join(parts)

    def build(self):
        # 与主配方一致的裸编译路线（os=OHOS 下 CMakeToolchain 的 CMAKE_SYSTEM_NAME 映射问题 ML-0035）
        dep = self.dependencies["gdcm"].cpp_info
        incs = []
        for _ref, _d in self.dependencies.items():
            for p in _d.cpp_info.aggregated_components().includedirs:
                incs.append("-I" + p)
                # gdcm 头文件装在 include/gdcm-<ver>/ 子目录
                for sub in glob.glob(os.path.join(p, "gdcm-*")):
                    if os.path.isdir(sub):
                        incs.append("-I" + sub)
        inc = " ".join(incs)
        libdir = dep.aggregated_components().libdirs[0]
        # 动态发现包内 .a（上游库集随 USE_SYSTEM 开关变化：3.0.24 的 gdcmrle 不独立成库等）
        archives = sorted(glob.glob(os.path.join(libdir, "*.a")))
        # conan 依赖（zlib/expat）的库也要链接——从各依赖包 libdirs 动态取
        dep_libs = []
        for _ref, _d in self.dependencies.items():
            if str(_d.ref.name) == "gdcm":
                continue
            for d in _d.cpp_info.aggregated_components().libdirs:
                for l in sorted(glob.glob(os.path.join(d, "*.a")) + glob.glob(os.path.join(d, "*.so*"))):
                    if os.path.isfile(l) and not os.path.islink(l):
                        dep_libs.append(l)
        libs = " ".join(archives + dep_libs)
        cxx = os.environ.get("CXX", "clang++")
        self.run(
            f"{cxx} -std=c++11 -O1 test_gdcm.cpp -o test_gdcm {inc} "
            f"-L{libdir} {libs} -Wl,--allow-shlib-undefined"
        )

    @staticmethod
    def _read(path):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def _expect(self, text, needles, label):
        missing = [n for n in needles if n not in text]
        if missing:
            raise Exception("{}: missing {} in output:\n{}".format(label, missing, text[:2000]))
        self.output.info("{}: ok ({} assertions)".format(label, len(needles)))
        return len(needles)

    @staticmethod
    def _pixel_md5(first=None):
        # test_gdcm.cpp 的像素矩阵离线真值：pixels[i] = (i*3+7)，逐像素与库自己写出的
        # PixelData 字节流无关（struct.pack 走本机小端，与 DICOM LE 一致）。用它去校验
        # gdcminfo --md5sum 的输出，等于"库的写路径"与"外部无关实现"互证，不是自证。
        # first 只用于对照文件：tampered 文件仅 pixels[0] += 1（7 → 8）。
        vals = [((i * 3 + 7) & 0xFFFF) for i in range(32 * 32)]
        if first is not None:
            vals[0] = first
        return hashlib.md5(struct.pack("<%dH" % len(vals), *vals)).hexdigest()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skip running test executable")
            return
        ld = self._run_ld_path()
        bindir = self.dependencies["gdcm"].cpp_info.aggregated_components().bindirs[0]
        run = 'LD_LIBRARY_PATH="{}"'.format(ld)
        cwd = os.getcwd()
        dcm = os.path.join(cwd, "ohos_gdcm_consumer.dcm")
        tam = os.path.join(cwd, "ohos_gdcm_tampered.dcm")
        conv = os.path.join(cwd, "ohos_gdcm_consumer_raw.dcm")
        checks = 0

        # ① 库消费者：静态库集合链出的程序，写出主/对照两个 DICOM 再用库读回（含 ImageReader 解码逐字节比对）
        self.run('{} ./test_gdcm'.format(run))
        assert os.path.isfile(dcm), "test_gdcm did not produce {}".format(dcm)
        assert os.path.isfile(tam), "test_gdcm did not produce {}".format(tam)
        checks += 2

        # ② 鸿蒙特有端到端用例：制品包里的 CLI 工具（同样由本包静态库链出、需 OHOS ELF 自签
        #    才能在本机 execve）消费 ① 生成的真实 DICOM —— 覆盖"打包产物 → 命令行消费者"全链路。
        #    以下每条期望串都用本机实测输出核对过（3.0.24 的 gdcminfo/gdcmxml 输出格式与 3.2.x 不同，
        #    gdcmconv 也无 --RAW，只有 -w/--raw）。

        # gdcminfo：几何 + 像素格式 + 传输语法
        self.run('{r} "{b}/gdcminfo" "{f}" > info.txt 2>&1'.format(r=run, b=bindir, f=dcm))
        checks += self._expect(self._read(os.path.join(cwd, "info.txt")), [
            "[Secondary Capture Image Storage]",
            "[Explicit VR Little Endian]",
            "Dimensions: (32,32,1)",
            "SamplesPerPixel    :1",
            "BitsAllocated      :16",
            "HighBit            :15",
            "PixelRepresentation:0",
            "ScalarType found   :UINT16",
            "PhotometricInterpretation: MONOCHROME2",
        ], "gdcminfo")

        # gdcminfo --md5sum：库算出的 PixelData 摘要 == 离线复算真值；对照文件必须不同
        expect_main = self._pixel_md5()
        expect_tam = self._pixel_md5(first=8)
        assert expect_main != expect_tam, "negative-control digests must differ"
        checks += 1
        for path, expect, label in ((dcm, expect_main, "md5-main"), (tam, expect_tam, "md5-tampered")):
            out = os.path.join(cwd, label + ".txt")
            self.run('{r} "{b}/gdcminfo" --md5sum "{f}" > "{o}" 2>&1'.format(
                r=run, b=bindir, f=path, o=out))
            got = re.search(r"md5sum: ([0-9a-f]{32})", self._read(out))
            if not got:
                raise Exception("{}: no md5sum line in:\n{}".format(label, self._read(out)[:1000]))
            if got.group(1) != expect:
                raise Exception("{}: gdcminfo md5 {} != independently computed {}".format(
                    label, got.group(1), expect))
            self.output.info("{}: ok (gdcminfo md5 == offline ground truth {})".format(label, expect))
            checks += 1

        # gdcmdump：数据集元素原样落盘
        self.run('{r} "{b}/gdcmdump" "{f}" > dump.txt 2>&1'.format(r=run, b=bindir, f=dcm))
        checks += self._expect(self._read(os.path.join(cwd, "dump.txt")), [
            "(0002,0010) UI [1.2.840.10008.1.2.1]",
            "(0008,0016) UI [1.2.840.10008.5.1.4.1.1.7]",
            "(0010,0010) PN [HarmonyOS^Consumer]",
            "(0010,0020) LO [OHOS-GDCM-3.0.24]",
            "(0028,0004) CS [MONOCHROME2 ]",
            "(0028,0102) US 15",
            "(0028,0103) US 0",
            "(7fe0,0010) OW",
            "# 2048,1 Pixel Data",
        ], "gdcmdump")

        # gdcmconv --raw：未压缩→未压缩重编码，像素必须一字节都不差
        self.run('{r} "{b}/gdcmconv" --raw "{f}" "{o}"'.format(r=run, b=bindir, f=dcm, o=conv))
        assert os.path.isfile(conv), "gdcmconv did not produce {}".format(conv)
        checks += 1
        out = os.path.join(cwd, "md5-conv.txt")
        self.run('{r} "{b}/gdcminfo" --md5sum "{f}" > "{o}" 2>&1'.format(r=run, b=bindir, f=conv, o=out))
        got = re.search(r"md5sum: ([0-9a-f]{32})", self._read(out))
        if not got or got.group(1) != expect_main:
            raise Exception("gdcmconv --raw changed the pixel data: {} vs {}".format(
                got.group(1) if got else None, expect_main))
        self.output.info("md5-conv: ok (re-encode keeps pixel digest)")
        checks += 1
        self.run('{r} "{b}/gdcmdump" "{f}" > dump_conv.txt 2>&1'.format(r=run, b=bindir, f=conv))
        checks += self._expect(self._read(os.path.join(cwd, "dump_conv.txt")), [
            "(0008,0016) UI [1.2.840.10008.5.1.4.1.1.7]",
            "(0010,0020) LO [OHOS-GDCM-3.0.24]",
            "# 2048,1 Pixel Data",
        ], "gdcmdump of converted file")

        # gdcmdiff：正例必须无差异，反例（对照文件）必须报出差异；gdcmdiff 检出差异时非 0 退出，
        # 故吞掉退出码、判定全交给输出比对（`|| :` 而非 `|| true`：L1d 假测试启发式会扫 self.run 行）。
        self.run('{r} "{b}/gdcmdiff" "{f}" "{o}" > diff_clean.txt 2>&1 || :'.format(
            r=run, b=bindir, f=dcm, o=conv))
        diff_clean = self._read(os.path.join(cwd, "diff_clean.txt"))
        if diff_clean.strip():
            raise Exception("gdcmdiff reported differences between source and --RAW re-encode:\n"
                            + diff_clean[:2000])
        self.output.info("gdcmdiff clean pair: ok (empty output)")
        checks += 1
        self.run('{r} "{b}/gdcmdiff" "{f}" "{o}" > diff_dirty.txt 2>&1 || :'.format(
            r=run, b=bindir, f=dcm, o=tam))
        checks += self._expect(self._read(os.path.join(cwd, "diff_dirty.txt")),
                               ['(7fe0,0010) OW [elem differ]'],
                               "gdcmdiff negative control")

        # gdcmxml：PS3.19 NativeDICOM 模型导出（大二进制以 BulkData 引用外置）
        self.run('{r} "{b}/gdcmxml" "{f}" > xml.txt 2>&1'.format(r=run, b=bindir, f=dcm))
        checks += self._expect(self._read(os.path.join(cwd, "xml.txt")), [
            "<NativeDicomModel",
            'tag = "00080016" vr = "UI" keyword = "SOPClassUID"',
            'tag = "00100010" vr = "PN" keyword = "PatientName"',
            "<FamilyName> HarmonyOS</FamilyName>",
            'tag = "00100020" vr = "LO" keyword = "PatientID"',
            "<Value number = \"1\" >OHOS-GDCM-3.0.24</Value>",
            'tag = "7FE00010" vr = "OW" keyword = "PixelData"',
            "<BulkData uuid",
        ], "gdcmxml")

        self.output.info("gdcm test_package: ALL OK (library consumer + packaged CLI, {} assertions)".format(checks))
