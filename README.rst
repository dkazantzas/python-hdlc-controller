======================
Python HDLC controller
======================

|Build Status| |Code Coverage| |Dependency Status| |Known Vulnerabilities|

HDLC controller written in Python and based on the
`python4yahdlc <https://github.com/SkypLabs/python4yahdlc>`__ Python
module to encode and decode HDLC frames.

Installation
============

With pip (recommanded)
----------------------

::

    pip3 install hdlcontroller

From sources
------------

::

    git clone https://github.com/SkypLabs/python-hdlc-controller.git
    cd python-hdlc-controller
    python3 setup.py install

Usage
=====

To create a new HDLC controller instance, you need to call the
``HDLController`` class with two parameters:

::

    hdlc_c = HDLController(read_func, write_func)

The first parameter is a function used to read from the serial bus while
the second parameter is a function to write on it. For example, using
the ``pyserial`` module:

::

    ser = serial.Serial('/dev/ttyACM0')

    def read_serial():
        return ser.read(ser.in_waiting)

    hdlc_c = HDLController(read_serial, ser.write)

To start the reception thread:

::

    hdlc_c.start()

To send a new data frame:

::

    hdlc_c.send('Hello world!')

And to get the next data frame received available in the ``HDLController``
internal queue:

::

    data = hdlc_c.get_data()

The ``get_data()`` method will block until a new data frame is available.

Finally, to stop all the ``HDLController`` threads:

::

    hdlc_c.stop()

License
=======

`MIT <http://opensource.org/licenses/MIT>`__

.. |Build Status| image:: https://travis-ci.org/SkypLabs/python-hdlc-controller.svg
   :target: https://travis-ci.org/SkypLabs/python-hdlc-controller
.. |Code Coverage| image:: https://api.codacy.com/project/badge/Grade/07336c5b36504927ab5c44550da13adf
   :target: https://www.codacy.com/app/skyper/python-hdlc-controller?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=SkypLabs/python-hdlc-controller&amp;utm_campaign=Badge_Grade
.. |Dependency Status| image:: https://gemnasium.com/badges/github.com/SkypLabs/python-hdlc-controller.svg
   :target: https://gemnasium.com/github.com/SkypLabs/python-hdlc-controller
.. |Known Vulnerabilities| image:: https://snyk.io/test/github/SkypLabs/python-hdlc-controller/badge.svg
   :target: https://snyk.io/test/github/SkypLabs/python-hdlc-controller
