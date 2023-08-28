import sys
import copy
import argparse
from enum import Enum, auto

MAX_CYCLE_WITDH = 5
MAX_DIFF_WITDH = 5
MAX_INF_WITDH = 3

L1_LATENCY = 20
L2_LATENCY = 160
INTER_LATENCY = 8


class Position(Enum):
      Core  = 0
      Warp = auto()
      Addr = auto()
      Fs = auto()
      Fe = auto()
      D = auto()
      I = auto()
      OPs = auto()
      OPe = auto()
      FUs = auto()
      MemI = auto()
      FUe = auto()
      WB = auto()
      C = auto()
      latency = auto()


def read_file(filename):
    with open(filename, 'r') as file:
        content = file.read()
        lines = content.split('\n')
        lines_list = [line.split() for line in lines if line]
        return lines_list


def sort_lines(lines):
    #Sort option - 1st : Fetch 2nd : Addr, 3rd : Core
    sorted_lines = sorted(lines, key=lambda x: (int(x[Position.Fs.value]), 
        int(x[Position.Addr.value], 16), int(x[Position.Core.value])))
    return sorted_lines


#Help to get register index in the line list
def get_out_idx(line):
    out_idx = Position.latency.value + 1

    return out_idx

def get_in_idx(line):
    out_idx = get_out_idx(line)
    outcount = int(line[out_idx])

    return out_idx + outcount + 1
    

def get_inst_idx(line):
    in_idx = get_in_idx(line)
    incount = int(line[in_idx])

    return in_idx + incount + 1




def sort_and_save(lines, output_filename, args):
    lines = sort_lines(lines)

    with open(output_filename, 'w') as file:

        line_p = []
        for idx, line in enumerate(lines):

            inst_cycle = mark_stall(line, idx, lines, args)
            
            formatted_output = ' '.join(inst_cycle) + ' '
            file.write(formatted_output)
            line_p = line

            if args.latency :
                file.write(line[Position.latency.value] + ' ')

            if args.inst :
                inst = line[get_inst_idx(line):]
                file.write(' '.join(inst) + '\n')
            else :
                file.write('\n')


def get_op(line):
    inst_idx = get_inst_idx(line)
    inst = line[inst_idx]
    
    if(inst[0] == "@") :
        inst = line[inst_idx + 1]

    return inst


def mark_stall(inst_cycle, idx, inst_cycles, args):

    op = get_op(inst_cycle)

    inst_cycle_m = [] 

    #Insert Core_idx, Warp_idx, Addr
    for i in range(0, Position.Addr.value + 1):
        inst_cycle_m.append(inst_cycle[i].rjust(MAX_INF_WITDH))
  

    #Insert Cycle
    for i in range(Position.Fs.value, Position.C.value + 1):

        # Get Stall length
        if int(inst_cycle[i]) != 0 :
            if int(inst_cycle[i+1]) != 0 :
                diff = int(inst_cycle[i+1]) - int(inst_cycle[i])
            else :
                j = 1
                while not int(inst_cycle[i + j]):
                    j += 1
                diff = int(inst_cycle[i + j]) - int(inst_cycle[i])
        else :
            diff = 0 
        
        #Check Fetch stall for inter dependency
        if i == Position.Fs.value:
            #Issue 
            if idx != 0 :
                if int(inst_cycle[i]) == int(inst_cycles[idx-1][Position.Fs.value]):
                    inst_cycle_m.append("X")
                elif int(inst_cycle[i]) == int(inst_cycles[idx-1][Position.I.value]):
                    inst_cycle_m.append("I")
                elif int(inst_cycle[i]) == (int(inst_cycles[idx-1][Position.I.value]) + 1):
                    #Check Hazard
                    assert int(inst_cycle[Position.Addr.value], 16) != int(inst_cycles[idx-1][Position.Addr.value], 16) - 8
                    inst_cycle_m.append("H")
                else:
                    inst_cycle_m.append("?")
            else :
                inst_cycle_m.append("X")

        inst_cycle_m.append(str(inst_cycle[i]).rjust(MAX_CYCLE_WITDH))

        if args.diff:
            if i != Position.C.value:
                inst_cycle_m.append(("+" + str(diff)).rjust(MAX_DIFF_WITDH))
         
        if i == Position.D.value:
            if idx != 0 and diff > 1:
                if int(inst_cycle[i+1]) == int(inst_cycles[idx-1][Position.WB.value]) \
                        or int(inst_cycle[i+1]) == int(inst_cycles[idx-2][Position.WB.value]):
                    inst_cycle_m.append("W")
                elif int(inst_cycle[i+1]) == int(inst_cycles[idx-1][Position.I.value])+1:
                    inst_cycle_m.append("I")
                else:
                    inst_cycle_m.append("?")
            else :
                inst_cycle_m.append("X")

        if i == Position.OPs.value:
            op_split = op.split('.')
            if bool(int(inst_cycle[get_in_idx(inst_cycle)])) != bool(diff) :
                if op_split[0] == "ld":
                    if op_split[1] != "param":
                        inst_cycle_m.append(" ")
                        continue
                inst_cycle_m.append("?")
            elif diff > 2 :
                inst_cycle_m.append("l")
            else :
                inst_cycle_m.append(" ")

        if i == Position.FUs.value:
            op_core = op.split('.')[0]
            if op_core != "ld" and op_core != "st":
                if diff == int(inst_cycle[Position.latency.value]) + 1:
                    inst_cycle_m.append("O")
                else:
                    inst_cycle_m.append("?")
            else :
                if diff == int(inst_cycle[Position.latency.value]):
                    inst_cycle_m.append("O")
                else:
                    inst_cycle_m.append("?")


            
    return inst_cycle_m

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--diff', action='store_true', help='Show cycle diff')
    parser.add_argument('--inst', action='store_true', help='Show instruction')
    parser.add_argument('--latency', action='store_true', help='Show latency')
    parser.add_argument('input_filename', help='Input filename')
    parser.add_argument('output_filename', help='Output filename')

    args = parser.parse_args()


    input_filename = args.input_filename
    output_filename = args.output_filename

    words_list = read_file(input_filename)
    sort_and_save(words_list, output_filename, args)
    print("Sorting completed. Result saved to", output_filename)

if __name__ == "__main__":
    main()
