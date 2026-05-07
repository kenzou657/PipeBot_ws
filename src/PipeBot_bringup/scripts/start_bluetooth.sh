#!/bin/bash

# PipeBot 蓝牙控制系统启动脚本
# 
# 用法：
#   ./start_bluetooth.sh              # 启动蓝牙控制系统
#   ./start_bluetooth.sh --help       # 显示帮助信息
#   ./start_bluetooth.sh --debug      # 启动并显示调试信息

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WORKSPACE_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# 显示帮助信息
show_help() {
    cat << EOF
${BLUE}PipeBot 蓝牙控制系统启动脚本${NC}

用法：
    $0 [选项]

选项：
    --help              显示此帮助信息
    --debug             启动并显示调试信息
    --no-launch         不使用启动文件，手动启动各个节点
    --check             仅检查环境，不启动节点

示例：
    $0                  # 启动蓝牙控制系统
    $0 --debug          # 启动并显示调试信息
    $0 --check          # 检查环境

EOF
}

# 检查环境
check_environment() {
    echo -e "${BLUE}[检查环境]${NC}"
    
    # 检查蓝牙硬件
    echo -n "检查蓝牙硬件... "
    if hciconfig | grep -q "hci0"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo -e "${RED}错误：未找到蓝牙适配器 hci0${NC}"
        return 1
    fi
    
    # 检查蓝牙是否启用
    echo -n "检查蓝牙状态... "
    if hciconfig hci0 | grep -q "UP RUNNING"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠${NC}"
        echo -e "${YELLOW}警告：蓝牙未启用，尝试启用...${NC}"
        sudo hciconfig hci0 up
        sleep 1
    fi
    
    # 检查 ROS2 环境
    echo -n "检查 ROS2 环境... "
    if [ -z "$ROS_DISTRO" ]; then
        echo -e "${RED}✗${NC}"
        echo -e "${RED}错误：ROS2 环境未配置${NC}"
        echo -e "${YELLOW}请执行：source /opt/ros/\$ROS_DISTRO/setup.bash${NC}"
        return 1
    else
        echo -e "${GREEN}✓${NC} (ROS_DISTRO=$ROS_DISTRO)"
    fi
    
    # 检查工作空间
    echo -n "检查工作空间... "
    if [ -d "$WORKSPACE_DIR/install" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo -e "${RED}错误：工作空间未构建${NC}"
        echo -e "${YELLOW}请执行：cd $WORKSPACE_DIR && colcon build${NC}"
        return 1
    fi
    
    # 检查依赖包
    echo -n "检查 Python 依赖... "
    if python3 -c "import bless" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠${NC}"
        echo -e "${YELLOW}警告：bless 库未安装，尝试安装...${NC}"
        pip install bless pybluez
    fi
    
    echo -e "${GREEN}环境检查完成${NC}\n"
    return 0
}

# 源环境
source_environment() {
    echo -e "${BLUE}[源环境]${NC}"
    
    # 源 ROS2 环境
    if [ -z "$ROS_DISTRO" ]; then
        echo "源 ROS2 环境..."
        source /opt/ros/humble/setup.bash 2>/dev/null || source /opt/ros/foxy/setup.bash 2>/dev/null || true
    fi
    
    # 源工作空间
    echo "源工作空间..."
    source "$WORKSPACE_DIR/install/setup.bash"
    
    echo -e "${GREEN}环境源完成${NC}\n"
}

# 启动蓝牙控制系统
start_bluetooth() {
    echo -e "${BLUE}[启动蓝牙控制系统]${NC}"
    echo "使用启动文件：bluetooth_control.launch.py"
    echo ""
    
    ros2 launch PipeBot_bringup bluetooth_control.launch.py
}

# 手动启动各个节点
start_manual() {
    echo -e "${BLUE}[手动启动各个节点]${NC}"
    echo "需要打开多个终端，每个终端运行一个节点"
    echo ""
    
    echo -e "${YELLOW}终端 1：蓝牙接收节点${NC}"
    echo "ros2 run PipeBot_driver bluetooth_receiver_node"
    echo ""
    
    echo -e "${YELLOW}终端 2：状态管理节点${NC}"
    echo "ros2 run PipeBot_driver state_manager_node"
    echo ""
    
    echo -e "${YELLOW}终端 3：命令处理节点${NC}"
    echo "ros2 run PipeBot_driver command_handler_node"
    echo ""
    
    echo -e "${YELLOW}终端 4：蓝牙发送节点${NC}"
    echo "ros2 run PipeBot_driver bluetooth_sender_node"
    echo ""
    
    echo -e "${YELLOW}终端 5：监听蓝牙状态${NC}"
    echo "ros2 topic echo bluetooth/status"
    echo ""
    
    echo -e "${YELLOW}终端 6：监听接收到的命令${NC}"
    echo "ros2 topic echo bluetooth/command"
    echo ""
    
    echo -e "${YELLOW}终端 7：监听机器人状态${NC}"
    echo "ros2 topic echo robot/state"
    echo ""
}

# 主函数
main() {
    # 解析命令行参数
    case "${1:-}" in
        --help)
            show_help
            exit 0
            ;;
        --debug)
            DEBUG=1
            ;;
        --no-launch)
            NO_LAUNCH=1
            ;;
        --check)
            CHECK_ONLY=1
            ;;
        *)
            ;;
    esac
    
    # 检查环境
    if ! check_environment; then
        exit 1
    fi
    
    # 如果仅检查，则退出
    if [ "$CHECK_ONLY" = "1" ]; then
        exit 0
    fi
    
    # 源环境
    source_environment
    
    # 启动系统
    if [ "$NO_LAUNCH" = "1" ]; then
        start_manual
    else
        start_bluetooth
    fi
}

# 运行主函数
main "$@"
