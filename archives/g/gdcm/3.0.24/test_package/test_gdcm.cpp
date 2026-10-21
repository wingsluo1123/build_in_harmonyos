// gdcm/3.0.24 test_package 消费程序：完整走一遍 "建 DICOM → 写盘 → 读回 → 取像素" 链路。
// 与 3.2.11 同族的字典/Attribute 检查之外，这里刻意不依赖任何外部 .dcm 样本：
// 文件由库自己生成，再被库读回，等价于一个离线可复现的真实消费者用例。
// 另外写出一个只差 1 个像素的副本，供 conanfile.py 侧的 CLI 用例做反向对照
// （证明 gdcmdiff / md5sum 不是"什么都比不出差别"的空断言）。
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "gdcmVersion.h"
#include "gdcmGlobal.h"
#include "gdcmDicts.h"
#include "gdcmDictEntry.h"
#include "gdcmTag.h"
#include "gdcmVR.h"
#include "gdcmAttribute.h"
#include "gdcmDataElement.h"
#include "gdcmDataSet.h"
#include "gdcmFile.h"
#include "gdcmFileMetaInformation.h"
#include "gdcmTransferSyntax.h"
#include "gdcmReader.h"
#include "gdcmWriter.h"
#include "gdcmImage.h"
#include "gdcmImageReader.h"

#define CHECK(cond, msg) do { if (!(cond)) { \
    fprintf(stderr, "FAIL: %s\n", std::string(msg).c_str()); return 1; } } while (0)

static const char *OUTFILE = "ohos_gdcm_consumer.dcm";
static const char *OUTFILE_TAMPERED = "ohos_gdcm_tampered.dcm";
static const unsigned int ROWS = 32;
static const unsigned int COLS = 32;

typedef std::vector<unsigned short> Pixels;

// 用库 API 组一个合法的 Secondary Capture（PS3.10 A.2, Explicit VR Little Endian）并写盘。
// 像素值完全由 (i*3+7) 决定，测试侧可离线复算 → 与 CLI 的 md5sum 互为交叉验证。
static bool write_sc_file(const Pixels &pixels, const char *path)
{
    gdcm::Writer writer;
    writer.SetFileName(path);
    gdcm::File &file = writer.GetFile();
    gdcm::DataSet &ds = file.GetDataSet();

    gdcm::Attribute<0x0008, 0x0016> attrSOPClass;
    attrSOPClass.SetValue("1.2.840.10008.5.1.4.1.1.7"); // Secondary Capture Image Storage
    ds.Replace(attrSOPClass.GetAsDataElement());
    gdcm::Attribute<0x0008, 0x0018> attrSOPInst;
    attrSOPInst.SetValue("1.2.840.113619.2.552.20261018.1");
    ds.Replace(attrSOPInst.GetAsDataElement());
    gdcm::Attribute<0x0008, 0x0060> attrMod;
    attrMod.SetValue("SC");
    ds.Replace(attrMod.GetAsDataElement());
    gdcm::Attribute<0x0010, 0x0010> attrPN;
    attrPN.SetValue("HarmonyOS^Consumer");
    ds.Replace(attrPN.GetAsDataElement());
    gdcm::Attribute<0x0010, 0x0020> attrPID;
    attrPID.SetValue("OHOS-GDCM-3.0.24");
    ds.Replace(attrPID.GetAsDataElement());
    gdcm::Attribute<0x0020, 0x000d> attrStudy;
    attrStudy.SetValue("1.2.840.113619.2.552.20261018.2");
    ds.Replace(attrStudy.GetAsDataElement());
    gdcm::Attribute<0x0020, 0x000e> attrSeries;
    attrSeries.SetValue("1.2.840.113619.2.552.20261018.3");
    ds.Replace(attrSeries.GetAsDataElement());
    gdcm::Attribute<0x0028, 0x0002> attrSamples;
    attrSamples.SetValue((unsigned short)1);
    ds.Replace(attrSamples.GetAsDataElement());
    gdcm::Attribute<0x0028, 0x0004> attrPI;
    attrPI.SetValue("MONOCHROME2");
    ds.Replace(attrPI.GetAsDataElement());
    gdcm::Attribute<0x0028, 0x0010> attrRows;
    attrRows.SetValue((unsigned short)ROWS);
    ds.Replace(attrRows.GetAsDataElement());
    gdcm::Attribute<0x0028, 0x0011> attrCols;
    attrCols.SetValue((unsigned short)COLS);
    ds.Replace(attrCols.GetAsDataElement());
    gdcm::Attribute<0x0028, 0x0100> attrBitsAlloc;
    attrBitsAlloc.SetValue((unsigned short)16);
    ds.Replace(attrBitsAlloc.GetAsDataElement());
    gdcm::Attribute<0x0028, 0x0101> attrBitsStored;
    attrBitsStored.SetValue((unsigned short)16);
    ds.Replace(attrBitsStored.GetAsDataElement());
    gdcm::Attribute<0x0028, 0x0102> attrHighBit;   // High Bit（0x0103 是 Pixel Representation）
    attrHighBit.SetValue((unsigned short)15);
    ds.Replace(attrHighBit.GetAsDataElement());
    gdcm::Attribute<0x0028, 0x0103> attrPixRep;    // Pixel Representation: 0 = unsigned
    attrPixRep.SetValue((unsigned short)0);
    ds.Replace(attrPixRep.GetAsDataElement());

    gdcm::DataElement dePixel(gdcm::Tag(0x7fe0, 0x0010));
    dePixel.SetByteValue((const char *)pixels.data(),
                         (gdcm::VL)(pixels.size() * sizeof(unsigned short)));
    dePixel.SetVR(gdcm::VR::OW);
    ds.Replace(dePixel);

    // 文件头（File Meta Information）：与上游 PixmapWriter::PrepareWrite 同一写法
    gdcm::FileMetaInformation &fmi = file.GetHeader();
    fmi.Clear();
    gdcm::DataElement deTS(gdcm::Tag(0x0002, 0x0010));
    const char *tsstr = gdcm::TransferSyntax::GetTSString(gdcm::TransferSyntax::ExplicitVRLittleEndian);
    deTS.SetByteValue(tsstr, (gdcm::VL)strlen(tsstr));
    deTS.SetVR(gdcm::Attribute<0x0002, 0x0010>::GetVR());
    fmi.Replace(deTS);
    fmi.SetDataSetTransferSyntax(gdcm::TransferSyntax(gdcm::TransferSyntax::ExplicitVRLittleEndian));
    fmi.FillFromDataSet(ds);
    writer.SetCheckFileMetaInformation(false);

    return writer.Write();
}

