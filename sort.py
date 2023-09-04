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


class p_check(Enum):
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

class p_stall(Enum):
    L1D = len(p_check)
    L2 = auto()
    Pipe = auto()
    

def read_file(filename):
    with open(filename, 'r') as file:
        content = file.read()
        lines = content.split('\n')
        lines_list = [line.split() for line in lines if line]
        return lines_list


def sort_lines(lines):
    #Sort option - 1st : Fetch 2nd : Addr, 3rd : Core
#    sorted_lines = sorted(lines, key=lambda x: (int(x[p_check.Fs.value]), 
#        int(x[p_check.Addr.value], 16), int(x[p_check.Core.value])))
    sorted_lines = sorted(lines, key=lambda x: (
        int(x[p_check.Fs.value]), 
#        int(x[p_check.Core.value]), 
        int(x[p_check.Warp.value]),
        int(x[p_check.Addr.value], 16),
        ))
    return sorted_lines

def get_latency_idx(line):
    latency_idx = len(p_check) + len(p_stall)
    
    return latency_idx

#Help to get register index in the line list
def get_out_idx(line):
    out_idx = get_latency_idx(line) + 1

    return out_idx

def get_in_idx(line):
    out_idx = get_out_idx(line)
    outcount = int(line[out_idx])

    return out_idx + outcount + 1
    

def get_inst_idx(line):
    return get_in_idx(line) + 1



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

    def intra_search(self, warp_idx, value, position, width = 0, base = 10):
        if width :
            lines = self.matrix[warp_idx][-2 : -1 * width -2  : -1]
        else :
            lines = self.matrix[warp_idx][::-1]

        for line in lines :
            if int(line[position], base) == value :
                return line

        return False
    
    def is_empty(self) :
        if self.matrix.count == 0 :
            return True
        else :
            return False


def sort_and_save(lines, output_filename, args):
    lines = sort_lines(lines)

    with open(output_filename, 'w') as file:
        warp_cycle_list = classified_list()

        for idx, line in enumerate(lines):
            if line[p_check.Core.value] == '0' and line[p_check.Warp.value] == '0':

                inst_cycle = mark_stall(line, idx, lines, args, warp_cycle_list)
                
                formatted_output = ' '.join(inst_cycle) + ' '
                file.write(formatted_output)

                if args.latency :
                    file.write(line[get_latency_idx(line)] + ' ')

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
    warp_idx = int(inst_cycle[p_check.Warp.value])

    warp_cycle_list.add(warp_idx, inst_cycle)

    inst_cycle_m = [] 

    #Insert Core_idx, Warp_idx, Addr
    for i in range(0, p_check.Addr.value + 1):
        inst_cycle_m.append(inst_cycle[i].rjust(MAX_INF_WITDH))
  

    #Insert Cycle
    for i in range(p_check.Fs.value, p_check.C.value + 1):

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
        if i == p_check.Fs.value:
            #Issue 
            if inst_cycle[p_check.Addr.value] != '0' :
                Fs_cycle = int(inst_cycle[i])
                #Check for data hazard
                prev_addr = int(inst_cycle[p_check.Addr.value], 16) - 8
                if warp_cycle_list.intra_search(warp_idx, Fs_cycle, p_check.Fs.value, 1):
                    inst_cycle_m.append("X")
                elif warp_cycle_list.intra_search(warp_idx, Fs_cycle, p_check.I.value, 1):
                    inst_cycle_m.append("I")
                    #Check Hazard
                elif not warp_cycle_list.intra_search(warp_idx, prev_addr, p_check.Addr.value, 1, 16):
                    inst_cycle_m.append("H")
                else:
                    inst_cycle_m.append("N")
            else :
                inst_cycle_m.append("X")

        inst_cycle_m.append(str(inst_cycle[i]).rjust(MAX_CYCLE_WITDH))

        if args.diff:
            if i != p_check.C.value:
                inst_cycle_m.append(("+" + str(diff)).rjust(MAX_DIFF_WITDH))
         
        if i == p_check.D.value:
            if not warp_cycle_list.is_empty() and diff > 1:
                I_cycle = int(inst_cycle[i+1])
                if int(inst_cycle[p_stall.Pipe.value]) == True:
                    inst_cycle_m.append("P")
                elif warp_cycle_list.intra_search(warp_idx, I_cycle - 1, p_check.I.value, 1):
                    inst_cycle_m.append("I")
                elif warp_cycle_list.intra_search(warp_idx, I_cycle, p_check.WB.value, 2):
                    inst_cycle_m.append("W")
                else:
                    inst_cycle_m.append("?")
            else :
                inst_cycle_m.append("X")
        
        if i == p_check.I.value:
            if diff > 1 :
                inst_cycle_m.append("F")
            else :
                inst_cycle_m.append(" ")

        if i == p_check.OPs.value:
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

        if i == p_check.OPe.value:
            if int(inst_cycle[i+1]) == int(inst_cycles[idx-1][p_check.MemI.value]) and diff > 0:
                inst_cycle_m.append("M")
            else :
                inst_cycle_m.append(" ")

        if i == p_check.FUs.value:
            op_core = op.split('.')[0]
            if op_core != "ld" and op_core != "st":
                if diff == int(inst_cycle[get_latency_idx(inst_cycle)]) + 1:
                    inst_cycle_m.append(" ")
                else:
                    inst_cycle_m.append("?")
            else :
                if diff == int(inst_cycle[get_latency_idx(inst_cycle)]):
                    inst_cycle_m.append(" ")
                else:
                    inst_cycle_m.append("C")

        if i == p_check.MemI.value:
            #Check only st instruction
            if inst_cycle[p_check.MemI.value] != '0' and diff != 0:
                if op.split('.')[1] == "global" :
                    if cal_cache_latency(inst_cycle) == diff :
                        inst_cycle_m.append(" ")
                    else :
                        inst_cycle_m.append("?")
#                else :
#                    if 0 == inst_cycle[p_check.MemI.value] :
#                        inst_cycle_m.append("O")
#                    else :
#                        inst_cycle_m.append("?")
            else :
                inst_cycle_m.append(" ")

        if i == p_check.FUe.value or i == p_check.WB.value :
            if diff > 1 :
                inst_cycle_m.append("?")
                
    return inst_cycle_m

def cal_cache_latency(line) :
    latency = L1_LATENCY

    if line[p_stall.L1D.value] == "1" :# Is L1D MISS
        latency += L2_LATENCY + INTER_LATENCY
    #if line[p_stall.L2.value] == "1" :

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
