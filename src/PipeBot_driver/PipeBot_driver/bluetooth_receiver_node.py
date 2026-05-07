import rclpy
from rclpy.node import Node
import threading
import time
from bluezero import peripheral, adapter
from std_msgs.msg import UInt8MultiArray, String
import logging
from gi.repository import GLib

logging.getLogger('bluezero').setLevel(logging.WARNING)


class BluetoothReceiverNode(Node):
    def __init__(self):
        super().__init__('bluetooth_receiver_node')
        
        # 声明参数
        self.declare_parameter('bt_name', 'PipeBot Control')
        self.declare_parameter('bt_adapter', 'hci0')
        self.declare_parameter('service_uuid', '12345678-1234-5678-1234-56789ABCDEF0')
        self.declare_parameter('rx_char_uuid', '12345678-1234-5678-1234-56789ABCDEF1')
        self.declare_parameter('tx_char_uuid', '12345678-1234-5678-1234-56789ABCDEF2')
        
        bt_name = self.get_parameter('bt_name').value
        bt_adapter = self.get_parameter('bt_adapter').value
        self.service_uuid = self.get_parameter('service_uuid').value
        self.rx_char_uuid = self.get_parameter('rx_char_uuid').value
        self.tx_char_uuid = self.get_parameter('tx_char_uuid').value
        
        # 发布者
        self.command_pub = self.create_publisher(UInt8MultiArray, 'bluetooth/command', 10)
        self.status_pub = self.create_publisher(String, 'bluetooth/status', 10)
        
        # 订阅者：接收反馈数据
        self.feedback_sub = self.create_subscription(
            UInt8MultiArray,
            'bluetooth/feedback',
            self.feedback_callback,
            10
        )
        
        # BLE 外设
        self.peripheral = None
        self.rx_characteristic = None
        self.tx_characteristic = None
        self.client_connected = False
        self.adapter_address = None
        self.mainloop = None
        
        # 硬编码蓝牙适配器地址
        self.adapter_address = '88:A2:9E:4B:BC:E6'
        self.get_logger().info(f'蓝牙适配器地址: {self.adapter_address}')
        
        # 在守护线程运行 BLE 服务器
        self.bt_thread = threading.Thread(target=self._run_ble_server, daemon=True)
        self.bt_thread.start()
        
        self.get_logger().info(f'蓝牙接收节点已启动: {bt_name}')
        self.get_logger().info('等待手机连接...')
        
        # 发布初始状态
        status_msg = String()
        status_msg.data = 'waiting'
        self.status_pub.publish(status_msg)
    
    def _run_ble_server(self):
        """在守护线程运行 BLE 服务器"""
        try:
            if self.adapter_address is None:
                self.get_logger().error('蓝牙适配器地址未获取，无法启动 BLE 服务器')
                return
            
            self._setup_ble_peripheral()
            
            # 创建并运行 GLib 主循环以处理 D-Bus 事件
            self.mainloop = GLib.MainLoop()
            self.get_logger().info('启动 GLib 主循环处理蓝牙事件')
            
            # 在主循环中启动广播
            GLib.idle_add(self._start_advertising)
            
            self.mainloop.run()
        
        except Exception as e:
            self.get_logger().error(f'BLE 服务器错误: {e}', exc_info=True)
    
    def _setup_ble_peripheral(self):
        """设置 BLE 外设"""
        try:
            # 创建外设，需要提供适配器地址
            self.peripheral = peripheral.Peripheral(
                adapter_address=self.adapter_address,
                local_name=self.get_parameter('bt_name').value
            )
            
            # 添加服务 - Peripheral.add_service(srv_id, uuid, primary)
            self.peripheral.add_service(
                srv_id=1,
                uuid=self.service_uuid,
                primary=True
            )
            
            # 添加接收特征值（写入）
            # Peripheral.add_characteristic(srv_id, chr_id, uuid, value, notifying, flags, ...)
            self.peripheral.add_characteristic(
                srv_id=1,
                chr_id=2,
                uuid=self.rx_char_uuid,
                value=b'',
                notifying=False,
                flags=['write', 'write-without-response'],
                write_callback=self._on_write_request
            )
            
            # 添加发送特征值（读取/通知）
            self.peripheral.add_characteristic(
                srv_id=1,
                chr_id=3,
                uuid=self.tx_char_uuid,
                value=b'',
                notifying=False,
                flags=['read', 'notify']
            )
            
            # 从特征值列表中获取引用（chr_id=3 是发送特征值）
            for char in self.peripheral.characteristics:
                # 通过路径中的 chr_id 来识别特征值
                if '0003' in char.get_path():
                    self.tx_characteristic = char
                    self.get_logger().info(f'找到发送特征值: {char.get_path()}')
                    break
            
            if self.tx_characteristic is None:
                self.get_logger().warn('未找到发送特征值，通知功能可能不可用')
            
            self.get_logger().info('BLE 外设已设置')
            self.get_logger().info(f'服务 UUID: {self.service_uuid}')
            self.get_logger().info(f'接收特征值 UUID: {self.rx_char_uuid}')
            self.get_logger().info(f'发送特征值 UUID: {self.tx_char_uuid}')
        
        except Exception as e:
            self.get_logger().error(f'设置 BLE 外设失败: {e}', exc_info=True)
    
    def _start_advertising(self):
        """开始广播（在 GLib 主循环中调用）"""
        try:
            if self.peripheral is None:
                self.get_logger().error('BLE 外设未初始化')
                return False
            
            self.get_logger().info('准备启动广播...')
            
            # 手动注册应用和广告，而不是调用 publish()
            for service in self.peripheral.services:
                self.peripheral.app.add_managed_object(service)
            for chars in self.peripheral.characteristics:
                self.peripheral.app.add_managed_object(chars)
            for desc in self.peripheral.descriptors:
                self.peripheral.app.add_managed_object(desc)
            
            self.peripheral._create_advertisement()
            
            if not self.peripheral.dongle.powered:
                self.peripheral.dongle.powered = True
            
            self.peripheral.srv_mng.register_application(self.peripheral.app, {})
            self.peripheral.ad_manager.register_advertisement(self.peripheral.advert, {})
            
            self.get_logger().info('BLE 广播已启动')
            
            # 发布连接状态
            status_msg = String()
            status_msg.data = 'advertising'
            self.status_pub.publish(status_msg)
            
            return False  # 从 idle 回调中移除
        
        except Exception as e:
            self.get_logger().error(f'启动广播失败: {e}', exc_info=True)
            return False
    
    def _on_write_request(self, value, options):
        """处理特征值写入请求
        
        :param value: 写入的数据（整数列表或字节）
        :param options: 写入选项
        """
        try:
            self.get_logger().info(f'写入回调被触发，value 类型: {type(value)}, value: {value}')
            
            # 处理不同的数据格式
            if isinstance(value, (list, tuple)):
                data = list(value)
            elif isinstance(value, bytes):
                data = list(value)
            else:
                data = list(value) if hasattr(value, '__iter__') else [value]
            
            # 将接收到的数据转换为字节数组
            command_msg = UInt8MultiArray()
            command_msg.data = data
            
            self.command_pub.publish(command_msg)
            
            # 记录日志
            hex_str = ' '.join([f'{b:02X}' for b in data])
            self.get_logger().info(f'接收到命令: {hex_str}')
        
        except Exception as e:
            self.get_logger().error(f'处理命令失败: {e}', exc_info=True)
    
    def feedback_callback(self, msg):
        """接收反馈数据并通过 BLE 发送"""
        if len(msg.data) > 0 and self.tx_characteristic is not None:
            try:
                # 将数据转换为整数列表（bluezero 期望的格式）
                data_list = list(msg.data)
                
                # 更新特征值
                self.tx_characteristic.set_value(data_list)
                
                # 通过 PropertiesChanged 信号通知客户端值已改变
                # 这会触发订阅该特征值的客户端接收通知
                self.tx_characteristic.PropertiesChanged(
                    'org.bluez.GattCharacteristic1',
                    {'Value': data_list},
                    []
                )
                
                # 记录日志
                hex_str = ' '.join([f'{b:02X}' for b in data_list[:20]])
                if len(data_list) > 20:
                    hex_str += '...'
                self.get_logger().info(f'已发送反馈数据: {len(data_list)} 字节 [{hex_str}]')
            
            except Exception as e:
                self.get_logger().error(f'发送反馈失败: {e}', exc_info=True)


def main(args=None):
    rclpy.init(args=args)
    node = BluetoothReceiverNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # 停止 GLib 主循环
        if node.mainloop is not None:
            try:
                node.mainloop.quit()
            except Exception as e:
                node.get_logger().error(f'停止主循环失败: {e}')
        
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
