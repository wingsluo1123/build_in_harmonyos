// test_package/test_boost.cpp — boost 1.84.0 L1 smoke test.
// Exercises Boost.Filesystem, Boost.Regex, and Boost.ProgramOptions.
#include <boost/filesystem.hpp>
#include <boost/regex.hpp>
#include <boost/program_options.hpp>
#include <iostream>
#include <string>

namespace fs = boost::filesystem;
namespace po = boost::program_options;

int main(int argc, char *argv[]) {
    // Boost.Filesystem: create temp path, check it
    fs::path p("/tmp/boost_test_dir");
    if (!p.has_filename()) {
        std::cerr << "filesystem: path has no filename" << std::endl;
        return 1;
    }
    std::cout << "filesystem: path filename = " << p.filename() << std::endl;

    // Boost.Regex: match a pattern
    boost::regex re("(\\d+)-(\\d+)");
    boost::smatch what;
    std::string text = "version 1-84-0";
    if (!boost::regex_search(text, what, re)) {
        std::cerr << "regex: no match found" << std::endl;
        return 1;
    }
    std::cout << "regex: matched '" << what[0] << "'" << std::endl;

    // Boost.ProgramOptions: parse a simple option
    po::options_description desc("options");
    desc.add_options()
        ("help", "show help")
        ("name", po::value<std::string>(), "set name");

    po::variables_map vm;
    const char *fake_argv[] = {"test_boost", "--name=boost184"};
    try {
        po::store(po::parse_command_line(2, const_cast<char**>(fake_argv), desc), vm);
    } catch (const std::exception &e) {
        std::cerr << "program_options: parse failed: " << e.what() << std::endl;
        return 1;
    }
    if (vm.count("name") == 0) {
        std::cerr << "program_options: --name not found" << std::endl;
        return 1;
    }
    std::cout << "program_options: --name = " << vm["name"].as<std::string>() << std::endl;

    std::cout << "boost 1.84.0: filesystem + regex + program_options OK" << std::endl;
    return 0;
}
