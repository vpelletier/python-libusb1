from distutils.core import setup
import os

long_description = open(
  os.path.join(os.path.dirname(__file__), 'README.rst')
).read()

try:
    next
except NameError:
    # "next" builtin missing < 2.6
    next = lambda x: x.next()

setup(
    name='libusb1',
    description=next(x for x in long_description.splitlines() if x.strip()),
    long_description='.. contents::\n\n' + long_description,
    keywords='usb libusb',
    version='1.2.0',
    author='Vincent Pelletier',
    author_email='plr.vincent@gmail.com',
    url='http://github.com/vpelletier/python-libusb1',
    license='GPL',
    platforms=['any'],
    py_modules=['libusb1', 'usb1'],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.4',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Hardware :: Hardware Drivers',
    ],
)
