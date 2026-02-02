from setuptools import setup
import os
from glob import glob

package_name = 'mint_ros'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
    ],
    install_requires=[
        'setuptools',
        'solders>=0.18.0',
        'solana>=0.30.0',
        'base58>=2.1.0',
    ],
    zip_safe=True,
    maintainer='FoundryNet',
    maintainer_email='hello@foundrynet.io',
    description='MINT Protocol integration for ROS 2 - Earn MINT tokens for robot work',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'settler = mint_ros.settler:main',
            'test_task = mint_ros.test_task:main',
        ],
    },
)
