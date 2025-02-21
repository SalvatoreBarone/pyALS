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
from pyosys import libyosys as ys
from liberty.parser import parse_liberty

class LibertySynth:

    def __init__(self, liberty_file_name):
        self.liberty = liberty_file_name
        with open(liberty_file_name) as f:
            library = parse_liberty(f.read())
        self.cell_area = { cell_group.args[0] : float(cell_group['area']) for cell_group in library.get_groups('cell') }
        self.cell_power = { cell_group.args[0] : float(cell_group['cell_leakage_power'] if cell_group['cell_leakage_power'] is not None else cell_group['drive_strength'] ) for cell_group in library.get_groups('cell') } 

    def get_area(self, design):
        return sum([self.cell_area[cell.type.str()[1:]] for module in design.selected_whole_modules_warn() for cell in module.selected_cells()])

    def get_power(self, design):
        return sum([self.cell_power[cell.type.str()[1:]] for module in design.selected_whole_modules_warn() for cell in module.selected_cells()])

    def do_synth(self, hdl_source, top_module):
        design = ys.Design()
        ys.run_pass(f"tee -q read_verilog {hdl_source}; tee -q synth -flatten -top {top_module}; tee -q clean -purge; tee -q read_liberty -lib {self.liberty}; tee -q abc -liberty {self.liberty };", design)
        return self.get_area(design), self.get_power(design) /10000