from setuptools import setup
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='galera-node-health',
    version='0.1.0',
    description='Health check for a Galera cluster node (MySQL, MariaDB, Percona XtraDB)',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/breakgard/galera-node-health',
    author='breakgard',
    author_email='breakgard.git@gmail.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Database',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6'
    ],
    keywords='galera mysql mariadb percona xtradb monitoring healthcheck health check',
    packages=['galera_node_health'],
    package_data={
        'galera_node_health': ['example_files/*']
    },
    install_requires=['flask', 'pymysql', 'gevent'],
    extras_requires={
        'dev': ['pytest', 'requests', 'py', 'psutil']
    },
    entry_points={
        'console_scripts': [
            'galera-node-health=galera_node_health.scripts:main',
            'galera-node-health_dev=galera_node_health.scripts:dev'
        ]
    },
    project_urls={
        'Bugs, issues and enhancements': 'https://github.com/breakgard/galera-node-health/issues',
        'Source': 'https://github.com/breakgard/galera-node-health/',
        'Docker': 'https://hub.docker.com/r/breakgard/galera-node-health/'
    }
)
