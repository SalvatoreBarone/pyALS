import imp, sys
  
  
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

    
