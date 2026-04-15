import rclpy
from rclpy.node import Node
import math
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32MultiArray
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
import tf2_ros


class OdometryPublisherNode(Node):
    def __init__(self):
        super().__init__('odometry_publisher_node')
        
        # 声明参数
        self.declare_parameter('wheel_base', 0.148)  # 轮距（米）
        
        self.wheel_base = self.get_parameter('wheel_base').value
        
        # 里程计状态变量
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.last_time = None
        
        # 存储最新的 IMU 数据
        self.latest_imu_msg = None
        
        # 订阅者
        self.motor_sub = self.create_subscription(
            Float32MultiArray,
            'motor/feedback',
            self.motor_callback,
            10
        )
        self.imu_sub = self.create_subscription(
            Imu,
            'imu/data_raw',
            self.imu_callback,
            10
        )
        
        # 发布者
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        
        # TF2 广播器
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        
        self.get_logger().info('Odometry publisher node started')
    
    def imu_callback(self, msg):
        """接收并存储最新的 IMU 数据"""
        self.latest_imu_msg = msg
    
    def motor_callback(self, msg):
        """
        接收电机反馈数据并计算里程计
        msg.data = [left_vel, right_vel]，单位：mm/s
        """
        if len(msg.data) < 2:
            return
        
        # 如果没有 IMU 数据，则无法发布（需要时间戳）
        if self.latest_imu_msg is None:
            return
        
        # 获取当前时间
        current_time = self.get_clock().now()
        
        # 初始化时间
        if self.last_time is None:
            self.last_time = current_time
            return
        
        # 计算时间差（秒）
        dt = (current_time - self.last_time).nanoseconds / 1e9
        self.last_time = current_time
        
        # 获取左右轮速度（单位：mm/s，已经过运动学解析）
        left_vel = msg.data[0] / 1000.0  # 转换为 m/s
        right_vel = msg.data[1] / 1000.0  # 转换为 m/s
        
        # 计算机器人线速度和角速度
        v = (left_vel + right_vel) / 2.0  # 线速度（m/s）
        omega = (right_vel - left_vel) / self.wheel_base  # 角速度（rad/s）
        
        # 更新位姿（使用简单的欧拉积分）
        delta_x = v * math.cos(self.theta) * dt
        delta_y = v * math.sin(self.theta) * dt
        delta_theta = omega * dt
        
        self.x += delta_x
        self.y += delta_y
        self.theta += delta_theta
        
        # 归一化角度到 [-pi, pi]
        self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))
        
        # 从 IMU 获取四元数（更准确的方向）
        qx = self.latest_imu_msg.orientation.x
        qy = self.latest_imu_msg.orientation.y
        qz = self.latest_imu_msg.orientation.z
        qw = self.latest_imu_msg.orientation.w
        
        # 发布 Odometry 消息
        odom_msg = Odometry()
        odom_msg.header.stamp = self.latest_imu_msg.header.stamp  # 使用 IMU 时间戳
        odom_msg.header.frame_id = 'odom'
        odom_msg.child_frame_id = 'base_link'
        
        # 设置位置
        odom_msg.pose.pose.position.x = self.x
        odom_msg.pose.pose.position.y = self.y
        odom_msg.pose.pose.position.z = 0.0
        
        # 设置方向（使用 IMU 的四元数）
        odom_msg.pose.pose.orientation.x = qx
        odom_msg.pose.pose.orientation.y = qy
        odom_msg.pose.pose.orientation.z = qz
        odom_msg.pose.pose.orientation.w = qw
        
        # 设置速度
        odom_msg.twist.twist.linear.x = v
        odom_msg.twist.twist.linear.y = 0.0
        odom_msg.twist.twist.angular.z = omega
        
        # 设置协方差（简单估计）
        odom_msg.pose.covariance[0] = 0.01  # x
        odom_msg.pose.covariance[7] = 0.01  # y
        odom_msg.pose.covariance[35] = 0.01  # yaw
        odom_msg.twist.covariance[0] = 0.01  # vx
        odom_msg.twist.covariance[35] = 0.01  # vyaw
        
        self.odom_pub.publish(odom_msg)
        
        # 广播 TF2 变换（odom -> base_link）
        t = TransformStamped()
        t.header.stamp = self.latest_imu_msg.header.stamp
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        
        t.transform.rotation.x = qx
        t.transform.rotation.y = qy
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw
        
        self.tf_broadcaster.sendTransform(t)
        
        self.get_logger().info(
            f'Odom: x={self.x:.3f}m, y={self.y:.3f}m, theta={math.degrees(self.theta):.1f}°, v={v:.3f}m/s'
        )


def main(args=None):
    rclpy.init(args=args)
    node = OdometryPublisherNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
