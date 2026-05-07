#!/bin/bash

# PipeBot 视觉流媒体系统启动脚本
# 功能：一键启动USB相机采集和web_video_server流媒体服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查ROS2环境
check_ros2_env() {
    print_info "检查ROS2环境..."
    
    if [ -z "$ROS_DISTRO" ]; then
        print_error "ROS2环境未配置，请先执行: source /opt/ros/humble/setup.bash"
        exit 1
    fi
    
    print_success "ROS2环境已配置: $ROS_DISTRO"
}

# 检查web_video_server
check_web_video_server() {
    print_info "检查web_video_server..."
    
    if ! ros2 pkg list | grep -q web_video_server; then
        print_error "web_video_server未安装"
        print_info "请执行: sudo apt install ros-humble-web_video_server"
        exit 1
    fi
    
    print_success "web_video_server已安装"
}

# 检查PipeBot_vision包
check_pipebot_vision() {
    print_info "检查PipeBot_vision包..."
    
    if ! ros2 pkg list | grep -q PipeBot_vision; then
        print_error "PipeBot_vision包未构建"
        print_info "请执行: cd ~/PipeBot_ws && colcon build --packages-select PipeBot_vision"
        exit 1
    fi
    
    print_success "PipeBot_vision包已构建"
}

# 检查USB相机
check_camera() {
    print_info "检查USB相机..."
    
    if [ ! -e /dev/video0 ]; then
        print_warning "未检测到/dev/video0，请检查USB相机连接"
        print_info "可用的视频设备:"
        ls -la /dev/video* 2>/dev/null || echo "  无"
    else
        print_success "USB相机已检测到: /dev/video0"
    fi
}

# 检查端口占用
check_port() {
    local port=$1
    print_info "检查端口 $port..."
    
    if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
        print_warning "端口 $port 已被占用"
        print_info "占用情况:"
        netstat -tlnp 2>/dev/null | grep ":$port " || true
    else
        print_success "端口 $port 可用"
    fi
}

# 显示使用帮助
show_help() {
    cat << EOF
PipeBot 视觉流媒体系统启动脚本

用法: $0 [选项]

选项:
    -h, --help              显示此帮助信息
    -c, --check             仅检查环境，不启动
    -p, --port PORT         指定web_video_server端口 (默认: 8080)
    -q, --quality QUALITY   指定JPEG质量 (默认: 80, 范围: 1-100)
    -w, --width WIDTH       指定采集帧宽度 (默认: 1920)
    -h, --height HEIGHT     指定采集帧高度 (默认: 1080)
    -f, --fps FPS           指定采集帧率 (默认: 30)

示例:
    # 使用默认参数启动
    $0
    
    # 仅检查环境
    $0 --check
    
    # 自定义端口和质量
    $0 --port 8081 --quality 70
    
    # 降低分辨率以减少带宽
    $0 --width 1280 --height 720 --quality 70

EOF
}

# 主函数
main() {
    local check_only=false
    local port=8080
    local quality=80
    local width=1920
    local height=1080
    local fps=30
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -c|--check)
                check_only=true
                shift
                ;;
            -p|--port)
                port="$2"
                shift 2
                ;;
            -q|--quality)
                quality="$2"
                shift 2
                ;;
            -w|--width)
                width="$2"
                shift 2
                ;;
            --height)
                height="$2"
                shift 2
                ;;
            -f|--fps)
                fps="$2"
                shift 2
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 执行检查
    print_info "=========================================="
    print_info "PipeBot 视觉流媒体系统"
    print_info "=========================================="
    
    check_ros2_env
    check_web_video_server
    check_pipebot_vision
    check_camera
    check_port $port
    
    if [ "$check_only" = true ]; then
        print_success "环境检查完成"
        exit 0
    fi
    
    # 显示启动参数
    print_info "=========================================="
    print_info "启动参数:"
    print_info "  端口: $port"
    print_info "  JPEG质量: $quality"
    print_info "  分辨率: ${width}×${height}"
    print_info "  采集帧率: $fps fps"
    print_info "=========================================="
    
    # 启动系统
    print_info "启动PipeBot视觉流媒体系统..."
    print_info "前端网页地址: http://localhost:$port"
    print_info "按 Ctrl+C 停止"
    print_info ""
    
    ros2 launch PipeBot_vision vision_streaming.launch.py \
        web_port:=$port \
        web_quality:=$quality \
        frame_width:=$width \
        frame_height:=$height \
        fps:=$fps
}

# 捕获Ctrl+C信号
trap 'print_info "系统已停止"; exit 0' INT TERM

# 执行主函数
main "$@"
