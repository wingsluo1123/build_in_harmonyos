#!/usr/bin/sh
# OpenHarmony 开发环境配置向导调度脚本
# 通过 hishell 执行，继承正确的 MAC label，规避 adhoc 进程权限限制
# 如果条件已满足，自动跳过进入下一步

SCRIPT_DIR="/storage/Users/currentUser"

# 颜色定义
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
CYAN='\033[36m'
RESET='\033[0m'

# 询问用户 yes/no
ask_yes_no() {
    printf "${YELLOW}%s (y/n): ${RESET}" "$1"
    read answer
    case "$answer" in
        y|Y) return 0 ;;
        *) return 1 ;;
    esac
}

# 显示步骤标题
show_step_header() {
    step_num=$1
    step_title=$2
    echo ""
    printf "${CYAN}============================================================${RESET}\n"
    printf "${CYAN}步骤 [%d/14] %s${RESET}\n" "$step_num" "$step_title"
    printf "${CYAN}============================================================${RESET}\n"
}

# Banner
echo ""
echo "  ╔══════════════════════════════════════════════════════════════════════╗"
echo "  ║                                                                      ║"
echo "  ║         ██████╗   ██╗   ██╗   ███████╗   ██████╗   ██████╗           ║" 
echo "  ║        ██╔═══██╗  ██║   ██║  ██╔═══██║  ██╔═══██╗  ██╔═══██╗         ║"
echo "  ║        ██║   ██║  ████████║  ████████║  ██║   ╚═╝  ██║   ██║         ║"
echo "  ║        ██║   ██║  ██╔═══██║  ██╔═════╝  ██║   ██╗  ██║   ██          ║"
echo "  ║         ██████╔╝  ██║   ██║  ██║         ██████╔╝  ██████╔╝          ║"
echo "  ║         ╚═════╝   ╚═╝   ╚═╝  ╚═╝         ╚═════╝    ╚════╝           ║"
echo "  ║                                                                      ║"
echo "  ║             Harmony 编译 智能工作站安装向导 v1.0                     ║"
echo "  ║                                                                      ║"
echo "  ║       Copyright (c) 2024-2026 OpenHarmony PC Developer 社区          ║"
echo "  ║                                                                      ║"
echo "  ╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# 检测系统环境
printf "${CYAN}正在检测系统环境...${RESET}\n"
printf "[✓] CPU: $(nproc) 核心\n"
printf "[✓] 内存: $(free -h | awk '/^Mem:/ {print $2}')\n"
printf "[✓] 磁盘空间: $(df -h "$SCRIPT_DIR" | awk 'NR==2 {print $4}')\n"
echo ""

printf "${YELLOW}按 Enter 开始配置...${RESET}"
read dummy

# ===== 步骤 1: 检查开发工具 =====
show_step_header 1 "下载安装 DevBox、GitNext、DevNode"

check_tools() {
    all_installed=1
    
    printf "检查 DevBox...\n"
    if clang --version > /dev/null 2>&1; then
        printf "${GREEN}✓ DevBox 已安装${RESET}\n"
    else
        printf "${RED}✗ DevBox 未安装${RESET}\n"
        printf "下载地址: https://appgallery.huawei.com/app/detail?id=com.develop.opensource.devbox&channelId=SHARE&source=appshare\n"
        all_installed=0
    fi
    
    printf "检查 GitNext...\n"
    if git --version > /dev/null 2>&1; then
        printf "${GREEN}✓ GitNext 已安装${RESET}\n"
    else
        printf "${RED}✗ GitNext 未安装${RESET}\n"
        printf "下载地址: https://appgallery.huawei.com/app/detail?id=com.develop.opensource.gitnext&channelId=SHARE&source=appshare\n"
        all_installed=0
    fi
    
    printf "检查 DevNode...\n"
    if /data/service/hnp/bin/node --version > /dev/null 2>&1; then
        printf "${GREEN}✓ DevNode 已安装${RESET}\n"
    else
        printf "${RED}✗ DevNode 未安装${RESET}\n"
        printf "下载地址: https://appgallery.huawei.com/app/detail?id=com.develop.opensource.ohdpc.devnode&channelId=SHARE&source=appshare\n"
        all_installed=0
    fi
    
    echo ""
    
    if [ $all_installed -eq 1 ]; then
        return 0
    else
        return 1
    fi
}

# 首次检测
check_tools

