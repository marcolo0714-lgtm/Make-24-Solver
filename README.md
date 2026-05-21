# Make24 Solver

`get24.py` is a small command-line program that takes a list of numbers and an expected target result, then tries to build arithmetic expressions from those numbers that evaluate to the target.

## Requirements

- Python 3
- `tqdm` package

Install `tqdm` with:

```bash
pip install tqdm
```

## How to run

From the folder containing `get24.py`:

```bash
python get24.py
```

Then follow the prompts:

1. Enter the input numbers separated by spaces.
2. Choose whether to generate all possible expressions (`y`) or stop after finding the first solution (`n`).
3. Enter the expected result.

## Example Usage

Input:

```text
Enter numbers (space-separated): 3 3 8 8
Generate all possible arithmetic expressions of the input numbers? (y/n): y
Enter expected result: 24
```

Output:

```text
✅ All possible solutions found!
1. 8 / (3 - 8 / 3)
```

## Program Logic

`get24.py` works by exploring every ordered permutation of the given input numbers and then recursively building all valid arithmetic expressions from each permutation.

### Main steps

1. Read user input:
   - a list of numbers
   - whether to generate all matching expressions or stop after the first match
   - the expected target value

2. For each permutation of the input numbers:
   - use `recur()` to recursively combine the numbers into every possible arithmetic expression using `+`, `-`, `*`, `/`, and parentheses.
   - evaluate each generated expression
   - if the evaluated result matches the target within a tiny floating-point tolerance, store the expression in a result set

3. If the user chose not to generate all expressions, the program stops early once it finds any solution.

4. Print either a matching expression or a message saying no solution exists.

### How `recur()` works

- If the input list has one item, it returns that single expression.
- Otherwise, it splits the list into two non-empty parts at every possible position.
- Each part first returns all of its possible expression. Then, for each pair of expression (taking one from each part), the pair is combined (using the 4 arithmetic operations) to form 4 new expressions.
- The function returns all expressions built from that permutation, with necessary parentheses inserted to preserve operation order.

### Examples of recur() calls

If `recur([a, b])` is called,
- The only possible spilt is `recur([a])` and `recur([b])`, returning [\'a\'] and ['b'] respectively.
- Therefore, 4 expressions ['(a + b)', '(a - b)', 'a * b', 'a / b'] are returned and to be evaluated.

If `recur([a, b, c])` is called,
- (`recur([a])` and `recur([b, c])`) and (`recur([a, b])` and `recur([c])`) will be called.
- Focusing on the 1st split, ['a'] and ['(b + c)', '(b - c)', 'b * c', 'b / c'] are returned respectively.
  - For the pair `'a'` and `'(b + c)'`, 4 expressions `'(a + (b + c))'`, `'(a - (b + c))'`, `'(a * (b + c))'`, `'(a / (b + c))'` are created.
  - The other 3 pairs also create 4 expressions each, so the 1st split creates 16 expressions.
- Similarly, the 2nd split also creates 16 expressions.
- So, 32 expressions are returned and to be evaluated.

### Time complexity analysis of `recur()`
- Let `n` be the number of numbers in the input list passed to `recur()`.
- Base case: `recur(1)` returns 1 expression, and `recur(2)` returns 4 expressions.
- Recursive case: for `n > 2`, `recur(n)` constructs expressions by splitting the list into two non-empty parts and combining every expression from the left part with every expression from the right part using the 4 operators.
- This recurrence has a closed form, valid for at least `n = 1` through `n = 10`:

```latex
\operatorname{recur}(n) = \frac{4^{\,n-1}}{n} \binom{2(n-1)}{n-1}
```

- In combinatorial terms, this equals `4^{n-1}` times the `(n-1)`-th Catalan number.

### Time complexity of this program
- The program iterates over every ordered permutation of the input numbers, and there are `n!` such permutations.
- For each permutation, it calls `recur()` and evaluates every generated expression.
- Therefore, the overall number of generated expressions is roughly:

```text
n! * recur(n) = n! * \frac{4^{\,n-1}}{n} \binom{2(n-1)}{n-1}
```

- In big-O terms, the runtime is super-exponential in `n` due to the permutation factor and the recursive expression growth.

- Assuming runtime scales directly with the total number of evaluated expressions, and taking `n = 5` as a 90-second reference point, the estimated runtime for other values of `n` is proportionally scaled.

| n | `n! * recur(n)` | Estimated time |
|---|---|---|
| 1 | 1 | 0.00021 s |
| 2 | 8 | 0.00167 s |
| 3 | 192 | 0.0402 s |
| 4 | 7,680 | 1.61 s |
| 5 | 430,080 | 90 s |
| 6 | 30,965,760 | 1.8 hours |
| 7 | 2,724,986,880 | 6.6 days |
| 8 | 283,398,635,520 | 22.5 months |
| 9 | 34,007,836,262,400 | 226 years |
| 10 | 4,625,065,731,686,400 | 30,800 years |

> Note: these estimates are directly proportional to the computed expression count and assume the runtime per expression remains constant.

### Notes

- Division by zero is ignored and does not crash the program.
- The program uses a tolerance of `1e-10` when comparing floating-point results to the expected target.
