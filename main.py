import random
import sys
import math
import subprocess
import re
import time
from functools import reduce
from Condition import Condition


# Speedup for optimization. Don't use n^2 grid, use n^2/16 for suitably large proteins
# Speedup for 3d. look at email for size of grid
# Speedup: speedup. Have clause that puts left or right end in center of grid. Possible that it'll result in impossible solution.
# might have to increase grid size if we do this
# Speedup: keep solver from looking @ symmetric solutions. If you put left end in middle, position of second one is equivalent no
# matter where it goes. Set position of 2nd (e.g. set to 1 above/below/left/right)
# Speedup: implement a better bound for k based on string

def read_data(file):
    with open(file) as f:
        data = f.readlines()
        
        return data[0].strip()


def get_positions_of_ones(s):
    positions_of_ones = list()

    for i in range(0, len(s)):
        if s[i] == "1":
            positions_of_ones.append(i)
    
    return positions_of_ones

def get_num_adjacent_ones(positions_of_ones):
    num_adjacent_ones = 0

    for i in range(0, len(positions_of_ones) - 1):
        if abs(positions_of_ones[i] - positions_of_ones[i+1]) == 1:
            num_adjacent_ones += 1
    
    return num_adjacent_ones

def is_binary_string(string):
    for x in string:
        if x != "1" and x != "0":
            return False

    return True

#n is the length for the binary string that will be produced
"""def gen_test_str(n):
    if n <= 0 or n == None:
        raise Exception("String length must be > 0. Please try again")
    else:
        test_str = str()
        while len(test_str) < n:
            test_str += str(random.randint(0, 1))

        return test_str
"""

def gen_embedding_conditions(n):
    embedding_conditions = list()

    # embedding condition 1 (every x_ij is somewhere)
    clause_1 = list()

    for x in range(1, n * n + 1):
        clause_1.append(x)

    embed_condition_1 = Condition([clause_1], True, n, n * n)
    embedding_conditions.append(embed_condition_1)

    # embedding condition 2 (every x_ij can only be true for one j)
    embed_condition_2 = Condition(list(), True, n, n * n)

    for i in range(1, n * n):
        for j in range (i+1, n * n + 1):
            embed_condition_2.add_clause([-1 * i,-1 * j])
    
    embedding_conditions.append(embed_condition_2)

    # embedding condition 3 (every x_ij can only be true for one i)
    embed_condition_3 = Condition(list(), True, n * n, 1)

    stop = (n - 1) * n * n + 1

    for j in range(1, stop, n * n):
        for i in range(j+n * n, stop+1, n * n):
            embed_condition_3.add_clause([-1 * j, -1 * i])
    
    embedding_conditions.append(embed_condition_3)

    # embedding condition 4
    embed_condition_4 = Condition(list(), True, n - 1, n * n)
    
    for i in range(1, n * n + 1):
        if i == 1:
            # condition 4f
            embed_condition_4.add_clause([-1 * i, i + n * n + 1, i + n * n + n])
        elif i == n:
            # conditin 4g
            embed_condition_4.add_clause([-1 * i, i + n * n - 1, i + n * n + n])
        elif i == n * n - n + 1:
            # condition 4h
            embed_condition_4.add_clause([-1 * i, i + n * n + 1, i + n * n - n])
        elif i == n * n:
            # condition 4i
            embed_condition_4.add_clause([-1 * i, i + n * n - 1, i + n * n - n])
        elif i % n == 1:
            # condition 4d
            embed_condition_4.add_clause([-1 * i, i + n * n + 1, i + n * n + n, i + n * n - n])
        elif i % n == 0:
            # condition 4e
            embed_condition_4.add_clause([-1 * i, i + n * n - 1, i + n * n + n, i + n * n - n])
        elif i > 1 and i < n:
            # condition 4b
            embed_condition_4.add_clause([-1 * i, i + n * n + 1, i + n * n - 1, i + n * n + n])
        elif i > n * n - n + 1 and i < n * n:
            # condition 4c
            embed_condition_4.add_clause([-1 * i, i + n * n + 1, i + n * n - 1, i + n * n - n])
        else:
            embed_condition_4.add_clause([-1 * i, i + n * n + 1, i + n * n - 1, i + n * n + n, i + n * n - n])

    embedding_conditions.append(embed_condition_4)

    return embedding_conditions

