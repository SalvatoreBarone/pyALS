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
import contextlib, sys, os, importlib
  
  
# dynamic import 
def dynamic_import(module_name):
    # Fast path: see if the module has already been imported.
    with contextlib.suppress(KeyError):
        return sys.modules[module_name]
    basename = os.path.basename(module_name)
    path = os.path.dirname(module_name)
    spec = importlib.machinery.PathFinder.find_spec(basename, [path])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[spec.name] = module
    return module

    