int main() {
    printf("GDCM version: %s\n", gdcm::Version::GetVersion());

    // 1) 数据字典（gdcmDICT）：标签名查询
    const gdcm::Global &g = gdcm::Global::GetInstance();
    const gdcm::Dicts &dicts = g.GetDicts();
    const gdcm::DictEntry &entry = dicts.GetDictEntry(gdcm::Tag(0x0002, 0x0010));
    CHECK(!std::string(entry.GetName()).empty(), "DictEntry for TransferSyntaxUID (0002,0010) is empty");
    printf("Dict lookup (0002,0010) => %s\n", entry.GetName());
    CHECK(!std::string(dicts.GetDictEntry(gdcm::Tag(0x7fe0, 0x0010)).GetName()).empty(),
          "PixelData dict entry empty");

    // 2) 强类型 Attribute 的定长填充语义（PS3.5 6.2 强制偶数长度，gdcm::Attribute 原样保留
    //    pad、GetValue() 不 trim）：奇数长度 UI 补 0x00、奇数长度 CS 补空格，偶数长度不补。
    const std::string uid25 = "1.2.840.10008.5.1.4.1.1.7"; // 25 字符，奇数
    gdcm::Attribute<0x0008, 0x0016> uiOdd;
    uiOdd.SetValue(uid25.c_str());
    std::string uiOut = uiOdd.GetValue();
    CHECK(uiOut.size() == 26, "odd-length UI must pad to even (26), got " + std::to_string(uiOut.size()));
    CHECK(uiOut.compare(0, uid25.size(), uid25) == 0, "UI payload must keep the UID prefix");
    CHECK(uiOut[25] == '\0', "UI pad byte must be NUL per PS3.5 6.2");

    const std::string uid22 = "1.2.840.113619.2.552.1";    // 22 字符，偶数
    gdcm::Attribute<0x0008, 0x0018> uiEven;
    uiEven.SetValue(uid22.c_str());
    CHECK(uiEven.GetValue() == uid22, "even-length UI must not be padded");

    gdcm::Attribute<0x0028, 0x0004> csOdd;
    csOdd.SetValue("MONOCHROME2");                          // 11 字符，奇数
    std::string csOut = csOdd.GetValue();
    CHECK(csOut.size() == 12, "odd-length CS must pad to even (12), got " + std::to_string(csOut.size()));
    CHECK(csOut[11] == ' ', "CS pad byte must be space per PS3.5 6.2");

    // 3) 生成像素 + 写盘（主文件与只差 pixels[0] 的对照文件）
    Pixels pixels(ROWS * COLS);
    for (size_t i = 0; i < pixels.size(); ++i) {
        pixels[i] = (unsigned short)(i * 3u + 7u);
    }
    CHECK(write_sc_file(pixels, OUTFILE), "Writer::Write of the generated Secondary Capture file");
    Pixels tampered = pixels;
    tampered[0] = (unsigned short)(tampered[0] + 1u);
    CHECK(write_sc_file(tampered, OUTFILE_TAMPERED), "Writer::Write of the tampered control file");

    // 4) 读回（gdcmDSED Reader）：元数据 + 像素字节逐字节比对
    gdcm::TransferSyntax const ts(gdcm::TransferSyntax::ExplicitVRLittleEndian);
    gdcm::Reader reader;
    reader.SetFileName(OUTFILE);
    CHECK(reader.Read(), "Reader::Read of the file GDCM just wrote");
    CHECK(reader.GetFile().GetHeader().GetDataSetTransferSyntax() == ts, "TransferSyntax roundtrip");
    const gdcm::DataSet &rds = reader.GetFile().GetDataSet();
    gdcm::Attribute<0x0010, 0x0010> rdnPN;
    rdnPN.SetFromDataSet(rds);
    CHECK(rdnPN.GetValue() == "HarmonyOS^Consumer", "PatientName roundtrip");
    gdcm::Attribute<0x0028, 0x0010> rdnRows;
    rdnRows.SetFromDataSet(rds);
    CHECK(rdnRows.GetValue() == ROWS, "Rows roundtrip");
    const gdcm::DataElement *rdnPd = &rds.GetDataElement(gdcm::Tag(0x7fe0, 0x0010));
    const gdcm::ByteValue *bv = rdnPd->GetByteValue();
    CHECK(bv && bv->GetLength() == pixels.size() * sizeof(unsigned short), "PixelData length roundtrip");
    CHECK(bv && memcmp(bv->GetPointer(), pixels.data(), bv->GetLength()) == 0, "PixelData bytes roundtrip");

    // 5) 高层图像接口（gdcmMSFF ImageReader）：维度/像素格式/解码缓冲
    gdcm::ImageReader ireader;
    ireader.SetFileName(OUTFILE);
    CHECK(ireader.Read(), "ImageReader::Read");
    const gdcm::Image &img = ireader.GetImage();
    const unsigned int *dims = img.GetDimensions();
    CHECK(dims[0] == ROWS && dims[1] == COLS, "Image dimensions");
    CHECK(img.GetPixelFormat().GetBitsAllocated() == 16, "PixelFormat bits allocated");
    CHECK(img.GetPixelFormat().GetHighBit() == 15, "PixelFormat high bit");
    CHECK(img.GetPixelFormat().GetPixelRepresentation() == 0, "PixelFormat must be unsigned");
    const unsigned long blen = img.GetBufferLength();
    CHECK(blen == pixels.size() * sizeof(unsigned short), "Image buffer length");
    std::vector<char> buf(blen);
    CHECK(img.GetBuffer(buf.data()), "Image::GetBuffer");
    CHECK(memcmp(buf.data(), pixels.data(), blen) == 0, "decoded pixel bytes identical to source");

    // 6) 对照文件必须真的不同（否则后续 gdcmdiff/md5sum 的反向断言是空的）
    gdcm::ImageReader treader;
    treader.SetFileName(OUTFILE_TAMPERED);
    CHECK(treader.Read(), "ImageReader::Read of control file");
    const gdcm::Image &timg = treader.GetImage();
    std::vector<char> tbuf(timg.GetBufferLength());
    CHECK(timg.GetBuffer(tbuf.data()), "Image::GetBuffer of control file");
    CHECK(tbuf.size() == buf.size(), "control file must decode to the same buffer size");
    const unsigned short *td = (const unsigned short *)tbuf.data();
    CHECK(td[0] == pixels[0] + 1u, "control pixel[0] must be exactly +1");
    CHECK(memcmp(tbuf.data(), buf.data(), tbuf.size()) != 0,
          "control file must differ from the main one (diff/md5 negative control would be vacuous otherwise)");

    printf("wrote+read back %u x %u 16-bit DICOM (%lu bytes pixel data) + tampered control\n",
           ROWS, COLS, blen);
    printf("gdcm test_package: ALL OK\n");
    return 0;
}
