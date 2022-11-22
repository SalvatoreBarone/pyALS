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
from .lut_pwr import *


class HwConfig:
    class Metric(Enum):
        GATES = 1
        DEPTH = 2
        SWITCHING = 3

    def __init__(self, metrics):
        self.metrics = []
        hw_metrics = HwConfig.get_hw_metrics()
        for metric in metrics:
            if metric in hw_metrics:
                self.metrics.append(hw_metrics[metric])
            else:
                raise ValueError(f"{metric}: hw-metric not recognized")
            
    @staticmethod
    def get_hw_metrics():
         return {
            "gates"     : HwConfig.Metric.GATES,
            "depth"     : HwConfig.Metric.DEPTH,
            "switching" : HwConfig.Metric.SWITCHING
        }

def get_gates(configuration, lut_io_info, graph):
    return sum(c["gates"] for c in configuration.values())


def get_depth(configuration, lut_io_info, graph):
    return graph.get_depth(configuration)


def get_switching(configuration, lut_io_info, graph):
    return np.sum([internal_node_activity(v["spec"], np.array(np.array(v["freq"], dtype=float) / np.sum(v["freq"])).tolist())[0] for v in lut_io_info.values()])
