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
import random, json, sys, numpy as np, matplotlib.pyplot as plt, seaborn as sns 
from fixedpoint import FixedPoint			
from .Utility import *
from .YosysHelper import *

class DatasetGenerator:
	def __init__(self, yosis_helper, profiledvalues, alpha, minv, name, 
		hist = "occurrence_frequency.pdf", 
		nhist = "normalized_occurrence_frequency.pdf", 
		boxp = "occurrence_frequency_boxplot.pdf",
		cov = "coverage_of_values.pdf",
		out = "generated_dataset.csv"):
		""" 
		Creates a new generator

		param profiledvalues 	JSON file containing the profiled values
		param alpha		Proportion factor on the basis of which the random test vectors to be generated, given a profiled value, is determined
		param minv		Minimum number of random test vectors to be generated, given a profiled value
		param name 		Name of the primary input for which profiled values are provided
		param hist		Path for the generated profiled values histogram
		param nhist		Path for the generated profiled values histogram (normalized occurrence frequency)
		param boxp		Path for the generated coverage plot for occurrence frequency ov provided profiled data
		param cov		Path for the coverage plot
		param csv		Path for the generated dataset
		"""
		self.helper = yosis_helper
		self.profiledvalues = profiledvalues
		self.alpha = alpha
		self.minv = minv
		self.name = name
		self.hist = hist
		self.nhist = nhist
		self.boxp = boxp
		self.cov = cov
		self.out = out

	def get_data(self):
		data = [] 
		if self.profiledvalues.endswith(".json"):
			with open(self.profiledvalues) as f:
				data = json.load(f)
			data = list(flatten(data))
			data = list(map(int, data))
		else:
			print("Unsupported file format")
			exit()
		return data

	def generate(self):
		data = self.get_data()
		# Computing the hystogram of utilization of each int8-value a weight
		hystogram = {}
		for w in data:
			if w in hystogram:
				hystogram[int(w)] += 1
			else:
				hystogram[int(w)] = 1
		self.plot_hystogram(hystogram)
		self.plot_boxandwisker(hystogram)
		PIs = self.get_PIs()
		dataset, coverage = self.generate_dataset(hystogram, PIs)
		self.plot_coverage(coverage)
		self.save_dataset(dataset, PIs, self.out)


	def get_PIs(self):
		wires = self.helper.get_PIs_and_Pos()
		PIs = {"Profiled" : [], "Non-Profiled" : []}
		for k, w in wires["PI"].items():
			if k.str()[1:] == self.name:
				PIs["Profiled"].append((k.str(), w.width))
			else:
				PIs["Non-Profiled"].append((k.str(), w.width))
		
		assert len(PIs["Profiled"]) == 1, f"No primary input named {self.name}"
		return PIs

	def generate_dataset(self, hystogram, PIs):
		# computing nbits for the profiled input
		profiled_nbits = PIs["Profiled"][0][1]
		non_profiled_nbits = sum(i[1] for i in PIs["Non-Profiled"])

		h_range = sorted(hystogram.keys())
		total_weights = sum(hystogram.values())
		normalized_frequency = [hystogram[i] / total_weights for i in h_range]

		# conputing the suggested alpha
		suggested_alpha = (2 ** non_profiled_nbits) / np.max(normalized_frequency)

		# printing some stats
		print(f"Freq. (min, mean, max): {np.min(normalized_frequency)}, {np.mean(normalized_frequency)}, {np.max(normalized_frequency)}\
				\nFreq. (Q1, Q2, Q3): {np.quantile(normalized_frequency, .25)}, {np.quantile(normalized_frequency, .5)}, {np.quantile(normalized_frequency, .75)}\
				\n\nSuggested alpha (max, Q2, Q3): {suggested_alpha} {(2 ** non_profiled_nbits) / np.quantile(normalized_frequency, .50)} {(2 ** non_profiled_nbits) / np.quantile(normalized_frequency, .75)}.")

		print("Generating dataset...")
		nvec = 0
		dataset = []
		coverage = {}
		for a, v in hystogram.items():
			# computing the proper amount random input vectors, with respect to alpha
			n_vectors = max(self.minv, int(v * self.alpha / total_weights))  # at least one vector
			n_vectors = min(int(2 ** non_profiled_nbits), n_vectors)

			# computing the coverage percentage
			coverage[a] = 100 * n_vectors / (2 ** non_profiled_nbits)
			#print(f"Generating {n_vectors} test vectors for W={a}, which occurs {v}/{total_weights}={v / total_weights} times. Coverage: {coverage[a]}%.")

			# keeps track of the total amount of random vectors being generated
			nvec += n_vectors

			# generating the complete input space B^m
			input_set = range(int(-2 ** (non_profiled_nbits - 1)), int(+2 ** (non_profiled_nbits - 1) - 1))

			# generating X_v from B^m
			if n_vectors == int(2 ** non_profiled_nbits):
				test_vectors = list(input_set)
			else:
				test_vectors = random.sample(input_set, n_vectors)

			dataset.extend((FixedPoint(a, signed=True, m=profiled_nbits, n=0), FixedPoint(b, signed=True, m=non_profiled_nbits, n=0)) for b in test_vectors)

		print("Done!")

		rho = list(coverage.values())
		print(f"\nDataset coverage is {100 * nvec / (2 ** (2 * non_profiled_nbits))}%.\
				\nVector coverage (min, mean, max): {np.min(rho)}, {np.mean(rho)}, {np.max(rho)}.\
				\nVector coverage. (Q1, Q2, Q3): {np.quantile(rho, .25)}, {np.quantile(rho, .50)}, {np.quantile(rho, .75)}\
				\n\nTotal test vectors: {nvec}.")
		return dataset, coverage

	def plot_hystogram(self, hystogram):
		h_range = sorted(hystogram.keys())
		frequency = [hystogram[i] for i in h_range]
		total_weights = sum(hystogram.values())
		normalized_frequency = [hystogram[i] / total_weights for i in h_range]
		print(f"Total weights: {total_weights}, total different weights: {len(h_range)}")
		# Plotting the frequency
		plt.figure(figsize=[8, 4])
		plt.bar(h_range, frequency, width=0.5)
		plt.yscale("log")
		plt.ylabel("Weight frequency")
		plt.xlabel("Weight")
		plt.savefig(self.hist, bbox_inches='tight', pad_inches=0)
		# Plotting the normalized frequency
		plt.figure(figsize=[8, 4])
		plt.bar(h_range, normalized_frequency, width=0.5)
		plt.yscale("log")
		plt.ylabel("Normalized weight frequency")
		plt.xlabel("Weight")
		plt.savefig(self.nhist, bbox_inches='tight', pad_inches=0)
		

	def plot_boxandwisker(self, hystogram):
		h_range = sorted(hystogram.keys())
		total_weights = sum(hystogram.values())
		normalized_frequency = [hystogram[i] / total_weights for i in h_range]
		self.plot_box_pdf_cdf(normalized_frequency)


	def plot_box_pdf_cdf(self, data):	
		q1, median, q3 = np.percentile(data, [25, 50, 75])
		iqr = q3 - q1
		fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, sharex=True)
		medianprops = dict(linestyle='-', linewidth=2, color='yellow')
		sns.boxplot(x=data, color='lightcoral', saturation=1, medianprops=medianprops, flierprops={'markerfacecolor': 'mediumseagreen'}, whis=1.5, ax=ax1)
		ax1.set_yticks([])
		ax1.tick_params(labelbottom=True)
		ax1.set_ylim(-0.5, 1.5)
		ax1.axis("off")
		ax1.errorbar([q1, q3], [1, 1], yerr=[-0.2, 0.2], color='black', lw=1)
		ax1.text(q1, 0.6, 'Q1', ha='center', va='center', color='black')
		ax1.text(q3, 0.6, 'Q3', ha='center', va='center', color='black')
		ax1.text(median, 1.2, 'IQR', ha='center', va='center', color='black')
		sns.kdeplot(data, ax=ax2)
		kdeline = ax2.lines[0]
		xs = kdeline.get_xdata()
		ys = kdeline.get_ydata()
		ylims = ax2.get_ylim()
		ax2.fill_between(xs, 0, ys, color='mediumseagreen')
		ax2.fill_between(xs, 0, ys, where=(xs >= q1 - 1.5*iqr) & (xs <= q3 + 1.5*iqr), color='skyblue')
		ax2.fill_between(xs, 0, ys, where=(xs >= q1) & (xs <= q3), color='lightcoral')
		ax2.set_ylim(0, ylims[1])
		ax2.set_xlim(0, np.max(data))
		ax2.set_xlabel("Occurrence-frequency of weights")
		sns.ecdfplot(data=data, ax=ax3)
		ecdline = ax3.lines[0]
		xs = ecdline.get_xdata()
		ys = ecdline.get_ydata()
		ylims = ax3.get_ylim()
		ax3.fill_between(xs, 0, ys, color='mediumseagreen')
		ax3.fill_between(xs, 0, ys, where=(xs >= q1 - 1.5*iqr) & (xs <= q3 + 1.5*iqr), color='skyblue')
		ax3.fill_between(xs, 0, ys, where=(xs >= q1) & (xs <= q3), color='lightcoral')
		ax3.set_ylim(0, ylims[1])
		plt.subplot_tool()
		plt.savefig(self.boxp, bbox_inches='tight', pad_inches=0)


	def plot_coverage(self, coverage):
		h_range = sorted(coverage.keys())
		rho = [coverage[i] for i in h_range]
		plt.figure(figsize=[8, 4])
		plt.bar(h_range, rho, width=0.5)
		plt.ylabel("Coverage (%)")
		plt.xlabel("Weight")
		plt.savefig(self.cov, bbox_inches='tight', pad_inches=0)


	def save_dataset(self, dataset, PIs, outfile):
		if not outfile.endswith(".csv"):
			print(f"Warning: {outfile} renamed as {outfile}.csv")
			outfile = f"{outfile}.csv"
		profiled_name = PIs["Profiled"][0][0]
		profiled_nbit = PIs["Profiled"][0][1]
		nbits = 0
		header = ",".join([f"{profiled_name}[{i}]" for i in reversed(range(profiled_nbit))]) 
		for pi in PIs["Non-Profiled"]:
			header += "," + ",".join([f"{pi[0]}[{i}]" for i in reversed(range(pi[1]))]) 
			nbits += pi[1]
		orig_stdout = sys.stdout
		with open(outfile, 'w') as f:
			sys.stdout = f
			print(header)
			for i in dataset:
				print(','.join(f"{i[0]:0{profiled_nbit}b}"), ',',','.join(f"{i[1]:0{nbits}b}"), sep="")
		sys.stdout = orig_stdout