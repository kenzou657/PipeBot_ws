# AGENTS.md - Architect Mode

This file provides architect-mode-specific guidance for designing and planning in this repository.

## Architectural Constraints & Patterns

### Serial Protocol Design
- **Fixed 11-byte frames**: Non-negotiable for STM32 simplicity. Changing frame size requires protocol version bump.
- **Sliding window parsing**: Required for robustness. Cannot use simple state machine (packet loss breaks it).
- **Checksum-only validation**: No CRC or advanced error correction. Assumes low-noise serial link.
- **Message ID routing**: 0x01=control, 0x02=feedback, 0x05=IMU, 0x06=distance. Adding new sensors requires new ID.

### ROS2 Integration Patterns
- **Parameter-driven config**: All hardware settings (port, baudrate, PID) must be ROS2 Parameters, not hardcoded.
- **Topic-based pub/sub**: No direct function calls between nodes. Enables loose coupling and independent testing.
- **100Hz timer loop**: Serial parsing runs at 0.01s intervals. Changing frequency affects latency and CPU load.
- **Separate message types**: IMU, motor feedback, distance use different topics. Simplifies filtering and routing.

### Coordinate System & Defect Recording
- **REP-105 compliance**: `base_link` at robot center, `odom` at odometry origin. Non-negotiable for navigation stack compatibility.
- **Synchronous defect capture**: Vision must capture `odom` coordinates at detection time, not retroactively. Requires tight coupling between vision and localization nodes.
- **Tuple format**: `[defect_type, confidence, odom_coordinates]` is immutable. Changing structure breaks downstream analysis.

### Build System Architecture
- **Monorepo structure**: All packages in `src/` directory. Enables single `colcon build` for entire system.
- **Mixed build types**: Python packages use `ament_python`, interfaces use `ament_cmake`. Cannot be unified without major refactoring.
- **Entry points in setup.py**: Console scripts defined per-package. Enables `ros2 run` without launch files.

### Scalability & Extension Points
- **New sensor types**: Add new message ID (0x07+) in serial protocol, create new publisher in `serial_node`, subscribe in appropriate node.
- **New nodes**: Follow `SerialDriverNode` pattern (inherit from `Node`, declare parameters, create pub/sub, use timer).
- **Cloud integration**: `PipeBot_cloud` node handles all external communication. Isolates network concerns from core logic.

### Known Limitations & Future Work
- **Launch files incomplete**: `robot_all.launch.py` not yet implemented. Blocks full system integration testing.
- **No message definitions**: `PipeBot_interfaces` directory exists but contains no `.msg` or `.srv` files. Blocks custom message types.
- **Localization stub**: `PipeBot_localization` package exists but is empty. Requires IMU/encoder fusion implementation.
- **Vision integration pending**: `PipeBot_vision` package structure ready but no defect detection logic implemented.

## Design Decisions to Preserve
- Do NOT change serial frame structure without protocol versioning
- Do NOT add hardcoded config values (use ROS2 Parameters)
- Do NOT bypass topic-based communication (maintain loose coupling)
- Do NOT change coordinate system (breaks navigation compatibility)
- Do NOT make defect recording asynchronous (loses spatial accuracy)
