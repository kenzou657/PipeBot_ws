import rclpy
from rclpy.node import Node
import cv2
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from nav_msgs.msg import Odometry


class ImageCaptureNode(Node):
    def __init__(self):
        super().__init__('image_capture_node')
        
        # 声明参数
        self.declare_parameter('camera_index', 0)  # USB 相机索引
        self.declare_parameter('frame_width', 1920)  # 1080p 宽度
        self.declare_parameter('frame_height', 1080)  # 1080p 高度
        self.declare_parameter('fps', 30)  # 相机采集帧率
        self.declare_parameter('publish_rate', 1.0)  # 发布频率（Hz），用于云端检测
        self.declare_parameter('jpeg_quality', 85)  # JPEG 压缩质量（用于云端上传）
        
        camera_index = self.get_parameter('camera_index').value
        frame_width = self.get_parameter('frame_width').value
        frame_height = self.get_parameter('frame_height').value
        fps = self.get_parameter('fps').value
        publish_rate = self.get_parameter('publish_rate').value
        self.jpeg_quality = self.get_parameter('jpeg_quality').value
        
        # 初始化 OpenCV 相机
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            self.get_logger().error(f'Failed to open camera {camera_index}')
            return
        
        # 设置相机参数
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        
        # 验证实际设置的参数
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        
        self.get_logger().info(
            f'Camera initialized: {actual_width}x{actual_height} @ {actual_fps}fps'
        )
        
        # CV Bridge 用于 OpenCV 和 ROS 图像消息转换
        self.bridge = CvBridge()
        
        # 存储最新的里程计数据（用于记录缺陷位置）
        self.latest_odom = None
        
        # 发布者
        self.image_pub = self.create_publisher(Image, 'camera/image_raw', 10)
        self.compressed_pub = self.create_publisher(Image, 'camera/image_compressed', 10)
        
        # 订阅里程计（用于同步位置信息）
        self.odom_sub = self.create_subscription(
            Odometry,
            'odom',
            self.odom_callback,
            10
        )
        
        # 定时器：按照 publish_rate 发布图像
        timer_period = 1.0 / publish_rate
        self.timer = self.create_timer(timer_period, self.capture_and_publish)
        
        self.get_logger().info(
            f'Image capture node started, publishing at {publish_rate} Hz'
        )
    
    def odom_callback(self, msg):
        """接收并存储最新的里程计数据"""
        self.latest_odom = msg
    
    def capture_and_publish(self):
        """捕获图像并发布"""
        ret, frame = self.cap.read()
        
        if not ret:
            self.get_logger().warn('Failed to capture frame')
            return
        
        # 获取当前时间戳
        current_time = self.get_clock().now().to_msg()
        
        # 发布原始图像（用于本地显示或调试）
        try:
            image_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            image_msg.header.stamp = current_time
            image_msg.header.frame_id = 'camera_link'
            self.image_pub.publish(image_msg)
        except Exception as e:
            self.get_logger().error(f'Failed to publish raw image: {e}')
        
        # 压缩图像（用于云端上传，减少带宽）
        try:
            # JPEG 压缩
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
            _, compressed_data = cv2.imencode('.jpg', frame, encode_param)
            
            # 转换为 ROS 图像消息（使用 mono8 编码存储压缩数据）
            compressed_msg = Image()
            compressed_msg.header.stamp = current_time
            compressed_msg.header.frame_id = 'camera_link'
            compressed_msg.height = 1
            compressed_msg.width = len(compressed_data)
            compressed_msg.encoding = 'jpeg'
            compressed_msg.is_bigendian = 0
            compressed_msg.step = len(compressed_data)
            compressed_msg.data = compressed_data.tobytes()
            
            self.compressed_pub.publish(compressed_msg)
        except Exception as e:
            self.get_logger().error(f'Failed to publish compressed image: {e}')
        
        # 记录当前位置信息（用于缺陷定位）
        if self.latest_odom is not None:
            x = self.latest_odom.pose.pose.position.x
            y = self.latest_odom.pose.pose.position.y
            self.get_logger().info(
                f'Image captured at position: x={x:.3f}m, y={y:.3f}m'
            )
        else:
            self.get_logger().warn('No odometry data available')
    
    def destroy_node(self):
        """清理资源"""
        if self.cap.isOpened():
            self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ImageCaptureNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
