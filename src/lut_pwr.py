"""
Copyright 2022 Salvatore Barone <salvatore.barone@unina.it>

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
import math

def get_K(lut_conf):
	"""
	Returns the K for a givejn LUT
	:param lut_conf: lut configuration (as string), lsb is lut_conf[0]
	:return: the K of the lut
	"""
	assert math.log2(len(lut_conf)) == math.ceil(math.log2(len(lut_conf))), "Error: function specification length must be a power of two"
	return int(math.log2(len(lut_conf)))

def get_equiprob_inputs(K):
	"""
	Returns an uniformly distributed leaf frequencies
	:param K: the K for the lut, i.e., the number of selection inputs
	:return: uniformly distributed leaf frequencies, as inputs are equiprobable
	"""
	return [1 / 2 ** K] * 2 ** K

def get_equiprob_frequencies_by_level(K):
	"""
	Returns the left-hand frequency and the right-hand frequency of the tree at level k as inputs are equiprobable
	:param K: the K for the lut, i.e., the number of selection inputs
	:return: the left-hand frequency and the right-hand frequency of the tree at level k as inputs are equiprobable
	"""
	return  [{"l": .5, "r": .5} for k in reversed(range(K))]

def frequencies_by_level(leaf_freq):
	"""
	Compute the left-hand frequency and the right-hand frequency for any level of the tree
	:param leaf_freq: leaf frequencies
	:return:  the left-hand frequency and the right-hand frequency of the tree at level k as the sum of the frequencies
	of the leaves on the left-hand side and the right-hand of the 2k trees rooted at level k.
	"""
	assert math.log2(len(leaf_freq)) == math.ceil(math.log2(len(leaf_freq))), "Error: frequency specification length must be a power of two"
	K = int(math.log2(len(leaf_freq)))
	f = [{"l": 0, "r": 0} for k in reversed(range(K))]
	f_below_i = [0] * (2 ** K - 1) + leaf_freq
	for k in reversed(range(K)):
		for i in range(2 ** k - 1, 2 ** (k + 1) - 1):
			f[k]["l"] += f_below_i[2 * i + 1]
			f[k]["r"] += f_below_i[2 * i + 2]
			f_below_i[i] = f_below_i[2 * i + 1] + f_below_i[2 * i + 2]
	return f

def internal_node_activity(lut_conf, leaf_freq = None) :
	"""
	Compute the internal node activity given the frequency of leaves
	:param lut_conf: lut configuration (as string), lsb is lut_conf[0]
	:param leaf_freq: leaf frequencies
	:return:  the left-hand frequency and the right-hand frequency of the tree at level k as the sum of the frequencies
	of the leaves on the left-hand side and the right-hand of the 2k trees rooted at level k.
	"""
	assert math.log2(len(lut_conf)) == math.ceil(math.log2(len(lut_conf))), "Error: function specification length must be a power of two"
	K = int(math.log2(len(lut_conf)))
	if leaf_freq:
		assert math.log2(len(leaf_freq)) == math.ceil(math.log2(len(leaf_freq))), "Error: frequency specification length must be a power of two"
		assert len(lut_conf) == len(leaf_freq), "Error: function and frequency specification must be the same length"
	else:
		leaf_freq = [1 / 2 ** K] * 2 ** K
	f = frequencies_by_level(leaf_freq)
	cost = [0] * (2 ** K - 1)
	p_0 = [0] * (2 ** K - 1) + [ 0 if x == '1' else 1 for x in lut_conf ]
	for k in reversed(range(K)):
		for i in range(2 ** k - 1, 2 ** (k + 1) - 1):
			p_0[i] = f[k]["l"] * p_0[2 * i + 1] + f[k]["r"] * p_0[2 * i + 2]
			cost[i] = (p_0[i] - p_0[i] ** 2) #+ cost[2 * i + 1] + cost[2 * i + 2]
	return sum(cost)
