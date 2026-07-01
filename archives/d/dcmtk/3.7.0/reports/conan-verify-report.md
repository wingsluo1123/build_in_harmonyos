# Conan Verify Report — dcmtk 3.7.0

**Verdict**: PASS
**Reference**: `dcmtk/3.7.0@ohpcd/stable`
**Profile**: ohos-aarch64-local
**Date**: 2026-06-30T18:36:14.292682

## G0: ✅ PASS
  📦 构建系统: cmake
  ✅ 已知风险 E092 已在配方中处理
     CMake 不认识 HarmonyOS 作为目标平台，
没有对应的 platform module。
当 CMake 检测到系统名称为 harmonyos/ohos 时，
无法匹配任何已知平台（Lin

## G1: ✅ PASS
  ✅ name 声明
  ✅ version 声明
  ✅ source() 方法
  ✅ build() 方法
  ✅ package() 方法
  ✅ package_info() 方法
  ✅ export_sources() 方法
  ✅ 补丁应用调用
  ✅ R26: 系统同名库静态链接配置存在
  ✅ conandata.yml 完整
  ✅ test_package/ 存在 (R28)

## G2: ✅ PASS
  ✅ conan create 成功
  📄 日志: archives/d/dcmtk/3.7.0/reports/conan-create.log

## G3: ✅ PASS
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS
  ✅ bin/: 66 个文件
  ✅ lib/: 29 .a + 0 .so
  ✅ include/: 1016 个头文件