def gen_contact_conditions(n, positions_of_ones):
    offset = pow(n, 3) #existing vars from X_ij conditions
    contact_conditions = list()
    
    # contact condition 1
    contact_condition_1 = Condition(list(), True, n * n, 1)

    for x in positions_of_ones:
        contact_condition_1.add_clause([n * n * n + 1, (-1 * x * n * n) - 1])

    last_clause = [-1 * n * n * n - 1]
    last_clause.extend(map(lambda x: (x * n * n) + 1, positions_of_ones))
    contact_condition_1.add_clause(last_clause)

    contact_conditions.append(contact_condition_1)

    # contact condition 2
    clauses = list()

    for j in range(1, n * n + 1):
        C_jr = n * n * n + n * n + j
        C_jd = C_jr + n * n
        T_j = C_jr - n * n
        T_jr = T_j + 1
        T_jd = T_j + n

        if j == n * n:
            clauses.extend([[-1 * C_jr]])
            clauses.extend([[-1 * C_jd]])
        elif j >= n * n - n + 1:
            clauses.extend([[-1 * C_jr, T_j], [-1 * C_jr, T_jr], [C_jr, -1 * T_j, -1 * T_jr]])
            clauses.extend([[-1 * C_jd]])
        elif j % n == 0:
            clauses.extend([[-1 * C_jr]])
            clauses.extend([[-1 * C_jd, T_j], [-1 * C_jd, T_jd], [C_jd, -1 * T_j, -1 * T_jd]]) 
        else:
            clauses.extend([[-1 * C_jr, T_j], [-1 * C_jr, T_jr], [C_jr, -1 * T_j, -1 * T_jr]])
            clauses.extend([[-1 * C_jd, T_j], [-1 * C_jd, T_jd], [C_jd, -1 * T_j, -1 * T_jd]])

    contact_condition_2 = Condition(clauses)
    contact_conditions.append(contact_condition_2)

    return contact_conditions

