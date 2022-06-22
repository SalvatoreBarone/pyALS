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
from fixedpoint import FixedPoint
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import freqz


class FIRFilter:
	def __init__(self, coefficients, m, n, as_float):
		"""
		Defines a new FIR filter

		The filter utilizes Qm.n, i.e., signed fixed-point, with m-bits for the integer and n-bits for the fractional part.

		:param coefficients:  coefficients for the filter. They will be interpreted as fixed-point, given Qm.n
		:param m: Integer part (number of bits to be used for its representation)
		:param n: Fractional part (number of bits to be used for its representation)
		:param as_float: if true, coefficients are interpreted as floating-point, else they are interpreted as signed-integer coded
		"""
		self.m = m
		self.n = n
		self.coefficients = [ FixedPoint(c if as_float else FIRFilter.sint2fixedp(c, m, n), signed = True, m = m, n = n) for c in coefficients ]

	def apply(self, input_signal, as_float):
		"""
		Applies the filter to the input signal
		:param input_signal: coefficients for the filter, as floating-point. They will be interpreted as fixed-point, given Qm.n
		:param as_float: if true, coefficients are interpreted as floating-point, else they are interpreted as signed-integer coded
		:return: the convolution between FIR filter coefficients and the input signal
		"""
		len_i, len_c = len(input_signal), len(self.coefficients)
		len_r = len_i + len_c - 1
		input_signal = [FixedPoint(c if as_float else FIRFilter.sint2fixedp(c, self.m, self.n), signed = True, m = self.m, n = self.n) for c in input_signal]
		return [FixedPoint(sum([self.multiply(input_signal[n - i - len_c], self.coefficients[i]) for i in range(len_c)]), signed = True, m = self.m, n = self.n) for n in range(len_c, len_r + 1)]

	def convolve1d(self, input_signal, as_float):
		input_signal = [FixedPoint(c if as_float else FIRFilter.sint2fixedp(c, self.m, self.n), signed = True, m = self.m, n = self.n) for c in input_signal]
		len_i, len_c = len(input_signal), len(self.coefficients)
		len_r = len_i + len_c - 1
		result = [FixedPoint(0, signed = True, m = self.m, n = self.n) ] * len_r
		for n in range(len_r-1):
			kmin = n if (n >= len_c - 1) else 0
			kmax = min(n, len_i - 1)
			result[n] = FixedPoint(sum([self.multiply(input_signal[k], self.coefficients[n - k]) for k in range(kmin, kmax)]), signed = True, m = self.m, n = self.n)
		return result

	def multiply(self, a, b):
		return a * b

	@staticmethod
	def two_complements_int2bin(num, digits):
		return format(num if num >= 0 else (((1 << digits) - 1) & num), f"0{digits}b")

	@staticmethod
	def bin2float(num, m, n):
		return (1 if num[0] == '1' else -1) * ((float(int(num[1:m], 2)) if m > 1 else 0) + (float(int(num[-n:], 2)) / 2 ** n))

	@staticmethod
	def sint2fixedp(num, m, n):
		return FIRFilter.bin2float(FIRFilter.two_complements_int2bin(num, m + n), m, n)


	@staticmethod
	def bode_plot(taps, sample_rate, title = 'Frequency Response'):
		# w, h = freqz(taps, worN=freqs)
		w, h = freqz(taps)
		fig = plt.figure(figsize = [6, 6])
		plt.plot((w / np.pi) * sample_rate, 20 * np.log10(np.abs(h)), linewidth = 2)
		# plt.axvline(cutoff_hz + width*nyq_rate, linestyle='--', linewidth=1, color='g')
		# plt.axvline(cutoff_hz - width*nyq_rate, linestyle='--', linewidth=1, color='g')
		# plt.axhline(-ripple_db, linestyle='--', linewidth=1, color='c')
		# delta = 10**(-ripple_db/20)
		# plt.axhline(20*np.log10(1 + delta), linestyle='--', linewidth=1, color='r')
		# plt.axhline(20*np.log10(1 - delta), linestyle='--', linewidth=1, color='r')
		plt.xlabel('Frequency (Hz)')
		plt.ylabel('Gain (dB)')
		plt.title(title)
		plt.xscale("symlog")
		plt.grid(True)
