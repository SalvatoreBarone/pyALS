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
from pyosys import libyosys as ys
from .Utility import *


def check_for_optional_file(file_name):
	if file_name is not None and not os.path.exists(file_name):
		print(f"{file_name}: no such file.")
		exit()


def check_for_file(file_name):
	if not os.path.exists(file_name):
		print(f"{file_name}: no such file.")
		exit()


class YosysHelper:
	def __init__(self):
		self.design = ys.Design()
		self.sources = None
		self.top_module = None
		self.module_id = None
		self.PIs = None
		self.POs = None

	def load_ghdl(self):
		ys.run_pass("plugin -i ghdl", self.design)
		print("GHDL plugin loaded successfully")

	def read_sources(self, source_files, top_module):
		print("Reading source files...")
		self.sources = source_files
		self.top_module = top_module
		if isinstance(source_files, (list, tuple)):
			for s in source_files:
				YosysHelper.read_single_source(s, self.design)
				print(f"{s} read successfully")
		else:
			YosysHelper.read_single_source(source_files, self.design)
			print(f"{source_files} read successfully")
		ys.run_pass(f"hierarchy -check -top {self.top_module}", self.design)
		self.module_id = ys.IdString(f"\\{self.top_module}")
		original_wires, original_modules = YosysHelper.get_wires_and_modules(self.design)
		self.PIs = [(i, w.width) for i, w in original_modules[self.module_id]["PI"].items()]
		self.POs = [(i, w.width) for i, w in original_modules[self.module_id]["PO"].items()]

	def prep_design(self, cut_size):
		ys.run_pass(
			f"prep; flatten; splitnets -ports; synth -top {self.top_module}; flatten; clean -purge; synth -lut {str(cut_size)}",
			self.design)
		print(f"{cut_size}-LUT mapping performed successfully")

	def clean(self):
		ys.run_pass("tee -q clean -purge", self.design)

	def opt(self):
		ys.run_pass("tee -q opt", self.design)

	def reset(self):
		ys.run_pass("design -reset", self.design)

	def delete(self):
		ys.run_pass("delete", self.design)

	def save_design(self, design_name):
		ys.run_pass(f"tee -q design -save {design_name}", self.design)

	def load_design(self, design_name):
		ys.run_pass(f"tee -q design -load {design_name}", self.design)

	def show(self):
		ys.run_pass("show", self.design)

	def write_verilog(self, file_name):
		if not file_name.endswith(".v"):
			file_name += ".v"
		ys.run_pass(f"tee -q write_verilog -noattr {file_name}", self.design)
		print(f"{file_name} written successfully")

	def reverse_splitnets(self):
		module = self.get_module(self.module_id)
		if module is not None:
			self.add_PIs(module)
			self.add_POs(module)
			module.fixup_ports()

	def get_luts_set(self):
		luts_set = set()
		for module in self.design.selected_whole_modules_warn():
			for cell in module.selected_cells():
				if ys.IdString("\LUT") in cell.parameters:
					spec = cell.parameters[ys.IdString("\LUT")].as_string()[::-1]
					if negate(spec) not in luts_set and spec not in luts_set:
						luts_set.add(spec)
		return list(luts_set)

	def to_aig(self, configuration):
		for module in self.design.selected_whole_modules_warn():
			for cell in module.selected_cells():
				if ys.IdString("\LUT") in cell.parameters:
					YosysHelper.cell_to_aig(configuration, module, cell)

	def get_module(self, module_id):
		for module in self.design.selected_whole_modules_warn():
			if module.name == module_id:
				return module
		return None

	def get_PIs_and_Pos(self):
		wires = {"PI": {}, "PO": {}}
		module = self.get_module(self.module_id)
		if module is not None:
			for wire in module.selected_wires():
				if (wire.port_input):  # the wire is a primary input
					if wire.name not in wires["PI"]:
						wires["PI"][wire.name] = wire
				if (wire.port_output):  # the wire is a primary output
					if wire.name not in wires["PO"]:
						wires["PO"][wire.name] = wire
		return wires

	def add_PIs(self, module):
		wires, modules = YosysHelper.get_wires_and_modules(self.design)
		sigmap = ys.SigMap(module)
		for pi in self.PIs:
			if pi[1] > 1:
				wire = module.addWire(pi[0])
				wire.width = pi[1]
				wire.port_input = True
				old_pis = [modules[module.name]["PI"][ys.IdString(f"{pi[0].str()}[{i}]")] for i in range(pi[1])]
				for b, o in zip(sigmap(wire).to_sigbit_vector(), old_pis):
					o.port_input = False
					module.connect(ys.SigSpec(o), ys.SigSpec(b, 1))

	def add_POs(self, module):
		wires, modules = YosysHelper.get_wires_and_modules(self.design)
		sigmap = ys.SigMap(module)
		for po in self.POs:
			if po[1] > 1:
				wire = module.addWire(po[0])
				wire.width = po[1]
				wire.port_output = True
				old_pos = [modules[module.name]["PO"][ys.IdString(f"{po[0].str()}[{i}]")] for i in range(po[1])]
				for b, o in zip(sigmap(wire).to_sigbit_vector(), old_pos):
					o.port_output = False
					module.connect(ys.SigSpec(b, 1), ys.SigSpec(o))
					#driving_cell = YosysHelper.get_driving_cell(o)
					#if driving_cell is not None:
					#	driving_cell.unsetPort(ys.IdString("\Y"))
					#	driving_cell.setPort(ys.IdString("\Y"), ys.SigSpec(b, 1))

	@staticmethod
	def get_driving_cell(wire):
		for cell in wire.module.selected_cells():
			Y = cell.connections_[ys.IdString("\Y")]
			if Y.is_wire() and Y.as_bit().wire.name == wire.name:
				return cell
		return None

	@staticmethod
	def read_single_source(source_file, ys_design):
		check_for_file(source_file)
		name, extension = os.path.splitext(source_file)
		if extension == ".vhd":
			ys.run_pass(f"ghdl -a {source_file}", ys_design)
		elif extension == ".sv":
			ys.run_pass(f"read_verilog -sv {source_file}", ys_design)
		elif extension == ".v":
			ys.run_pass(f"read_verilog {source_file}", ys_design)
		elif extension == ".blif":
			ys.run_pass(f"read_blif {source_file}", ys_design)
		else:
			raise RuntimeError(f"Error parsing source file {source_file}: unknown extension ({extension})")

	@staticmethod
	def get_wires_and_modules(design):
		wires = {"PI": {}, "PO": {}}
		modules = {}
		for module in design.selected_whole_modules_warn():
			if module.name not in modules:
				modules[module.name] = {"PI": {}, "PO": {}}
			for wire in module.selected_wires():
				if (wire.port_input):  # the wire is a primary input
					if wire.name not in wires["PI"]:
						wires["PI"][wire.name] = {}
					wires["PI"][wire.name][module.name] = wire
					modules[module.name]["PI"][wire.name] = wire
				if (wire.port_output):  # the wire is a primary output
					if wire.name not in wires["PO"]:
						wires["PO"][wire.name] = {}
					wires["PO"][wire.name][module.name] = wire
					modules[module.name]["PO"][wire.name] = wire
		return wires, modules

	@staticmethod
	def cell_to_aig(configuration, module, cell):
		ax_cell_conf = configuration[cell.name.str()]
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
