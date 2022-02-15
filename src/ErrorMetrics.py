"""
Copyright 2021 Salvatore Barone <salvatore.barone@unina.it>

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
from .ALSGraph import *
from .Utility import *

class ErrorConfig:
    class Metric(Enum):
        EPROB = 1
        AWCE = 2
        MED = 3

    def __init__(self, metric, threshold, vectors, weights = None):
        error_metrics = {
            "eprob": ErrorConfig.Metric.EPROB,
            "EProb": ErrorConfig.Metric.EPROB,
            "EPROB": ErrorConfig.Metric.EPROB,
            "awce": ErrorConfig.Metric.AWCE,
            "AWCE": ErrorConfig.Metric.AWCE,
            "med" : ErrorConfig.Metric.MED,
            "MED" : ErrorConfig.Metric.MED}
        if metric not in error_metrics.keys():
            raise ValueError(f"{metric}: error-metric not recognized")
        else:
            self.metric = error_metrics[metric]
        self.threshold = threshold
        self.n_vectors = vectors
        self.weights = weights

def evaluate_output(graph, samples, configuration):
    return [{"e" : s["output"], "a" : graph.evaluate(s["input"], configuration)} for s in samples]

def evaluate_eprob(graph, samples, configuration):
    return sum([0 if sample["output"] == graph.evaluate(sample["input"], configuration) else 1 for sample in samples])

def evaluate_awce(graph, samples, configuration, weights):
        current_outputs = [ graph.evaluate(sample["input"], configuration) for sample in samples ]
        return np.max([ sum([weights[o] if sample["output"][o] != current[o] else 0 for o in weights.keys() ]) for sample, current in zip(samples, current_outputs) ])

def evaluate_med(graph, samples, configuration, weights):
    error_hystogram = { i: 0 for i in range(2**len(weights)) }
    for sample in samples:
        current_output = graph.evaluate(sample["input"], configuration)
        error = sum([weights[o] if sample["output"][o] != current_output[o] else 0 for o in weights.keys()])
        error_hystogram[error] += 1
    return error_hystogram
