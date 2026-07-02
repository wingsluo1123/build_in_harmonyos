# Net::SNMP

面向对象的 SNMP 接口模块，支持 SNMPv1/v2c/v3 协议、UDP/TCP 传输、IPv4/IPv6。

## 特点

- **纯 Perl 实现**：无 XS/C 编译依赖，不受 OpenHarmony SELinux HMDFS 限制
- **完整协议支持**：SNMPv1、SNMPv2c、SNMPv3（USM: SHA/MD5 认证 + DES 加密）
- **多种传输**：UDP/IPv4、TCP/IPv4、UDP/IPv6、TCP/IPv6
- **异步支持**：通过 `snmp_dispatcher()` 支持非阻塞请求
- **即时可用**：通过 PERL5LIB 加载，无需管理员安装

## 可选依赖

SNMPv3 和 IPv6 功能需要可选依赖，通过纯 Perl 包装器解决：

| 依赖 | 包装器 | 后端 | 来源 |
|------|--------|------|------|
| Crypt::DES | Crypt::DES | Crypt::DES_PP | CPAN |
| Digest::SHA1 | Digest::SHA1 | Digest::SHA | Perl 核心 |
| Socket6 | Socket6 | Socket v2.038 | Perl 核心 |

### 安装可选依赖

```bash
# 1. 下载 Crypt::DES_PP
curl -sSL "https://mirrors.tuna.tsinghua.edu.cn/CPAN/authors/id/G/GU/GUIDO/Crypt-DES_PP-1.00.tar.gz" | tar xz
cp Crypt-DES_PP-1.00/lib/Crypt/DES_PP.pm ~/usr/local/lib/site_perl/5.42.0/Crypt/

# 2. 包装器文件已包含在归档中 (Crypt/DES.pm, Digest/SHA1.pm, Socket6.pm)
# 复制到 ~/usr/local/lib/site_perl/5.42.0/

# 3. 设置 PERL5LIB (追加,不要覆盖)
export PERL5LIB="/path/to/conan/lib:$PERL5LIB"
```

## 使用方式

```bash
# 设置 PERL5LIB
export PERL5LIB=$CONAN_LIB_DIR:$PERL5LIB

# SNMPv2c
perl -MNet::SNMP -e '
  my ($s,$e) = Net::SNMP->session(-hostname=>"127.0.0.1",-community=>"public");
  print $s->get_request(-varbindlist=>["1.3.6.1.2.1.1.1.0"]);
'

# SNMPv3 (需可选依赖)
perl -MNet::SNMP -e '
  my ($s,$e) = Net::SNMP->session(
    -hostname=>"127.0.0.1", -version=>"snmpv3",
    -username=>"admin", -authprotocol=>"sha",
    -authpassword=>"authpass", -privprotocol=>"des",
    -privpassword=>"privpass");
'
```

## 编译指导

纯 Perl 模块，使用 Perl ExtUtils::MakeMaker 构建：

```bash
perl Makefile.PL
make
make install DESTDIR=/path/to/staging
```

无需特殊平台适配，`perl Makefile.PL && make` 即可。

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [6.0.1-r8](./6.0.1-r8/) | built | 2026-06-26 |
