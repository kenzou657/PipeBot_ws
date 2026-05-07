"""
PipeBot 视觉流媒体启动文件

功能：
- 启动image_capture_node：采集1920×1080@30fps的USB相机图像
- 启动web_video_server：通过HTTP/MJPEG提供5fps的流媒体服务

网络配置：
- 分辨率：1920×1080
- 帧率：5fps（web_video_server输出）
- 编码：MJPEG
- 质量：80
- 带宽：~0.54 Mbps
- 端口：8080
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    # 声明启动参数
    camera_index_arg = DeclareLaunchArgument(
        'camera_index',
        default_value='0',
        description='USB相机索引'
    )
    
    frame_width_arg = DeclareLaunchArgument(
        'frame_width',
        default_value='1920',
        description='采集帧宽度'
    )
    
    frame_height_arg = DeclareLaunchArgument(
        'frame_height',
        default_value='1080',
        description='采集帧高度'
    )
    
    fps_arg = DeclareLaunchArgument(
        'fps',
        default_value='30',
        description='相机采集帧率'
    )
    
    jpeg_quality_arg = DeclareLaunchArgument(
        'jpeg_quality',
        default_value='85',
        description='JPEG压缩质量'
    )
    
    web_port_arg = DeclareLaunchArgument(
        'web_port',
        default_value='8080',
        description='web_video_server端口'
    )
    
    web_quality_arg = DeclareLaunchArgument(
        'web_quality',
        default_value='80',
        description='网络传输JPEG质量'
    )
    
    # image_capture_node
    image_capture_node = Node(
        package='PipeBot_vision',
        executable='image_capture_node',
        name='image_capture_node',
        parameters=[{
            'camera_index': LaunchConfiguration('camera_index'),
            'frame_width': LaunchConfiguration('frame_width'),
            'frame_height': LaunchConfiguration('frame_height'),
            'fps': LaunchConfiguration('fps'),
            'publish_rate': 30.0,  # 发布30fps到ROS话题
            'jpeg_quality': LaunchConfiguration('jpeg_quality'),
        }],
        output='screen',
        emulate_tty=True,
    )
    
    # web_video_server
    web_video_server_node = Node(
        package='web_video_server',
        executable='web_video_server',
        name='web_video_server',
        parameters=[{
            'port': LaunchConfiguration('web_port'),
            'quality': LaunchConfiguration('web_quality'),
            'default_stream_type': 'mjpeg',
            'max_streams': 5,
            'bitrate_kbps': 600,  # 限制码率 ≈ 0.6 Mbps
        }],
        output='screen',
        emulate_tty=True,
    )
    
    return LaunchDescription([
        camera_index_arg,
        frame_width_arg,
        frame_height_arg,
        fps_arg,
        jpeg_quality_arg,
        web_port_arg,
        web_quality_arg,
        image_capture_node,
        web_video_server_node,
    ])
