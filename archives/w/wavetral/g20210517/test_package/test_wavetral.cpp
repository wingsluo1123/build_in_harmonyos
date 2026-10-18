#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>

#ifndef WAVETRAL_BIN
#error "WAVETRAL_BIN must be defined by the build"
#endif

#ifndef SINE8_TXT
#error "SINE8_TXT must be defined by the build"
#endif

namespace {

int total = 0;
int failed = 0;

void check(bool condition, const std::string& what)
{
    ++total;
    if (condition) {
        std::cout << "ok   " << total << " - " << what << "\n";
    } else {
        ++failed;
        std::cout << "NOT OK " << total << " - " << what << "\n";
    }
}

int run(const std::string& command, const std::string& log)
{
    const std::string wrapped = command + " > " + log + " 2>&1";
    std::cerr << "[cmd] " << wrapped << "\n";
    return std::system(wrapped.c_str());
}

std::vector<double> read_values(const std::string& path)
{
    std::ifstream input(path);
    std::vector<double> values;
    double value = 0.0;
    while (input >> value) {
        values.push_back(value);
    }
    return values;
}

std::vector<std::uint8_t> read_bytes(const std::string& path)
{
    std::ifstream input(path, std::ios::binary);
    return std::vector<std::uint8_t>(
        std::istreambuf_iterator<char>(input),
        std::istreambuf_iterator<char>());
}

std::uint32_t le32(const std::vector<std::uint8_t>& bytes, std::size_t offset)
{
    return static_cast<std::uint32_t>(bytes[offset])
         | (static_cast<std::uint32_t>(bytes[offset + 1]) << 8)
         | (static_cast<std::uint32_t>(bytes[offset + 2]) << 16)
         | (static_cast<std::uint32_t>(bytes[offset + 3]) << 24);
}

std::uint16_t le16(const std::vector<std::uint8_t>& bytes, std::size_t offset)
{
    return static_cast<std::uint16_t>(bytes[offset])
         | (static_cast<std::uint16_t>(bytes[offset + 1]) << 8);
}

} // namespace

int main()
{
    std::cout << "== wavetral consumer test: " << WAVETRAL_BIN << " ==\n";

    int rc = run('"' + std::string(WAVETRAL_BIN) + "\" --version", "wavetral-version.txt");
    check(rc == 0, "version probe exits 0");
    std::ifstream version_file("wavetral-version.txt");
    std::string version_text{
        std::istreambuf_iterator<char>(version_file),
        std::istreambuf_iterator<char>()};
    check(version_text.find("Wavetral") != std::string::npos,
          "version banner identifies Wavetral");
    check(version_text.find("0.9.0") != std::string::npos,
          "version banner reports 0.9.0");

    rc = run('"' + std::string(WAVETRAL_BIN) + "\" -i \"" + SINE8_TXT
             + "\" -t wave -o wavetral-spectrum.txt -T harm -s 4",
             "wavetral-spectrum.log");
    check(rc == 0, "text wave to text spectrum exits 0");
    const std::vector<double> spectrum = read_values("wavetral-spectrum.txt");
    check(spectrum.size() == 4, "spectrum contains the requested four harmonics");
    check(spectrum.size() == 4 && std::fabs(spectrum[0] - 1.0) < 1e-4,
          "fundamental harmonic is normalized to one");
    check(spectrum.size() == 4
          && std::fabs(spectrum[1]) < 1e-4
          && std::fabs(spectrum[2]) < 1e-4
          && std::fabs(spectrum[3]) < 1e-4,
          "pure sine leaves upper harmonics below threshold");

    rc = run('"' + std::string(WAVETRAL_BIN) + "\" -i \"" + SINE8_TXT
             + "\" -t wave -o wavetral-sine16.wav -s 16 -r 44100",
             "wavetral-wav.log");
    check(rc == 0, "text wave to WAV exits 0");
    const std::vector<std::uint8_t> wav = read_bytes("wavetral-sine16.wav");
    check(wav.size() >= 44 && wav[0] == 'R' && wav[1] == 'I' && wav[2] == 'F'
          && wav[3] == 'F' && wav[8] == 'W' && wav[9] == 'A' && wav[10] == 'V'
          && wav[11] == 'E',
          "output has a RIFF/WAVE header");

    bool saw_fmt = false;
    bool saw_data = false;
    std::uint16_t channels = 0;
    std::uint16_t bits = 0;
    std::uint32_t rate = 0;
    std::uint32_t data_size = 0;
    if (wav.size() >= 12) {
        std::size_t offset = 12;
        while (offset + 8 <= wav.size()) {
            const std::string id(reinterpret_cast<const char*>(&wav[offset]), 4);
            const std::uint32_t size = le32(wav, offset + 4);
            if (offset + 8 + size > wav.size()) {
                break;
            }
            if (id == "fmt " && size >= 16) {
                saw_fmt = true;
                channels = le16(wav, offset + 10);
                rate = le32(wav, offset + 12);
                bits = le16(wav, offset + 22);
            } else if (id == "data") {
                saw_data = true;
                data_size = size;
            }
            offset += 8 + size + (size & 1);
        }
    }
    check(saw_fmt && channels == 1, "WAV fmt chunk declares one channel");
    check(saw_fmt && rate == 44100, "WAV fmt chunk preserves requested sample rate");
    check(saw_fmt && bits == 16, "WAV fmt chunk uses signed 16-bit samples");
    check(saw_data && data_size == 32, "WAV data chunk contains 16 mono frames");

    rc = run('"' + std::string(WAVETRAL_BIN) + "\" -i wavetral-missing-input.txt"
             " -t wave -o wavetral-missing-output.txt -T harm -s 4",
             "wavetral-missing.log");
    check(rc != 0, "missing input fails instead of pretending success");

    std::cout << (failed == 0 ? "15/15 checks passed" : "FAILED")
              << " (" << total << " checks)\n";
    return failed == 0 ? 0 : 1;
}
