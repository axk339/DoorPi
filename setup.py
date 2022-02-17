#!/usr/bin/env python3

"""DoorPi Setup"""

import setuptools

setuptools.setup(
    package_data={
        # include
        '': ['*.yml', '*.cfg', '*.txt', '*.toml', '*.rst', '*.wav', '*.ico', '*.md', '*.json', '*.html', '*.js',
             '*.css', '*.png', '*.tab', '*.sh', '*.gif', '*.jpg', '*.coffee', '*.less', '*.psd', '*.swf', '*.svg',
             '*.otf', '*.eot', '*.woff', '*.ttf', '*.scss', '*.db', '*.map', '*.lang', '*.xml', '*.pack', '*.idx',
             '*.sample'],
    },
    data_files=[],
)
