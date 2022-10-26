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
from .YosysHelper import *

class ALSRewriter:
    def __init__(self, helper, problem):
        self.helper = helper
        self.problem = problem

    def generate_hdl(self, pareto_set, out_dir):
        for n, c in enumerate(pareto_set):
            self.rewrite_and_save("original", c, f"{out_dir}/variant_{n:05d}")

    def rewrite_and_save(self, design_name, solution, destination):
        configuration = self.problem.matter_configuration(solution)
        self.helper.load_design(design_name)
        self.helper.to_aig(configuration)
        self.helper.reverse_splitnets()
        self.helper.clean()
        self.helper.opt()
        self.helper.write_verilog(destination)
        self.helper.reset()
        self.helper.delete()
