from setuptools import find_packages, setup

package_name = 'PipeBot_driver'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=[
        'setuptools',
        'bluezero>=0.6.0',
    ],
    zip_safe=True,
    maintainer='pi',
    maintainer_email='pi@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            # '可执行文件名 = 包名.文件名:main函数'
            'serial_node = PipeBot_driver.serial_node:main',
            'odometry_publisher_node = PipeBot_driver.odometry_publisher_node:main',
            'bluetooth_receiver_node = PipeBot_driver.bluetooth_receiver_node:main',
            'command_handler_node = PipeBot_driver.command_handler_node:main',
            'state_manager_node = PipeBot_driver.state_manager_node:main',
            'bluetooth_sender_node = PipeBot_driver.bluetooth_sender_node:main',
        ],
    },
)
