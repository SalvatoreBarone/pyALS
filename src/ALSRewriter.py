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
    def __init__(self, graph, catalog, module_id, PIs, POs):
        self.graph = graph
        self.catalog = catalog
        self.module_id = module_id
        self.helper = YosysHelper()
        self.helper.module_id = module_id
        self.helper.PIs = PIs
        self.helper.POs = POs

    def rewrite_and_save(self, design_name, solution, destination):
        configuration = self.__configuration(solution)
        self.helper.load_design(design_name)
        self.helper.to_aig(configuration)
        self.helper.reverse_splitnets()
        self.helper.clean()
        self.helper.opt()
        self.helper.write_verilog(destination)
        self.helper.reset()
        self.helper.delete()

    def __configuration(self, x):
        matter = {}
        for c, l in zip(x, self.graph.get_cells()):
            for e in self.catalog:
                if e[0]["spec"] == l["spec"]:
                    matter[l["name"]] = {"dist": c, "spec": e[0]["spec"], "axspec": e[c]["spec"], "gates": e[c]["gates"], "S": e[c]["S"], "P": e[c]["P"], "out_p": e[c]["out_p"], "out": e[c]["out"], "depth": e[c]["depth"]}
                if negate(e[0]["spec"]) == l["spec"]:
                    matter[l["name"]] = {"dist": c, "spec": negate(e[0]["spec"]), "axspec": negate(e[c]["spec"]), "gates": e[c]["gates"], "S": e[c]["S"], "P": e[c]["P"], "out_p": 1 - e[c]["out_p"], "out": e[c]["out"], "depth": e[c]["depth"]}
        return matter
