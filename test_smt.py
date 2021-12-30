from src.ALSSMT import *
from pyosys import libyosys as ys
import math
import sys


def create_smt_miter(fun_spec, S, P, out_p, sel_var):
    m = ys.Module()
    m.name = ys.IdString("\\miter")

    aig_num_inputs = math.ceil(math.log2(len(fun_spec)))
    aig_vars = [[], [ys.SigSpec(ys.State.S0, 1)]]
    aig_and_ab = [[], []]
    aig_out = ys.SigSpec(m.addWire(ys.IdString("\\gate_output")))

    for i in range(aig_num_inputs):
        w = m.addWire(ys.IdString(f"\\gate_input_{i}"))
        w.port_input = True
        aig_vars[1].append(ys.SigSpec(w))

    if len(S[0]) == 0:
        for i in range(len(aig_vars[1])):
            not_y = m.addWire(ys.IdString(f"\\gate_not_{i}_y"))
            m.addNot(ys.IdString(f"\\gate_not_{i}_gate"), ys.SigSpec(aig_vars[1][i]), ys.SigSpec(not_y))
            aig_vars[0].append(ys.SigSpec(not_y))

        m.connect(ys.SigSpec(aig_out), aig_vars[out_p][sel_var])
    else:
        for i in range(len(S[0])):
            a = m.addWire(ys.IdString(f"\\gate_and_{i}_a"))
            b = m.addWire(ys.IdString(f"\\gate_and_{i}_b"))
            y = m.addWire(ys.IdString(f"\\gate_and_{i}_y"))
            m.addAnd(ys.IdString(f"\\gate_and_{i}_gate"), ys.SigSpec(a), ys.SigSpec(b), ys.SigSpec(y))
            aig_and_ab[0].append(ys.SigSpec(a))
            aig_and_ab[1].append(ys.SigSpec(b))
            aig_vars[1].append(ys.SigSpec(y))

        for i in range(len(aig_vars[1])):
            not_y = m.addWire(ys.IdString(f"\\gate_not_{i}_y"))
            m.addNot(ys.IdString(f"\\gate_not_{i}_gate"), ys.SigSpec(aig_vars[1][i]), ys.SigSpec(not_y))
            aig_vars[0].append(ys.SigSpec(not_y))

        for i in range(len(aig_and_ab[0])):
            for c in [0, 1]:
                p = P[c][i]
                s = S[c][i]
                m.connect(aig_and_ab[c][i], aig_vars[p][s])
        m.connect(ys.SigSpec(aig_out), aig_vars[out_p][-1])

    lut_a = ys.SigSpec([ys.SigChunk(ys.SigBit(sig)) for sig in aig_vars[1][1:aig_num_inputs+1]])
    lut_y = ys.SigSpec(m.addWire(ys.IdString("\\gold_lut_y")))
    state_spec = [ys.State.S0 if c == '0' else ys.State.S1 for c in fun_spec]
    m.addLut(ys.IdString("\\gold_lut_cell"), lut_a, lut_y, ys.Const(state_spec))

    xor_out = m.addWire(ys.IdString("\\miter_xor_out"))
    xor_out.port_output = True
    m.addXor(ys.IdString("\\miter_xor_gate"), aig_out, lut_y, ys.SigSpec(xor_out))

    m.fixup_ports()
    return m


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 test_ALSSMT.py [fun_spec]")
        exit()

    fun_spec = sys.argv[1]

    if math.log2(len(fun_spec)) != math.ceil(math.log2(len(fun_spec))):
        print("Error: function specification length must be a power of two")
        exit()

    for c in fun_spec:
        if c not in ['0', '1']:
            print("Error: only '0' and '1' are allowed in function specification")
            exit()
    aig = ALSSMT_Boolector(fun_spec, 2, 120)
    tup = aig.synthesize()
    print(*tup)


    d = ys.Design()
    miter = create_smt_miter(*tup)
    d.add(miter)
    ys.run_pass("hierarchy -check -top miter", d)
    ys.run_pass("clean -purge", d)
    ys.run_pass("sat -prove miter_xor_out 0", d)
    ys.run_pass("show", d)


if __name__ == '__main__':
    main()