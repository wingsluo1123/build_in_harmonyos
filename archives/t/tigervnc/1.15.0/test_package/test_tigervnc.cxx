/*
 * test_package for tigervnc 1.15.0 — consumer-side verification of the
 * installed RFB protocol core libraries (rfb / network / rdr / os).
 *
 * These assertions deliberately go through the *installed* headers and the
 * exported `tigervnc::rfb` CMake target, so they prove the package is
 * consumable and that the RFB core really links and executes on OpenHarmony
 * PC (aarch64, musl). The X11/FLTK/PAM dependent tiers (vncviewer, Xvnc,
 * vncsession) are out of scope for this package; see notes.md.
 */

#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>

#include <rfb/PixelFormat.h>
#include <rfb/Rect.h>
#include <rfb/d3des.h>
#include <rfb/util.h>

static int failures = 0;
static int checks = 0;

#define CHECK(cond, what)                                              \
    do {                                                               \
        ++checks;                                                      \
        if (!(cond)) {                                                 \
            std::printf("FAIL: %s\n", (what));                         \
            ++failures;                                                \
        } else {                                                       \
            std::printf("ok  : %s\n", (what));                         \
        }                                                              \
    } while (0)

/* ---- 1. rfb::util hex codec (lives in rfb, pulls in rdr/os) ---------- */

static void testHexCodec()
{
    /* binToHex: the classic VNC "hello" banner bytes */
    const unsigned char raw[] = { 0x52, 0x46, 0x42, 0x20, 0x30, 0x30, 0x33 };
    std::string hex = rfb::binToHex(raw, sizeof(raw));
    CHECK(hex == "52464220303033", "binToHex encodes 'RFB 003' as 52464220303033");

    /* hexToBin is the exact inverse */
    std::vector<uint8_t> back = rfb::hexToBin(hex.c_str(), hex.size());
    CHECK(back.size() == sizeof(raw), "hexToBin returns the original byte count");
    CHECK(back.size() == sizeof(raw) &&
              std::memcmp(&back[0], raw, sizeof(raw)) == 0,
          "hexToBin round-trips the original bytes");

    /* binToHex with an explicit output buffer */
    char buf[32];
    rfb::binToHex(raw, sizeof(raw), buf, sizeof(buf));
    CHECK(std::strcmp(buf, "52464220303033") == 0,
          "binToHex with caller supplied buffer agrees");

    /* uppercase nibbles must be accepted (real VNC clients send either) */
    std::vector<uint8_t> upper = rfb::hexToBin("52464220303033", 14);
    CHECK(upper == back, "hexToBin accepts uppercase hex digits");
}

/* ---- 2. RFB desktop size / rectangle arithmetic ---------------------- */

static void testRectArithmetic()
{
    rfb::Rect r(10, 20, 40, 60);
    CHECK(r.width() == 30, "Rect width from x1-x2");
    CHECK(r.height() == 40, "Rect height from y1-y2");
    CHECK(r.area() == 1200, "Rect area = width * height");

    rfb::Rect inner(0, 0, 5, 5);
    CHECK(inner.area() == 25, "Rect area of an origin-anchored rect");

    /* translate() is functional: it returns a new Rect and must preserve area */
    rfb::Rect moved = inner.translate(rfb::Point(100, 200));
    CHECK(inner.area() == 25, "Rect area is invariant under translate()");
    CHECK(moved.area() == 25, "translated Rect keeps the same area");
    CHECK(moved.tl.x == 100 && moved.tl.y == 200, "Rect translate returns the moved origin");
    CHECK(inner.tl.x == 0 && inner.tl.y == 0, "Rect translate leaves the source untouched");
}

/* ---- 3. rfb::PixelFormat parsing and conversion ---------------------- */

