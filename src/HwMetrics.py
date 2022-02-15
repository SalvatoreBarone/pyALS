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
from liberty.parser import parse_liberty
from .ALSGraph import *

class HwConfig:
    class Metric(Enum):
        GATES = 1
        AREA = 2
        POWER = 3
        DEPTH = 5

    def __init__(self, metrics, liberty = None):
        hw_metrics = {
            "gates" : HwConfig.Metric.GATES,
            "area"  : HwConfig.Metric.AREA,
            "power" : HwConfig.Metric.POWER,
            "depth": HwConfig.Metric.DEPTH,
        }
        self.metrics = []
        for metric in metrics:
            if metric not in hw_metrics.keys():
                raise ValueError(f"{metric}: hw-metric not recognized")
            else:
                self.metrics.append(hw_metrics[metric])
        self.liberty = liberty
        if HwConfig.Metric.AREA in self.metrics or HwConfig.Metric.POWER in self.metrics:
            if self.liberty == None:
                raise ValueError(f"you need to specify a technology library for area or power optimization")
            else:
                library = parse_liberty(open(self.liberty).read())
                self.cell_area = {cell_group.args[0]: float(cell_group['area']) for cell_group in library.get_groups('cell')}
                self.cell_power = { cell_group.args[0] : float(cell_group['cell_leakage_power'] if cell_group['cell_leakage_power'] is not None else cell_group['drive_strength'] ) for cell_group in library.get_groups('cell') }
        else:
            self.cell_area = None
            self.cell_power = None

def get_gates(configuration):
    return sum([c["gates"] for c in configuration.values()])

def get_depth(configuration, graph):
    return graph.get_depth(configuration)

def get_area(design, cell_area):
    return sum([cell_area[cell.type.str()[1:]] for module in design.selected_whole_modules_warn() for cell in module.selected_cells()])

def get_power(design, cell_power):
    return sum([cell_power[cell.type.str()[1:]] for module in design.selected_whole_modules_warn() for cell in module.selected_cells()])
