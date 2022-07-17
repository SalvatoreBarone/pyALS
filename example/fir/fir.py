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
import numpy as np, sys
from fixedpoint import FixedPoint


def multiply(graph, configuration, weights, a, b, m, n):
    if a != 0 and b != 0:
        bin_a, bin_b = f"{a:0{m+n}b}"[::-1], f"{b:0{m+n}b}"[::-1]
        input_assignment = { **{ f"\\a[{i}]": bin_a[i] == "1" for i in range(n+m) }, **{ f"\\b[{i}]": bin_b[i] == "1" for i in range(n+m) }}
        output_assignment = graph.evaluate(input_assignment, configuration)
        return np.sum([float(weights[o]) * output_assignment[o] for o in weights.keys()])
    else:
        return 0


def compute_fir(graph, input_data, configuration, weights):
    m = int(input_data["m"])
    n = int(input_data["n"])
    input_signal = [FixedPoint(c, signed = True, m = m, n = n) for c in input_data["input_signal"]]
    filter_coefficients = [FixedPoint(c, signed = True, m = m, n = n) for c in input_data["filter_coefficients"]]
    len_i, len_c = len(input_signal), len(filter_coefficients)
    len_r = len_i + len_c - 1
    return [sum([multiply(graph, configuration, weights, input_signal[j - i - len_c], filter_coefficients[i], m, n) for i in range(len_c)]) for j in range(len_c, len_r + 1)]


def get_ssim(x, y, k1 = 0.01, k2 = 0.003):
    xy = np.concatenate((x, y))
    L = np.max(xy) / np.min(xy)
    c1 = (k1 * L)**2
    c2 = (k2 * L)**2
    mu_x = np.average(x)
    mu_y = np.average(y)
    return (2 * mu_x * mu_y + c1) * (2 * np.cov(x, y)[0][1] + c2) / (mu_x ** 2 + mu_y ** 2 + c1) / (np.var(x) + np.var(y) + c2)


def compute_mdssim(graph, input_data, configuration, weights):
    reference_signal = input_data["reference_output"]
    output_signal = compute_fir(graph, input_data, configuration, weights)
    assert len(reference_signal) == len(output_signal), "Reference and output signals must be equal in size"
    output_signal = [float(x) for x in output_signal]
    return (1 - get_ssim(output_signal, reference_signal)) / 2


def get_mse_psnr(a, b):
    assert len(a) == len(b), "Arrays must be equal in size"
    mse = np.mean([(x - y) ** 2 for x, y in zip(a, b)])
    if mse == 0:
        #return mse, np.inf # np.inf makes computation cumbersome (because of nan), so select an high-enough value!
        return mse, 100
    max_ab = np.max(np.concatenate((a, b)))
    psnr = 20 * np.log10(max_ab / np.sqrt(mse))
    return mse, psnr


def compute_psnr(graph, input_data, configuration, weights):
    reference_signal = input_data["reference_output"]
    output_signal = compute_fir(graph, input_data, configuration, weights)
    assert len(reference_signal) == len(output_signal), "Reference and output signals must be equal in size"
    output_signal = [float(x) for x in output_signal]
    mse, psnr = get_mse_psnr(output_signal, reference_signal)
    return -psnr # the PSNR has to be MAXIMIZED to minimize the error


def compute_mse(graph, input_data, configuration, weights):
    reference_signal = input_data["reference_output"]
    output_signal = compute_fir(graph, input_data, configuration, weights)
    assert len(reference_signal) == len(output_signal), "Reference and output signals must be equal in size"
    output_signal = [float(x) for x in output_signal]
    mse, _ = get_mse_psnr(output_signal, reference_signal)
    return mse