if [ $? -eq 0 ]; then
    printf "${GREEN}所有工具已安装！${RESET}\n"
    : # 自动跳过
else
    printf "${CYAN}请在浏览器中打开上述链接下载安装对应应用。${RESET}\n"
    printf "${YELLOW}安装完成后，按 Enter 重新检测...${RESET}\n"
    read dummy
    
    # 重新检测
    echo ""
    printf "${CYAN}重新检测工具...${RESET}\n"
    show_step_header 1 "下载安装 DevBox、GitNext、DevNode"
    check_tools
    
    if [ $? -eq 0 ]; then
        printf "${GREEN}所有工具已安装！${RESET}\n"
        : # 自动跳过
    else
        printf "${RED}仍有工具未安装，请完成安装后重新运行此脚本。${RESET}\n"
        exit 1
    fi
fi

# ===== 步骤 2: 登录 GitCode =====
show_step_header 2 "登录 GitCode"

printf "打开以下地址并登录:\n"
printf "${CYAN}https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos${RESET}\n"
echo ""

printf "${YELLOW}登录完成后，按 Enter 继续...${RESET}"
read dummy

# ===== 步骤 3: 配置 Git 用户信息 =====
show_step_header 3 "配置 Git 用户信息"

existing_name=$(git config --global user.name 2>/dev/null || echo "")
existing_email=$(git config --global user.email 2>/dev/null || echo "")

if [ -n "$existing_name" ] && [ -n "$existing_email" ]; then
    printf "${GREEN}✓ Git 已配置${RESET}\n"
    printf "  用户名: ${GREEN}${existing_name}${RESET}\n"
    printf "  邮箱:   ${GREEN}${existing_email}${RESET}\n"
    echo ""
    
    if ask_yes_no "是否重新配置？"; then
        echo ""
        printf "${YELLOW}请输入 Git 用户名: ${RESET}"
        read username
        printf "${YELLOW}请输入 Git 邮箱: ${RESET}"
        read email
        
        git config --global user.name "$username"
        git config --global user.email "$email"
        
        printf "${GREEN}✓ Git 配置完成${RESET}\n"
    fi
    # 用户选择 n 时自动跳过，无需回车
else
    printf "${YELLOW}Git 未配置，请输入用户信息${RESET}\n"
    echo ""
    printf "${YELLOW}请输入 Git 用户名: ${RESET}"
    read username
    printf "${YELLOW}请输入 Git 邮箱: ${RESET}"
    read email
    
    git config --global user.name "$username"
    git config --global user.email "$email"
    
    printf "${GREEN}✓ Git 配置完成${RESET}\n"
fi

# ===== 步骤 4: 配置 SSH Key =====
show_step_header 4 "配置 SSH Key"

email=$(git config --global user.email)

if [ -z "$email" ]; then
    printf "${RED}错误: 未找到 Git 邮箱配置${RESET}\n"
    printf "${YELLOW}按 Enter 继续...${RESET}"
    read dummy
else
    printf "使用 Git 邮箱: ${GREEN}${email}${RESET}\n"
    echo ""
fi

# 检查 SSH Key 是否存在
if [ -f ~/.ssh/id_rsa.pub ]; then
    printf "${GREEN}✓ SSH Key 已存在${RESET}\n"
    
    # 测试 SSH 连接
    printf "测试 SSH 连接...\n"
    if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -T git@gitcode.com 2>&1 | grep -qi "welcome"; then
        printf "${GREEN}✓ SSH 连接成功${RESET}\n"
        : # 自动跳过
    else
        printf "${YELLOW}SSH 连接失败，可能需要重新添加 Key${RESET}\n"
        
        # 显示公钥
        echo ""
        printf "${GREEN}==================================================${RESET}\n"
        printf "${GREEN}SSH 公钥 (请复制以下内容)${RESET}\n"
        printf "${GREEN}==================================================${RESET}\n"
        cat ~/.ssh/id_rsa.pub
        printf "${GREEN}==================================================${RESET}\n"
        echo ""
        
        printf "${RED}【需要手动操作】${RESET}\n"
        echo "1. 复制上面显示的 SSH 公钥"
        echo "2. 打开 https://gitcode.com/setting/key-ssh"
        echo "3. 点击「新增 SSH Key」"
        echo "4. 粘贴公钥内容，点击「新建」"
        echo ""
        
        printf "${YELLOW}添加完成后，按 Enter 检测连接...${RESET}"
        read dummy
        
        echo ""
        printf "测试 SSH 连接...\n"
        if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -T git@gitcode.com 2>&1 | grep -qi "welcome"; then
            printf "${GREEN}✓ SSH 连接成功${RESET}\n"
        else
            printf "${RED}✗ SSH 连接失败${RESET}\n"
        fi
    fi
