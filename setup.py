from setuptools import setup, find_packages
import os

version = '0.1.0'


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='ZFindS',
    version=version,
    author='Tyler Bailey',
    author_email='baileytj3@gmail.com',
    description='Python tool to find deleted ZFS files.',
    long_description=read('README.md'),
    url='https://github.com/baileytj3/ZFindS',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 2.7',
        'Topic :: Utilities',
    ],
    install_requires=[
        'click>=6.7',
    ],
    entry_points='''
        [console_scripts]
        zfinds=zfinds.cli:cli
    ''',
    )
