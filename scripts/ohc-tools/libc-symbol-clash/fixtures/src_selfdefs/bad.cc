// fixture: 项目自身重定义 libc 名字（source 模式应命中）
struct sockaddr_storage {
    unsigned short ss_family;
};

int fixture_selfdefine(void);
