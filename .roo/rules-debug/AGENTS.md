# AGENTS.md - Debug Mode

This file provides debug-mode-specific guidance for troubleshooting this repository.

## Serial Communication Debugging

### Common Issues & Solutions
- **Frame misalignment**: Check if buffer contains garbage data before 0x55 header. Use `self.buffer.popleft()` to slide window.
- **Checksum failures**: Verify calculation includes exactly first 9 bytes. Mask result with `0xFF`. Log at WARN level (expected in noisy serial).
- **Silent message loss**: All frame parsing failures must be logged. Check `self.get_logger().warn()` calls in receive_loop.
- **Timeout issues**: Serial timeout set to 0.1s in [`serial_node.py:23`](../../../src/PipeBot_driver/PipeBot_driver/serial_node.py:23). Increase if STM32 is slow.

### ROS2 Node Debugging
- **Parameter not found**: Verify `declare_parameter()` called before `get_parameter()` in `__init__`
- **Node won't start**: Check if serial port exists (`/dev/ttyAMA0` on RPi). Use `ls /dev/tty*` to verify.
- **No messages published**: Verify publisher created with `self.create_publisher()` before timer callback fires
- **Subscription callback not called**: Ensure `create_subscription()` uses correct topic name and message type

### Data Conversion Bugs
- **Signed integer overflow**: Use `to_s16()` helper for Big Endian conversion (see [`serial_node.py:51-53`](../../../src/PipeBot_driver/PipeBot_driver/serial_node.py:51))
- **Float precision loss**: Serial protocol transmits integers (×1000). Divide by 1000 when converting back to float.
- **Byte order confusion**: Protocol uses Big Endian (high byte first). Check `(h << 8) | l` order.

### Environment Setup
- **ROS2 environment not sourced**: Must run `source install/setup.bash` after `colcon build`
- **Package not found**: Rebuild with `colcon build` after adding new packages
- **Import errors**: Verify `__init__.py` exists in package directories

## Testing & Validation
- Run single package tests: `colcon build --packages-select PipeBot_driver --cmake-args -DCMAKE_BUILD_TYPE=Release`
- Check linting: `ament_flake8`, `ament_pep257`, `ament_copyright` run automatically
- Verify serial frames with hex dump: `hexdump -C /dev/ttyAMA0` (requires minicom or similar)
