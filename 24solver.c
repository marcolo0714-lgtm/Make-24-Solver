#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>
#include <time.h>

int generate_all_sol = 0;
int sol_count = 0;

/*
 * Parse whitespace-separated integers from a single input line.
 * Supports negative numbers by tracking a sign state.
 *
 * Parameters:
 *   *input - null-terminated input string from fgets()
 *   *nums  - output array filled with parsed integers
 *
 * Returns:
 *   number of integers parsed into *nums
 */
int split(char *input, int *nums) {
    int value = 0;
    int sign = 1;
    int num_pos = 0;
    int in_number = 0;

    for (int i = 0; input[i] != '\0' && input[i] != '\n'; ++i) {
        char c = input[i];

        if (c == '-') {
            // Regard as new number if '-' appears right after a digit
            if (in_number) nums[num_pos++] = sign * value;
            value = 0;
            sign = -1;
            in_number = 0;
        } else if (isdigit((unsigned char)c)) {
            value = value * 10 + (c - '0');
            in_number = 1;
        } else if (isspace((unsigned char)c)) {
            if (in_number) {
                nums[num_pos++] = sign * value;
                value = 0;
                sign = 1;
                in_number = 0;
            }
        }
    }

    if (in_number) {
        nums[num_pos++] = sign * value;
    }

    return num_pos;
}

/*
 * Build a new arithmetic expression string by surrounding a binary
 * operation with parentheses.
 *
 * Example: left="1", op="+", right="2" => "(1+2)"
 *
 * Parameters:
 *   left  - string containing left operand expression
 *   op    - operator string, such as "+", "-", "*", or "/"
 *   right - string containing right operand expression
 *
 * Returns:
 *   malloc-allocated string containing the combined expression,
 *   or NULL if allocation fails.
 */
char *make_expr(const char *left, const char *op, const char *right) {
    size_t len = strlen(left) + strlen(op) + strlen(right) + 2; 
    char *buffer = (char *)malloc(len + 1);
    if (buffer == NULL) {
        return NULL;
    }
    // like printf(), but write to buffer instead of console, with maximum size to be written set
    snprintf(buffer, len + 1, "(%s%s%s)", left, op, right);
    return buffer;
}

/*
 * Recursively search for a valid expression that evaluates to the target.
 *
 * This function picks every unordered pair of current numbers and joins them
 * using each valid arithmetic operator. It reduces the problem size by one on
 * each recursive call until only one number remains.
 *
 * Parameters:
 *   nums      - array of current numeric values
 *   expr      - array of current expression strings for each value in nums
 *   input_num - current number of values in the arrays
 *   target    - target value to reach
 *
 * Returns:
 *   1 if a solution is found and printed, otherwise 0.
 */
int recur(double *nums, char **expr, int input_num, double target) {
    /* Base case: only one number left, check if it matches target. */
    if (input_num == 1) {
        if (fabs(nums[0] - target) < 1e-10) {
            printf("%d: %s = %.2lf\n", ++sol_count, expr[0], target);
            return 1;
        }
        return 0;
    }

    /* Try every pair of distinct numbers from the current list. */
    for (int i = 0; i < input_num - 1; ++i) {
        for (int j = i + 1; j < input_num; ++j) {
            double a = nums[i];
            double b = nums[j];

            struct {
                double value;
                char *expression;
            } candidates[6];
            int candidate_count = 0;

            /* Add the two values. */
            candidates[candidate_count].value = a + b;
            candidates[candidate_count].expression = make_expr(expr[i], "+", expr[j]);
            candidate_count++;

            /* Subtract b from a and a from b. */
            candidates[candidate_count].value = a - b;
            candidates[candidate_count].expression = make_expr(expr[i], "-", expr[j]);
            candidate_count++;

            candidates[candidate_count].value = b - a;
            candidates[candidate_count].expression = make_expr(expr[j], "-", expr[i]);
            candidate_count++;

            /* Multiply the two values. */
            candidates[candidate_count].value = a * b;
            candidates[candidate_count].expression = make_expr(expr[i], "*", expr[j]);
            candidate_count++;

            /* Divide only if the divisor is not effectively zero. */
            if (fabs(b) > 1e-9) {
                candidates[candidate_count].value = a / b;
                candidates[candidate_count].expression = make_expr(expr[i], "/", expr[j]);
                candidate_count++;
            }

            if (fabs(a) > 1e-9) {
                candidates[candidate_count].value = b / a;
                candidates[candidate_count].expression = make_expr(expr[j], "/", expr[i]);
                candidate_count++;
            }

            /*
             * For each candidate operation, build the reduced problem state by
             * copying the remaining numbers and expressions, then appending the
             * result of the chosen operation.
             */
            for (int c = 0; c < candidate_count; ++c) {
                if (candidates[c].expression == NULL) {
                    continue;
                }

                /* Reconstruct *nums and **expr by inserting combined number at the end*/
                double next_nums[10];
                char *next_expr[10];
                int next_index = 0;

                for (int k = 0; k < input_num; ++k) {
                    if (k == i || k == j) {
                        continue;
                    }
                    next_nums[next_index] = nums[k];
                    next_expr[next_index] = expr[k];
                    next_index++;
                }

                next_nums[next_index] = candidates[c].value;
                next_expr[next_index] = candidates[c].expression;

                /* Recurse with one fewer active value. */
                if (recur(next_nums, next_expr, input_num - 1, target)) {
                    free(candidates[c].expression);
                    if (!generate_all_sol) return 1;   // stop early if any solution is found, and is requested
                }

                free(candidates[c].expression);
            }
        }
    }

    return 0;
}