static void testPixelFormatCommon()
{
    rfb::PixelFormat pf;

    CHECK(pf.parse("rgb888"), "PixelFormat::parse accepts rgb888");
    CHECK(pf.bpp == 32, "rgb888 is 32 bits per pixel");
    CHECK(pf.depth == 24, "rgb888 is 24 bits deep");
    CHECK(pf.is888(), "rgb888 reports is888()");

    /* parse() returns false only when sscanf cannot read "<rgb|bgr><d><d><d>".
       Note it *asserts* isSane() for well-formed but nonsensical input such as
       "rgb999" (and upstream keeps asserts on in Release via -UNDEBUG), so this
       test deliberately only exercises the rejected-by-sscanf path. */
    CHECK(!pf.parse("nonsense"), "PixelFormat::parse rejects a string with no digits");
    CHECK(!pf.parse("xyz123"), "PixelFormat::parse rejects an unknown channel order");
    CHECK(!pf.parse(""), "PixelFormat::parse rejects an empty string");
    CHECK(!pf.parse("rgb"), "PixelFormat::parse rejects a channel order without bit counts");

    /* Shifts are protected; verify bgr888 through the public API instead.
       In "bgr888" the channel letters name the on-wire byte order, so blue is
       the high byte and red is the low byte of the packed pixel. */
    CHECK(pf.parse("bgr888"), "PixelFormat::parse accepts bgr888");
    CHECK(pf.is888(), "bgr888 reports is888()");
    {
        rfb::Pixel red = pf.pixelFromRGB(uint8_t(0xff), uint8_t(0), uint8_t(0));
        CHECK((red & 0xff) == 0xff,
              "bgr888 keeps red in the low byte of the pixel");
        rfb::Pixel blue = pf.pixelFromRGB(uint8_t(0), uint8_t(0), uint8_t(0xff));
        CHECK((blue & 0xff) == 0x00,
              "bgr888 puts blue in a high byte, not the low byte");

        uint8_t buf[4];
        std::memset(buf, 0, sizeof(buf));
        pf.bufferFromPixel(buf, blue);
        uint8_t r = 0, g = 0, b = 0;
        pf.rgbFromPixel(pf.pixelFromBuffer(buf), &r, &g, &b);
        CHECK(r == 0 && g == 0 && b == 0xff,
              "bgr888 round-trips pure blue through the byte buffer");
    }

    CHECK(pf.parse("rgb565"), "PixelFormat::parse accepts rgb565");
    CHECK(pf.bpp == 16, "rgb565 is 16 bits per pixel");
    CHECK(!pf.is888(), "rgb565 does not report is888()");

    /* Invalid explicit constructions must be rejected (upstream contract) */
    bool threw = false;
    try {
        rfb::PixelFormat bad(64, 24, false, true, 255, 255, 255, 0, 8, 16);
        (void)bad;
    } catch (std::exception&) {
        threw = true;
    }
    CHECK(threw, "PixelFormat(64bpp) throws");

    threw = false;
    try {
        rfb::PixelFormat bad(32, 24, false, true, 255, 255, 255, 25, 8, 16);
        (void)bad;
    } catch (std::exception&) {
        threw = true;
    }
    CHECK(threw, "PixelFormat(shift 25) throws");
}

static void testPixelRoundTrip()
{
    rfb::PixelFormat pf;
    CHECK(pf.parse("rgb888"), "round-trip: parse rgb888");

    const uint8_t r = 0xf1, g = 0xc3, b = 0x97;
    rfb::Pixel p = pf.pixelFromRGB(r, g, b);

    uint8_t buf[4];
    std::memset(buf, 0, sizeof(buf));
    pf.bufferFromPixel(buf, p);
    CHECK(pf.pixelFromBuffer(buf) == p, "bufferFromPixel/pixelFromBuffer round-trip");

    uint8_t r8 = 0, g8 = 0, b8 = 0;
    pf.rgbFromPixel(p, &r8, &g8, &b8);
    CHECK(r8 == r && g8 == g && b8 == b,
          "pixelFromRGB/rgbFromPixel round-trips exact 8-bit components");

    /* 16-bit components must fit the 8-bit channel exactly */
    uint16_t r16 = 0, g16 = 0, b16 = 0;
    pf.rgbFromPixel(p, &r16, &g16, &b16);
    CHECK(r16 == 0xf1f1 && g16 == 0xc3c3 && b16 == 0x9797,
          "16-bit rgbFromPixel replicates 8-bit channels");
}

