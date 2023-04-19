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
import os
from tqdm import tqdm
from .ErrorMetrics import *
from .template_render import template_render
from distutils.dir_util import mkpath

class PyModelArithInt:
    __resource_dir = "../resources/"
    __single_circuit_model_dict_py = "single_circuit_model_dict.py.template"
    __single_circuit_model_mat_py = "single_circuit_model_mat.py.template"

    def __init__(self, helper, problem, signal_weights, design_name = "original"):
        dir_path = os.path.dirname(os.path.abspath(__file__))
        self.resource_dir =  f"{dir_path}/{self.__resource_dir}"
        #self.lut_model_py = f"{self.resource_dir}{self.__library_model_dict_py}"
        #self.single_circuit_model = f"{self.resource_dir}{self.__single_circuit_model_dict_py}"
        self.helper = helper
        self.problem = problem
        self.design_name = design_name
        self.helper.load_design(design_name)
        self.helper.reverse_splitnets()
        self.wires = helper.get_PIs_and_Pos()
        assert len(self.wires["PI"]) == 2, "This circuit has more than two multi-bit primary inputs. This is not supported"
        assert len(self.wires["PO"]) == 1, "This circuit has more than one multi-bit primary output. This is not supported"
        self.pis_weights = [{f"{pi.str()}[{i}]": signal_weights[f"{pi.str()}[{i}]"] for i in range(w.width)} for pi, w in self.wires["PI"].items()]
        for po, w in self.wires["PO"].items():
            self.po_weights = { f"{po.str()}[{i}]": signal_weights[f"{po.str()}[{i}]"] for i in range(w.width)}
  
    def generate(self, top_module, pareto_set, destination):
        items = {"top_module" : top_module,	"lut" : {} } | { f"operand{i+1}" : k.str()[1:] for i, k in zip(range(2), self.wires["PI"].keys())}
        for n, c in enumerate(tqdm(pareto_set)):
            configuration = self.problem.matter_configuration(c)
            computed_circuit_output, _ = self.problem.get_outputs(configuration)
            model, signed, offset_op1, offset_op2 = self.get_lut_for_variant_as_mat(computed_circuit_output)
            items["top_module"] = f"{top_module}"
            items["lut"] = model.tolist()
            items["signed"] = signed
            items["offset1"] = offset_op1
            items["offset2"] = offset_op2
            destination_dir = f"{destination}/variant_{n:05d}"
            mkpath(destination_dir)
            output_file = f"{destination_dir}/{top_module}.py"
            template_render(self.resource_dir, self.__single_circuit_model_mat_py, items, output_file)        

    def get_lut_for_variant_as_mat(self, computed_circuit_outputs):
        signed = np.min(list(self.pis_weights[0].values())) < 0 or np.min(list(self.pis_weights[1].values())) < 0 or np.min(list(self.po_weights.values())) < 0
        result = np.zeros((2**len(self.pis_weights[0]), 2**len(self.pis_weights[1])), dtype = int)
        offset_op1 = 2**(len(self.pis_weights[0])-1) if signed else 0
        offset_op2 = 2**(len(self.pis_weights[1])-1) if signed else 0
        for o in computed_circuit_outputs:
            a = int(bool_to_value({ k : i for k, i in o["i"].items() if k in self.pis_weights[0] }, self.pis_weights[0]))
            b = int(bool_to_value({ k : i for k, i in o["i"].items() if k in self.pis_weights[1] }, self.pis_weights[1]))
            r = int(bool_to_value(o["a"], self.po_weights))
            result[a + offset_op1 if signed else a][b + offset_op2 if signed else b] = r
        return result, signed, offset_op1, offset_op2