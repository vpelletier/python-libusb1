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
from __future__ import print_function
from setuptools import setup
from distutils.core import Command
import distutils.command.install
from codecs import open
import errno
import hashlib
import os
import subprocess
import sys
import versioneer
try:
    from urllib.request import urlopen
    from urllib.parse import urlsplit
    from html.parser import HTMLParser
except ImportError:
    # BBB: python 2.7
    from urllib2 import urlopen
    from urlparse import urlsplit
    from HTMLParser import HTMLParser

if os.getenv('I_KNOW_HOW_TO_RELEASE_PYTHON_LIBUSB1') != '1' and any(
    x in sys.argv for x in ('sdist', 'upload')
):
    print('Use setup.sh to build')
    sys.exit(1)

CURRENT_WINDOWS_7Z_SHA256 = (
    'd3087e7d09ec4e463f5f4b394dcfec0b90e835545318af1a75575de59d2dfaac'
)

cmdclass = versioneer.get_cmdclass()
class install(distutils.command.install.install):
    def run(self):
        # XXX: distutils.command.install.install is an old-style class on
        # python2.7 :(
        distutils.command.install.install.run(self)
        if os.getenv('LIBUSB_BINARY'):
            self.copy_file(
                os.getenv('LIBUSB_BINARY'),
                os.path.join(self.install_lib, 'usb1'),
            )
cmdclass['install'] = install

class upload(Command):
    def run(self):
        print('This project uses signed releases. See KEYS for instructions.')
        print('Hint:')
        print('  twine upload dist/<release file> dist/<release file>.asc')
        sys.exit(1)
cmdclass['upload'] = upload

class update_libusb(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    class WindowsBinariesArchiveLinkFinder(HTMLParser):
        found = None
        __a_href = None
        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                assert self.__a_href is None, repr(self.__a_href)
                self.__a_href = dict(attrs).get('href')

        def handle_endtag(self, tag):
            if tag == 'a':
                self.__a_href = None

        def handle_data(self, data):
            if self.__a_href is not None and data == 'Latest Windows Binaries':
                assert self.found is None, repr(self.found)
                self.found = self.__a_href

    def run(self):
        finder = self.WindowsBinariesArchiveLinkFinder()
        finder.feed(urlopen('https://libusb.info/').read().decode('utf-8'))
        finder.close()
        url = finder.found
        if url is None:
            raise ValueError('Failed to locate current windows binary release')
        build_dir = os.path.join(os.path.dirname(__file__), 'build')
        download_cache_path = os.path.join(build_dir, 'download-cache')
        archive_path = os.path.join(
            download_cache_path,
            urlsplit(url).path.rsplit('/', 1)[-1],
        )
        if not os.path.exists(archive_path):
            os.makedirs(download_cache_path)
            with open(archive_path, 'wb') as archive_file:
                archive_file.write(urlopen(url).read())
        with open(archive_path, 'rb') as archive_file:
            archive_sha256 = hashlib.sha256(archive_file.read()).hexdigest()
        if archive_sha256 != CURRENT_WINDOWS_7Z_SHA256:
            raise ValueError(
                'Windows release sha56 mismatch: %r fetched with a sha256 of %r' % (
                    url,
                    archive_sha256,
                )
            )
        # py2 does not have subprocess.DEVNULL.
        with open(os.devnull, 'wb') as devnull:
            for arch_path, out_dir in (
                ('MS32/dll/libusb-1.0.dll', os.path.join(build_dir, 'win32')),
                ('MS64/dll/libusb-1.0.dll', os.path.join(build_dir, 'win_amd64')),
            ):
                subprocess.check_call(
                    [
                        '7z', 'e', '-aoa',
                        '-o' + out_dir,
                        archive_path,
                        arch_path,
                    ],
                    # 7z will not shut its pie hole.
                    stdout=devnull,
                    close_fds=True,
                )
cmdclass['update_libusb'] = update_libusb

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
    cmdclass=cmdclass,
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
    setup_requires=[
        'wheel',
    ],
    use_2to3=True,
    test_suite='usb1.testUSB1',
)
