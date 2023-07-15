"""
Copyright 2021-2023 Salvatore Barone <salvatore.barone@unina.it>

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
from .template_render import template_render

class TbGenerator:
    __resource_dir = "../resources/"
    __tb_v = "tb.v.template"
    
    def __init__(self, helper, problem, delay, design_name = "original"):
        dir_path = os.path.dirname(os.path.abspath(__file__))
        self.resource_dir =  f"{dir_path}/{self.__resource_dir}"
        self.helper = helper
        self.helper.reset()
        self.helper.delete()
        self.problem = problem
        self.delay = delay
        self.design_name = design_name
        self.helper.load_design(self.design_name)
        self.helper.reverse_splitnets()
        self.wires = helper.get_PIs_and_Pos()
        
    def generate(self, outfile):
        items = {
            "top_module"   : self.helper.top_module,
            "pi"           : self.get_pi(),
            "po"           : self.get_po(),
            "stimuli"      : self.get_stimuli(),
            "initialdelay" : 2*self.delay,
            "delay"        : self.delay,
        }
        template_render(self.resource_dir, self.__tb_v, items, outfile)
        
    def generate_split(self, outdir):
        items = {
            "top_module"   : self.helper.top_module,
            "pi"           : self.get_pi(),
            "po"           : self.get_po(),
            "initialdelay" : 2*self.delay,
            "delay"        : self.delay,
        }
        stimuli = self.get_stimuli()

    def get_pi(self):
        return [ {"name": name.str()[1:], "width": wire.width} for name, wire in self.wires["PI"].items() ]
    
    def get_po(self):
        return [ {"name": name.str()[1:], "width": wire.width} for name, wire in self.wires["PO"].items() ]
        
    def get_stimuli(self):
        return [{name.str()[1:] : f"{wire.width}'b" + "".join(reversed([ "1" if s["input"][f"{name.str()}[{i}]"] else "0" for i in reversed(range(wire.width)) ])) for name, wire in self.wires["PI"].items()} for s in self.problem.samples ]