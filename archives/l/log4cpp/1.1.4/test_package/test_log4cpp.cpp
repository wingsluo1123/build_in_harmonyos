#include <log4cpp/BasicLayout.hh>
#include <log4cpp/Category.hh>
#include <log4cpp/NDC.hh>
#include <log4cpp/OstreamAppender.hh>
#include <log4cpp/Priority.hh>

#include <cstdlib>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << message << std::endl;
        std::abort();
    }
}

}  // namespace

int main() {
    std::ostringstream output;

    auto* appender = new log4cpp::OstreamAppender("stream", &output);
    appender->setLayout(new log4cpp::BasicLayout());

    log4cpp::Category& root = log4cpp::Category::getRoot();
    root.setPriority(log4cpp::Priority::WARN);
    root.addAppender(appender);

    root.info("hidden informational message");
    root.warn("visible warning message");
    const std::string first_log = output.str();
    require(first_log.find("visible warning message") != std::string::npos, "warn message missing");
    require(first_log.find("hidden informational message") == std::string::npos, "priority filter did not hide info");

    log4cpp::NDC::push("request-42");
    require(log4cpp::NDC::get() == "request-42", "NDC push/get failed");
    require(log4cpp::NDC::pop() == "request-42", "NDC pop failed");
    require(log4cpp::NDC::get().empty(), "NDC stack was not cleared");

    root << log4cpp::Priority::ERROR << "streamed error message";
    require(output.str().find("streamed error message") != std::string::npos, "Category stream API failed");

    log4cpp::Category::shutdown();
    return 0;
}
