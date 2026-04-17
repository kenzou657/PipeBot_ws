# PipeBot: 多功能管道内检测机器人系统(树莓派端)

[![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue)](https://docs.ros.org/en/humble/index.html)
[![Platform RaspberryPi](https://img.shields.io/badge/Platform-Raspberry%20Pi%204B/5-orange)](https://www.raspberrypi.com/)
[![License MIT](https://img.shields.io/badge/License-MIT-green)](https://opensource.org/licenses/MIT)

## 1. 项目简介
本项目旨在设计并实现一款针对小口径管道的智能检测小车。通过集成嵌入式控制、ROS2 机器人框架、计算机视觉以及边缘计算技术，实现对管道内部堵塞、形变及裂纹的实时检测与定位。

---

## 2. 软件架构设计

项目采用功能解耦的设计思想，划分为 6 个核心 ROS2 功能包：

### PipeBot_ws/src
| 功能包名称 | 类型 | 核心职责说明 |
| :--- | :--- | :--- |
| **PipeBot_interfaces** | `CMake` | **自定义接口层**：定义项目特有的消息 (`.msg`) 和服务 (`.srv`)。包含电机编码器数据、管道缺陷报警信息等自定义结构。 |
| **PipeBot_driver** | `Python` | **硬件驱动层**：负责树莓派与 STM32 的串口通信。解析底层传感器数据（IMU、里程计、测距），并将 ROS2 控制指令 (`cmd_vel`) 下发给下位机。 |
| **PipeBot_localization** | `Python` | **定位导航层**：融合 IMU 和编码器数据。 |
| **PipeBot_vision** | `Python` | **视觉感知层**：摄像头驱动。 |
| **PipeBot_cloud** | `Python` | **云端通信层**：负责端云交互。将采集图像、小车状态、历史轨迹上传至数据中台。 |
| **PipeBot_bringup** | `Python` | **系统集成层**：包含所有启动脚本 (`launch`) 和参数配置文件 (`config`)。实现“一键启动”整个机器人系统。 |
---

## 3. 快速上手指南

### 软件编译
```bash
# 进入工作空间
cd ~/PipeBot_ws

# 编译项目
colcon build

# 刷新环境变量
source install/setup.bash
```

### 启动系统

#### 基础驱动启动
1.  **启动底层驱动与串口通信**:
    ```bash
    ros2 run PipeBot_driver serial_node
    ```
2.  **启动里程计发布**:
    ```bash
    ros2 run PipeBot_driver odometry_publisher_node
    ```

#### 蓝牙控制系统启动（使用 Bless 库）
启用蓝牙遥控功能，需要启动以下节点（建议在不同终端中运行）：

```bash
# 安装依赖
pip3 install bless

# 终端 1：蓝牙接收（使用 Bless 库接收手机命令）
ros2 run PipeBot_driver bluetooth_receiver_node

# 终端 2：命令处理（解析命令 + 看门狗保护）
ros2 run PipeBot_driver command_handler_node

# 终端 3：状态管理（收集所有传感器数据）
ros2 run PipeBot_driver state_manager_node

# 终端 4：蓝牙发送（可选，发送状态反馈到手机）
ros2 run PipeBot_driver bluetooth_sender_node
```

3.  **[未完成]启动整机功能 (包含定位与视觉)**:
    ```bash
    ros2 launch PipeBot_bringup robot_all.launch.py
    ```

---

## 4. 蓝牙控制系统使用指南

### 系统架构
```
手机蓝牙应用 ↔ bluetooth_receiver_node ↔ command_handler_node ↔ serial_node ↔ STM32
                                              ↓
                                    state_manager_node ↔ bluetooth_sender_node
```

### 命令协议

**上行命令**（手机 → 树莓派）：

| 命令 | 命令码 | 参数 | 说明 |
|------|--------|------|------|
| 自动模式 | `0x10` | 无 | 切换到自动模式，依赖测距模块避障 |
| 手动模式 | `0x11` | 无 | 切换到手动模式，遥控操作 |
| 前进 | `0x20` | [速度] | 手动模式：前进，速度 0-255 |
| 后退 | `0x21` | [速度] | 手动模式：后退，速度 0-255 |
| 制动 | `0x22` | 无 | 停止运动 |
| 紧急停止 | `0x23` | 无 | 两种模式：立即停止 |
| 左转 | `0x24` | 无 | 手动模式：原地左转 |
| 右转 | `0x25` | 无 | 手动模式：原地右转 |

**下行反馈**（树莓派 → 手机）：

| 数据类型 | 说明 | 内容 |
|---------|------|------|
| `0x01` | 位置信息 | x, y, theta（欧拉角） |
| `0x02` | 速度信息 | 线速度, 角速度 |
| `0x03` | 测距信息 | 左距离, 右距离 |
| `0x04` | 模式状态 | 当前模式, 蓝牙连接状态 |
| `0x05` | 警告信息 | 警告文本（如障碍物接近） |

### 运行模式

#### 自动模式
- **触发**：发送 `0x10` 命令
- **行为**：机器人自动前进，根据测距模块数据避障
- **控制**：只能发送 `0x23`（紧急停止），其他命令被忽略

#### 手动模式
- **触发**：发送 `0x11` 命令
- **行为**：完全由手机控制，长按发送连续命令
- **安全**：500ms 无命令自动制动（看门狗保护）

### 参数配置

```bash
# 命令处理节点参数
ros2 run PipeBot_driver command_handler_node --ros-args \
  -p command_timeout:=0.5 \        # 命令超时时间（秒）
  -p default_speed:=100 \           # 默认速度（0-255）
  -p turn_speed:=80                 # 转向速度

# 状态管理节点参数
ros2 run PipeBot_driver state_manager_node --ros-args \
  -p publish_rate:=2.0 \            # 状态发布频率（Hz）
  -p distance_warning_threshold:=200.0  # 测距警告阈值（mm）
```

### 手机应用开发

详见 [`docs/蓝牙控制系统.md`](docs/蓝牙控制系统.md) 中的 Android 开发示例。

**快速示例**（Python 测试）：
```python
import bluetooth

# 连接到树莓派
addr = "B8:27:EB:XX:XX:XX"  # 树莓派蓝牙地址
port = 1
sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
sock.connect((addr, port))

# 发送命令
sock.send(b'\x11')           # 切换手动模式
sock.send(b'\x20\x96')       # 前进，速度 150
sock.send(b'\x22')           # 制动

sock.close()
```

### 安全机制

1. **看门狗定时器**：手动模式下 500ms 无命令自动制动
2. **蓝牙断线保护**：检测连接状态，发出警告
3. **测距警告**：障碍物接近（< 200mm）时提醒
4. **紧急停止**：两种模式都可立即停止

---

## 5. 详细文档

- **蓝牙控制系统**：[`docs/蓝牙控制系统.md`](docs/蓝牙控制系统.md)
- **项目要求**：[`docs/项目要求.md`](docs/项目要求.md)
- **开发规范**：[`.roorules`](.roorules)