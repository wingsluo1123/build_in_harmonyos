# MIME 集成：ECM 的 FindSharedMimeInfo 找的是 update-mime-database 工具
set(SHARED_MIME_INFO_MINIMUM_VERSION "0.23")
find_package(SharedMimeInfo REQUIRED)

install(FILES kf6-di-sample-mimetypes.xml DESTINATION ${KDE_INSTALL_MIMEDIR})
update_xdg_mimetypes(${KDE_INSTALL_MIMEDIR})
