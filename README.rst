Pure-python wrapper for libusb-1.0

Supports all transfer types, both in synchronous and asynchronous mode.

Home: http://github.com/vpelletier/python-libusb1

PyPI: http://pypi.python.org/pypi/libusb1

Requirements
============

- Python_ 2.4+ required, 2.6+ recommended

  Python 3.x somewhat tested

  pypy_ somewhat tested, 1.9 has a `bug <https://bugs.pypy.org/issue1242>`_
  affecting python-libusb, which is fixed in their HG

- ctypes_ (included in Python 2.5+)

- libusb-1.0_

  libusbx should work, too

Compatibility
=============

python-libusb1 is expected to work on any OS supported by libusb. It can be
expected to work on:

- GNU/Linux

- Windows

  *not* libusb-win32 (this is libusb0.1, the old API)

- Cygwin

- OSX (macports, fink, homebrew)

  (beware of possible lack of select.poll support in python)

- FreeBSD

  libusb reimplementation: http://svnweb.freebsd.org/base/head/lib/libusb/
  (including Debian GNU/kFreeBSD)

- OpenBSD

Installation
============

::

  python setup.py install

(you might need root access to do this)

Documentation
=============

python-libusb1 follows libusb1.0 documentation as closely as possible, without
taking decisions for you. Thanks to this, python-libusb1 does not need to
duplicate the nice existing `libusb1.0 documentation`_.

Some description is needed though on how to jump from libusb1.0 documentation
to python-libusb1, and vice-versa.

``libusb1`` module is a ctypes translation of ``libusb1.h`` file, including all
macros, constants and enums. You should not need to call any function from
this module, but will probably need to import it for the constants.

``usb1`` module wraps libusb1 functions so caller does not need to worry about
ctype. It regroup them as class methods, the first parameter (when it's a
``libusb_...`` pointer) defining the class the fonction belongs to. Examples:

- ``int libusb_init (libusb_context **context)`` becomes USBContext class
  constructor

- ``ssize_t libusb_get_device_list (libusb_context *ctx,
  libusb_device ***list)`` becomes an USBContext method, returning a
  list of USBDevice instances

- ``uint8_t libusb_get_bus_number (libusb_device *dev)`` becomes an USBDevice
  method

Functions returning an error status instead raise ``libusb1.USBError``
instances, with the status as ``value``.

It wraps further some functions which are otherwise not so convenient to call
from Python: the event handling API needed by async API. Those classes are
docstring-documented, so using ``pydoc`` is recommended.

Contents of source distribution
===============================

- libusb1.py

  Bare ctype wrapper, inspired from library C header file.

- usb1.py

  Python-ish (classes, exceptions, ...) wrapper around libusb1.py .
  See docstrings (pydoc recommended) for usage.

- setup.py

  To package as python egg.

- stdeb.cfg

  To package as Debian package. See https://github.com/astraw/stdeb .

- testUSB1.py

  Very limited regression test, only testing functions which do not require a
  USB device.

History
=======

0.0.1
-----

Initial release

0.1.1
-----

Massive rework of usb1.py, making it more python-ish and fixing some
memory leaks.

0.1.2
-----

Deprecate "transfer" constructor parameter to allow instance reuse.

0.1.3
-----

Some work on isochronous "in" transfers. They don't raise exceptions anymore,
but data validity and python-induced latency impact weren't properly checked.

0.2.0
-----

Fix asynchronous configuration transfers.

Stand-alone polling thread for multi-threaded apps.

More libusb methods exposed on objects, including ones not yet part of
released libusb versions (up to their commit 4630fc2).

2to3 friendly.

Drop deprecated USBDevice.reprConfigurations method.

0.2.1
-----

Add FreeBSD support.

0.2.2
-----

Add Cygwin support.

OpenBSD support checked (no change).

0.2.3
-----

Add fink and homebrew support on OSX.

Drop PATH_MAX definition.

Try harder when looking for libusb.

1.0.0
-----

Fix FreeBSD ABI compatibility.

Easier to list connected devices.

Easier to terminate all async transfers for clean exit.

Fix few segfault causes.

pypy support.

1.1.0
-----

Descriptor walk API documented.

Version and capability APIs exposed.

Some portability fixes (OSes, python versions).

Isochronous transfer refuses to round transfer size.

Better exception handling in enumeration.

Add examples.

Better documentation.

1.2.0
-----

Wrap hotplug API.

Wrap port number API.

Wrap kernel auto-detach API.

Drop wrapper for libusb_strerror, with compatibility place-holder.

Add a few new upstream enum values.

1.3.0
-----

**Backward-incompatible change**: Enum class now affects caller's local scope,
not its global scope. This should not be of much importance, as:

- This class is probably very little used outside libusb1.py

- This class is probably mostly used at module level, where locals == globals.

  It is possible to get former behaviour by providing the new ``scope_dict``
  parameter to ``Enum`` constructor::

    SOME_ENUM = libusb1.Enum({...}, scope_dict=globals())

Improve start-up time on CPython by not importing standard ``inspect`` module.

Fix some more USBTransfer memory leaks.

Add Transfer.iterISO for more efficient isochronous reception.

1.3.1
-----

Fixed USBContext.waitForEvent.

Fix typo in USBInterfaceSetting.getClassTuple method name. Backward
compatibility preserved.

Remove globals accesses from USBDeviceHandle destructor.

Assorted documentation improvements.

See also
========

Other projects, different author

- pyusb_:  another python wrapper for (among others) libusb1.
  Does not support asynchronous API, nor isochorous transfers.

.. _Python: http://www.python.org/

.. _pypy: http://pypy.org/

.. _ctypes: http://python.net/crew/theller/ctypes/

.. _libusb-1.0: http://www.libusb.org/wiki/libusb-1.0

.. _pyusb: http://sourceforge.net/projects/pyusb/

.. _libusb1.0 documentation: http://libusb.sourceforge.net/api-1.0/
