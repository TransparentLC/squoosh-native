import os
import ctypes
import wvruntime

__all__ = [
    'write',
]

match (os.name):
    case 'nt':
        dllext = '.dll'
    case 'posix':
        dllext = '.so'
    case _:
        raise NotImplementedError(f'libsvpng is not supported on os.name = {os.name}')

libsvpng = ctypes.cdll.LoadLibrary(os.path.join(wvruntime.contentPath, f'libsvpng{dllext}'))
libsvpng.svpng_file.argtypes = (ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_char_p, ctypes.c_int)
libsvpng.svpng_file.restype = None

def write(file: str, w: int, h: int, img: bytes, alpha: bool):
    '''
    Save a RGB/RGBA image in PNG format.

    Parameters
    ----------
    file : str
        Output filename.
    w : int
        Width of the image.
    h : int
        Height of the image.
    img : bytes
        Image pixel data in 24-bit RGB or 32-bit RGBA format.
    alpha : bool
        Whether the image contains alpha channel.
    '''
    libsvpng.svpng_file(ctypes.create_string_buffer(file.encode()), w, h, ctypes.create_string_buffer(img), alpha)

