# AGENTS.md - Ask Mode

This file provides ask-mode-specific guidance for understanding this repository.

## Project Architecture Overview

### System Components
- **PipeBot_driver**: Handles STM32 ↔ RPi serial communication (11-byte fixed protocol)
- **PipeBot_localization**: Fuses IMU + encoder data for odometry (REP-105 compliant)
- **PipeBot_vision**: Camera driver and defect detection (uses cloud ML models)
- **PipeBot_cloud**: Uploads images, state, and trajectory to data platform
- **PipeBot_bringup**: Launch scripts and parameter configs for system integration
- **PipeBot_interfaces**: Custom ROS2 message/service definitions (CMake-based)

### Data Flow
1. STM32 sends sensor data (IMU, motor feedback, distance) via serial protocol
2. `serial_node` parses frames and publishes to ROS2 topics
3. `localization` node subscribes to IMU/encoder, publishes odometry
4. `vision` node captures images, detects defects, records with current `odom` coordinates
5. `cloud` node uploads results to data platform

### Non-Obvious Design Decisions
- **Fixed 11-byte frames**: Simplifies parsing and reduces STM32 complexity
- **Sliding window buffer**: Handles packet loss and frame misalignment gracefully
- **ROS2 Parameters for all config**: Enables runtime reconfiguration without recompilation
- **Defect tuple format**: `[type, confidence, odom_coords]` ensures spatial context for analysis

## Key Files & Their Roles
- [`serial_node.py`](../../../src/PipeBot_driver/PipeBot_driver/serial_node.py): Core serial protocol implementation (141 lines)
- [`setup.py`](../../../src/PipeBot_driver/setup.py): Entry point definition for `serial_node` command
- [`.roorules`](../../../.roorules): Project-wide development guidelines (ROS2, serial protocol, coordinate system)

## Message Types & Topics
- **imu/data_raw**: `Imu` message (gyro euler angles from 0x05 frames)
- **motor/feedback**: `Float32MultiArray` [left_vel, right_vel] from 0x02 frames
- **sensor/distance**: `Float32MultiArray` [left_dist, right_dist] from 0x06 frames
- **cmd_vel**: `Twist` subscription for motor control (converted to 0x01 frames)

## Testing & Validation
- All packages use pytest + ament linting (flake8, pep257, copyright)
- Build system: `colcon build` (ament_python for Python packages, ament_cmake for interfaces)
- No launch files currently in `PipeBot_bringup/launch/` (under development)
