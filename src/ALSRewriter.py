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
import gc
from pyosys import libyosys as ys

class ALSRewriter:
    def __init__(self, graph, catalog):
        self.graph = graph
        self.catalog = catalog

    def load_and_rewrite(self, design, design_name, solution):
        configuration = self.__configuration(solution)
        ys.run_pass(f"tee -q design -load {design_name}", design)
        for module in design.selected_whole_modules_warn():
            for cell in module.selected_cells():
                if ys.IdString("\LUT") in cell.parameters:
                    self.__cell_to_aig(configuration, module, cell)
        ys.run_pass("tee -q clean -purge", design)
        ys.run_pass("tee -q opt", design)

    def rewrite(self, design_name, solution):
        configuration = self.__configuration(solution)
        design = ys.Design()
        ys.run_pass(f"tee -q design -load {design_name}", design)
        for module in design.selected_whole_modules_warn():
            for cell in module.selected_cells():
                if ys.IdString("\LUT") in cell.parameters:
                    self.__cell_to_aig(configuration, module, cell)
        ys.run_pass("tee -q clean -purge", design)
        ys.run_pass("tee -q opt", design)
        return design

    def rewrite_and_save(self, design_name, solution, destination):
        design = ys.Design()
        configuration = self.__configuration(solution)
        ys.run_pass(f"tee -q design -load {design_name}", design)
        for module in design.selected_whole_modules_warn():
            for cell in module.selected_cells():
                if ys.IdString("\LUT") in cell.parameters:
                    self.__cell_to_aig(configuration, module, cell)
        ys.run_pass("tee -q clean -purge", design)
        ys.run_pass("tee -q opt", design)
        ys.run_pass(f"tee -q write_verilog -noattr {destination}.v", design)
        ys.run_pass(f"tee -q write_ilang {destination}.ilang", design)
        ys.run_pass("design -reset", design)
        ys.run_pass("delete", design)
        del design
        gc.collect()

    def __configuration(self, x):
        return [{"name": l["name"], "dist": c, "spec": e[0]["spec"], "axspec": e[c]["spec"], "gates": e[c]["gates"],
                 "S": e[c]["S"], "P": e[c]["P"], "out_p": e[c]["out_p"], "out": e[c]["out"]} for c, l in
                zip(x, self.graph.get_cells()) for e in self.catalog if e[0]["spec"] == l["spec"]]

    def __cell_to_aig(self, configuration, module, cell):
        ax_cell_conf = [c for c in configuration if c["name"] == cell.name.str()][0]
        sigmap = ys.SigMap(module)
        S = ax_cell_conf["S"]
        P = ax_cell_conf["P"]
        out_p = ax_cell_conf["out_p"]
        out = ax_cell_conf["out"]
        aig_vars = [[], [ys.SigSpec(ys.State.S0, 1)]]
        Y = cell.connections_[ys.IdString("\Y")]
        aig_out = ys.SigSpec(sigmap(Y).to_sigbit_vector()[0].wire)
        A = cell.connections_[ys.IdString("\A")]
        if cell.input(ys.IdString("\A")):
            for sig in sigmap(A).to_sigbit_vector():
                if sig.is_wire():
                    aig_vars[1].append(ys.SigSpec(sig.wire))
                else:
                    aig_vars[1].append(ys.SigSpec(sig, 1))
        aig_a_and_b = [[], []]
        for i in range(len(S[0])):
            a = module.addWire(ys.IdString(f"\\{cell.name.str()}_a_{i}"))
            b = module.addWire(ys.IdString(f"\\{cell.name.str()}_b_{i}"))
            y = module.addWire(ys.IdString(f"\\{cell.name.str()}_y_{i}"))
            module.addAnd(ys.IdString(f"\\{cell.name.str()}_and_{i}"), ys.SigSpec(a), ys.SigSpec(b), ys.SigSpec(y))
            aig_a_and_b[0].append(ys.SigSpec(a))
            aig_a_and_b[1].append(ys.SigSpec(b))
            aig_vars[1].append(ys.SigSpec(y))
        for i, w in zip(range(len(aig_vars[1])), aig_vars[1]):
            not_w = module.addWire(ys.IdString(f"\\{cell.name.str()}_not_{i}"))
            module.addNot(ys.IdString(f"\\{cell.name.str()}_not_gate_{i}"), w, ys.SigSpec(not_w))
            aig_vars[0].append(ys.SigSpec(not_w))
        if len(S[0]) == 0:
            module.connect(aig_out, aig_vars[out_p][out])
        else:
            for i in range(len(aig_a_and_b[0])):
                for c in [0, 1]:
                    module.connect(aig_a_and_b[c][i], aig_vars[P[c][i]][S[c][i]])
            module.connect(aig_out, aig_vars[out_p][-1])
        module.remove(cell)