else
    printf "${YELLOW}SSH Key 不存在，需要生成${RESET}\n"
    
    ssh-keygen -t rsa -b 2048 -C "$email" -N "" -f ~/.ssh/id_rsa
    
    echo ""
    printf "${GREEN}==================================================${RESET}\n"
    printf "${GREEN}SSH 公钥 (请复制以下内容)${RESET}\n"
    printf "${GREEN}==================================================${RESET}\n"
    cat ~/.ssh/id_rsa.pub
    printf "${GREEN}==================================================${RESET}\n"
    echo ""
    
    printf "${RED}【需要手动操作】${RESET}\n"
    echo "1. 复制上面显示的 SSH 公钥"
    echo "2. 打开 https://gitcode.com/setting/key-ssh"
    echo "3. 点击「新增 SSH Key」"
    echo "4. 粘贴公钥内容，点击「新建」"
    echo ""
    
    printf "${YELLOW}添加完成后，按 Enter 检测连接...${RESET}"
    read dummy
    
    echo ""
    printf "测试 SSH 连接...\n"
    if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -T git@gitcode.com 2>&1 | grep -qi "welcome"; then
        printf "${GREEN}✓ SSH 连接成功${RESET}\n"
    else
        printf "${RED}✗ SSH 连接失败${RESET}\n"
    fi
fi

# ===== 步骤 5: 下载 Skill 代码仓 =====
show_step_header 5 "下载 Skill 代码仓"

agent_name="${AGENT_NAME:-}"

