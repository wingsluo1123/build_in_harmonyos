#ifndef QUORUM_PORTABLE_GZIP_STREAM_HPP
#define QUORUM_PORTABLE_GZIP_STREAM_HPP
#include <ostream>
#include <streambuf>
#include <stdexcept>
#include <limits>
#include <algorithm>
#include <zlib.h>

// zlib implements genuine gzip output without libstdc++'s private FILE adapter.
class gzip_output_buffer : public std::streambuf {
  gzFile file_;
protected:
  std::streamsize xsputn(const char* data, std::streamsize length) override {
    std::streamsize done = 0;
    while(file_ && done < length) {
      unsigned chunk = static_cast<unsigned>(std::min<std::streamsize>(length - done, 1024 * 1024));
      int written = gzwrite(file_, data + done, chunk);
      if(written <= 0) break;
      done += written;
    }
    return done;
  }
  int_type overflow(int_type value) override {
    if(traits_type::eq_int_type(value, traits_type::eof())) return traits_type::not_eof(value);
    char c = traits_type::to_char_type(value);
    return xsputn(&c, 1) == 1 ? value : traits_type::eof();
  }
  int sync() override {
    return file_ && gzflush(file_, Z_SYNC_FLUSH) == Z_OK ? 0 : -1;
  }
public:
  explicit gzip_output_buffer(const char* filename) : file_(gzopen(filename, "wb1")) {
    if(!file_) throw std::runtime_error("Cannot open gzip output");
  }
  int close() noexcept {
    if(!file_) return Z_OK;
    gzFile saved = file_;
    file_ = nullptr;
    return gzclose(saved);
  }
  ~gzip_output_buffer() { close(); }
};

class gzipstream : public std::ostream {
  gzip_output_buffer buffer_;
public:
  explicit gzipstream(const char* filename) : std::ostream(nullptr), buffer_(filename) {
    rdbuf(&buffer_);
  }
  void close() {
    flush();
    if(buffer_.close() != Z_OK) setstate(std::ios::badbit);
  }
  ~gzipstream() { buffer_.close(); }
};
#endif
