"""
MINT Settler Launch File

Usage:
    ros2 launch mint_ros settler.launch.py keypair_path:=/path/to/keypair.json
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'keypair_path',
            default_value='',
            description='Path to Solana keypair JSON file'
        ),
        DeclareLaunchArgument(
            'rpc_endpoint',
            default_value='https://api.mainnet-beta.solana.com',
            description='Solana RPC endpoint'
        ),
        DeclareLaunchArgument(
            'min_duration',
            default_value='1',
            description='Minimum task duration to settle (seconds)'
        ),
        
        Node(
            package='mint_ros',
            executable='settler',
            name='mint_settler',
            parameters=[{
                'keypair_path': LaunchConfiguration('keypair_path'),
                'rpc_endpoint': LaunchConfiguration('rpc_endpoint'),
                'min_duration': LaunchConfiguration('min_duration'),
            }],
            output='screen',
        ),
    ])
