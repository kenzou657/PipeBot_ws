import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32MultiArray
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
import time


class StateManagerNode(Node):
    def __init__(self):
        super().__init__('state_manager_node')
        
        # 声明参数
        self.declare_parameter('publish_rate', 2.0)  # 状态发布频率（Hz）
        self.declare_parameter('distance_warning_threshold', 200.0)  # 测距警告阈值（mm）
        
        publish_rate = self.get_parameter('publish_rate').value
        self.distance_threshold = self.get_parameter('distance_warning_threshold').value
        
        # 状态变量
        self.robot_state = {
            'mode': 'manual',
            'bluetooth_status': 'disconnected',
            'position': {'x': 0.0, 'y': 0.0, 'theta': 0.0},
            'velocity': {'linear': 0.0, 'angular': 0.0},
            'imu': {'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0},
            'distance': {'left': 0.0, 'right': 0.0},
            'motor_feedback': {'left': 0.0, 'right': 0.0},
            'warnings': [],
            'timestamp': time.time()
        }
        
        # 订阅者
        self.mode_sub = self.create_subscription(
            String, 'robot/mode', self.mode_callback, 10
        )
        self.bt_status_sub = self.create_subscription(
            String, 'bluetooth/status', self.bt_status_callback, 10
        )
        self.odom_sub = self.create_subscription(
            Odometry, 'odom', self.odom_callback, 10
        )
        self.cmd_vel_sub = self.create_subscription(
            Twist, 'cmd_vel', self.cmd_vel_callback, 10
        )
        self.imu_sub = self.create_subscription(
            Imu, 'imu/data_raw', self.imu_callback, 10
        )
        self.distance_sub = self.create_subscription(
            Float32MultiArray, 'sensor/distance', self.distance_callback, 10
        )
        self.motor_sub = self.create_subscription(
            Float32MultiArray, 'motor/feedback', self.motor_callback, 10
        )
        
        # 发布者
        self.state_pub = self.create_publisher(String, 'robot/state', 10)
        self.warning_pub = self.create_publisher(String, 'robot/warning', 10)
        
        # 定时器：定期发布状态
        timer_period = 1.0 / publish_rate
        self.timer = self.create_timer(timer_period, self.publish_state)
        
        self.get_logger().info('State manager node started')
    
    def mode_callback(self, msg):
        """接收模式状态"""
        self.robot_state['mode'] = msg.data
    
    def bt_status_callback(self, msg):
        """接收蓝牙连接状态"""
        old_status = self.robot_state['bluetooth_status']
        self.robot_state['bluetooth_status'] = msg.data
        
        if old_status != msg.data:
            self.get_logger().info(f'Bluetooth status changed: {old_status} -> {msg.data}')
            
            # 如果蓝牙断开，发出警告
            if msg.data == 'disconnected':
                self.add_warning('bluetooth_disconnected')
    
    def odom_callback(self, msg):
        """接收里程计数据"""
        self.robot_state['position']['x'] = msg.pose.pose.position.x
        self.robot_state['position']['y'] = msg.pose.pose.position.y
        
        # 从四元数提取 yaw 角
        qz = msg.pose.pose.orientation.z
        qw = msg.pose.pose.orientation.w
        import math
        yaw = math.atan2(2.0 * (qw * qz), 1.0 - 2.0 * (qz * qz))
        self.robot_state['position']['theta'] = math.degrees(yaw)
    
    def cmd_vel_callback(self, msg):
        """接收速度命令"""
        self.robot_state['velocity']['linear'] = msg.linear.x
        self.robot_state['velocity']['angular'] = msg.angular.z
    
    def imu_callback(self, msg):
        """接收 IMU 数据"""
        # 从四元数提取欧拉角
        import math
        
        qx = msg.orientation.x
        qy = msg.orientation.y
        qz = msg.orientation.z
        qw = msg.orientation.w
        
        # Roll (x-axis rotation)
        sinr_cosp = 2.0 * (qw * qx + qy * qz)
        cosr_cosp = 1.0 - 2.0 * (qx * qx + qy * qy)
        roll = math.atan2(sinr_cosp, cosr_cosp)
        
        # Pitch (y-axis rotation)
        sinp = 2.0 * (qw * qy - qz * qx)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)
        else:
            pitch = math.asin(sinp)
        
        # Yaw (z-axis rotation)
        siny_cosp = 2.0 * (qw * qz + qx * qy)
        cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        
        self.robot_state['imu']['roll'] = math.degrees(roll)
        self.robot_state['imu']['pitch'] = math.degrees(pitch)
        self.robot_state['imu']['yaw'] = math.degrees(yaw)
    
    def distance_callback(self, msg):
        """接收测距数据"""
        if len(msg.data) >= 2:
            self.robot_state['distance']['left'] = msg.data[0]
            self.robot_state['distance']['right'] = msg.data[1]
            
            # 检查距离警告
            if msg.data[0] < self.distance_threshold or msg.data[1] < self.distance_threshold:
                self.add_warning(f'obstacle_detected: L={msg.data[0]:.0f}mm, R={msg.data[1]:.0f}mm')
    
    def motor_callback(self, msg):
        """接收电机反馈"""
        if len(msg.data) >= 2:
            self.robot_state['motor_feedback']['left'] = msg.data[0]
            self.robot_state['motor_feedback']['right'] = msg.data[1]
    
    def add_warning(self, warning):
        """添加警告"""
        if warning not in self.robot_state['warnings']:
            self.robot_state['warnings'].append(warning)
            
            # 发布警告
            warning_msg = String()
            warning_msg.data = warning
            self.warning_pub.publish(warning_msg)
            
            self.get_logger().warn(f'Warning: {warning}')
    
    def clear_warnings(self):
        """清除警告"""
        self.robot_state['warnings'] = []
    
    def publish_state(self):
        """发布机器人状态"""
        self.robot_state['timestamp'] = time.time()
        
        # 构造状态字符串（JSON 格式）
        import json
        state_json = json.dumps(self.robot_state, indent=2)
        
        state_msg = String()
        state_msg.data = state_json
        self.state_pub.publish(state_msg)
        
        # 定期清除已处理的警告
        if len(self.robot_state['warnings']) > 0:
            self.get_logger().info(f'Active warnings: {len(self.robot_state["warnings"])}')


def main(args=None):
    rclpy.init(args=args)
    node = StateManagerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
