from distutils.core import setup

setup(
    name='libusb1',
    description='Python wrapper around libusb-1.0',
    keywords='usb libusb',
    version='0.2.0',
    author='Vincent Pelletier',
    author_email='plr.vincent@gmail.com',
    url='http://github.com/vpelletier/python-libusb1',
    license='GPL',
    platforms=['any'],
    py_modules=['libusb1','usb1'],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
    ],
)
