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

    def __init__(self, metrics, threshold, vectors, dataset = None):
        self.metrics = None
        self.threshold = threshold
        self.n_vectors = vectors
        self.dataset = dataset
        self.function = None
        self.builtin_metric = None
        if isinstance(metrics, (list, tuple, str)):
            self.builtin_metric = True
            self.get_builin_metric(metrics)
        elif isinstance(metrics, dict):
           self.get_custom_metric(metrics)

    def get_builin_metric(self, metrics):
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
        if isinstance(metrics, str):
            self.metrics = [error_metrics[metrics]]
        elif isinstance(metrics, (list, tuple)):
            self.metrics = [ error_metrics[m] for m in metrics ]

    def get_custom_metric(self, metric):
        if "module" not in metric.keys():
            raise ValueError("'module' field not specified")
        if "function" not in metric.keys():
            raise ValueError("'function' field not specified")
        self.function = dynamic_import(metric["module"], metric["function"])
        self.builtin_metric = False

def evaluate_output(graph, samples, configuration):
    return [{"i" : s["input"], "e" : s["output"], "a" : graph.evaluate(s["input"], configuration)} for s in samples]


def bool_to_value(signal, weights):
    return np.sum([float(weights[o]) * signal[o] for o in weights.keys()])


def evaluate_abs_ed(outputs, weights):
    return [np.abs( bool_to_value(o["e"], weights) - bool_to_value(o["a"], weights) ) for o in outputs]


def evaluate_signed_ed(outputs, weights):
    return [bool_to_value(o["a"], weights) - bool_to_value(o["e"], weights) for o in outputs]


def evaluate_squared_ed(outputs, weights):
    return [( bool_to_value(o["e"], weights) - bool_to_value(o["a"], weights))**2 for o in outputs]


def evaluate_relative_ed(outputs, weights):
    return [ np.abs ( (1 + bool_to_value(o["e"], weights)) / (1 + bool_to_value(o["a"], weights)) ) for o in outputs]



