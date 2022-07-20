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
import json

import numpy as np
from .ALSGraph import *
from .Utility import *
from .DynLoader import *

class ErrorConfig:
    class Metric(Enum):
        EPROB = 1           # Classic error probability
        AWCE = 2            # Absolute worst-case error
        MAE = 3             # Mean absolute error
        WRE = 4             # Worst-case relative error
        MRE = 5             # Mean relative error
        MSE = 6             # Mean squared error
        MED = 7             # Mean error distance
        MRED = 8            # Relative mean error distance
        RMSED = 9           # Root Mean Squared Error Distance
        VARED = 10          # Variance of the Error Distance

    def __init__(self, metric, threshold, vectors, dataset = None, weights = None):
        self.metric = None
        self.threshold = threshold
        self.n_vectors = vectors
        self.dataset = dataset
        self.weights = weights
        self.function = None
        self.builtin_metric = None
        if type(metric) == str:
            self.get_builin_metric(metric)
        elif type(metric) == dict:
           self.get_custom_metric(metric)

    def get_builin_metric(self, metric):
        error_metrics = {
            "ep": ErrorConfig.Metric.EPROB,
            "awce": ErrorConfig.Metric.AWCE,
            "mae" : ErrorConfig.Metric.MAE,
            "wre" : ErrorConfig.Metric.WRE,
            "mre": ErrorConfig.Metric.MRE,
            "mse": ErrorConfig.Metric.MSE,
            "med": ErrorConfig.Metric.MED,
            "mred": ErrorConfig.Metric.MRED,
            "rmsed" : ErrorConfig.Metric.RMSED,
            "vared" : ErrorConfig.Metric.VARED
        }
        if metric not in error_metrics.keys():
            raise ValueError(f"{metric}: error-metric not recognized")
        else:
            self.builtin_metric = True
            self.metric = error_metrics[metric]

    def get_custom_metric(self, metric):
        if "module" not in metric.keys():
            raise ValueError(f"'module' field not specified")
        if "function" not in metric.keys():
            raise ValueError(f"'function' field not specified")
        self.function = dynamic_import(metric["module"], metric["function"])
        self.builtin_metric = False

    def validate_weights(self, graph):
        po_names = [o["name"] for o in graph.get_po()]
        for k in self.weights.keys():
            if k not in po_names:
                graph.plot()
                raise ValueError(f"{k} not found in POs {po_names}")


def evaluate_output(graph, samples, configuration):
    return [{"e" : s["output"], "a" : graph.evaluate(s["input"], configuration)} for s in samples]


def bool_to_value(output, weights):
    return np.sum([float(weights[o]) * output[o] for o in weights.keys()])


def evaluate_ep(graph, samples, configuration, weights):
    return sum([0 if sample["output"] == graph.evaluate(sample["input"], configuration) else 1 for sample in samples])


def evaluate_absolute_ed(graph, samples, configuration, weights):
    current_outputs = [ graph.evaluate(sample["input"], configuration) for sample in samples ]
    return [ np.abs( bool_to_value(current, weights) - bool_to_value(sample["output"], weights) ) for sample, current in zip(samples, current_outputs) ]


def evaluate_signed_ed(graph, samples, configuration, weights):
    current_outputs = [ graph.evaluate(sample["input"], configuration) for sample in samples ]
    return [ bool_to_value(current, weights) - bool_to_value(sample["output"], weights) for sample, current in zip(samples, current_outputs) ]


def evaluate_squared_ed(graph, samples, configuration, weights):
    current_outputs = [ graph.evaluate(sample["input"], configuration) for sample in samples ]
    return [ ( bool_to_value(current, weights) - bool_to_value(sample["output"], weights) )**2 for sample, current in zip(samples, current_outputs) ]


def evaluate_relative_ed(graph, samples, configuration, weights):
    current_outputs = [ graph.evaluate(sample["input"], configuration) for sample in samples ]
    return [ np.abs ( (1 + bool_to_value(sample["output"], weights)) / (1 + bool_to_value(current, weights)) ) for sample, current in zip(samples, current_outputs) ]


def evaluate_med(graph, samples, configuration, weights):
    error_hystogram = {}
    for sample in samples:
        current = graph.evaluate(sample["input"], configuration)
        error = np.abs( bool_to_value(current, weights) - bool_to_value(sample["output"], weights) )
        index = round(error, 2)
        if index in error_hystogram.keys():
            error_hystogram[index] += 1
        else:
            error_hystogram[index] = 1
    return error_hystogram


def evaluate_mred(graph, samples, configuration, weights):
    error_hystogram = {}
    for sample in samples:
        current = graph.evaluate(sample["input"], configuration)
        error = np.abs ( (1 + bool_to_value(sample["output"], weights)) / (1 + bool_to_value(current, weights)) )
        index = round(error, 2)
        if index in error_hystogram.keys():
            error_hystogram[index] += 1
        else:
            error_hystogram[index] = 1
    return error_hystogram


