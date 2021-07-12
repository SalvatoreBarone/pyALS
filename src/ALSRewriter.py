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

from pyosys import libyosys as ys
from distutils.dir_util import copy_tree, mkpath
from distutils.file_util import copy_file

class ALSRewriter:
  """
  @brief Instantiate a new rewriter

  @param [in] design
              A Yosys design instance

  @param [in] configurations
              A list of configurations. Each configuration is a list of dict in which each dict entry is in the 
              following format
              {"name" : lut_name, "spec" : lut specification, "gates" : and-gates}

  @param [in] out_directory
              The output directory, i.e. the directory in which all files will be placed
  """
  def __init__(self, design, configurations, out_directory):
    self.__design = design
    self.__configurations = configurations
    self.__outdir = out_directory
    mkpath(self.__outdir)
    ys.run_pass("write_ilang {dir}/{name}.ilang".format(dir = self.__outdir, name = "reference"), self.__design)

  def rewrite(self):
    for conf, i in zip(self.__configurations, range(len(self.__configurations))):
      for module in self.__design.selected_whole_modules_warn():
        for cell in module.selected_cells():
          if ys.IdString("\LUT") in cell.parameters:
            # get the specification for the current cell
            c = [ c for c in conf if c["name"] == cell.name.str() ][0]
            print("cell: {name}; spec: {spec}; new spec {newspec}".format(name = c["name"], spec = cell.parameters[ys.IdString("\LUT")], newspec = c["spec"]))
            cell.setParam(ys.IdString("\LUT"), ys.Const.from_string(c["spec"]))
      ys.run_pass("write_ilang {dir}/variant_{i}.ilang".format(dir = self.__outdir, i = i), self.__design)