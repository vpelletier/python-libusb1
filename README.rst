.. contents::

Supports all transfer types, both in synchronous and asynchronous mode.

Home: http://github.com/vpelletier/python-libusb1

PyPI: http://pypi.python.org/pypi/libusb1

.. role:: c_code(code)
  :language: c

.. role:: python_code(code)
  :language: python

Dependencies
============

- CPython_ 3.6+, pypy_ 2.0+. Older versions may work, but are not
  recommended as there is no automated regression testing set up for them.
- libusb-1.0_

Supported OSes
==============

python-libusb1 can be expected to work on:

- GNU/Linux
- Windows [#]_ native dll or via Cygwin_
- OSX [#]_ via MacPorts_, Fink_ or Homebrew_
- FreeBSD (including Debian GNU/kFreeBSD)
- OpenBSD

.. [#] Beware of libusb-win32, which implements 0.1 API, not 1.0 .

.. [#] Beware of possible lack of select.poll if you want to use asynchronous
       API.

Installation
============

Releases from PyPI, with name *libusb1*. Installing from command line::

    $ pip install libusb1

Latest version from source tree::

    $ git clone https://github.com/vpelletier/python-libusb1.git
    $ cd python-libusb1
    $ pip install .

Windows installation notes
--------------------------

On Windows, installing wheels from pypi also installs the libusb dll within the
usb1 python module. It does not install any driver, so you still need to decide
which of libusbk or WinUSB to use for each device and install it appropriately
(possibly using Zadig_, or by providing a driver for your users to install).

Installing from source tree does not install the dll, so you need to install the
library where ctypes can find it - and of course the driver as well.

Checking release file signature
-------------------------------

pipy releases are signed. To verify the signature:

- download the release file, note its URL
- download its detached signature by adding `.asc` at the end of the release
  file URL
- add the release key(s) to a gnupg keyring (`KEYS` file in the home
  repository), and use gnupg to validate the signature both corresponds to the
  distribution file and is trusted by your keyring
- install the already-fetched release file

Usage
=====

Finding a device and gaining exclusive access:

.. code:: python

    import usb1
    with usb1.USBContext() as context:
        handle = context.openByVendorIDAndProductID(
            VENDOR_ID,
            PRODUCT_ID,
            skip_on_error=True,
        )
        if handle is None:
            # Device not present, or user is not allowed to access device.
        with handle.claimInterface(INTERFACE):
            # Do stuff with endpoints on claimed interface.

Synchronous I/O:

.. code:: python

    while True:
        data = handle.bulkRead(ENDPOINT, BUFFER_SIZE)
        # Process data...

Asynchronous I/O, with more error handling:

.. code:: python

    def processReceivedData(transfer):
        if transfer.getStatus() != usb1.TRANSFER_COMPLETED:
            # Transfer did not complete successfully, there is no data to read.
            # This example does not resubmit transfers on errors. You may want
            # to resubmit in some cases (timeout, ...).
            return
        data = transfer.getBuffer()[:transfer.getActualLength()]
        # Process data...
        # Resubmit transfer once data is processed.
        transfer.submit()

    # Build a list of transfer objects and submit them to prime the pump.
    transfer_list = []
    for _ in range(TRANSFER_COUNT):
        transfer = handle.getTransfer()
        transfer.setBulk(
            usb1.ENDPOINT_IN | ENDPOINT,
            BUFFER_SIZE,
            callback=processReceivedData,
        )
        transfer.submit()
        transfer_list.append(transfer)
    # Loop as long as there is at least one submitted transfer.
    while any(x.isSubmitted() for x in transfer_list):
        try:
            context.handleEvents()
        except usb1.USBErrorInterrupted:
            pass

For more, see the ``example`` directory.

Documentation
=============

python-libusb1 main documentation is accessible with python's standard
``pydoc`` command.

python-libusb1 follows libusb-1.0 documentation as closely as possible, without
taking decisions for you. Thanks to this, python-libusb1 does not need to
duplicate the nice existing `libusb1.0 documentation`_.

Some description is needed though on how to jump from libusb-1.0 documentation
to python-libusb1, and vice-versa:

``usb1`` module groups libusb-1.0 functions as class methods. The first
parameter (when it's a ``libusb_...`` pointer) defined the class the function
belongs to. For example:

- :c_code:`int libusb_init (libusb_context **context)` becomes USBContext class
  constructor, :python_code:`USBContext.__init__(self)`

- :c_code:`ssize_t libusb_get_device_list (libusb_context *ctx,
  libusb_device ***list)` becomes an USBContext method, returning a
  list of USBDevice instances, :python_code:`USBDevice.getDeviceList(self)`

- :c_code:`uint8_t libusb_get_bus_number (libusb_device *dev)` becomes an
  USBDevice method, :python_code:`USBDevice.getBusNumber(self)`

Error statuses are converted into :python_code:`usb1.USBError` exceptions, with
status as ``value`` instance property.

``usb1`` module also defines a few more functions and classes, which are
otherwise not so convenient to call from Python: the event handling API needed
by async API.

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

1.3.2
-----

Made USBDevice instances hashable.

Relaxed licensing by moving from GPL v2+ to LGPL v2.1+, for consistency with
libusb1.

1.4.0
-----

Reduce (remove ?) the need to import libusb1 module by exposing USBError and
constants in usb1 module.

Fix libusb1.LIBUSB_ENDPOINT_ENDPOINT_MASK and
libusb1.LIBUSB_ENDPOINT_DIR_MASK naming.

Fix pydoc appearance of several USBContext methods.

Define exception classes for each error values.

1.4.1
-----

Fix wheel generation (``python3 setup.py bdist_wheel``).

1.5.0
-----

controlWrite, bulkWrite and interruptWrite now reject (with TypeError) numeric
values for ``data`` parameter.

Fix libusb1.REQUEST_TYPE_* names (were TYPE_*). Preserve backward
compatibility.

Add USBContext.getDeviceIterator method.

Rename USBContext.exit as USBContext.close for consistency with other USB*
classes. Preserve backward compatibility.

Make USBDeviceHandle.claimInterface a context manager, for easier interface
releasing.

1.5.1
-----

Introduce USBPollerThread.stop .

Fix USBDeviceHandle.getSupportedLanguageList bug when running under python 3.
While fixing this bug it was realised that this method returned ctypes objects.
This was not intended, and it now returns regular integers.

1.5.2
-----

Make USBTransfer.cancel raise specific error instances.

1.5.3
-----

Fix USBTransfer.cancel exception raising introduced in 1.5.2: it was
accidentally becomming a bound method, preventing the raise to actually
happen (in at least CPython 2.x) or raising type conversion errors (in at least
CPython 3.5.2).

1.6
---

Improve asynchronous transfer performance: (very) suboptimal code was used to
initialise asynchronous transfer buffer. As a consequence, usb1 now exposes
``bytearrays`` where it used to expose ``bytes`` or ``str`` objects.

Deprecate libusb1 module import, which should not be needed since all (?)
needed constants were re-bound to usb1 module.

Move testUSB1 module inside usb1, to eventually only expose usb1 as top-level
module.

1.6.1
-----

Fix getSupportedLanguageList.

Fix and extend get{,ASCII}StringDescriptor .

Fix iterISO and getISOBufferList.

1.6.2
-----

Fix getASCIIStringDescriptor: unlike getStringDescriptor, this returns only the
payload of the string descriptor, without its header.

1.6.3
-----

Deprecate USBPollerThread . It is mileading users for which the simple version
(a thread calling ``USBContext.handleEvents``) would be enough. And for more
advanced uses (ie, actually needing to poll non-libusb file descriptors), this
class only works reliably with epoll: kqueue (which should tehcnically work)
has a different API on python level, and poll (which has the same API as epoll
on python level) lacks the critical ability to change the set of monitored file
descriptors while a poll is already running, causing long pauses - if not
deadlocks.

1.6.4
-----

Fix asynchronous control transfers.

1.6.5
-----

Document hotplug handler limitations.

Run 2to3 when running setup.py with python3, and reduce differences with
python3.

Properly cast libusb_set_pollfd_notifiers arguments.
Fix null pointer value: POINTER(None) is the type of a pointer which may be a
null pointer, which falls back to c_void_p. But c_void_p() is an actual null
pointer.

1.6.6
-----

Expose bare string descriptors (aka string indexes) on USBDevice.

1.6.7
-----

get{,ASCII}StringDescriptor now return None for descriptor 0 instead of raising
UnicodeDecodeError. Use getSupportedLanguageList to access it.

Moved getManufacturer, getProduct and getSerialNumber to USBDeviceHandle. Kept
shortcuts for these on USBDevice.

1.7
---

get{,ASCII}StringDescriptor now return None for descriptor 0, use
getSupportedLanguageList to get its content.

getManufacturer, getProduct and getSerialNumber are now on USBDeviceHandle,
with backward-compatibility aliases on their original location.

Synchronous bulk and interrupt API exposes number of bytes sent and received
bytes even when a timeout occurs.

1.7.1
-----

usb1.__version__ is now present, managed by versioneer.

Fix an occasional segfault when closing a transfer from inside its callback
function.

1.8
---

Fix getExtra and libusb1.libusb_control_transfer_get_data .

Fix getMaxPower unit on SuperSpeed devices.

1.8.1
-----

Release process rework:

- embed libusb1 dll for easier deployment on Windows
- cryptographically signed releases

Use libusb_free_pollfds whenever available (libusb1>=1.0.20).

Fix hotplug callback destruction at context teardown.

Drop remnants of python 2.6 support code.

1.9
---

Drop USBPollerThread and deprecate libusb-lock-related USBContext API.

1.9.1
-----

Fix installation from pypi source tarball, broken in 1.8.1 .

1.9.2
-----

Windows wheels: Update bundled libusb to 1.0.24 .

Fix soure-only build when wheel is not available.

1.9.3
-----

Add support for pyinstaller.

Improve the way the windows dlls are embedded in wheels.

Fix support for python 3.10 .

Add support for homebrew on Apple M1.

1.10.1 (yanked)
---------------

NOTE: Release yanked_ from pypi and re-released as 2.0.0.

2.0.0
-----

Drop python <3.4 support.

Do not load the C library on import. Allows applications to customise the
lookup logic (see `usb1.loadLibrary`).

Add LIBUSB_SPEED_SUPER_PLUS.

Better control device iterator end of life.

Fix objects escaping control from their parent.

2.0.1
-----

Fix a TypeError exception in USBContext.handleEvents .

Fix an AttributeError exception in USBContext.hotplugRegisterCallback .

Fix segfault in pypy3 when finalizing USBDevice objects .

Source only: convert examples to python3.

Release process: also run some examples scripts.

3.0.0
-----

Update versioneer to be compatible with 3.11 .

Drop python <3.6 support (consequence of versioneer update), hence the major
version change.

.. _CPython: http://www.python.org/

.. _pypy: http://pypy.org/

.. _Cygwin: https://www.cygwin.com/

.. _MacPorts: https://www.macports.org/

.. _Fink: http://www.finkproject.org/

.. _Homebrew: http://brew.sh/

.. _libusb-1.0: https://github.com/libusb/libusb/wiki/

.. _libusb1.0 documentation: http://libusb.sourceforge.net/api-1.0/

.. _Zadig: https://zadig.akeo.ie/

.. _yanked: https://www.python.org/dev/peps/pep-0592/
