import sys
import copy

def read_file(filename):
    with open(filename, 'r') as file:
        content = file.read()
        lines = content.split('\n')
        words_list = [line.split() for line in lines if line]
        return words_list

def hex_key(item):
    try:
        return int(item[2], 16)
    except ValueError:
        return item[2]




def sort_and_save(words_list, output_filename):
    header = ["Core", "Warp", "Addr", "FD", "Fs", "Fe", "D", "I", "OPs", "OPe", "FUs", "FUe", "WB", "End", "Inst"]
    #Sort option - 1st : Addr, 2nd : Core
    sorted_words_list = sorted(words_list, key=lambda x: (int(x[3], 16), int(x[0])))
    #sorted_words_list = sorted(words_list, key=hex_key)
    #sorted_words_list = sorted(words_list, key=lambda x: int(x[0]))
    #sorted_words_list = sorted(words_list, key=lambda x: (int(x[2], 16), int(x[0]))) 
    with open(output_filename, 'w') as file:
        header_output = ' '.join('{:<5}'.format(name) if idx < 4 else '{:<7}'.format(name) for idx, name in enumerate(header))
        file.write(header_output + '\n')

        inst_cycle_1 = []
        inst_cycle_2 = []

        for words in sorted_words_list:
            words_m = mark_stall(words,inst_cycle_1, inst_cycle_2)
            inst_cycle_2 = inst_cycle_1
            inst_cycle_1 = copy.deepcopy(words)
            
            formatted_output = ' '.join('{:<0}'.format(name) if name == " " or name == "*" else '{:<5}'.format(name) for idx, name in enumerate(words_m))
            file.write(formatted_output + '\n')
    
def mark_stall(numbers, inst_cycle_1, inst_cycle_2):
    Addr_idx = 2
    Fs_idx = 3
    I_idx = 6
    WB_idx = 12

    marked_numbers = []

    for i in range(len(numbers)):
        #Check Fetch stall for inter dependency
        if i == Fs_idx:
            try:
                diff = int(numbers[i]) - int(inst_cycle_1[i])
                #Issue 
                if diff > 1:
                    if int(numbers[i]) == int(inst_cycle_1[I_idx]):
                        marked_numbers.append("I")
                    elif int(numbers[i]) == int(inst_cycle_2[I_idx]):
                        #Check instruction fetched at same time
                        assert int(inst_cycle_1[Fs_idx]) == int(inst_cycle_2[Fs_idx])
                        marked_numbers.append("I")
                        #Control hazard delay 1 Cycle at fetch stage
                    elif int(numbers[i]) == (int(inst_cycle_1[I_idx]) + 1):
                        #Check Hazard
                        assert int(numbers[Addr_idx], 16) != int(inst_cycle_1[Addr_idx], 16) - 8
                        marked_numbers.append("H")
                    else:
                        marked_numbers.append("?")
                else :
                    marked_numbers.append("X")
            except IndexError:
                marked_numbers.append("X")

        marked_numbers.append(numbers[i])

        if i > 2:
            if i + 1 < len(numbers):
                try:
                    if numbers[i] == "0":
                        diff = int(numbers[i + 1]) - int(numbers[i - 1])
                    else:
                        diff = int(numbers[i + 1]) - int(numbers[i])

                    if diff <= 1:
                        marked_numbers.append(" ")
                    else:
                        marked_numbers.append("*")
                except ValueError:
                    marked_numbers.append(" ")

    return marked_numbers 

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
