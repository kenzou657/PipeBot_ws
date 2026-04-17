import rclpy
from rclpy.node import Node
import asyncio
import threading
from bless import BlessServer
from std_msgs.msg import UInt8MultiArray, String
import logging

# 禁用 bless 的调试日志
logging.getLogger('bless').setLevel(logging.WARNING)


class BluetoothReceiverNode(Node):
    def __init__(self):
        super().__init__('bluetooth_receiver_node')
        
        # 声明参数
        self.declare_parameter('bt_name', 'PipeBot Control')
        self.declare_parameter('bt_adapter', 'hci0')
        
        bt_name = self.get_parameter('bt_name').value
        bt_adapter = self.get_parameter('bt_adapter').value
        
        # 发布者
        self.command_pub = self.create_publisher(UInt8MultiArray, 'bluetooth/command', 10)
        self.status_pub = self.create_publisher(String, 'bluetooth/status', 10)
        
        # 蓝牙服务器
        self.server = BlessServer(name=bt_name, adapter_index=0)  # adapter_index 对应 hci0
        self.client_connected = False
        self.rx_characteristic = None
        self.tx_characteristic = None
        
        # 在后台线程运行蓝牙服务器
        self.bt_thread = threading.Thread(target=self._run_bluetooth_server, daemon=True)
        self.bt_thread.start()
        
        self.get_logger().info(f'Bluetooth receiver node started: {bt_name}')
        self.get_logger().info('Waiting for mobile app connection...')
        
        # 发布初始状态
        status_msg = String()
        status_msg.data = 'waiting'
        self.status_pub.publish(status_msg)
    
    def _run_bluetooth_server(self):
        """在后台线程运行蓝牙服务器"""
        try:
            asyncio.run(self._bluetooth_loop())
        except Exception as e:
            self.get_logger().error(f'Bluetooth server error: {e}')
    
    async def _bluetooth_loop(self):
        """蓝牙事件循环"""
        try:
            async with self.server:
                self.get_logger().info('Bluetooth server started')
                
                # 设置事件处理
                @self.server.on("connect")
                def on_connect(peer):
                    self.client_connected = True
                    self.get_logger().info(f'Client connected: {peer}')
                    
                    # 发布连接状态
                    status_msg = String()
                    status_msg.data = 'connected'
                    self.status_pub.publish(status_msg)
                
                @self.server.on("disconnect")
                def on_disconnect(peer):
                    self.client_connected = False
                    self.get_logger().warn(f'Client disconnected: {peer}')
                    
                    # 发布断开状态
                    status_msg = String()
                    status_msg.data = 'disconnected'
                    self.status_pub.publish(status_msg)
                
                # 保持服务器运行
                while True:
                    await asyncio.sleep(1)
        
        except Exception as e:
            self.get_logger().error(f'Bluetooth loop error: {e}')
    
    def handle_command(self, data: bytes):
        """处理接收到的命令"""
        try:
            # 将接收到的数据转换为字节数组
            command_msg = UInt8MultiArray()
            command_msg.data = list(data)
            
            self.command_pub.publish(command_msg)
            
            # 记录日志
            hex_str = ' '.join([f'{b:02X}' for b in data])
            self.get_logger().info(f'Received command: {hex_str}')
            
        except Exception as e:
            self.get_logger().error(f'Failed to handle command: {e}')
    
    def send_feedback(self, data: bytes):
        """发送反馈数据到手机（供其他节点调用）"""
        if self.client_connected and self.tx_characteristic is not None:
            try:
                # 这里需要通过 Bless 的特征值写入
                # 实际实现需要在异步上下文中进行
                pass
            except Exception as e:
                self.get_logger().error(f'Failed to send feedback: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = BluetoothReceiverNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