def gen_counting_conditions(n, r, positions_of_ones):
    # counting conditions 1 and 2
    # make one condition per level w/ appropriate # of repeats
    num_contact_conditions = 2 * pow(n, 2)
    num_tree_levels = math.ceil(math.log(num_contact_conditions, 2))
    counting_conditions = list()
    num_existing_vars = pow(n, 3) + pow(n, 2) + num_contact_conditions
    num_vars = num_existing_vars

    for l in range(1, num_tree_levels - 1):
        t_k = min(r, pow(2, num_tree_levels - l))
        t_ki = min(r, pow(2, num_tree_levels - l - 1))
        repeats = pow(2, l)
        if l < num_tree_levels - 1:
            count_condition_l = Condition(list(), True, repeats, t_k)
        else:
            count_condition_l = Condition(list(), False)

        # i and j are the two children of node k.
        for j in range(0, t_ki + 1):
            if l == num_tree_levels - 1:
                b_j_2k =  -1 * (n * n * n + n * n + t_ki + j)
            else:
                b_j_2k = num_vars + repeats * t_k + t_ki + j # var number will be the existing number of variables + the number of variables at level k + i

            for i in range(0, t_ki + 1):
                clause = list()

                if (i + j) > (t_k + 1):
                    break
                elif i + j < 1:
                    continue

                if l == num_tree_levels - 1:
                    b_i_2k = -1 * (n * n * n + n * n + i)
                else:
                    b_i_2k = num_vars + repeats * t_k + i # vars number is the existing vars + the number of variables at level k + the number of variables under node i + j

                if not(i == 0):
                    clause.append(-1 * b_i_2k)

                if not(j == 0):   
                    clause.append(-1 * b_j_2k)
                if i > 0 or j > 0:
                    b_r_k = num_vars + i + j # existing vars + whatever k value we're on (k is the highest node in question for all clauses)
                    clause.append(b_r_k)

                if clause not in count_condition_l.clauses:
                    count_condition_l.add_clause(clause)

        if l < num_tree_levels - 1:
            num_vars += t_k * repeats
        counting_conditions.append(count_condition_l)

    last_level_condition = Condition(list(), False)
    t_k = min(r, 2) # only two nodes below each node on the second to last level
    repeats = pow(2, num_tree_levels - 1)

    for k in range(0, repeats):
        for j in range(0, 2): #only two leaves per pre-terminal node
            for i in range(0, 2):
                last_level_clause = list()
                b_i_2k = -1 * (n * n * n + n * n + k * t_k + 1)
                b_j_2k = b_i_2k - 1
                b_r_k = num_vars + k * t_k + i + j

                if i + j > t_k + 1:
                    break
                if i + j == 0:
                    continue

                if (i > 0 and b_i_2k >= -1 * num_existing_vars):
                    last_level_clause.append(-1 * b_i_2k)
                if (j > 0 and b_j_2k >= -1 * num_existing_vars):
                    last_level_clause.append(-1 * b_j_2k)

                if (b_i_2k < -1 * num_existing_vars or b_j_2k < -1 * num_existing_vars):
                    last_level_clause.append(-1 * b_r_k)
                else:
                    last_level_clause.append(b_r_k)
                
                if len(last_level_clause) > 0 and last_level_clause not in last_level_condition.clauses:
                    last_level_condition.add_clause(last_level_clause)
    
    counting_conditions.append(last_level_condition)
    num_vars += t_k *repeats
    t_2 = min(r, pow(2, num_tree_levels - 1)) # node 2 is at level 1
    count_condition_2 = Condition(list(), False)

    # there's another way to do this beside doing two nested loops, but is it better?
    for i in range(0, t_2 + 1):
        for j in range(0, t_2 + 1):
            count_clause = list()
            if i + j < r + 1:
                continue
            elif i + j > r + 1:
                break
            if i != 0:
                count_clause.append(-1 * (num_existing_vars + i))
            if j != 0:
                count_clause.append(-1 * (num_existing_vars + t_2 + j))
            if len(count_clause) > 0:
                count_condition_2.add_clause(count_clause)
            
    counting_conditions.append(count_condition_2)

    return list([counting_conditions, num_vars])

def get_num_clauses(n, conditions):
    num_clauses = 0
    #n +  pow(n, 3) * (pow(n, 2) - 1)//2 +  pow(n, 3) * (n - 1)//2 + pow(n, 2) * (n - 1) + pow(n, 2) * (num_existing_ones + 1)

    for i in range(0, len(conditions)):
        num_clauses += conditions[i].num_repeats * len(conditions[i].clauses)

    return num_clauses

def write_conditions(num_vars, num_clauses, conditions, file):
    with open(file, "w") as f:
        print("c " + file, file=f)
        print("c", file=f)
        print("p cnf " + str(num_vars) + " " + str(num_clauses), file=f)
        for c in conditions:
            c.write_condition(f)

def gen_cnf_file(string, k, embedding_conditions, contact_conditions, outfile):
    n = len(string)

    positions_of_ones = get_positions_of_ones(string)
    num_adjacent_ones = get_num_adjacent_ones(positions_of_ones)
    r = 2 * pow(n, 2) - (num_adjacent_ones + k)
    counting_conditions_num_vars = gen_counting_conditions(n, r, positions_of_ones)
    counting_conditions = counting_conditions_num_vars[0]
    num_vars = counting_conditions_num_vars[1]
    conditions = embedding_conditions + contact_conditions + counting_conditions
    num_clauses = get_num_clauses(n, conditions)
    write_conditions(num_vars, num_clauses, conditions, outfile)

