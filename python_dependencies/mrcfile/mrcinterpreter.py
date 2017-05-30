# Copyright (c) 2016, Science and Technology Facilities Council
# This software is distributed under a BSD licence. See LICENSE.txt.
"""
mrcinterpreter
--------------

Module which exports the :class:`MrcInterpreter` class.

Classes:
    :class:`MrcInterpreter`: An object which can interpret an I/O stream as MRC
        data.

"""

# Import Python 3 features for future-proofing
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import warnings

import numpy as np

from . import utils
from .dtypes import HEADER_DTYPE
from .mrcobject import MrcObject
from .constants import MAP_ID


class MrcInterpreter(MrcObject):
    
    """An object which interprets an I/O stream as MRC / CCP4 map data.
    
    The header and data are handled as numpy arrays - see
    :class:`~mrcfile.mrcobject.MrcObject` for details.
    
    This class can be used directly, but it is mostly intended as a superclass
    to provide common stream-handling functionality. This can be used by
    subclasses which will handle opening and closing the stream.
    
    This class implements the __enter__() and __exit__() special methods which
    allow it to be used by the Python context manager in a 'with' block. This
    ensures that close() is called after the object is finished with.
    
    Methods:
    
    * :meth:`flush`
    * :meth:`close`
    
    Methods relevant to subclasses:
    
    * :meth:`_read`
    * :meth:`_read_data`
    
    """
    
    def __init__(self, iostream=None, permissive=False, **kwargs):
        """Initialise a new MrcInterpreter object.
        
        This initialiser reads the stream if it is given. In general, subclasses
        should call super().__init__() without giving an iostream argument, then
        set the _iostream attribute themselves and call _read() when ready.
        
        To use the MrcInterpreter class directly, pass a stream when creating
        the object (or for a write-only stream, create an MrcInterpreter with no
        stream, call _create_default_attributes() and set the _iostream
        attribute directly).
        
        Args:
            iostream: The I/O stream to use to read and write MRC data. The
                default is None.
        """
        super(MrcInterpreter, self).__init__(**kwargs)
        
        self._iostream = iostream
        self._permissive = permissive
        
        # If iostream is given, initialise by reading it
        if self._iostream is not None:
            self._read()
    
    def __enter__(self):
        """Called by the context manager at the start of a 'with' block.
        
        Returns:
            This object (self).
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Called by the context manager at the end of a 'with' block.
        
        This ensures that the close() method is called.
        """
        self.close()
    
    def __del__(self):
        """Attempt to flush the stream when this object is garbage collected.
        
        It's better not to rely on this - instead, use a 'with' block or
        explicitly call the close() method.
        """
        try:
            self.close()
        except Exception:
            pass
    
    def _read(self):
        """Read the header, extended header and data from the I/O stream.
        
        Before calling this method, the stream should be open and positioned at
        the start of the header. This method will advance the stream to the end
        of the data block.
        
        Raises:
            ValueError: If the file is not a valid MRC file.
        """
        self._read_header()
        self._read_extended_header()
        self._read_data()

    def _read_header(self):
        """Read the MRC header from the I/O stream.
        
        The header will be read from the current stream position, and the stream
        will be advanced by 1024 bytes.
        
        Raises:
            ValueError: If the file is not a valid MRC file.
        """
        # Read 1024 bytes from the stream
        header_str = self._iostream.read(HEADER_DTYPE.itemsize)
        
        if len(header_str) < HEADER_DTYPE.itemsize:
            raise ValueError("Couldn't read enough bytes for MRC header")
        
        # Use a recarray to allow access to fields as attributes
        # (e.g. header.mode instead of header['mode'])
        header = np.rec.fromstring(header_str, dtype=HEADER_DTYPE, shape=())
        
        # Make header writeable, because fromstring() creates a read-only array
        header.flags.writeable = True
        
        # Check this is an MRC file, and read machine stamp to get byte order
        if header.map != MAP_ID:
            msg = "Map ID string not found - not an MRC file, or file is corrupt"
            if self._permissive:
                warnings.warn(msg, RuntimeWarning)
            else:
                raise ValueError(msg)
        
        try:
            byte_order = utils.byte_order_from_machine_stamp(header.machst)
        except ValueError as err:
            if self._permissive:
                byte_order = '<' # try little-endian as a sensible default
                warnings.warn(str(err), RuntimeWarning)
            else:
                raise
        
        # Create a new dtype with the correct byte order and update the header
        header.dtype = header.dtype.newbyteorder(byte_order)
        
        header.flags.writeable = not self._read_only
        self._header = header
    
    def _read_extended_header(self):
        """Read the extended header from the stream.
        
        If there is no extended header, a zero-length array is assigned to the
        extended_header attribute.
        """
        ext_header_str = self._iostream.read(int(self.header.nsymbt))
        self._extended_header = np.fromstring(ext_header_str, dtype='V1')
        self._extended_header.flags.writeable = not self._read_only
    
    def _read_data(self):
        """Read the data array from the stream.
        
        This method uses information from the header to set the data array's
        shape and dtype.
        """
        try:
            dtype = utils.data_dtype_from_header(self.header)
        except ValueError as err:
            if self._permissive:
                warnings.warn("{0} - data block cannot be read".format(err),
                              RuntimeWarning)
                self._data = None
                return
            else:
                raise
        
        shape = utils.data_shape_from_header(self.header)
        
        nbytes = dtype.itemsize
        for axis_length in shape:
            nbytes *= axis_length
        
        data_bytes = self._iostream.read(nbytes)
        
        if len(data_bytes) < nbytes:
            msg = ("Expected {0} bytes in data block but could only read {1}"
                   .format(nbytes, len(data_bytes)))
            if self._permissive:
                warnings.warn(msg, RuntimeWarning)
                self._data = None
                return
            else:
                raise ValueError(msg)
        
        self._data = np.frombuffer(data_bytes, dtype=dtype).reshape(shape)
        self._data.flags.writeable = not self._read_only
    
    def close(self):
        """Flush to the stream and clear the header and data attributes."""
        if self._header is not None and not self._iostream.closed:
            self.flush()
        self._header = None
        self._extended_header = None
        self._close_data()
    
    def flush(self):
        """Flush the header and data arrays to the I/O stream.
        
        This implementation seeks to the start of the stream, writes the header,
        extended header and data arrays, and then truncates the stream.
        
        Subclasses should override this implementation for streams which do not
        support seek() or truncate().
        """
        if not self._read_only:
            self._iostream.seek(0)
            self._iostream.write(self.header)
            self._iostream.write(self.extended_header)
            self._iostream.write(np.ascontiguousarray(self.data))
            self._iostream.truncate()
            self._iostream.flush()
