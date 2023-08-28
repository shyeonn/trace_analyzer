import sys
import copy
from enum import Enum, auto

MAX_CYCLE_WITDH = 5
MAX_DIFF_WITDH = 5
MAX_INF_WITDH = 3

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
def get_idx(line):
    out_idx = Position.latency + 1
    outcount = inform[out_idx]

    in_idx = out_idx + outcount + 1
    inst_idx = in_idx + incount + 1

    return out_idx, in_idx, inst_idx


def sort_and_save(lines, output_filename):
    lines = sort_lines(lines)

    with open(output_filename, 'w') as file:
#        header_output = ' '.join('{:<8}'.format(name) if idx == 4 or idx == 5 or idx == 8 or idx == 9 else '{:<6}'.format(name) for idx, name in enumerate(header))
#        file.write(header_output + '\n')

        line_p = []
        for line in lines:
            inst_cycle = mark_stall(line, line_p)
            
            formatted_output = ' '.join(inst_cycle) + '\n'
            file.write(formatted_output)
            line_p = line

            #file.write(' '.join(inform) + '\n')

    
def mark_stall(inst_cycle, inst_cycle_p):

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
            if len(inst_cycle_p) :
                if int(inst_cycle[i]) == int(inst_cycle_p[Position.Fs.value]):
                    inst_cycle_m.append("X")
                elif int(inst_cycle[i]) == int(inst_cycle_p[Position.I.value]):
                    inst_cycle_m.append("I")
                elif int(inst_cycle[i]) == (int(inst_cycle_p[Position.I.value]) + 1):
                    #Check Hazard
                    assert int(inst_cycle[Position.Addr.value], 16) != int(inst_cycle_p[Position.Addr.value], 16) - 8
                    inst_cycle_m.append("H")
                else:
                    inst_cycle_m.append("?")
            else :
                inst_cycle_m.append("X")

        inst_cycle_m.append(str(inst_cycle[i]).rjust(MAX_CYCLE_WITDH))

        if __debug__:
            if i != Position.C.value:
                inst_cycle_m.append(("+" + str(diff)).rjust(MAX_DIFF_WITDH))
        

#        if i > 2:
#            if i + 1 < len(numbers):
#                try:
#                    if numbers[i] == "0":
#                        diff = 0
#                    elif numbers[i+1] == "0":
#                        diff = int(numbers[i + 2]) - int(numbers[i])
#                    else:
#                        diff = int(numbers[i + 1]) - int(numbers[i])
#
#                    #Issue index
#                    if i + 1 == I_idx:
#                        if diff <= 1:
#                            marked_numbers.append("X")
#                        else :
#                            # 1 issue/cycle in warp
#                            if int(numbers[i+1]) == int(inst_cycle_1[I_idx]) + 1:
#                                marked_numbers.append("I")
#                            # Check dependency
#                            elif int(numbers[i+1]) == int(inst_cycle_1[WB_idx]):
#                                marked_numbers.append("W")
#                            elif int(numbers[i+1]) == int(inst_cycle_2[WB_idx]):
#                                marked_numbers.append("W")
#                            else : 
#                                marked_numbers.append("?")
#                    #Fs index
#                    elif i + 1 == FUs_idx :
##                        if diff == 2 :
##                            marked_numbers.append("*")
##                        else :
#                        marked_numbers.append("+" + str(diff))
#                    elif i + 1 == FUe_idx :
#                        marked_numbers.append("+" + str(diff+1))
#
#                    else :
#                        if diff <= 1:
#                            marked_numbers.append(" ")
#                        else:
#                            marked_numbers.append("*")
#                except ValueError:
#                    marked_numbers.append(" ")
    return inst_cycle_m

def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py input_filename output_filename")
        return

    input_filename = sys.argv[1]
    output_filename = sys.argv[2]

    words_list = read_file(input_filename)
    sort_and_save(words_list, output_filename)
    print("Sorting completed. Result saved to", output_filename)

if __name__ == "__main__":
    main()