/*
 * Program entry point.
 *
 * Reads a line of integers from stdin, reads a target value, and searches for
 * an arithmetic expression using the input numbers to evaluate to the target.
 */
int main(void) {
    printf("------------------------------------------------------------------------------\n");
    printf("| [C] This program is to be input some numbers and an expected result,       |\n");
    printf("| and try to give any arithmetic expression of the input numbers that equals |\n");
    printf("| to the expected result, or claim that there is no such expression.         |\n");
    printf("------------------------------------------------------------------------------\n");
    
    printf("Enter numbers (space-separated): ");
    char input[100];
    if (fgets(input, sizeof(input), stdin) == NULL) {
        printf("No numbers were entered.\n");
        return 1;
    }

    int int_nums[100];
    int input_num = split(input, int_nums);
    if (input_num == 0) {
        printf("No numbers were entered.\n");
        return 1;
    }

    /* Allocate numeric values and expression strings. */
    double *nums = (double *)malloc(sizeof(double) * input_num);
    if (nums == NULL) {
        return 1;
    }

    char **expr = (char **)malloc(sizeof(char *) * input_num);
    if (expr == NULL) {
        free(nums);
        return 1;
    }

    /* Initialize each expression entry to the original numeric literal. */
    for (int i = 0; i < input_num; ++i) {
        nums[i] = (double)int_nums[i];
        expr[i] = (char *)malloc(12);  // enough to hold "-2147483648" and null terminator
        if (expr[i] == NULL) {
            for (int j = 0; j < i; ++j) free(expr[j]);
            free(expr);
            free(nums);
            return 1;
        }
        snprintf(expr[i], 12, "%d", int_nums[i]);
    }

    printf("Enter target number: ");
    double target;
    if (scanf("%lf", &target) != 1) {
        printf("Invalid target number.\n");
        for (int i = 0; i < input_num; ++i) free(expr[i]);
        free(expr);
        free(nums);
        return 1;
    }

    printf("Generate all possible arithmetic expressions of the input numbers? (y/n): ");
    char choice;
    if (scanf(" %c", &choice) != 1){
        printf("Invalid target number.\n");
        for (int i = 0; i < input_num; ++i) free(expr[i]);
        free(expr);
        free(nums);
        return 1;
    }
    if (choice == 'y' || choice == 'Y')
        generate_all_sol = 1;
    else
        generate_all_sol = 0;

    // Program now starts searching for arithmetic expression
    clock_t start_time = clock();

    recur(nums, expr, input_num, target);

    if (sol_count == 0)
        printf("There are no arithmetic expression of the input numbers that gives the expected result.\n");

    clock_t end_time = clock();
    double time_spent = (double)(end_time - start_time) / CLOCKS_PER_SEC;

    printf("Execution Time (excluding input time): %f seconds\n", time_spent);

    for (int i = 0; i < input_num; ++i) free(expr[i]);
    free(expr);
    free(nums);

    return 0;
}
