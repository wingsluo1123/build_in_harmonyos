#include <vamp-hostsdk/Plugin.h>
#include <vamp-hostsdk/PluginLoader.h>

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>

static int fail(const std::string &message) {
    std::cerr << "FAIL: " << message << '\n';
    return 1;
}

int main(int argc, char **argv) {
    if (argc != 2) return fail("expected one case name");
    const std::string test_case = argv[1];
    if (test_case != "portable" && test_case != "ohos-storage") {
        return fail("unknown case");
    }

    auto *loader = Vamp::HostExt::PluginLoader::getInstance();
    const auto key = loader->composePluginKey("vamp-example-plugins",
                                               "zerocrossing");
    std::unique_ptr<Vamp::Plugin> plugin(loader->loadPlugin(key, 8000.0f));
    if (!plugin) return fail("could not load delivered example plugin");
    if (plugin->getIdentifier() != "zerocrossing") {
        return fail("wrong plugin loaded");
    }
    if (!plugin->initialise(1, 8, 8)) return fail("plugin initialisation");

    const float samples[8] = {1, 1, -1, -1, 1, 1, -1, -1};
    const float *channels[1] = {samples};
    const auto features = plugin->process(channels, Vamp::RealTime::zeroTime);
    auto count_output = features.find(0);
    auto timestamp_output = features.find(1);
    if (count_output == features.end() || count_output->second.size() != 1 ||
        count_output->second[0].values.size() != 1 ||
        std::fabs(count_output->second[0].values[0] - 4.0f) > 0.001f) {
        return fail("wrong zero-crossing count for synthetic audio");
    }
    if (timestamp_output == features.end() ||
        timestamp_output->second.size() != 4) {
        return fail("wrong number of located crossings");
    }
    for (size_t i = 0; i < 4; ++i) {
        if (!timestamp_output->second[i].hasTimestamp) {
            return fail("missing crossing timestamp");
        }
    }

    if (test_case == "ohos-storage") {
#ifndef __OHOS__
        return fail("OHOS case executed on a different platform");
#endif
        const char *directory = std::getenv("VAMP_OHOS_TEST_DIR");
        if (!directory) return fail("missing user-storage directory");
        const std::string path = std::string(directory) +
                                 "/vamp-sdk-e-crossings.txt";
        {
            std::ofstream output(path, std::ios::trunc);
            if (!output) return fail("cannot open user-storage output");
            output << count_output->second[0].values[0] << '\n';
            for (const auto &feature : timestamp_output->second) {
                output << feature.timestamp.sec << ':' << feature.timestamp.nsec
                       << '\n';
            }
            if (!output) return fail("cannot write feature output");
        }
        std::ifstream input(path);
        if (!input) return fail("cannot read persisted feature output");
        float persisted_count = -1;
        input >> persisted_count;
        if (std::fabs(persisted_count - 4.0f) > 0.001f) {
            return fail("persisted crossing count differs");
        }
        for (const auto &feature : timestamp_output->second) {
            std::string stored;
            if (!(input >> stored)) {
                return fail("missing persisted crossing timestamp");
            }
            const std::string expected =
                std::to_string(feature.timestamp.sec) + ':' +
                std::to_string(feature.timestamp.nsec);
            if (stored != expected) {
                return fail("persisted crossing timestamp differs");
            }
        }
        std::string extra;
        if (input >> extra) {
            return fail("unexpected persisted feature output");
        }
    }

    std::cout << "PASS " << test_case << ": loaded installed plugin, "
              << "processed 8 samples, verified 4 crossing features"
              << (test_case == "ohos-storage" ? " and persisted them" : "")
              << '\n';
    return 0;
}
