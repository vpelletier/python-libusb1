# Copyright (C) 2010-2021  Vincent Pelletier <plr.vincent@gmail.com>
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
from setuptools import Command
from codecs import open
import hashlib
from html.parser import HTMLParser
import os
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import urlopen
import versioneer

if os.getenv('I_KNOW_HOW_TO_RELEASE_PYTHON_LIBUSB1') != '1' and any(
    x in sys.argv for x in ('sdist', 'upload')
):
    print('Use setup.sh to build')
    sys.exit(1)

CURRENT_WINDOWS_7Z_SHA256 = (
    '19835e290f46fab6bd8ce4be6ab7dc5209f1c04bad177065df485e51dc4118c8'
)

cmdclass = versioneer.get_cmdclass()
class upload(Command):
    """
    Declaw "setup.py upload".
    """
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

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
        if not url.endswith('.7z'):
            raise ValueError('unexpected extension: %r' % (url, ))
        build_dir = os.path.join(os.path.dirname(__file__), 'build')
        download_cache_path = os.path.join(build_dir, 'download-cache')
        if not os.path.exists(download_cache_path):
            os.makedirs(download_cache_path)
        url_basename = urlsplit(url).path.rsplit('/', 1)[-1]
        archive_path = os.path.join(download_cache_path, url_basename)
        if not os.path.exists(archive_path):
            for suffix in ('', '.asc'):
                with open(archive_path + suffix, 'wb') as archive_file:
                    archive_file.write(urlopen(url + suffix).read())
        # to build/update trustedkeys-libusb.kbx:
        # gpg --no-default-keyring --keyring trustedkeys-libusb.kbx --receive-keys ...
        subprocess.check_call(
            [
                'gpgv',
                '--keyring', 'trustedkeys-libusb.kbx',
                archive_path + '.asc', archive_path,
            ],
            # gnupg will not shut its pie hole.
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        # This check is for the maintainer to notice a new release, and
        # to retrospectively confirm that a release was done with files
        # from a certain archive (and not just any signed release).
        # It is *not* to check file authenticity (for this, we have gpg).
        with open(archive_path, 'rb') as archive_file:
            archive_sha256 = hashlib.sha256(archive_file.read()).hexdigest()
        if archive_sha256 != CURRENT_WINDOWS_7Z_SHA256:
            raise ValueError(
                'Windows release sha56 mismatch: %r fetched with a sha256 of %r' % (
                    url,
                    archive_sha256,
                )
            )
        for arch_path, out_dir in (
            ('VS2019/MS32/dll/libusb-1.0.dll', os.path.join(build_dir, 'win32')),
            ('VS2019/MS64/dll/libusb-1.0.dll', os.path.join(build_dir, 'win_amd64')),
        ):
            subprocess.check_call(
                [
                    '7z', 'e', '-aoa',
                    '-o' + out_dir,
                    archive_path,
                    arch_path,
                ],
                # 7z will not shut its pie hole.
                stdout=subprocess.DEVNULL,
                close_fds=True,
            )
cmdclass['update_libusb'] = update_libusb

setup(
    version=versioneer.get_version(),
    cmdclass=cmdclass,

    setup_requires=(
        ['wheel']
        if 'bdist_wheel' in sys.argv else
        []
    ),
)
