#include <boost/archive/text_oarchive.hpp>
#include <boost/program_options.hpp>
#include <boost/regex.hpp>
#include <boost/thread.hpp>

#include <sstream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    namespace po = boost::program_options;

    po::options_description options("options");
    options.add_options()
        ("name", po::value<std::string>()->required(), "name to validate")
        ("count", po::value<int>()->default_value(1), "thread increment count");

    po::variables_map vm;
    po::store(po::parse_command_line(argc, argv, options), vm);
    po::notify(vm);

    const std::string name = vm["name"].as<std::string>();
    const int count = vm["count"].as<int>();

    if (!boost::regex_match(name, boost::regex("[A-Za-z0-9_]+"))) {
        throw std::runtime_error("regex validation failed");
    }

    std::ostringstream buffer;
    boost::archive::text_oarchive archive(buffer);
    archive << name;
    archive << count;
    if (buffer.str().empty()) {
        throw std::runtime_error("serialization produced no output");
    }

    int value = 0;
    boost::thread worker([&value, count]() {
        for (int i = 0; i < count; ++i) {
            ++value;
        }
    });
    worker.join();

    if (value != count) {
        throw std::runtime_error("thread did not update value");
    }

    return 0;
}
