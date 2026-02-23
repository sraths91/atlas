#!/usr/bin/env python3
"""
Fleet Agent Setup
"""
from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='mac-fleet-agent',
    version='1.0.0',
    description='Fleet monitoring agent for macOS systems',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Your Organization',
    author_email='support@example.com',
    url='https://github.com/yourorg/mac-fleet-agent',
    packages=find_packages(),
    install_requires=[
        'psutil>=5.9.0',
        'requests>=2.28.0',
        'urllib3>=1.26.0',
        'cryptography>=41.0.0',
    ],
    entry_points={
        'console_scripts': [
            'fleet-agent=fleet_agent.agent:main',
        ],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: MacOS :: MacOS X',
    ],
    python_requires='>=3.8',
)