## L2: ✅ PASS
  ✅ cda2dcm: $dcmtk: dcmencap v3.7.0 2025-12-15 $
  ✅ dcm2cda: $dcmtk: dcmdecap v3.7.0 2025-12-15 $
  ✅ dcm2img: $dcmtk: dcm2img v3.7.0 2025-12-15 $
  ✅ dcm2json: $dcmtk: dcm2json v3.7.0 2025-12-15 $
  ✅ dcm2pdf: $dcmtk: dcmdecap v3.7.0 2025-12-15 $
  ✅ dcm2pnm: $dcmtk: dcm2img v3.7.0 2025-12-15 $
  ✅ dcm2xml: $dcmtk: dcm2xml v3.7.0 2025-12-15 $
  ✅ dcmcjpeg: $dcmtk: dcmcjpeg v3.7.0 2025-12-15 $
  ✅ dcmcjpls: $dcmtk: dcmcjpls v3.7.0 2025-12-15 $
  ✅ dcmconv: $dcmtk: dcmconv v3.7.0 2025-12-15 $
  ✅ dcmcrle: $dcmtk: dcmcrle v3.7.0 2025-12-15 $
  ✅ dcmdecap: $dcmtk: dcmdecap v3.7.0 2025-12-15 $
  ✅ dcmdjpeg: $dcmtk: dcmdjpeg v3.7.0 2025-12-15 $
  ✅ dcmdjpls: $dcmtk: dcmdjpls v3.7.0 2025-12-15 $
  ✅ dcmdrle: $dcmtk: dcmdrle v3.7.0 2025-12-15 $
  ✅ dcmdspfn: $dcmtk: dcmdspfn v3.7.0 2025-12-15 $
  ✅ dcmdump: $dcmtk: dcmdump v3.7.0 2025-12-15 $
  ✅ dcmencap: $dcmtk: dcmencap v3.7.0 2025-12-15 $
  ⚠️ dcmftest: --version 和 --help 均失败
  ✅ dcmgpdir: $dcmtk: dcmmkdir v3.7.0 2025-12-15 $
  ✅ dcmicmp: $dcmtk: dcmicmp v3.7.0 2025-12-15 $
  ✅ dcmj2pnm: $dcmtk: dcm2img v3.7.0 2025-12-15 $
  ✅ dcml2pnm: $dcmtk: dcm2img v3.7.0 2025-12-15 $
  ✅ dcmmkcrv: $dcmtk: dcmmkcrv v3.7.0 2025-12-15 $
  ✅ dcmmkdir: $dcmtk: dcmmkdir v3.7.0 2025-12-15 $
  ✅ dcmmklut: $dcmtk: dcmmklut v3.7.0 2025-12-15 $
  ✅ dcmodify: $dcmtk: dcmodify v3.7.0 2025-12-15 $
  ✅ dcmp2pgm: $dcmtk: dcmp2pgm v3.7.0 2025-12-15 $
  ✅ dcmprscp: $dcmtk: dcmprscp v3.7.0 2025-12-15 $
  ✅ dcmprscu: $dcmtk: dcmprscu v3.7.0 2025-12-15 $
  ✅ dcmpschk: $dcmtk: dcmpschk v3.7.0 2025-12-15 $
  ✅ dcmpsmk: $dcmtk: dcmpsmk v3.7.0 2025-12-15 $
  ✅ dcmpsprt: $dcmtk: dcmpsprt v3.7.0 2025-12-15 $
  ✅ dcmpsrcv: $dcmtk: dcmpsrcv v3.7.0 2025-12-15 $
  ✅ dcmpssnd: $dcmtk: dcmpssnd v3.7.0 2025-12-15 $
  ✅ dcmqridx: $dcmtk: dcmqridx v3.7.0 2025-12-15 $
  ✅ dcmqrscp: $dcmtk: dcmqrscp v3.7.0 2025-12-15 $
  ✅ dcmqrti: $dcmtk: dcmqrti v3.7.0 2025-12-15 $
  ✅ dcmquant: $dcmtk: dcmquant v3.7.0 2025-12-15 $
  ✅ dcmrecv: $dcmtk: dcmrecv v3.7.0 2025-12-15 $
  ✅ dcmscale: $dcmtk: dcmscale v3.7.0 2025-12-15 $
  ✅ dcmsend: $dcmtk: dcmsend v3.7.0 2025-12-15 $
  ✅ dcmsign: $dcmtk: dcmsign v3.7.0 2025-12-15 $
  ✅ dcod2lum: $dcmtk: dcod2lum v3.7.0 2025-12-15 $
  ⚠️ dconvlum: --version 和 --help 均失败
  ✅ drtdump: $dcmtk: drtdump v3.7.0 2025-12-15 $
  ✅ dsr2html: $dcmtk: dsr2html v3.7.0 2025-12-15 $
  ✅ dsr2xml: $dcmtk: dsr2xml v3.7.0 2025-12-15 $
  ✅ dsrdump: $dcmtk: dsrdump v3.7.0 2025-12-15 $
  ✅ dump2dcm: $dcmtk: dump2dcm v3.7.0 2025-12-15 $
  ✅ echoscu: $dcmtk: echoscu v3.7.0 2025-12-15 $
  ✅ findscu: $dcmtk: findscu v3.7.0 2025-12-15 $
  ✅ getscu: $dcmtk: getscu v3.7.0 2025-12-15 $
  ✅ img2dcm: $dcmtk: img2dcm v3.7.0 2025-12-15 $
  ✅ json2dcm: $dcmtk: json2dcm v3.7.0 2025-12-15 $
  ⚠️ mkcsmapper: --version 和 --help 均失败
  ⚠️ mkesdb: --version 和 --help 均失败
  ✅ movescu: $dcmtk: movescu v3.7.0 2025-12-15 $
  ✅ pdf2dcm: $dcmtk: dcmencap v3.7.0 2025-12-15 $
  ✅ stl2dcm: $dcmtk: dcmencap v3.7.0 2025-12-15 $
  ✅ storescp: $dcmtk: storescp v3.7.0 2025-12-15 $
  ✅ storescu: $dcmtk: storescu v3.7.0 2025-12-15 $
  ✅ termscu: $dcmtk: termscu v3.7.0 2025-12-15 $
  ✅ wlmscpfs: $dcmtk: wlmscpfs v3.7.0 2025-12-15 $
  ✅ xml2dcm: $dcmtk: xml2dcm v3.7.0 2025-12-15 $
  ✅ xml2dsr: $dcmtk: xml2dsr v3.7.0 2025-12-15 $
  ⚠️ 4 个二进制文件无法运行: dcmftest, dconvlum, mkcsmapper, mkesdb

## L4: ✅ PASS
  ✅ 0 个 ELF 文件安全扫描通过

## L5: ✅ PASS
  ✅ 产物与基线完全一致 (1394 个文件)
