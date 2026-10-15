# Keep Basix's actual upstream minimum without overriding a consumer's C++23.
if(TARGET Basix::basix)
  target_compile_features(Basix::basix INTERFACE cxx_std_20)
endif()
