# Overview

A set of simple python scripts to summarize the order counts per student given a SchoolCash Online CSV report.

Parse the csv file exported from SCO

```sh
python parse-sco.py --src sco.csv --out orders.csv
```

Sample Output:
```csv
First Name,Last Name,Teacher,Cheese,Pepperoni,Halal Pepperoni,Juice Box,Yop Yoghurt,Payment
Nick,Carter,Frazzle,1,1,,,,Online
Bob,Dole,Frizzle,2,,1,,,Online
Richard,Nixon,Frazzle,,3,,2,,Online
```

Group all students in the generated report by classroom teacher and summarize the order totals

```sh
python group.py --src orders.csv --out orders-by-class.csv
```

Sample Output:

```csv
First Name,Last Name,Teacher,Cheese,Pepperoni,Halal Pepperoni,Juice Box,Yop Yoghurt,Payment
Nick,Carter,Frazzle,1,1,,,,Online
Richard,Nixon,Frazzle,,3,,2,,Online
,,,,,,,,,
,,,,,,,,,
Bob,Dole,Frizzle,2,,1,,,Online
,,,,,,,,,
,,,,,,,,,
,,,Frizzle,2,,1,,,
,,,Frazzle,1,4,,2,,
```

# schoolcash-tally

`src/schoolcash_parsing/tally.py` is an installable tool that does the per-student tally in one step. It
takes one or more item order report exports, `.xlsx` (first worksheet) or `.csv` in any mix, and writes
`First Name, Last Name, Teacher, Cheese, Pepperoni, Halal Pepperoni, Juice Box, Yop Yoghurt`.

```sh
pip install .
schoolcash-tally "list-A.xlsx" "list-B.xlsx" "list-B-later.csv" -o tally.csv
```

- Orders are coalesced by **Student Number**, so students with the same name stay separate. A student
  with orders in more than one report has them summed, and a note is printed for each.
- If every order in one input also appears in another (e.g. an earlier export of a revised list), the
  subset input is ignored. Report-level `Total ...` columns are left out of that comparison because they
  change between exports.
- Validation: each order's items are priced (pizza slice $3, juice $1, Yop $2) and compared with its
  `Paid Amount`. Each report's `Total Paid Amount` is checked against its orders, and the tally's value is checked
  against the total paid. The exit status is 1 on any mismatch.

Prices and item spellings live in `PRICES` and `ITEM_PATTERNS` in `tally.py`.

## Tests

```sh
tox -e py3         # unit tests
tox                # unit tests, mypy, flake8
```

Tests parse the fake reports in `tests/data`. That folder's README pairs each fake student's orders with
their row in `expected-tally.csv`.
