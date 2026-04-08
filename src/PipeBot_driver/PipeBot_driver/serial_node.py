import rclpy
from rclpy.node import Node
import serial
import struct
import collections
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray

class SerialDriverNode(Node):
    def __init__(self):
        super().__init__('serial_driver_node')
        
        # 1. 串口参数配置
        self.declare_parameter('port', '/dev/ttyAMA0') # 树莓派默认硬件串口
        self.declare_parameter('baudrate', 115200)
        self.buffer = collections.deque(maxlen=1024)
        
        port = self.get_parameter('port').value
        baud = self.get_parameter('baudrate').value
        
        try:
            self.ser = serial.Serial(port, baud, timeout=0.1)
            self.ser.reset_input_buffer()
            self.get_logger().info(f"Connected to STM32 at {port}")
        except Exception as e:
            self.get_logger().error(f"Failed to open serial port: {e}")

        # 2. 发布者与订阅者
        self.imu_pub = self.create_publisher(Imu, 'imu/data_raw', 10)
        self.odom_raw_pub = self.create_publisher(Float32MultiArray, 'motor/feedback', 10)
        self.distance_pub = self.create_publisher(Float32MultiArray, 'sensor/distance', 10)
        self.cmd_sub = self.create_subscription(Twist, 'cmd_vel', self.cmd_vel_callback, 10)

        # 3. 定时器：100Hz 频率解析串口
        self.timer = self.create_timer(0.01, self.receive_loop)

    def check_sum(self, data):
        """计算前9字节的和校验"""
        return sum(data[:9]) & 0xFF

    def parse_frame(self, frame):
        """根据标识位解析 11 Bytes 帧数据"""
        header, msg_id, length, *data, checksum, footer = frame
        
        # 校验位验证
        if self.check_sum(frame) != checksum or footer != 0xBB:
            return

        # 转换为带符号的16位整数 (Big Endian)
        def to_s16(h, l):
            val = (h << 8) | l
            return val if val < 32768 else val - 65536

        if msg_id == 0x02:  # 速度反馈
            # data[0]:左方向, data[1]:左速度, data[3]:右方向, data[4]:右速度
            left_vel = data[1] if data[0] == 0 else -data[1]
            right_vel = data[4] if data[3] == 0 else -data[4]
            msg = Float32MultiArray(data=[float(left_vel), float(right_vel)])
            self.odom_raw_pub.publish(msg)

        elif msg_id == 0x05:  # 陀螺仪欧拉角 (示例：发布IMU或自定义姿态)
            roll = to_s16(data[0], data[1]) / 100.0   # 假设单位是0.01度
            pitch = to_s16(data[2], data[3]) / 100.0
            yaw = to_s16(data[4], data[5]) / 100.0
            # 这里可以进一步封装成四元数发布

        elif msg_id == 0x06:  # 测距模块数据 (单位: mm)
            # data[0,1] 是左距离，data[2,3] 是右距离
            left_dist = to_s16(data[0], data[1])
            right_dist = to_s16(data[2], data[3])

            self.get_logger().info(f'测距: 左 {left_dist}mm, 右 {right_dist}mm')

            # 发布数据（建议在 __init__ 中先创建 distance_pub）
            dist_msg = Float32MultiArray()
            dist_msg.data = [float(left_dist), float(right_dist)]
            self.distance_pub.publish(dist_msg)
            
    def receive_loop(self):
        # 1. 将串口中所有可用字节读入缓冲区
        if self.ser.in_waiting > 0:
            new_data = self.ser.read(self.ser.in_waiting)
            self.buffer.extend(new_data)

        # 2. 只要缓冲区长度可能包含一个完整帧（11字节）就持续处理
        while len(self.buffer) >= 11:
            # 查找帧头
            if self.buffer[0] != 0x55:
                self.buffer.popleft() # 丢弃非帧头字节，窗口向后滑动
                continue
            
            # 找到了 0x55，提取潜在的整帧数据（不弹出，只读取）
            potential_frame = list(self.buffer)[:11]
            
            # 检查帧尾和校验位
            if potential_frame[10] == 0xBB:
                checksum = sum(potential_frame[:9]) & 0xFF
                if checksum == potential_frame[9]:
                    # 校验通过，这确实是一个完整帧
                    self.parse_frame(bytes(potential_frame))
                    # 处理完后，从缓冲区弹出这11个字节
                    for _ in range(11):
                        self.buffer.popleft()
                else:
                    # 校验失败，说明这个 0x55 可能是伪造的（数据位里的0x55）
                    # 弹出帧头，继续寻找下一个 0x55
                    self.get_logger().warn("Checksum mismatch, sliding window...")
                    self.buffer.popleft()
            else:
                # 帧尾不对，说明这也不是正确的帧
                self.buffer.popleft()

    def cmd_vel_callback(self, msg):
        """将 ROS2 cmd_vel 转换为 STM32 控制指令 (标识位 0x01)"""
        # 简单的差速转换逻辑（需根据你的物理参数调整）
        linear = msg.linear.x
        angular = msg.angular.z
        
        left_speed = int(max(min((linear - angular) * 100, 255), -255))
        right_speed = int(max(min((linear + angular) * 100, 255), -255))
        
        # 构造协议帧
        frame = bytearray([0x55, 0x01, 0x06])
        frame.append(0 if left_speed >= 0 else 1) # 左方向
        frame.append(abs(left_speed))             # 左速度
        frame.append(0x00)                        # 预留
        frame.append(0 if right_speed >= 0 else 1)# 右方向
        frame.append(abs(right_speed))            # 右速度
        frame.append(0x00)                        # 预留
        frame.append(self.check_sum(frame))       # 校验位
        frame.append(0xBB)                        # 帧尾
        
        self.ser.write(frame)

def main(args=None):
    rclpy.init(args=args)
    node = SerialDriverNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()