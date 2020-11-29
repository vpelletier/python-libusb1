# Copyright (C) 2010-2018  Vincent Pelletier <plr.vincent@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from setuptools import setup
from distutils.command.install import install
from codecs import open
import os
import versioneer

class install(install):
    def run(self):
        super().run()
        if os.getenv('LIBUSB_BINARY'):
            self.copy_file(os.getenv('LIBUSB_BINARY'), os.path.join(self.install_lib, 'usb1'))

long_description = open(
    os.path.join(os.path.dirname(__file__), 'README.rst'),
    encoding='utf8',
).read()

setup(
    name='libusb1',
    description=next(x for x in long_description.splitlines() if x.strip()),
    long_description='.. contents::\n\n' + long_description,
    keywords='usb libusb',
    version=versioneer.get_version(),
    cmdclass={
        'install': install,
        **versioneer.get_cmdclass(),
    },
    author='Vincent Pelletier',
    author_email='plr.vincent@gmail.com',
    url='http://github.com/vpelletier/python-libusb1',
    license='LGPLv2.1+',
    platforms=['any'],
    py_modules=['libusb1'],
    packages=['usb1'],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Hardware :: Hardware Drivers',
    ],
    use_2to3=True,
    test_suite='usb1.testUSB1',
)
