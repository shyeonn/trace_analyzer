import sys
import copy
import argparse
from enum import Enum, auto

MAX_CYCLE_WITDH = 5
MAX_DIFF_WITDH = 4
MAX_INF_WITDH = 3

MAX_WARP_SIZE = 32

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

class Cache(Enum):
    L1D = 0
    L2 = auto()



def read_file(filename):
    with open(filename, 'r') as file:
        content = file.read()
        lines = content.split('\n')
        lines_list = [line.split() for line in lines if line]
        return lines_list


def sort_lines(lines):
    #Sort option - 1st : Fetch 2nd : Addr, 3rd : Core
#    sorted_lines = sorted(lines, key=lambda x: (int(x[Position.Fs.value]), 
#        int(x[Position.Addr.value], 16), int(x[Position.Core.value])))
    sorted_lines = sorted(lines, key=lambda x: (
        int(x[Position.Fs.value]), 
#        int(x[Position.Addr.value], 16),
#        int(x[Position.Core.value]), 
#        int(x[Position.Warp.value]),
        ))
    return sorted_lines


#Help to get register index in the line list
def get_out_idx(line):
    out_idx = Position.latency.value + 1

    return out_idx

def get_in_idx(line):
    out_idx = get_out_idx(line)
    outcount = int(line[out_idx])

    return out_idx + outcount + 1
    

def get_cache_idx(line):
    in_idx = get_in_idx(line)
    incount = int(line[in_idx])

    return in_idx + incount + 1


def get_inst_idx(line):
    return get_cache_idx(line) + len(Cache)



class classified_list:
    def __init__(self):
        self.matrix = []
        self.create_matrix(MAX_WARP_SIZE)
    
    def create_matrix(self, row_size):
        for i in range(row_size):
            row = []  
            self.matrix.append(row)
    
    def add(self, warp_idx, cycle_list):
        self.matrix[warp_idx].append(cycle_list)

    def intra_search(self, warp_idx, value, position, width = 0):
        if width :
            lines = self.matrix[warp_idx][-2 : -1 * width -2  : -1]
        else :
            lines = self.matrix[warp_idx][::-1]

        for line in lines :
            if int(line[position]) == value :
                return line

        return False


def sort_and_save(lines, output_filename, args):
    lines = sort_lines(lines)

    with open(output_filename, 'w') as file:
        warp_cycle_list = classified_list()

        for idx, line in enumerate(lines):
            if line[Position.Core.value] == '0' :

                inst_cycle = mark_stall(line, idx, lines, args, warp_cycle_list)
                
                formatted_output = ' '.join(inst_cycle) + ' '
                file.write(formatted_output)

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


def mark_stall(inst_cycle, idx, inst_cycles, args, warp_cycle_list):

    op = get_op(inst_cycle)
    warp_idx = int(inst_cycle[Position.Warp.value])

    warp_cycle_list.add(warp_idx, inst_cycle)

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
            if inst_cycle[Position.Addr.value] != '0' :
                Fs_cycle = int(inst_cycle[i])
                if warp_cycle_list.intra_search(warp_idx, Fs_cycle, Position.Fs.value, 1):
                    inst_cycle_m.append("X")
                elif warp_cycle_list.intra_search(warp_idx, Fs_cycle, Position.I.value, 1):
                    inst_cycle_m.append("I")
                    #Check Hazard
#                    if int(inst_cycle[Position.Addr.value], 16) != \
#                    int(inst_cycles[idx-1][Position.Addr.value], 16) - 8 :
                    #inst_cycle_m.append("H")
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

        if i == Position.OPe.value:
            if int(inst_cycle[i+1]) == int(inst_cycles[idx-1][Position.MemI.value]) and diff > 0:
                inst_cycle_m.append("M")
            else :
                inst_cycle_m.append(" ")

        if i == Position.FUs.value:
            op_core = op.split('.')[0]
            if op_core != "ld" and op_core != "st":
                if diff == int(inst_cycle[Position.latency.value]) + 1:
                    inst_cycle_m.append(" ")
                else:
                    inst_cycle_m.append("?")
            else :
                if diff == int(inst_cycle[Position.latency.value]):
                    inst_cycle_m.append(" ")
                else:
                    inst_cycle_m.append("C")

        if i == Position.MemI.value:
            #Check only st instruction
            if inst_cycle[Position.MemI.value] != '0' and diff != 0:
                if op.split('.')[1] == "global" :
                    if cal_latency(inst_cycle) == diff :
                        inst_cycle_m.append(" ")
                    else :
                        inst_cycle_m.append("?")
#                else :
#                    if 0 == inst_cycle[Position.MemI.value] :
#                        inst_cycle_m.append("O")
#                    else :
#                        inst_cycle_m.append("?")
            else :
                inst_cycle_m.append(" ")

        if i == Position.FUe.value or i == Position.WB.value :
            if diff > 1 :
                inst_cycle_m.append("?")
                
    return inst_cycle_m

def cal_latency(line) :
    latency = L1_LATENCY

    cache_idx = get_cache_idx(line)
    if line[cache_idx] == "1" :# Is L1D MISS
        latency += L2_LATENCY + INTER_LATENCY
    #if line[cache_idx + 1] == "1" :

    return latency



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
