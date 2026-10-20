/* Validates the WAVE file the packaged tao2wav/taosf produced from a Tao
 * .dat stream: RIFF/WAVE container, a PCM fmt chunk at the engine's sample
 * rate, a non-empty data chunk and a payload that actually carries signal.
 *
 * The parser walks the real chunk list instead of assuming a 44-byte header,
 * because libaudiofile is free to emit extra chunks (LIST/INFO ...).
 */
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>

namespace {

int failures = 0;

void check(bool ok, const char *what)
{
    std::cout << (ok ? "[ ok ] " : "[FAIL] ") << what << std::endl;
    if (!ok) ++failures;
}

unsigned int le32(const std::vector<unsigned char> &b, size_t offset)
{
    return static_cast<unsigned int>(b[offset]) |
           (static_cast<unsigned int>(b[offset + 1]) << 8) |
           (static_cast<unsigned int>(b[offset + 2]) << 16) |
           (static_cast<unsigned int>(b[offset + 3]) << 24);
}

unsigned int le16(const std::vector<unsigned char> &b, size_t offset)
{
    return static_cast<unsigned int>(b[offset]) |
           (static_cast<unsigned int>(b[offset + 1]) << 8);
}

}  // namespace

int main(int argc, char *argv[])
{
    if (argc < 2)
    {
        std::cerr << "usage: check_wav <file.wav>" << std::endl;
        return 2;
    }

    std::ifstream in(argv[1], std::ios::binary);
    const std::vector<unsigned char> bytes((std::istreambuf_iterator<char>(in)),
                                           std::istreambuf_iterator<char>());
    std::cout << "file=" << argv[1] << " bytes=" << bytes.size() << std::endl;

    check(bytes.size() >= 44, "file is large enough to hold a WAVE header");
    if (bytes.size() < 44)
        return 1;

    check(std::memcmp(&bytes[0], "RIFF", 4) == 0, "file starts with the RIFF magic");
    check(std::memcmp(&bytes[8], "WAVE", 4) == 0, "RIFF form type is WAVE");
    check(le32(bytes, 4) + 8 <= bytes.size(), "the RIFF size field matches the file length");

    size_t offset = 12;
    bool have_fmt = false;
    bool have_data = false;
    unsigned int audio_format = 0;
    unsigned int channels = 0;
    unsigned int sample_rate = 0;
    unsigned int bits = 0;
    size_t data_offset = 0;
    size_t data_size = 0;

    while (offset + 8 <= bytes.size())
    {
        const unsigned int size = le32(bytes, offset + 4);
        const size_t body = offset + 8;
        if (std::memcmp(&bytes[offset], "fmt ", 4) == 0 && body + 16 <= bytes.size())
        {
            have_fmt = true;
            audio_format = le16(bytes, body);
            channels = le16(bytes, body + 2);
            sample_rate = le32(bytes, body + 4);
            bits = le16(bytes, body + 14);
        }
        else if (std::memcmp(&bytes[offset], "data", 4) == 0)
        {
            have_data = true;
            data_offset = body;
            data_size = size;
        }
        offset = body + size + (size & 1);  // chunks are word aligned
    }

    check(have_fmt, "the file carries a fmt chunk");
    check(audio_format == 1, "the payload is uncompressed PCM");
    check(channels == 1 || channels == 2, "the payload is mono or stereo");
    check(sample_rate == 44100, "the sample rate is the engine's 44100 Hz");
    check(bits == 16, "samples are 16 bit");

    check(have_data, "the file carries a data chunk");
    check(data_size > 0, "the data chunk is not empty");
    check(data_offset + data_size <= bytes.size(), "the data chunk fits in the file");

    if (!have_data || data_offset + data_size > bytes.size())
        return 1;

    int peak = 0;
    int distinct = 0;
    int previous = 0;
    bool first = true;
    for (size_t i = data_offset; i + 1 < data_offset + data_size; i += 2)
    {
        const int sample = static_cast<short>(le16(bytes, i));
        const int magnitude = sample < 0 ? -sample : sample;
        if (magnitude > peak)
            peak = magnitude;
        if (first || sample != previous)
        {
            ++distinct;
            previous = sample;
            first = false;
        }
    }

    std::cout << "channels=" << channels << " rate=" << sample_rate
              << " bits=" << bits << " data_bytes=" << data_size
              << " peak=" << peak << " distinct=" << distinct << std::endl;

    check(peak > 0, "the converted waveform contains non-silent samples");
    check(distinct > 1, "the converted waveform is not a constant value");

    if (failures)
    {
        std::cerr << failures << " check(s) failed" << std::endl;
        return 1;
    }
    std::cout << "tao2wav WAVE validation passed" << std::endl;
    return 0;
}
