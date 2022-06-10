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


def compute_rem(graph, samples, configuration, weights):
    current_outputs = [ graph.evaluate(sample["input"], configuration) for sample in samples ]  #compute the output of the circuit for each of the samples
    rem = 0.0
    for sample, current in zip(samples, current_outputs):
        f_exact = np.sum([float(weights[o]) * sample["output"][o] for o in weights.keys() ]) # compute f(x), from the circuit output
        f_apprx = np.sum([float(weights[o]) * current[o] for o in weights.keys() ])          # compute the same, but for the approximate circuit
        err = np.abs(1 - (f_apprx + 1) / (f_exact + 1))                                      # computing the relative error
        if rem < err:                                                                        # keeping track of the maximum
            rem = err
        return float(rem)
