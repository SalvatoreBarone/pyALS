# pyALS
Python implementation of the "Catalog-based Aig-rewriting Approximate Logic Synthesis" technique.

## Installation
pyALS has quite a lot of dependencies. You need to install Yosys (and its dependencies), GHDL (and, again, its dependencies), and so forth.
Before you get a headache, follow this guide step by step. I'm sure it will be very helpful.
The guide has been tested on Debian 11.

### Preliminaries
You need to install some basic dependencies. So, run
```
# apt-get install --fix-missing -y git bison clang cmake curl flex fzf g++ gnat gawk libffi-dev libreadline-dev libsqlite3-dev  libssl-dev make p7zip-full pkg-config python3 python3-dev python3-pip tcl-dev vim-nox wget xdot zlib1g-dev zlib1g-dev zsh libboost-dev libboost-filesystem-dev libboost-graph-dev libboost-iostreams-dev libboost-program-options-dev libboost-python-dev libboost-serialization-dev libboost-system-dev libboost-thread-dev
```

You also need to create some symbolic links.
```
# ln -s /usr/lib/x86_64-linux-gnu/libtinfo.so /usr/lib/x86_64-linux-gnu/libtinfo.so.5
# ln -fs /usr/lib/x86_64-linux-gnu/libboost_python39.a /usr/lib/x86_64-linux-gnu/libboost_python.a
# ln -fs /usr/lib/x86_64-linux-gnu/libboost_python39.so /usr/lib/x86_64-linux-gnu/libboost_python.so
```
Please, kindly note you are required to amend any differences concerning the python version. I'm using python 3.9 here.


### Installing Yosys
First, you need to clone Yosys from its public repository
```
$ git clone https://github.com/YosysHQ/yosys
```
This will create a ```yosys``` sub-directory inside your current directory. Now move into the ```yosys``` directory, and create a ```Makefile.conf``` file.
```
$ cd yosys
$ touch Makefile.conf
```
Paste the following into the ```Makefile.conf``` file.
```
CONFIG := clang
CXXFLAGS += -I/usr/include/python3.9/ -fPIC
ENABLE_LIBYOSYS=1
ENABLE_PYOSYS=1
PYTHON_EXECUTABLE=/usr/bin/python3 
PYTHON_VERSION=3.9 
PYTHON_CONFIG=python3-config 
PYTHON_DESTDIR=/usr/local/lib/python3.9/dist-packages
BOOST_PYTHON_LIB=/usr/lib/x86_64-linux-gnu/libboost_python.so -lpython3.9
```
Please, kindly note you are required to amend any differences concerning the python version. I'm using python 3.9 here.
Now you need to a little quick fix to yosys: edit the ```kernel/yosys.cc``` file, searching for the definition of the 
```run_pass``` function. Comment the call to the ```log``` function as follows.
```
void run_pass(std::string command, RTLIL::Design *design)
{
	if (design == nullptr)
		design = yosys_design;

	//log("\n-- Running command `%s' --\n", command.c_str());

	Pass::call(design, command);
}
```
This will remove redundant logs while running the optimizer.
Ok, now you are ready.
```
$ make -j `nproc`
# make install
# ln -s `realpath yosys` /usr/bin
# ln -s `realpath yosys-abc` /usr/bin
```

### Installing GHDL
GHDL and its Yosys plugin are required to process VHDL-encoded designs. 
Please, kindly note that you will be able to successfully install the GHDL Yosys plugin only if you successfully installed Yosys. 
Let's install GHDL first. As always, you need to clone GHDL from ist public repository and compile it.
```
$ git clone https://github.com/ghdl/ghdl.git
$ cd ghdl
$ ./configure --prefix=/usr/local
$ make
# make install
```
The same applies to its Yosys plugin. 
```
$ git clone https://github.com/ghdl/ghdl-yosys-plugin.git
$ cd ghdl-yosys-plugin
$ make
# make install
```

### Installing python dependencies
You're almost done, the last step is to install python dependencies. It's quite simple, and you just need to issue the following command from within the pyALS directory.
```
pip3 install -r requirements.txt 
```

## Running pyALS
In order to run pyALS, only a few cli parameters must be specified, since most of the configuration is done through a configuration file.
```
pyALS [-h] [--config CONFIG] [--source SOURCE] [--weights WEIGHTS] [--top TOP] [--output OUTPUT]

optional arguments:
  -h, --help         show this help message and exit
  --config CONFIG    path of the configuration file
  --source SOURCE    specify the input HDL source file
  --weights WEIGHTS  specify weights for AWCE evaluation
  --top TOP          specify the top-module name
  --output OUTPUT    Output directory. Everything will be placed there.

```

For instance, if you want to run ALS on ```mult_2bit.sv```
```
./pyALS --config config.ini --source mult_2_bit.sv --top mult_2_bit --output prova --weights output_weights.txt
```

### The configuration file
Here, I report the basic structure of a configuration file. You will find it within the pyALS root directory.
```
[als]
cut_size = 4              ; specifies the "k" for AIG-cuts, or, alternatively, the k-LUTs for LUT-mapping during cut-enumeration
catalog = lut_catalog.db ; This is the path of the file where synthesized Boolean functions are stored. You can find a ready to use cache at git@github.com:SalvatoreBarone/LUTCatalog.git
solver = btor            ; SAT-solver to be used. It can be either btor (Boolector) or z3 (Z3-solver)
timeout = 60000          ; Timeout (in ms) for the Exact synthesis process. You don't need to change its default value.

[error]
metric = med             ; Error metric to be used during Design-Space exploration. It can be "eprob", "awce" or "med", for error-probability, absolute worst-case error or mean error distance, respectively
threshold = 1            ; The error threshold
vectors = 0              ; The number of test vectors for error assessment. "0" will unlock exhaustive evaluation.

[hardware]
metric = gates, depth    ; hardware metric(s) to be optimized (gates, depth, area, power). Note that area and power refer to ASIC, and require the user to specify a liberty file for tech-map. 
liberty = gscl45nm.lib   ; liberty file for technology mapping (if area and/or power metric are to be minimizer)

[amosa]
archive_hard_limit = 30         ; Archive hard limit for the AMOSA optimization heuristic, see [1]
archive_soft_limit = 50         ; Archive soft limit for the AMOSA optimization heuristic, see [1]
archive_gamma = 2               ; Gamma parameter for the AMOSA optimization heuristic, see [1]
hill_climbing_iterations = 250  ; the number of iterations performed during the initial hill-climbing refinement, see [1];
initial_temperature = 500       ; Initial temperature of the matter for the AMOSA optimization heuristic, see [1]
final_temperature = 0.000001    ; Final temperature of the matter for the AMOSA optimization heuristic, see [1]
cooling_factor =  0.9           ; It governs how quickly the temperature of the matter decreases during the annealing process, see [1]
annealing_iterations = 600      ; The amount of refinement iterations performed during the main-loop of the AMOSA heuristic, see [1]
```

Please kindly note you have to specify the path of the file where synthesized Boolean functions are stored. You can find a ready to use cache at ```git@github.com:SalvatoreBarone/LUTCatalog.git```.
If you do not want to use the one I mentioned, pyALS will perform exact synthesis as needed.

## References
1. Bandyopadhyay, S., Saha, S., Maulik, U., & Deb, K. (2008). A simulated annealing-based multiobjective optimization algorithm: AMOSA. IEEE transactions on evolutionary computation, 12(3), 269-283.
