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
import imp
  
  
# dynamic import 
def dynamic_import(module_name, object_name):
    try:
        # find_module() method is used to find the module and return its description and path
        fp, path, desc = imp.find_module(module_name)
        # load_modules() loads the module dynamically ans takes the filepath module and description as parameter
        requested_module = imp.load_module(module_name, fp, path, desc)
        requested_object = imp.load_module(f"{module_name}.{object_name}", fp, path, desc)
        #return requested_module, requested_object
        return getattr(requested_object, object_name)
    except Exception as e:
        print(e)
        exit()

    
