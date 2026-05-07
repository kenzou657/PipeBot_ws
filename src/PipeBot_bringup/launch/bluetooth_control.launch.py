"""
蓝牙控制系统启动文件

启动蓝牙相关的所有节点：
- bluetooth_receiver_node: BLE 服务器，接收手机连接和命令
- state_manager_node: 聚合所有状态信息
- command_handler_node: 处理蓝牙命令，发送速度控制
- bluetooth_sender_node: 构造反馈数据包

使用方法：
    ros2 launch PipeBot_bringup bluetooth_control.launch.py
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """生成启动描述"""
    
    # 蓝牙接收节点 - BLE 服务器
    bluetooth_receiver_node = Node(
        package='PipeBot_driver',
        executable='bluetooth_receiver_node',
        name='bluetooth_receiver_node',
        output='screen',
        parameters=[
            {'bt_name': 'PipeBot Control'},
            {'bt_adapter': 'hci0'},
            {'service_uuid': '12345678-1234-5678-1234-56789ABCDEF0'},
            {'rx_char_uuid': '12345678-1234-5678-1234-56789ABCDEF1'},
            {'tx_char_uuid': '12345678-1234-5678-1234-56789ABCDEF2'},
        ],
    )
    
    # 状态管理节点 - 聚合所有状态
    state_manager_node = Node(
        package='PipeBot_driver',
        executable='state_manager_node',
        name='state_manager_node',
        output='screen',
        parameters=[
            {'publish_rate': 2.0},  # 状态发布频率（Hz）
            {'distance_warning_threshold': 200.0},  # 测距警告阈值（mm）
        ],
    )
    
    # 命令处理节点 - 处理蓝牙命令
    command_handler_node = Node(
        package='PipeBot_driver',
        executable='command_handler_node',
        name='command_handler_node',
        output='screen',
        parameters=[
            {'command_timeout': 0.5},  # 命令超时时间（秒）
            {'default_speed': 100},  # 默认速度（0-255）
            {'turn_speed': 80},  # 转向速度
        ],
    )
    
    # 蓝牙发送节点 - 构造反馈数据包
    bluetooth_sender_node = Node(
        package='PipeBot_driver',
        executable='bluetooth_sender_node',
        name='bluetooth_sender_node',
        output='screen',
        parameters=[
            {'feedback_rate': 2.0},  # 反馈发送频率（Hz）
        ],
    )
    
    return LaunchDescription([
        bluetooth_receiver_node,
        state_manager_node,
        command_handler_node,
        bluetooth_sender_node,
    ])
