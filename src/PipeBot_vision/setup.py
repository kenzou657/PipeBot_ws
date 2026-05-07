from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'PipeBot_vision'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # 添加launch文件
        (os.path.join('share', package_name, 'launch'),
            glob(os.path.join('launch', '*.launch.py'))),
        # 添加web文件
        (os.path.join('share', package_name, 'web'),
            glob(os.path.join('web', '*.html'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='pi',
    maintainer_email='pi@todo.todo',
    description='PipeBot 视觉系统 - USB相机采集与流媒体传输',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'image_capture_node = PipeBot_vision.image_capture_node:main',
        ],
    },
)
