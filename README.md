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
1.  **启动底层驱动与串口通信**:
    ```bash
    ros2 run PipeBot_driver serial_node
    ```
2.  **[未完成]启动整机功能 (包含定位与视觉)**:
    ```bash
    ros2 launch PipeBot_bringup robot_all.launch.py
    ```