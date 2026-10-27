"""Immutable in-memory RGBA image, without file or optional imaging dependencies."""
from dataclasses import dataclass
from functools import cached_property
import struct
import zlib


@dataclass(frozen=True)
class RGBAImage:
    width: int
    height: int
    data: bytes

    def __post_init__(self):
        if (type(self.width) is not int or type(self.height) is not int or
                min(self.width, self.height) < 1 or max(self.width, self.height) > 16384 or
                self.width * self.height > 1048576):
            raise ValueError('RGBA image requires positive dimensions and at most 1048576 pixels')
        data = bytes(self.data)
        if len(data) != self.width * self.height * 4:
            raise ValueError('RGBA buffer length does not match dimensions')
        object.__setattr__(self, 'data', data)

    def crop(self, x, y, width, height):
        x,y,width,height = map(int,(x,y,width,height))
        # Validate dimensions before allocating; outside-source pixels stay transparent.
        if min(width,height)<1 or max(width,height)>16384 or width*height>1048576:
            raise ValueError('Invalid RGBA crop dimensions')
        output=bytearray(width*height*4)
        left,right=max(0,x),min(self.width,x+width)
        if right>left:
            for row in range(max(0,y),min(self.height,y+height)):
                source=(row*self.width+left)*4
                target=((row-y)*width+left-x)*4
                output[target:target+(right-left)*4]=self.data[source:source+(right-left)*4]
        return RGBAImage(width,height,bytes(output))

    @cached_property
    def png(self):
        def chunk(name, data):
            return struct.pack('!I', len(data)) + name + data + struct.pack('!I', zlib.crc32(name+data))
        stride = self.width * 4
        pixels = b''.join(b'\0'+self.data[i:i+stride] for i in range(0,len(self.data),stride))
        return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',self.width,self.height,8,6,0,0,0))+
                chunk(b'IDAT', zlib.compress(pixels))+chunk(b'IEND',b''))
