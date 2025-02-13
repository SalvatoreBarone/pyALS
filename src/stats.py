"""
Copyright 2021-2025 Salvatore Barone <salvatore.barone@unina.it>

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
from pyalslib import ALSCatalogCache
from src.lut_pwr import *
import matplotlib.pyplot as plt


def gates_histogram(catalog):
	cache = ALSCatalogCache(catalog)
	gates_per_luts = {}
	for s in cache.get_all_exact_luts():
		synth_spec, S, P, out_p, out, depth = s
		ngates = len(S[0])
		if ngates in gates_per_luts:
			gates_per_luts[ngates] += 1
		else:
			gates_per_luts[ngates] = 1
	plt.figure(figsize=[8,4])
	gates_range = sorted(gates_per_luts.keys())
	plt.bar(gates_range, [gates_per_luts[i] for i in gates_range], width=0.5)
	plt.xticks(gates_range)
	plt.ylabel("Number of specifications")
	plt.xlabel("#AIG nodes")
	plt.savefig("gates_hystogram.pdf", bbox_inches='tight', pad_inches=0)


def get_data_from_boxplot(bp):
	medians = [item.get_ydata()[0] for item in bp['medians']]
	bounds = [item.get_ydata() for item in bp['caps']]
	q1 = [round(min(item.get_ydata()), 1) for item in bp['boxes']]
	q3 = [round(max(item.get_ydata()), 1) for item in bp['boxes']]
	fliers = [item.get_ydata() for item in bp['fliers']]
	lower_outliers = []
	upper_outliers = []
	for i in range(len(fliers)):
		lower_outliers_by_box = []
		upper_outliers_by_box = []
		for outlier in fliers[i]:
			if outlier < q1[i]:
				lower_outliers_by_box.append(round(outlier, 1))
			else:
				upper_outliers_by_box.append(round(outlier, 1))
		lower_outliers.append(lower_outliers_by_box)
		upper_outliers.append(upper_outliers_by_box)
	return medians, bounds, q1, q3, lower_outliers, upper_outliers


def power_gates_boxplot(catalog):
	cache = ALSCatalogCache(catalog)
	power_per_gates = {}
	for spec in cache.get_all_exact_luts():
		exact_synth_spec, exact_S, exact_P, exact_out_p, exact_out, exact_depth = spec
		exact_gates = len(exact_S[0])
		exact_power, ex_reord = internal_node_activity(exact_synth_spec)
		if exact_gates not in power_per_gates.keys():
			power_per_gates[exact_gates] = []
		power_per_gates[exact_gates].append(exact_power)
	gates_range = sorted(power_per_gates.keys())
	plt.figure(figsize=[8,4])
	data = [power_per_gates[i] for i in reversed(gates_range)]
	plt.boxplot(data, labels=list(reversed(gates_range)))
	plt.ylabel("Switching activity")
	plt.xlabel("#AIG nodes")
	plt.savefig("switching_per_gates_boxplot.pdf", bbox_inches='tight', pad_inches=0)


def power_truth_boxplot(catalog):
	cache = ALSCatalogCache(catalog)
	power_per_ones = {}
	for spec in cache.get_all_exact_luts():
		exact_synth_spec, exact_S, exact_P, exact_out_p, exact_out, exact_depth = spec
		ones = exact_synth_spec.count('1')
		exact_power, ex_reord = internal_node_activity(exact_synth_spec)
		if ones not in power_per_ones.keys():
			power_per_ones[ones] = []
		power_per_ones[ones].append(exact_power)
	ones_range = sorted(power_per_ones.keys())
	plt.figure(figsize=[8,4])
	data = [power_per_ones[i] for i in ones_range]
	plt.boxplot(data, labels=ones_range)
	plt.ylabel("Switching activity")
	plt.xlabel("Truth-density")
	plt.savefig("switching_per_truth_boxplot.pdf", bbox_inches='tight', pad_inches=0)


def power_truth_k_boxplot(k):
	relevant_truth = range(2, 2 ** k - 1)
	powers = {i: [] for i in range(2 ** k + 1)}
	for bool_f in range(2 ** ((2 ** k) - 1)):
		print(f"  {bool_f + 1}/{2 ** ((2 ** k) - 1)} ({(bool_f + 1) * 100 // (2 ** ((2 ** k) - 1))}%)" + " " * 30,	end="\r", flush=True)
		spec = '{bool_f:0' + str(2 ** k) + 'b}'
		spec = spec.format(bool_f=bool_f)
		ones = spec.count('1')
		powers[ones].append(internal_node_activity(spec)[0])
	fig = plt.figure(figsize=[8,4])
	plt.boxplot([powers[i] for i in relevant_truth], labels=relevant_truth)
	plt.ylabel("Switching activity")
	plt.xlabel("Truth density")
	plt.savefig(f"switching_per_truth_density_k_{k}_boxplot.pdf", bbox_inches='tight', pad_inches=0)