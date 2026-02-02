"""
Test Task Publisher
===================
Simulates robot tasks for testing MINT settlements.

Usage:
    ros2 run mint_ros test_task
    
    # Or with custom task duration:
    ros2 run mint_ros test_task --ros-args -p duration:=10
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import time
import uuid


class TestTaskPublisher(Node):
    """Publishes fake task start/end events for testing."""

    def __init__(self):
        super().__init__('mint_test_task')
        
        self.declare_parameter('duration', 5)
        self.declare_parameter('task_id', '')
        
        self.start_pub = self.create_publisher(String, '/mint/task_start', 10)
        self.end_pub = self.create_publisher(String, '/mint/task_end', 10)
        
        # Give publishers time to connect
        time.sleep(1.0)
        
        # Run a test task
        self.run_task()

    def run_task(self):
        duration = self.get_parameter('duration').value
        task_id = self.get_parameter('task_id').value
        
        if not task_id:
            task_id = f"test_task_{uuid.uuid4().hex[:8]}"
        
        self.get_logger().info(f'Starting task: {task_id}')
        
        # Publish start
        start_msg = String()
        start_msg.data = task_id
        self.start_pub.publish(start_msg)
        
        # Wait for duration
        self.get_logger().info(f'Working for {duration} seconds...')
        time.sleep(duration)
        
        # Publish end
        end_msg = String()
        end_msg.data = task_id
        self.end_pub.publish(end_msg)
        
        self.get_logger().info(f'Task completed: {task_id}')
        
        # Give time for settlement
        time.sleep(2.0)


def main(args=None):
    rclpy.init(args=args)
    node = TestTaskPublisher()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
