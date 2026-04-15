# AGENTS.md - Code Mode

This file provides code-mode-specific guidance for working with this repository.

## Code Style & Conventions

### Python Imports & Structure
- ROS2 nodes must import `rclpy` and `Node` from `rclpy.node`
- Serial communication requires `serial` and `struct` modules
- Use `collections.deque` for circular buffers in serial parsing (see [`serial_node.py:5,17`](../../../src/PipeBot_driver/PipeBot_driver/serial_node.py:5))
- Use Chinese for code comments.

### Node Implementation Pattern
- All nodes inherit from `rclpy.node.Node`
- Constructor must call `super().__init__('node_name')`
- Declare all parameters in `__init__` before using them
- Create publishers/subscribers before timers
- Use `self.create_timer(period, callback)` for periodic tasks (100Hz = 0.01s)

### Serial Frame Handling
- **Sliding window parsing**: Use `collections.deque` with fixed maxlen for robustness
- **Frame validation**: Check both frame footer (0xBB) AND checksum before processing
- **Error recovery**: On checksum failure, pop one byte and continue searching (don't discard entire buffer)
- **Conversion helper**: Implement `to_s16(h, l)` for Big Endian signed 16-bit conversion (see [`serial_node.py:51-53`](../../../src/PipeBot_driver/PipeBot_driver/serial_node.py:51))

### Message Publishing
- Use `Float32MultiArray` for sensor arrays (motor feedback, distance sensors)
- Use `Imu` message type for IMU data
- Use `Twist` for velocity commands (linear.x, angular.z)

### Logging Best Practices
- Replace all `print()` with `self.get_logger().info/warn/error()`
- Log frame parsing failures at WARN level (not ERROR, as they're expected in noisy serial)
- Include context in log messages (e.g., sensor values, frame IDs)

## Testing
- Test files use pytest framework (see `package.xml` test_depend)
- Linting: ament_flake8, ament_pep257, ament_copyright
- Run tests: `colcon build --packages-select <pkg> --cmake-args -DCMAKE_BUILD_TYPE=Release`
