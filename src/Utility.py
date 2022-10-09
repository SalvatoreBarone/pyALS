"""
Copyright 2021-2022 Salvatore Barone <salvatore.barone@unina.it>

This is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free
Software Foundation; either version 3 of the License, or any later version.

This is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details.

You should have received a copy of the GNU General Public License along with
RMEncoder; if not, write to the Free Software Foundation, Inc., 51 Franklin
Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

import numpy as np
import struct

def float_to_hex(f):
  return hex(struct.unpack('<I', struct.pack('<f', f))[0])


def double_to_hex(d):
  return hex(struct.unpack('<Q', struct.pack('<d', d))[0])


def float_to_bin(f):
  return format(struct.unpack('<I', struct.pack('<f', f))[0], "032b")


def double_to_bin(d):
  return format(struct.unpack('<Q', struct.pack('<d', d))[0], "064b")


def bin_to_double(b):
  return struct.unpack('d', struct.pack('Q', int(b, 2)))[0]


def bin_to_float(b):
  return struct.unpack('f', struct.pack('I', int(b, 2)))[0]


def apply_mask_to_double(f, nab):
  return bin_to_double(double_to_bin(f)[:-nab] + "0" * nab)


def apply_mask_to_float(f, nab):
  return bin_to_float(float_to_bin(f)[:-nab] + "0" * nab)


def apply_mask_to_int(i, nab):
  return i & (~((1<<nab)-1))


def list_partitioning(a_list, num_of_partitions):
    list_of_list = []
    np_split = np.array_split(a_list, num_of_partitions)
    for item in np_split:
      list_of_list.append(list(item))
    return list_of_list


def string_to_nested_list_int(s):
  if s == '[[], []]':
    return [[], []]
  l = [sl.strip('[]').split(',') for sl in s.split('], [')]
  return [[int(i) for i in l[0]], [int(i) for i in l[1]]]


def flatten(container):
	for i in container:
		if isinstance(i, (list, tuple)):
			for j in flatten(i):
				yield j
		else:
			yield i


def negate(spec):
    return spec.translate(spec.maketrans({"1": "0", "0": "1"}))