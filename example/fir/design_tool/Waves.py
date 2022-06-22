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
import numpy as np
import matplotlib.pyplot as plt


class Wave:

	@staticmethod
	def saw(freq, armonics = 1000, alpha = 10, amplitude = 1):
		sample_f = freq * 100  # sampling frequency (Hz)
		sample_period = 1 / sample_f  # sampling period
		num_of_sample = int(alpha * sample_f / freq)  # number of samples
		time_instants = np.linspace(0, (num_of_sample - 1) * sample_period, num_of_sample)  # sampling time-instants
		return amplitude * np.sum([(-1)**(i+1) / (i * np.pi) * np.sin(2 * np.pi * i * freq * time_instants) for i in range(1, armonics)], axis = 0), time_instants, sample_f

	@staticmethod
	def square(freq, armonics = 1000, alpha = 10, amplitude = 1):
		sample_f = freq * 100  # sampling frequency (Hz)
		sample_period = 1 / sample_f  # sampling period
		num_of_sample = int(alpha * sample_f / freq)  # number of samples
		time_instants = np.linspace(0, (num_of_sample - 1) * sample_period, num_of_sample)  # sampling time-instants
		return amplitude * np.sum([4 / ((2 * i + 1) * np.pi) * np.sin(2 * np.pi * (2 * i + 1) * freq * time_instants) for i in range(0, armonics)], axis = 0), time_instants, sample_f

	@staticmethod
	def triangle(freq, armonics = 1000, alpha = 10, amplitude = 1):
		sample_f = freq * 100  # sampling frequency (Hz)
		sample_period = 1 / sample_f  # sampling period
		num_of_sample = int(alpha * sample_f / freq)  # number of samples
		time_instants = np.linspace(0, (num_of_sample - 1) * sample_period, num_of_sample)  # sampling time-instants
		return amplitude * np.sum([8 / ((2 * i + 1)**2 * np.pi**2) * np.cos(2 * np.pi * (2 * i + 1) * freq * time_instants) for i in range(0, armonics)], axis = 0), time_instants, sample_f

	@staticmethod
	def plot(x, freq, alpha = 10, title = "", outfile = None):
		sample_f = freq * 100  # sampling frequency (Hz)
		sample_period = 1 / sample_f  # sampling period
		num_of_sample = int(alpha * sample_f / freq)  # number of samples
		step_f = sample_f / num_of_sample
		t = np.linspace(0, (num_of_sample - 1) * sample_period, num_of_sample)  # sampling time-instants
		f = np.linspace(0, (num_of_sample - 1) * step_f, num_of_sample)  # sampling frequencies

		X = np.fft.fft(x)
		mag_X = np.abs(X) / num_of_sample
		mag_X_plot = 2 * mag_X[0:int(num_of_sample / 2 + 1)]
		mag_X_plot[0] /= 2
		f_plot = f[0:int(num_of_sample / 2 + 1)]

		fig, ax = plt.subplots(figsize = [6, 6], nrows = 2, ncols = 1)
		fig.suptitle(title)
		ax[0].plot(t, x)
		ax[0].set_title("Time domain")
		ax[0].set_xlabel("Time (s)")
		ax[0].set_ylabel("Amplitude")
		ax[1].set_title("Spectrum")
		ax[1].plot(f_plot, mag_X_plot)
		ax[1].set_xlabel("Frequency (Hz)")
		ax[1].set_ylabel("Magnitude")
		ax[1].set_xscale("symlog")
		fig.tight_layout()
		if outfile is not None:
			fig.savefig(outfile, pad_inches = 0)

