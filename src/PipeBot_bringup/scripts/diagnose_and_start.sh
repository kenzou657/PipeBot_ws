#!/bin/bash

# PipeBot 蓝牙系统诊断和启动脚本
# 
# 功能：
# 1. 检查串口设备
# 2. 检查串口占用情况
# 3. 清理占用的进程
# 4. 启动蓝牙系统

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERIAL_PORT="/dev/serial1"
WORKSPACE_DIR="/home/pi/PipeBot_ws"

echo -e "${BLUE}=== PipeBot 蓝牙系统诊断 ===${NC}\n"

# 1. 检查串口设备
echo -e "${BLUE}[1/5] 检查串口设备...${NC}"
if [ -e "$SERIAL_PORT" ]; then
    echo -e "${GREEN}✓ 串口设备存在${NC}"
    ls -la "$SERIAL_PORT"
else
    echo -e "${RED}✗ 串口设备不存在${NC}"
    echo "请检查树莓派配置或蓝牙模块连接"
    exit 1
fi

echo ""

# 2. 检查串口权限
echo -e "${BLUE}[2/5] 检查串口权限...${NC}"
if [ -r "$SERIAL_PORT" ] && [ -w "$SERIAL_PORT" ]; then
    echo -e "${GREEN}✓ 串口权限正常${NC}"
else
    echo -e "${YELLOW}⚠ 串口权限不足，尝试添加用户到 dialout 组${NC}"
    sudo usermod -a -G dialout $USER
    echo "请重新登录或运行: newgrp dialout"
fi

echo ""

# 3. 检查串口占用
echo -e "${BLUE}[3/5] 检查串口占用情况...${NC}"
if lsof "$SERIAL_PORT" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ 串口被占用，正在清理...${NC}"
    lsof "$SERIAL_PORT"
    
    # 获取占用的 PID
    PIDS=$(lsof "$SERIAL_PORT" | awk 'NR>1 {print $2}')
    
    for PID in $PIDS; do
        echo "关闭进程 PID: $PID"
        kill -9 $PID 2>/dev/null || true
    done
    
    sleep 1
    
    if lsof "$SERIAL_PORT" > /dev/null 2>&1; then
        echo -e "${RED}✗ 无法清理占用的进程${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ 串口已释放${NC}"
    fi
else
    echo -e "${GREEN}✓ 串口未被占用${NC}"
fi

echo ""

# 4. 检查工作空间
echo -e "${BLUE}[4/5] 检查工作空间...${NC}"
if [ -d "$WORKSPACE_DIR/install" ]; then
    echo -e "${GREEN}✓ 工作空间已构建${NC}"
else
    echo -e "${RED}✗ 工作空间未构建${NC}"
    echo "请执行: cd $WORKSPACE_DIR && colcon build"
    exit 1
fi

echo ""

# 5. 启动蓝牙系统
echo -e "${BLUE}[5/5] 启动蓝牙系统...${NC}"
echo -e "${GREEN}准备启动以下节点：${NC}"
echo "  - bluetooth_receiver_node"
echo "  - state_manager_node"
echo "  - command_handler_node"
echo "  - bluetooth_sender_node"
echo ""

cd "$WORKSPACE_DIR"
source install/setup.bash

echo -e "${GREEN}启动中...${NC}\n"
ros2 launch PipeBot_bringup bluetooth_control.launch.py
