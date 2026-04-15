# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Build & Test Commands

```bash
# Build entire workspace
colcon build

# Build single package
colcon build --packages-select PipeBot_driver

# Run tests for a package
colcon build --packages-select PipeBot_driver --cmake-args -DCMAKE_BUILD_TYPE=Release

# Source environment (required before running nodes)
source install/setup.bash

# Run serial driver node
ros2 run PipeBot_driver serial_node

# Run full system (incomplete, under development)
ros2 launch PipeBot_bringup robot_all.launch.py
```

## Critical Project-Specific Rules

### Serial Protocol (STM32 ↔ RPi)
- **Frame structure**: `[0x55][ID][0x06][Data0-5][Checksum][0xBB]` (11 bytes fixed)
- **Checksum**: Sum of first 9 bytes, masked with `0xFF`
- **Float handling**: All floats transmitted as integers (multiply by 1000) or use `struct` serialization
- **Frame parsing**: Must handle packet loss and frame misalignment with sliding window buffer (see [`serial_node.py:80-112`](src/PipeBot_driver/PipeBot_driver/serial_node.py:80))
- **Message IDs**: 0x01=motor control, 0x02=speed feedback, 0x05=gyro euler angles, 0x06=distance sensor

### ROS2 Node Naming & Parameters
- **Node class names**: Use PascalCase (e.g., `SerialDriverNode`)
- **Package names**: Use CamelCase with underscores (e.g., `PipeBot_driver`)
- **All hardware config MUST use ROS2 Parameters**: Serial port, baudrate, PID values, etc. (see [`serial_node.py:14-20`](src/PipeBot_driver/PipeBot_driver/serial_node.py:14))
- **Logging**: Use `self.get_logger()` instead of `print()` with appropriate levels (info/warn/error)

### Coordinate System & Defect Recording
- **Frame convention**: REP-105 compliant. `base_link` at robot center, `odom` at odometry origin
- **Defect tuple format**: `[defect_type, confidence, odom_coordinates]` when `PipeBot_vision` detects issues
- **Sync requirement**: Vision defects MUST capture current `odom` coordinates synchronously

### Build System
- **Python packages**: Use `ament_python` build type
- **Interface package**: `PipeBot_interfaces` uses `ament_cmake` (CMake-based)
- **Entry points**: Defined in `setup.py` console_scripts (e.g., `serial_node = PipeBot_driver.serial_node:main`)

### Error Handling
- **Serial robustness**: Code must handle packet loss, frame misalignment, and checksum failures gracefully
- **Silent failures**: Avoid silent failures in IPC/serial communication; log all anomalies