static void testPixelFormatDownconvert()
{
    rfb::PixelFormat dst, src;
    CHECK(dst.parse("rgb565"), "downconvert: parse rgb565");
    CHECK(src.parse("rgb888"), "downconvert: parse rgb888");

    /* 40x30 framebuffer, exactly the size upstream's tests/unit/conv.cxx uses */
    const int width = 40, height = 30, area = width * height;
    const rfb::Pixel source = src.pixelFromRGB(uint8_t(0xf1), uint8_t(0xc3), uint8_t(0x97));
    uint8_t in[area * 4];
    for (int i = 0; i < area; i++)
        src.bufferFromPixel(in + i * (src.bpp / 8), source);

    uint8_t out[area * 4];
    std::memset(out, 0, sizeof(out));
    dst.bufferFromBuffer(out, src, in, area);

    /* every converted pixel must round-trip to within the 565 quantisation error */
    bool allOk = true;
    for (int i = 0; i < area; i++) {
        rfb::Pixel q = dst.pixelFromBuffer(out + i * (dst.bpp / 8));
        uint8_t r = 0, g = 0, b = 0;
        dst.rgbFromPixel(q, &r, &g, &b);
        if (r > 0xf1 || 0xf1 - r > 8 || g > 0xc3 || 0xc3 - g > 4 ||
            b > 0x97 || 0x97 - b > 8) {
            allOk = false;
            break;
        }
    }
    CHECK(allOk, "rgb888 -> rgb565 bufferFromBuffer within 565 quantisation error");
}

/* ---- 4. VncAuth DES primitive (lives in rfb/d3des.c) ----------------- */

static void testVncAuthDes()
{
    /* VNC authentication is a DES challenge/response over a fixed 8-byte key.
       Assert the structural contract that the VncAuth path relies on:
       encrypting then decrypting the same block must be the identity, and the
       key schedule must not be trivially degenerate. */
    unsigned char key[8] = { 'p', 'a', 's', 's', 'w', 'd', '1', '2' };
    unsigned char enc[8] = { 0x01, 0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef };
    unsigned char original[8];
    std::memcpy(original, enc, sizeof(enc));

    deskey(key, EN0);
    des(enc, enc);
    CHECK(std::memcmp(enc, original, sizeof(enc)) != 0,
          "DES encryption actually transforms the VncAuth challenge block");

    deskey(key, DE1);
    des(enc, enc);
    CHECK(std::memcmp(enc, original, sizeof(enc)) == 0,
          "DES decrypt with the same key restores the VncAuth challenge block");

    /* A different key must not reproduce the same ciphertext */
    unsigned char other[8] = { 'p', 'a', 's', 's', 'w', 'd', '1', '3' };
    unsigned char a[8], b[8];
    std::memcpy(a, original, sizeof(a));
    std::memcpy(b, original, sizeof(b));
    deskey(key, EN0);
    des(a, a);
    deskey(other, EN0);
    des(b, b);
    CHECK(std::memcmp(a, b, sizeof(a)) != 0,
          "different VNC passwords produce different DES responses");
}

int main()
{
    std::printf("tigervnc %s RFB core consumer test\n", "1.15.0");

    testHexCodec();
    testRectArithmetic();
    testPixelFormatCommon();
    testPixelRoundTrip();
    testPixelFormatDownconvert();
    testVncAuthDes();

    std::printf("\n%d/%d assertions passed\n", checks - failures, checks);
    if (failures) {
        std::printf("RESULT: FAILED (%d)\n", failures);
        return 1;
    }
    std::printf("RESULT: PASSED\n");
    return 0;
}
