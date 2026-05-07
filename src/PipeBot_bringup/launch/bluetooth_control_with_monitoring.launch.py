"""
蓝牙控制系统启动文件（带监控节点）

启动蓝牙相关的所有节点，并启动 ROS2 话题监控节点用于调试：
- bluetooth_receiver_node: BLE 服务器
- state_manager_node: 状态聚合
- command_handler_node: 命令处理
- bluetooth_sender_node: 反馈构造
- 话题监控节点（可选）

使用方法：
    ros2 launch PipeBot_bringup bluetooth_control_with_monitoring.launch.py
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    """生成启动描述"""
    
    # 声明启动参数
    enable_monitoring = DeclareLaunchArgument(
        'enable_monitoring',
        default_value='false',
        description='是否启用话题监控节点'
    )
    
    # 蓝牙接收节点
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
    
    # 状态管理节点
    state_manager_node = Node(
        package='PipeBot_driver',
        executable='state_manager_node',
        name='state_manager_node',
        output='screen',
        parameters=[
            {'publish_rate': 2.0},
            {'distance_warning_threshold': 200.0},
        ],
    )
    
    # 命令处理节点
    command_handler_node = Node(
        package='PipeBot_driver',
        executable='command_handler_node',
        name='command_handler_node',
        output='screen',
        parameters=[
            {'command_timeout': 0.5},
            {'default_speed': 100},
            {'turn_speed': 80},
        ],
    )
    
    # 蓝牙发送节点
    bluetooth_sender_node = Node(
        package='PipeBot_driver',
        executable='bluetooth_sender_node',
        name='bluetooth_sender_node',
        output='screen',
        parameters=[
            {'feedback_rate': 2.0},
        ],
    )
    
    return LaunchDescription([
        enable_monitoring,
        bluetooth_receiver_node,
        state_manager_node,
        command_handler_node,
        bluetooth_sender_node,
    ])
