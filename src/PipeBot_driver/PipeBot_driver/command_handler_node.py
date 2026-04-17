import rclpy
from rclpy.node import Node
from std_msgs.msg import UInt8MultiArray, String
from geometry_msgs.msg import Twist
import time


# 命令类型定义
CMD_MODE_AUTO = 0x10
CMD_MODE_MANUAL = 0x11
CMD_FORWARD = 0x20
CMD_BACKWARD = 0x21
CMD_BRAKE = 0x22
CMD_STOP = 0x23
CMD_LEFT = 0x24
CMD_RIGHT = 0x25


class CommandHandlerNode(Node):
    def __init__(self):
        super().__init__('command_handler_node')
        
        # 声明参数
        self.declare_parameter('command_timeout', 0.5)  # 命令超时时间（秒）
        self.declare_parameter('default_speed', 100)  # 默认速度（0-255）
        self.declare_parameter('turn_speed', 80)  # 转向速度
        
        self.command_timeout = self.get_parameter('command_timeout').value
        self.default_speed = self.get_parameter('default_speed').value
        self.turn_speed = self.get_parameter('turn_speed').value
        
        # 状态变量
        self.current_mode = 'manual'  # 'auto' 或 'manual'
        self.last_command_time = time.time()
        self.is_moving = False
        
        # 订阅者
        self.command_sub = self.create_subscription(
            UInt8MultiArray,
            'bluetooth/command',
            self.command_callback,
            10
        )
        
        # 发布者
        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.mode_pub = self.create_publisher(String, 'robot/mode', 10)
        
        # 看门狗定时器
        self.watchdog_timer = self.create_timer(0.1, self.watchdog_callback)
        
        self.get_logger().info('Command handler node started')
        self.get_logger().info(f'Mode: {self.current_mode}, Timeout: {self.command_timeout}s')
    
    def command_callback(self, msg):
        """处理蓝牙命令"""
        if len(msg.data) < 1:
            self.get_logger().warn('Invalid command: empty data')
            return
        
        cmd_type = msg.data[0]
        
        # 更新最后命令时间
        self.last_command_time = time.time()
        
        # 处理命令
        if cmd_type == CMD_MODE_AUTO:
            self.handle_mode_auto()
        elif cmd_type == CMD_MODE_MANUAL:
            self.handle_mode_manual()
        elif cmd_type == CMD_STOP:
            self.handle_stop()
        elif self.current_mode == 'manual':
            # 手动模式下的命令
            if cmd_type == CMD_FORWARD:
                speed = msg.data[1] if len(msg.data) > 1 else self.default_speed
                self.handle_forward(speed)
            elif cmd_type == CMD_BACKWARD:
                speed = msg.data[1] if len(msg.data) > 1 else self.default_speed
                self.handle_backward(speed)
            elif cmd_type == CMD_LEFT:
                self.handle_left()
            elif cmd_type == CMD_RIGHT:
                self.handle_right()
            elif cmd_type == CMD_BRAKE:
                self.handle_brake()
            else:
                self.get_logger().warn(f'Unknown command: 0x{cmd_type:02X}')
        elif self.current_mode == 'auto':
            # 自动模式下只处理模式切换和停止命令
            if cmd_type in [CMD_FORWARD, CMD_BACKWARD]:
                self.get_logger().info(f'Command 0x{cmd_type:02X} ignored in auto mode')
            else:
                self.get_logger().warn(f'Unknown command: 0x{cmd_type:02X}')
    
    def handle_mode_auto(self):
        """切换到自动模式"""
        self.current_mode = 'auto'
        self.get_logger().info('Switched to AUTO mode')
        
        # 发布模式状态
        mode_msg = String()
        mode_msg.data = 'auto'
        self.mode_pub.publish(mode_msg)
        
        # 自动模式下发送初始前进命令
        self.send_velocity(0.2, 0.0)  # 慢速前进
        self.is_moving = True
    
    def handle_mode_manual(self):
        """切换到手动模式"""
        self.current_mode = 'manual'
        self.get_logger().info('Switched to MANUAL mode')
        
        # 发布模式状态
        mode_msg = String()
        mode_msg.data = 'manual'
        self.mode_pub.publish(mode_msg)
        
        # 切换到手动模式时先制动
        self.send_velocity(0.0, 0.0)
        self.is_moving = False
    
    def handle_forward(self, speed):
        """前进"""
        linear_speed = speed / 255.0 * 0.5  # 归一化到 0-0.5 m/s
        self.send_velocity(linear_speed, 0.0)
        self.is_moving = True
        self.get_logger().info(f'Forward: speed={speed}')
    
    def handle_backward(self, speed):
        """后退"""
        linear_speed = -(speed / 255.0 * 0.5)  # 负值表示后退
        self.send_velocity(linear_speed, 0.0)
        self.is_moving = True
        self.get_logger().info(f'Backward: speed={speed}')
    
    def handle_left(self):
        """左转"""
        self.send_velocity(0.0, 0.5)  # 正角速度 = 左转
        self.is_moving = True
        self.get_logger().info('Turn left')
    
    def handle_right(self):
        """右转"""
        self.send_velocity(0.0, -0.5)  # 负角速度 = 右转
        self.is_moving = True
        self.get_logger().info('Turn right')
    
    def handle_brake(self):
        """制动"""
        self.send_velocity(0.0, 0.0)
        self.is_moving = False
        self.get_logger().info('Brake')
    
    def handle_stop(self):
        """紧急停止"""
        self.send_velocity(0.0, 0.0)
        self.is_moving = False
        self.get_logger().warn('EMERGENCY STOP')
    
    def send_velocity(self, linear, angular):
        """发送速度命令"""
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self.cmd_vel_pub.publish(twist)
    
    def watchdog_callback(self):
        """看门狗定时器：检测命令超时"""
        if self.current_mode == 'manual' and self.is_moving:
            elapsed = time.time() - self.last_command_time
            
            if elapsed > self.command_timeout:
                self.get_logger().warn(f'Command timeout ({elapsed:.2f}s), auto brake')
                self.handle_brake()


def main(args=None):
    rclpy.init(args=args)
    node = CommandHandlerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
