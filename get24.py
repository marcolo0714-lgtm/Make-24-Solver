def recur(inputl):
    n = len(inputl)
    if n == 1:
        return [inputl[0]]

    newl = []
    for i in range(1, n):
        l1 = recur(inputl[ : i])
        l2 = recur(inputl[i : ])
        for exp1 in l1:
            for exp2 in l2:
                newl.append(f"({exp1} + {exp2})")
                newl.append(f"({exp1} - {exp2})")
                newl.append(f"{exp1} * {exp2}")
                newl.append(f"{exp1} / {exp2}")

    return newl

def fact(n):
    if n == 0:
        return 1
    else:
        return n * fact(n - 1)

from itertools import permutations
print("-----------------------------------------------------------------------------")
print("| This program let users input some numbers and an expected result, and     |")
print("| try to give any arithmetic expression of the input numbers that equals to |")
print("| the expected result, or claim that there is no such expression.           |")
print("-----------------------------------------------------------------------------")

inputnum = input(f"Enter numbers (space-separated): ").split()
choice = input("Generate all possible arithmetic expressions of the input numbers? (y/n): ")
if choice.lower() == "y" or choice.lower() == "yes":
    choice = 1
else:
    choice = 0
expected = eval(input("Enter expected result: "))

# stores arithmetic expressions that give the expected result, if there is any
expression_set = set()

# 1 progress for each permutation of the input numbers, and there are fact(len(inputnum)) permutations in total
progress = 0
for inputl in permutations(inputnum):
    print(f"Progress: {progress} / {fact(len(inputnum))}")

    # recur() generates all possible arithmetic expressions of the input numbers in a certain permutation, 
    # and then we evaluate each expression to check if it gives the expected result
    expression_list = recur(inputl)
    for expression in expression_list:
        try:
            if -10**-10 <= (eval(expression) - expected) <= 10**-10:
                expression_set.add(expression)
        except:  # in case of division by zero, we just ignore that expression and evaluate the next one
            continue

    # if the user doesn't want to generate all possible arithmetic expressions, then we can stop the program as soon as we find a solution    
    if choice == 0 and len(expression_set) != 0:
        break
    progress = progress + 1

# After checking all permutations of the input numbers (choice = 1) or stopping early (choice = 0), we can print the result
if len(expression_set) != 0:
    if choice == 0:
        print("✅ Possible solution found!")
        print(expression_set.pop())
    else:
        print("✅ All possible solutions found!")
        counter = 1
        for expression in expression_set:
            print(f"{counter}. {expression}")
            counter += 1
else:
    print("❌ There are no arithmetic expression of the input numbers that gives the expected result.")