# 尝试从现有目录推断
if [ -z "$agent_name" ]; then
    for dir in "$SCRIPT_DIR"/*; do
        if [ -d "$dir/build_in_harmonyos" ] && [ -d "$dir/cmd-pkgs" ]; then
            candidate=$(basename "$dir")
            printf "${YELLOW}检测到已有工作目录: ${candidate}${RESET}\n"
            if ask_yes_no "是否使用此目录？"; then
                agent_name="$candidate"
                break
            fi
        fi
    done
fi

if [ -z "$agent_name" ]; then
    printf "${YELLOW}请输入一个英文名称作为工作目录 (例如: runner002): ${RESET}"
    read agent_name
    [ -z "$agent_name" ] && agent_name="runner002"
fi

echo ""
printf "使用名称: ${GREEN}${agent_name}${RESET}\n"
export AGENT_NAME="$agent_name"

WORK_DIR="${SCRIPT_DIR}/${agent_name}"

# 检查仓库是否已存在
repos_exist=1
if [ ! -d "${WORK_DIR}/build_in_harmonyos" ]; then
    repos_exist=0
fi
if [ ! -d "${WORK_DIR}/cmd-pkgs" ]; then
    repos_exist=0
fi

if [ $repos_exist -eq 1 ]; then
    printf "${GREEN}✓ 代码仓已存在${RESET}\n"
    printf "  build_in_harmonyos: ${WORK_DIR}/build_in_harmonyos\n"
    printf "  cmd-pkgs:           ${WORK_DIR}/cmd-pkgs\n"
    : # 自动跳过
else
    mkdir -p "$WORK_DIR"
    
    if [ ! -d "${WORK_DIR}/build_in_harmonyos" ]; then
        printf "克隆 build_in_harmonyos...\n"
        git clone git@gitcode.com:OpenHarmonyPCDeveloper/build_in_harmonyos.git "${WORK_DIR}/build_in_harmonyos"
    fi
    
    if [ ! -d "${WORK_DIR}/cmd-pkgs" ]; then
        printf "克隆 cmd-pkgs...\n"
        git clone git@gitcode.com:OpenHarmonyPCDeveloper/cmd-pkgs.git "${WORK_DIR}/cmd-pkgs"
    fi
    
    printf "${GREEN}✓ 代码仓克隆完成${RESET}\n"
fi

# ===== 步骤 6: 配置环境变量 =====
show_step_header 6 "配置环境变量"

ZSHRC_CONFIG="${WORK_DIR}/build_in_harmonyos/config/.zshrc"

if [ ! -f "$ZSHRC_CONFIG" ]; then
    printf "${RED}错误: 配置文件不存在: ${ZSHRC_CONFIG}${RESET}\n"
    printf "${YELLOW}按 Enter 继续...${RESET}"
    read dummy
else
    printf "${CYAN}检查并添加环境变量配置...${RESET}\n"
    echo ""
    
    # 备份现有 .zshrc
    cp ~/.zshrc ~/.zshrc.backup.$(date +%Y%m%d%H%M%S) 2>/dev/null || true
    
    added_count=0
    skipped_count=0
    
    # 检查并添加各项配置
    # PATH (npm/bin)
    if grep -q "npm/bin" ~/.zshrc 2>/dev/null; then
        printf "${GREEN}✓${RESET} PATH (npm/bin) 已存在\n"
        skipped_count=$((skipped_count + 1))
    else
        printf "${YELLOW}+${RESET} PATH (npm/bin)\n"
        echo 'export PATH=/storage/Users/currentUser/npm/bin:/storage/Users/currentUser/usr/local/bin:$PATH' >> ~/.zshrc
        added_count=$((added_count + 1))
    fi
    
    # TMPDIR
    if grep -q "TMPDIR" ~/.zshrc 2>/dev/null; then
        printf "${GREEN}✓${RESET} TMPDIR 已存在\n"
        skipped_count=$((skipped_count + 1))
    else
        printf "${YELLOW}+${RESET} TMPDIR\n"
        echo 'export TMPDIR=$HOME/tmp' >> ~/.zshrc
        added_count=$((added_count + 1))
    fi
    
    # CMAKE_PREFIX_PATH
    if grep -q "CMAKE_PREFIX_PATH" ~/.zshrc 2>/dev/null; then
        printf "${GREEN}✓${RESET} CMAKE_PREFIX_PATH 已存在\n"
        skipped_count=$((skipped_count + 1))
    else
        printf "${YELLOW}+${RESET} CMAKE_PREFIX_PATH\n"
        echo 'export CMAKE_PREFIX_PATH=$HOME/usr/local${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}' >> ~/.zshrc
        added_count=$((added_count + 1))
    fi
    
    # LD_LIBRARY_PATH
    if grep -q "LD_LIBRARY_PATH" ~/.zshrc 2>/dev/null; then
        printf "${GREEN}✓${RESET} LD_LIBRARY_PATH 已存在\n"
        skipped_count=$((skipped_count + 1))
    else
        printf "${YELLOW}+${RESET} LD_LIBRARY_PATH\n"
        echo 'export LD_LIBRARY_PATH=$HOME/usr/local/lib:/data/service/hnp/magic-cli.org/magic-cli_1.0.0/lib:$LD_LIBRARY_PATH' >> ~/.zshrc
        added_count=$((added_count + 1))
    fi
    
    # DEFAULT_PREFIX
    if grep -q "DEFAULT_PREFIX" ~/.zshrc 2>/dev/null; then
        printf "${GREEN}✓${RESET} DEFAULT_PREFIX 已存在\n"
        skipped_count=$((skipped_count + 1))
    else
        printf "${YELLOW}+${RESET} DEFAULT_PREFIX\n"
        echo 'export DEFAULT_PREFIX=$HOME/usr/local' >> ~/.zshrc
        added_count=$((added_count + 1))
    fi
    
    # 编译工具链 (CC, CXX, etc.)
    compiler_vars="CC CXX AS LD STRIP RANLIB OBJDUMP OBJCOPY NM AR"
    for var in $compiler_vars; do
        if grep -q "export ${var}=" ~/.zshrc 2>/dev/null; then
            printf "${GREEN}✓${RESET} ${var} 已存在\n"
            skipped_count=$((skipped_count + 1))
        else
            printf "${YELLOW}+${RESET} ${var}\n"
            added_count=$((added_count + 1))
        fi
    done
    
    # 如果编译工具链有新增，添加整个块
    if grep -q "export CC=\"clang\"" ~/.zshrc 2>/dev/null; then
        : # 已存在
    else
        echo 'export AS="llvm-as"' >> ~/.zshrc
        echo 'export CC="clang"' >> ~/.zshrc
        echo 'export CC_FOR_BUILD="clang"' >> ~/.zshrc
        echo 'export CXX="clang++"' >> ~/.zshrc
        echo 'export LD="ld.lld"' >> ~/.zshrc
        echo 'export STRIP="llvm-strip"' >> ~/.zshrc
        echo 'export RANLIB="llvm-ranlib"' >> ~/.zshrc
        echo 'export OBJDUMP="llvm-objdump"' >> ~/.zshrc
        echo 'export OBJCOPY="llvm-objcopy"' >> ~/.zshrc
        echo 'export NM="llvm-nm"' >> ~/.zshrc
        echo 'export AR="llvm-ar"' >> ~/.zshrc
    fi
    
    # CFLAGS, CXXFLAGS, LDFLAGS
    flags_vars="CFLAGS CXXFLAGS LDFLAGS CPPFLAGS"
    for var in $flags_vars; do
        if grep -q "export ${var}=" ~/.zshrc 2>/dev/null; then
            printf "${GREEN}✓${RESET} ${var} 已存在\n"
            skipped_count=$((skipped_count + 1))
        else
            printf "${YELLOW}+${RESET} ${var}\n"
            added_count=$((added_count + 1))
        fi
    done
    
    if grep -q "export CFLAGS=\"-fPIC" ~/.zshrc 2>/dev/null; then
        : # 已存在
    else
        echo 'export CFLAGS="-fPIC -O2"' >> ~/.zshrc
        echo 'export CXXFLAGS="-fPIC -O2"' >> ~/.zshrc
        echo 'export LDFLAGS="-L$HOME/usr/local/lib"' >> ~/.zshrc
        echo 'export CPPFLAGS="-I$HOME/usr/local/include"' >> ~/.zshrc
    fi
    
    # Aliases
    aliases="configure cmake Configure ar nm objdump objcopy strip as ld link"
    for alias in $aliases; do
        if grep -q "alias ${alias}=" ~/.zshrc 2>/dev/null; then
            printf "${GREEN}✓${RESET} alias ${alias} 已存在\n"
            skipped_count=$((skipped_count + 1))
        else
            printf "${YELLOW}+${RESET} alias ${alias}\n"
            added_count=$((added_count + 1))
        fi
    done
    
    if grep -q "alias configure=" ~/.zshrc 2>/dev/null; then
        : # 已存在
    else
        echo "alias configure='./configure --prefix=$DEFAULT_PREFIX'" >> ~/.zshrc
        echo "alias cmake='cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX'" >> ~/.zshrc
        echo "alias Configure='./Configure --prefix=$DEFAULT_PREFIX'" >> ~/.zshrc
        echo "alias ar='llvm-ar'" >> ~/.zshrc
        echo "alias nm='llvm-nm'" >> ~/.zshrc
        echo "alias objdump='llvm-objdump'" >> ~/.zshrc
        echo "alias objcopy='llvm-objcopy'" >> ~/.zshrc
        echo "alias strip='llvm-strip'" >> ~/.zshrc
        echo "alias as='llvm-as'" >> ~/.zshrc
        echo "alias ld='ld.lld'" >> ~/.zshrc
        echo "alias link='llvm-link'" >> ~/.zshrc
    fi
    
    # AGENT_NAME
    if grep -q "AGENT_NAME" ~/.zshrc 2>/dev/null; then
        printf "${GREEN}✓${RESET} AGENT_NAME 已存在\n"
        skipped_count=$((skipped_count + 1))
    else
        printf "${YELLOW}+${RESET} AGENT_NAME\n"
        echo "export AGENT_NAME=${agent_name}" >> ~/.zshrc
        added_count=$((added_count + 1))
    fi
    
    echo ""
    printf "${CYAN}配置统计:${RESET}\n"
    printf "  已存在: ${GREEN}${skipped_count}${RESET} 项\n"
    printf "  新添加: ${YELLOW}${added_count}${RESET} 项\n"
    
    if [ $added_count -gt 0 ]; then
        echo ""
        printf "${CYAN}提示: 请执行 'source ~/.zshrc' 使配置生效${RESET}\n"
    fi
    
    printf "${GREEN}✓ 环境变量配置完成${RESET}\n"
fi

# ===== 步骤 7: 创建必要目录 =====
show_step_header 7 "创建必要目录"

dirs_exist=1
if [ ! -d "${SCRIPT_DIR}/npm/bin" ]; then
    dirs_exist=0
fi
if [ ! -d "${SCRIPT_DIR}/usr/local" ]; then
    dirs_exist=0
fi

if [ $dirs_exist -eq 1 ]; then
    printf "${GREEN}✓ 目录已存在${RESET}\n"
    : # 自动跳过
else
    mkdir -p "${SCRIPT_DIR}/npm/bin"
    mkdir -p "${SCRIPT_DIR}/usr/local"
    
    printf "${GREEN}✓ 目录创建完成${RESET}\n"
    printf "验证目录:\n"
    ls -la "${SCRIPT_DIR}/npm/" 2>/dev/null || true
    ls -la "${SCRIPT_DIR}/usr/" 2>/dev/null || true
fi

# ===== 步骤 8: 配置 npm 并安装 OpenDesk CLI =====
show_step_header 8 "配置 npm 并安装 OpenDesk CLI"

NPMRC="${SCRIPT_DIR}/.npmrc"
OPENDESK_BIN="${SCRIPT_DIR}/npm/bin/opendesk"
OPENDESK_LIB="${SCRIPT_DIR}/npm/lib/node_modules/@bitclub.ai/opendesk-cli"

# 检查 npm prefix 配置
npm_config_ok=0
if [ -f "$NPMRC" ]; then
    if grep -q "prefix=${SCRIPT_DIR}/npm" "$NPMRC"; then
        npm_config_ok=1
    fi
fi

if [ $npm_config_ok -eq 0 ]; then
    printf "${YELLOW}配置 npm prefix...${RESET}\n"
    echo "prefix=${SCRIPT_DIR}/npm" > "$NPMRC"
    printf "${GREEN}✓ npm 配置完成${RESET}\n"
else
    printf "${GREEN}✓ npm 配置已存在${RESET}\n"
fi

echo ""

# 检查 opendesk 是否已安装
opendesk_installed=0
    if opendesk --version > /dev/null 2>&1; then
        opendesk_installed=1
        printf "${GREEN}✓ OpenDesk CLI 已安装${RESET}\n"
       opendesk --version
    fi

if [ $opendesk_installed -eq 1 ]; then
    : # 自动跳过
else
    printf "安装 OpenDesk CLI...\n"
    
    npm install -g @bitclub.ai/opendesk-cli
    
    printf "${GREEN}✓ OpenDesk CLI 安装完成${RESET}\n"
   opendesk --version
fi

# ===== 步骤 9: 设置 Agent 参数 =====
show_step_header 9 "设置 Agent 参数"

SETTING_PATH="${SCRIPT_DIR}/.opendesk/setting.json"

# 检查是否已有有效配置
config_valid=0
if [ -f "$SETTING_PATH" ]; then
    if grep '"api_key"' "$SETTING_PATH" | grep -qv '""'; then
        config_valid=1
        printf "${GREEN}✓ Agent 配置已存在${RESET}\n"
        printf "当前配置:\n"
        cat "$SETTING_PATH"
        echo ""
    fi
fi

if [ $config_valid -eq 1 ]; then
    if ask_yes_no "是否重新配置？"; then
        configure_agent=1
    fi
    # 用户选择 n 时自动跳过，无需回车
else
    configure_agent=1
fi

if [ "$configure_agent" = "1" ]; then
    echo ""
    printf "${CYAN}请选择配置方式:${RESET}\n"
    printf "  1. 阿里云百炼\n"
    printf "  2. 自定义配置\n"
    echo ""
    
    printf "${YELLOW}请输入选项 (1-2): ${RESET}"
    read choice
    
    case "$choice" in
        1)
            provider="aliyun-cn"
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            
            echo ""
            printf "${CYAN}阿里云百炼常用模型:${RESET}\n"
            printf "  - qwen-turbo, qwen-plus, qwen-max, deepseek-v3\n"
            echo ""
            
            printf "${YELLOW}请输入模型名称 (默认 qwen-plus): ${RESET}"
            read model
            [ -z "$model" ] && model="qwen-plus"
            ;;
        2)
            echo ""
            printf "${YELLOW}请输入服务商名称: ${RESET}"
            read provider
            [ -z "$provider" ] && provider="custom"
            
            printf "${YELLOW}请输入 API Base URL: ${RESET}"
            read base_url
            [ -z "$base_url" ] && base_url="https://api.openai.com/v1"
            
            printf "${YELLOW}请输入模型名称: ${RESET}"
            read model
            [ -z "$model" ] && model="gpt-4"
            ;;
        *)
            printf "${RED}无效选项${RESET}\n"
            exit 1
            ;;
    esac
    
    # API Key
    echo ""
    api_key=""
    while [ -z "$api_key" ]; do
        if [ "$choice" = "1" ] && [ -n "${ALIYUN_API_KEY:-}" ]; then
            printf "检测到环境变量 ALIYUN_API_KEY\n"
            if ask_yes_no "是否使用此 API Key？"; then
                api_key="$ALIYUN_API_KEY"
                break
            fi
        fi
        
        printf "${YELLOW}请输入 API Key: ${RESET}"
        read api_key
        [ -z "$api_key" ] && printf "${RED}API Key 不能为空${RESET}\n"
    done
    
    # 创建配置文件
    mkdir -p "${SCRIPT_DIR}/.opendesk/"
    
    cat > "$SETTING_PATH" << EOF
{
    "default_model": "${model}",
    "default_intent_parsing_model": "",
    "default_embedding_model": "${model}",
    "default_reranker_model": "${model}",
    "default_vision_model": "",
    "providers": [
        {
            "name": "${provider}",
            "base_url": "${base_url}",
            "api_key": "${api_key}",
            "no_proxy": false
        }
    ],
    "models": [
        {
            "alias": "${model}",
            "provider_name": "${provider}",
            "model_name": "${model}"
        }
    ],
    "applications": {}
}
EOF
    
    echo ""
    printf "${GREEN}✓ 配置文件已创建${RESET}\n"
fi

# ===== 步骤 10: 安装 Python =====
show_step_header 10 "安装 Python"

python_installed=0
pip_installed=0

# 检测 python3
if command -v python3 > /dev/null 2>&1; then
    python_version=$(python3 --version 2>/dev/null)
    printf "${GREEN}✓ Python 已安装: ${python_version}${RESET}\n"
    python_installed=1
fi

# 检测 pip3
if command -v pip3 > /dev/null 2>&1; then
    printf "${GREEN}✓ pip 已安装${RESET}\n"
    pip_installed=1
fi

echo ""

if [ $python_installed -eq 1 ] && [ $pip_installed -eq 1 ]; then
    : # 自动跳过
elif [ $python_installed -eq 1 ] && [ $pip_installed -eq 0 ]; then
    printf "${YELLOW}pip 未安装，尝试安装...${RESET}\n"
    python3 -m ensurepip --default-pip 2>/dev/null
    pip3 --version 2>/dev/null && printf "${GREEN}✓ pip 安装完成${RESET}\n" || printf "${RED}pip 安装失败${RESET}\n"
else
    printf "${YELLOW}安装 Python 3.12.9...${RESET}\n"
    curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- python 3.12.9
    
    printf "${YELLOW}安装 pip...${RESET}\n"
    python3 -m ensurepip --default-pip 2>/dev/null
    
    echo ""
    printf "验证安装:\n"
    python3 --version
    pip3 --version 2>/dev/null || printf "${RED}pip 未找到${RESET}\n"
    
    printf "${GREEN}✓ Python 安装完成${RESET}\n"
fi

# ===== 步骤 11: 安装 Python 库依赖 =====
show_step_header 11 "安装 Python 库依赖"

SKILL_SCRIPTS="${WORK_DIR}/build_in_harmonyos/scripts"

if [ -d "$SKILL_SCRIPTS" ]; then
    printf "${CYAN}分析 Skill Python 依赖...${RESET}\n"
    
    REQ_FILE="${WORK_DIR}/build_in_harmonyos/requirements.txt"
    
    if [ -f "$REQ_FILE" ]; then
        printf "${YELLOW}发现 requirements.txt，安装依赖...${RESET}\n"
        pip3 install -r "$REQ_FILE"
        printf "${GREEN}✓ 依赖安装完成${RESET}\n"
    else
        printf "${GREEN}✓ Skill 使用 Python 标准库，无额外依赖${RESET}\n"
    fi
else
    printf "${YELLOW}Skill 脚本目录不存在${RESET}\n"
fi
# 自动跳过，无需回车

# ===== 步骤 12: 设置系统电源选项 =====
show_step_header 12 "设置系统电源选项"

printf "${RED}【需要手动操作】${RESET}\n"
echo "1. 打开「系统设置」->「电源」"
echo "2. 将「屏幕关闭时间」设置为「从不」"
echo "3. 将「睡眠时间」设置为「从不」"
echo "4. 关闭所有节能相关选项"
echo ""

printf "${YELLOW}设置完成后，按 Enter 继续...${RESET}"
read dummy

# ===== 步骤 13: 添加 Skill 到 OpenDesk =====
show_step_header 13 "添加 Skill 到 OpenDesk"

SKILL_PATH="${WORK_DIR}/build_in_harmonyos"

# 检查 skill 是否已安装
skill_installed=0

if [ -f "$SETTING_PATH" ]; then
    if grep -q "openharmony-compile-agent" "$SETTING_PATH" 2>/dev/null; then
        skill_installed=1
        printf "${GREEN}✓ Skill 已安装${RESET}\n"
    fi
fi

if [ $skill_installed -eq 1 ]; then
    : # 自动跳过
else
    printf "${CYAN}安装 Skill 到 OpenDesk...${RESET}\n"
    
    opendesk skill install "$SKILL_PATH" 2>&1
    
    printf "${GREEN}✓ Skill 安装完成${RESET}\n"
fi

# ===== 步骤 14: 启动 OpenDesk 并执行编译任务 =====
show_step_header 14 "启动 OpenDesk 并执行编译任务"

PORT_PLAN="${WORK_DIR}/cmd-pkgs/PORTS_PLAN/P0-P1-编译分析与建议.md"

printf "${CYAN}启动 OpenDesk${RESET}\n"
echo ""
printf "在终端中执行以下命令启动 OpenDesk:\n"
echo ""
printf "${GREEN}  opendesk --allow-everything --language zh-CN${RESET}\n"
echo ""

printf "${CYAN}============================================================${RESET}\n"
printf "${CYAN}标准提示词（启动后复制输入）${RESET}\n"
printf "${CYAN}============================================================${RESET}\n"
echo ""
printf "${BLUE}加载编译SKILL编译XXX软件，用子任务完成，子任务作为编译协作者需要加载skill来完成任务，每个子任务处理一个独立软件，子任务完成后由你检查质量，不满足SKILL质量要求的，需要打回重做。${RESET}\n"
echo ""
printf "${CYAN}============================================================${RESET}\n"
echo ""

printf "${YELLOW}提示：${RESET}\n"
printf "  - 将上述提示词中的 XXX 替换为具体的软件名称\n"
printf "  - 编译计划路径: ${PORT_PLAN}\n"
echo ""

printf "${YELLOW}按 Enter 完成配置向导...${RESET}"
read dummy

# ===== 完成 =====
echo ""
printf "${GREEN}============================================================${RESET}\n"
printf "${GREEN}               配置向导执行完成！${RESET}\n"
printf "${GREEN}============================================================${RESET}\n"
echo ""

# source 配置使其在当前环境生效
printf "${CYAN}加载配置到当前环境...${RESET}\n"
source ~/.zshrc 2>/dev/null || true
printf "${GREEN}✓ 配置已加载${RESET}\n"
echo ""

printf "已完成配置:\n"
echo ""
printf "${GREEN}  ✓${RESET}  1. 下载安装 DevBox、GitNext、DevNode\n"
printf "${GREEN}  ✓${RESET}  2. 登录 GitCode 仓库\n"
printf "${GREEN}  ✓${RESET}  3. 配置 Git 用户信息\n"
printf "${GREEN}  ✓${RESET}  4. 配置 SSH Key\n"
printf "${GREEN}  ✓${RESET}  5. 下载 Skill 代码仓\n"
printf "${GREEN}  ✓${RESET}  6. 配置环境变量\n"
printf "${GREEN}  ✓${RESET}  7. 创建必要目录\n"
printf "${GREEN}  ✓${RESET}  8. 配置 npm 并安装 OpenDesk CLI\n"
printf "${GREEN}  ✓${RESET}  9. 设置 Agent 参数\n"
printf "${GREEN}  ✓${RESET} 10. 安装 Python\n"
printf "${GREEN}  ✓${RESET} 11. 安装 Python 库依赖\n"
printf "${GREEN}  ✓${RESET} 12. 设置系统电源选项\n"
printf "${GREEN}  ✓${RESET} 13. 添加 Skill 到 OpenDesk\n"
printf "${GREEN}  ✓${RESET} 14. 启动 OpenDesk 并执行编译任务\n"
echo ""

printf "${CYAN}当前环境变量:${RESET}\n"
printf "  AGENT_NAME: ${AGENT_NAME:-未设置}\n"
echo ""

printf "${CYAN}祝您开发顺利！${RESET}\n"
