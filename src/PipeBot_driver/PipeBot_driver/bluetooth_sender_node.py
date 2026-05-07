import rclpy
from rclpy.node import Node
from std_msgs.msg import String, UInt8MultiArray
from std_srvs.srv import Trigger
import json
import struct


class BluetoothSenderNode(Node):
    def __init__(self):
        super().__init__('bluetooth_sender_node')
        
        # 声明参数
        self.declare_parameter('feedback_rate', 2.0)  # 反馈发送频率（Hz）
        
        feedback_rate = self.get_parameter('feedback_rate').value
        
        # 状态变量
        self.latest_state = None
        self.bluetooth_receiver_node = None
        
        # 订阅者
        self.state_sub = self.create_subscription(
            String,
            'robot/state',
            self.state_callback,
            10
        )
        self.bt_status_sub = self.create_subscription(
            String,
            'bluetooth/status',
            self.bt_status_callback,
            10
        )
        
        # 发布者：发送反馈数据到蓝牙接收节点
        self.feedback_pub = self.create_publisher(UInt8MultiArray, 'bluetooth/feedback', 10)
        
        # 定时器：定期发送反馈
        timer_period = 1.0 / feedback_rate
        self.timer = self.create_timer(timer_period, self.send_feedback)
        
        self.get_logger().info('蓝牙发送节点已启动')
    
    def bt_status_callback(self, msg):
        """监听蓝牙连接状态"""
        self.get_logger().info(f'蓝牙状态: {msg.data}')
    
    def state_callback(self, msg):
        """接收机器人状态"""
        try:
            self.latest_state = json.loads(msg.data)
        except Exception as e:
            self.get_logger().error(f'解析状态失败: {e}')
    
    def send_feedback(self):
        """发送反馈数据到手机"""
        if self.latest_state is None:
            return
        
        # 构造反馈数据包
        feedback_data = self.build_feedback_packet()
        
        if feedback_data is not None:
            # 发布到 bluetooth/feedback 话题
            # bluetooth_receiver_node 会订阅此话题并通过 BLE 发送
            feedback_msg = UInt8MultiArray()
            feedback_msg.data = list(feedback_data)
            self.feedback_pub.publish(feedback_msg)
            
            self.get_logger().debug(f'反馈数据已发布: {len(feedback_data)} 字节')
    
    def build_feedback_packet(self):
        """
        构造反馈数据包
        
        数据包格式：
        [0xAA] [数据类型] [数据长度] [数据] [校验位] [0xBB]
        
        数据类型：
        0x01 = 位置信息
        0x02 = 速度信息
        0x03 = 测距信息
        0x04 = 模式状态
        0x05 = 警告信息
        """
        try:
            packets = []
            
            # 1. 位置信息包
            x = self.latest_state['position']['x']
            y = self.latest_state['position']['y']
            theta = self.latest_state['position']['theta']
            
            pos_data = struct.pack('<fff', x, y, theta)  # 小端序，3个浮点数
            pos_packet = self.create_packet(0x01, pos_data)
            packets.append(pos_packet)
            
            # 2. 速度信息包
            linear = self.latest_state['velocity']['linear']
            angular = self.latest_state['velocity']['angular']
            
            vel_data = struct.pack('<ff', linear, angular)
            vel_packet = self.create_packet(0x02, vel_data)
            packets.append(vel_packet)
            
            # 3. 测距信息包
            left_dist = int(self.latest_state['distance']['left'])
            right_dist = int(self.latest_state['distance']['right'])
            
            dist_data = struct.pack('<HH', left_dist, right_dist)  # 2个无符号短整型
            dist_packet = self.create_packet(0x03, dist_data)
            packets.append(dist_packet)
            
            # 4. 模式状态包
            mode = self.latest_state['mode']
            bt_status = self.latest_state['bluetooth_status']
            
            mode_byte = 0x01 if mode == 'auto' else 0x00
            bt_byte = 0x01 if bt_status == 'connected' else 0x00
            
            mode_data = bytes([mode_byte, bt_byte])
            mode_packet = self.create_packet(0x04, mode_data)
            packets.append(mode_packet)
            
            # 5. 警告信息包（如果有警告）
            if len(self.latest_state['warnings']) > 0:
                # 只发送第一个警告（简化处理）
                warning = self.latest_state['warnings'][0]
                warning_bytes = warning.encode('utf-8')[:50]  # 限制长度
                
                warning_packet = self.create_packet(0x05, warning_bytes)
                packets.append(warning_packet)
            
            # 合并所有数据包
            return b''.join(packets)
            
        except Exception as e:
            self.get_logger().error(f'构造反馈数据包失败: {e}')
            return None
    
    def create_packet(self, data_type, data):
        """
        创建数据包
        格式：[0xAA] [数据类型] [数据长度] [数据] [校验位] [0xBB]
        """
        packet = bytearray()
        packet.append(0xAA)  # 帧头
        packet.append(data_type)  # 数据类型
        packet.append(len(data))  # 数据长度
        packet.extend(data)  # 数据
        
        # 计算校验位（前面所有字节的和）
        checksum = sum(packet) & 0xFF
        packet.append(checksum)
        
        packet.append(0xBB)  # 帧尾
        
        return bytes(packet)


def main(args=None):
    rclpy.init(args=args)
    node = BluetoothSenderNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
