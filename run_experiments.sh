#!/bin/bash
./pyALS --config config_gen_ers_1000.ini --source Evaluation/LGSynth91/Verilog/cmlexamples/alu4_orig.v --top alu4_cl --output alu_4
./pyALS --config config_gen_ers_1000.ini --source Evaluation/LGSynth91/Verilog/cmlexamples/cm163a_orig.v --top CM163  --output cm163
./pyALS --config config_gen_ers_1000.ini --source Evaluation/LGSynth91/Verilog/cmlexamples/count_orig.v --top count --output count
./pyALS --config config_gen_ers_1000.ini --source Evaluation/LGSynth91/Verilog/cmlexamples/frg1_orig.v --top frg1 --output frg1
./pyALS --config config_gen_ers_1000.ini --source Evaluation/LGSynth91/Verilog/cmlexamples/term1_orig.v --top term1 --output term1
./pyALS --config config_gen_ers_1000.ini --source Evaluation/LGSynth91/Verilog/cmlexamples/unreg_orig.v --top unreg --output unreg
./pyALS --config config_gen_ers_1000.ini --source Evaluation/LGSynth91/Verilog/cmlexamples/x2_orig.v --top x2 --output x2
./pyALS --config config_gen_ers_1000.ini --source Evaluation/LGSynth91/Verilog/cmlexamples/z4ml_orig.v --top z4ml --output z4ml
./pyALS --config config_adder_awce_full_64.ini --source Evaluation/chandrasekaran/HommaArith/UBHCA_7_0_7_0.v --top UBHCA_7_0_7_0 --output UBHCA_7_0_7_0  --weights Evaluation/chandrasekaran/HommaArith/adder_7_weights.txt
./pyALS --config config_adder_awce_full_64.ini --source Evaluation/chandrasekaran/HommaArith/UBRCL_7_0_7_0.v --top UBRCL_7_0_7_0 --output UBRCL_7_0_7_0  --weights Evaluation/chandrasekaran/HommaArith/adder_7_weights.txt
./pyALS --config config_adder_awce_full_64.ini --source Evaluation/chandrasekaran/HommaArith/UBRCA_7_0_7_0.v --top UBRCA_7_0_7_0 --output UBRCA_7_0_7_0  --weights Evaluation/chandrasekaran/HommaArith/adder_7_weights.txt
./pyALS --config config_adder_awce_5000_256.ini --source Evaluation/chandrasekaran/HommaArith/UBCSe_15_0_15_0.v --top UBCSe_15_0_15_0 --output UBCSe_15_0_15_0  --weights Evaluation/chandrasekaran/HommaArith/adder_15_weights.txt
./pyALS --config config_adder_awce_5000_256.ini --source Evaluation/chandrasekaran/HommaArith/UBHCA_15_0_15_0.v --top UBHCA_15_0_15_0 --output UBHCA_15_0_15_0  --weights Evaluation/chandrasekaran/HommaArith/adder_15_weights.txt
./pyALS --config config_adder_awce_5000_256.ini --source Evaluation/chandrasekaran/HommaArith/UBVCSkA_15_0_15_0.v --top UBVCSkA_15_0_15_0 --output UBVCSkA_15_0_15_0  --weights Evaluation/chandrasekaran/HommaArith/adder_15_weights.txt
./pyALS --config config_mul_awce_full_128.ini --source Evaluation/chandrasekaran/HommaArith/wallace.v --top wallace --output wallace  --weights Evaluation/chandrasekaran/HommaArith/wallace_weights.txt
./pyALS --config config_mul_awce_full_128.ini --source Evaluation/chandrasekaran/HommaArith/dadda_Multiplier_7_0_7_000.v --top Multiplier_7_0_7_000 --output dadda_Multiplier_7_0_7_000  --weights Evaluation/chandrasekaran/HommaArith/multiplier_7_weights.txt
./pyALS --config config_mul_awce_full_128.ini --source Evaluation/chandrasekaran/HommaArith/array_Multiplier_7_0_7_000.v --top Multiplier_7_0_7_000 --output array_Multiplier_7_0_7_000_full --weights Evaluation/chandrasekaran/HommaArith/mul_7_weights.txt