def bin_search(string, min_k, max_k, embedding_conditions, contact_conditions, outfile, time_elapsed, k_vals_tried = dict()):
    k = (min_k + max_k) // 2

    if k == 0:
        return 0

    if k in k_vals_tried:
        if k_vals_tried[k]:
            if min_k == max_k:
                return k
            return bin_search(string, k, max_k, embedding_conditions, contact_conditions, time_elapsed, k_vals_tried)
        else:
            return bin_search(string, min_k, k - 1, embedding_conditions, contact_conditions, time_elapsed, k_vals_tried)

    else:
        gen_cnf_file(string, k, embedding_conditions, contact_conditions, outfile)
        start = time.time()
        result = subprocess.run(["./lingeling/lingeling", outfile], capture_output=True)
        end = time.time()
        time_elapsed[0] += end - start
        time_elapsed[1] += 1 #another try

        if result.returncode < 10:
            print(result.stderr)
            return 0
        elif result.returncode == 10:
            if (min_k == max_k):
                return k
            k_vals_tried[k] = True
            return bin_search(string, k, max_k, embedding_conditions, contact_conditions, outfile, time_elapsed, k_vals_tried)
        elif result.returncode == 20:
            k_vals_tried[k] = False
            return bin_search(string, min_k, k-1, embedding_conditions, contact_conditions, outfile, time_elapsed, k_vals_tried)
        else:
            print("I found a bug! Unaccounted for return code: " + result.returncode)
    
def maximize_contacts(string, k, embedding_conditions, contact_conditions, outfile, time_elapsed, k_vals_tried=dict()):
    if k == 0:
        return 0

    gen_cnf_file(string, k, embedding_conditions, contact_conditions, outfile)
    start = time.time()
    result = subprocess.run(["./lingeling/lingeling", outfile], capture_output=True)
    end = time.time()
    time_elapsed[0] += end - start
    time_elapsed[1] += 1

    if result.returncode < 10:
        print(result.stderr)
        return
    elif result.returncode == 10:
        k_vals_tried[k] = True
        return maximize_contacts(string, 2 * k, embedding_conditions, contact_conditions, outfile, time_elapsed, k_vals_tried)
    elif result.returncode == 20:
        k_vals_tried[k] = False
        return bin_search(string, k // 2, k-1, embedding_conditions, contact_conditions, outfile, time_elapsed, k_vals_tried)
    else:
        print("I found a bug! Unaccounted for return code: " + result.returncode)

def maximize_with_gurobi(file, time_elapsed):
    sol_file = "./gurobi_output/" + file + ".sol"
    lp_file = "./input/" + file + ".lp"
    subprocess.run(["perl", "./HPb.pl", "./input/" + file])
    start = time.time()
    result = subprocess.run(["gurobi_cl", "ResultFile=./gurobi_output/" + sol_file, "./input/" + lp_file], capture_output=True)
    end = time.time()

    if (result.returncode == 1):
        print(str(result.stdout))
        return
    else:
        with open("./gurobi_output/" + file + ".sol") as f:
            lines = f.readlines()
            if "value =" in lines[0]:
                contacts_found = re.search(r"\d+", lines[0]).group()
            else:
                contacts_found = 0
                
            time_elapsed[0] = end - start
            return contacts_found

def main(argv):
    if len(argv) < 2 or len(argv) > 3:
        print("ERROR: wrong number of arguments given\n\tUsage: main.py {list of input files} {output directory}")
        return
    elif len(argv) == 2:
        outdir = "./lingeling/output/"

    else:
        outdir = argv[2]
    
    files = argv[1]

    for file_name in files:
        string = read_data("./input/" + file_name)

        if not is_binary_string(string):
            print("Error:", string, " is not a binary string")
            continue

        n = len(string)
        k = 1 # start by looking for only one contact
        ling_output_file = "./lingeling/input/" + file_name + ".cnf"
        embedding_conditions = gen_embedding_conditions(n)
        positions_of_ones = get_positions_of_ones(string)
        contact_conditions = gen_contact_conditions(n, positions_of_ones)
        ling_time_elapsed = [0,0]
        gurobi_time_elapsed = [0]
        lingeling_max_contacts = maximize_contacts(string, k, embedding_conditions, contact_conditions, ling_output_file, ling_time_elapsed)
        gurobi_max_contacts = maximize_with_gurobi(file_name, gurobi_time_elapsed)

        print("Maximum contacts found for", string, "using Lingeling:", lingeling_max_contacts)
        print("Lingeling time taken:", ling_time_elapsed[0])
        print("Lingeling runs required:", ling_time_elapsed[1])
        print("Maximum contacts found for", string, "using gurobi:", gurobi_max_contacts)
        print("Gurobi time taken:", gurobi_time_elapsed[0])

main(["main.py", ["1pspB1"]])