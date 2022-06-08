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
from .ALSGraph import *
from .Utility import *

class ErrorConfig:
    class Metric(Enum):
        EPROB = 1           # Classic error probability
        AWCE = 2            # Absolute worst-case error
        MED = 3             # Mean error distance
        IA_EPROB = 4,       # Input (distribution)-aware error-probability
        IA_MED = 5          # Input (distribution)-aware error.distance

    def __init__(self, metric, threshold, vectors, distribution = None, weights = None):
        error_metrics = {
            "ep": ErrorConfig.Metric.EPROB,
            "eprob": ErrorConfig.Metric.EPROB,
            "EProb": ErrorConfig.Metric.EPROB,
            "EPROB": ErrorConfig.Metric.EPROB,
            "awce": ErrorConfig.Metric.AWCE,
            "AWCE": ErrorConfig.Metric.AWCE,
            "med" : ErrorConfig.Metric.MED,
            "MED" : ErrorConfig.Metric.MED,
            "ia-ep" : ErrorConfig.Metric.IA_EPROB,
            "ia_ep": ErrorConfig.Metric.IA_EPROB,
            "IA-EP": ErrorConfig.Metric.IA_EPROB,
            "IA_EP": ErrorConfig.Metric.IA_EPROB,
            "ia-ed" : ErrorConfig.Metric.IA_MED,
            "ia_ed": ErrorConfig.Metric.IA_MED,
            "IA-ED": ErrorConfig.Metric.IA_MED,
            "IA_ED": ErrorConfig.Metric.IA_MED,
        }
        if metric not in error_metrics.keys():
            raise ValueError(f"{metric}: error-metric not recognized")
        else:
            self.metric = error_metrics[metric]
        self.threshold = threshold
        self.n_vectors = vectors
        self.distribution = distribution
        self.weights = weights

    def validate_weights(self, graph):
        po_names = [o["name"] for o in graph.get_po()]
        for k in self.weights.keys():
            if k not in po_names:
                graph.plot()
                raise ValueError(f"{k} not found in POs {po_names}")

    def validate_input_distribution(self, graph):
        pass


def evaluate_output(graph, samples, configuration):
    return [{"e" : s["output"], "a" : graph.evaluate(s["input"], configuration)} for s in samples]


def evaluate_eprob(graph, samples, configuration):
    return sum([0 if sample["output"] == graph.evaluate(sample["input"], configuration) else 1 for sample in samples])


def evaluate_awce(graph, samples, configuration, weights):
    current_outputs = [ graph.evaluate(sample["input"], configuration) for sample in samples ]
    return float(np.max([ sum([float(weights[o]) if sample["output"][o] != current[o] else 0 for o in weights.keys() ]) for sample, current in zip(samples, current_outputs) ]))


def evaluate_med(graph, samples, configuration, weights):
    error_hystogram = { i: 0 for i in range(2**len(weights)) }
    for sample in samples:
        current_output = graph.evaluate(sample["input"], configuration)
        error = sum([float(weights[o]) if sample["output"][o] != current_output[o] else 0 for o in weights.keys()])
        error_hystogram[error] += 1
    return error_hystogram


def evaluate_ia_eprob(graph, i_distribution, samples, configuration):
    return sum([0 if sample["output"] == graph.evaluate(sample["input"], configuration) else 1 for sample in samples])


def evaluate_ia_med(graph, i_distribution, samples, configuration, weights):
    error_hystogram = {i: 0 for i in range(2 ** len(weights))}
    for sample in samples:
        current_output = graph.evaluate(sample["input"], configuration)
        error = sum([float(weights[o]) if sample["output"][o] != current_output[o] else 0 for o in weights.keys()])
        error_hystogram[error] += 1
    return error_hystogram