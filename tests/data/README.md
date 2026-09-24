# Test data

Fake School Cash Online order reports. Students are named after US presidents and Canadian prime
ministers, and teachers after prime ministers. Emails use `example.com`, and student numbers are in the
range 900000000-999999999. None of it belongs to a real student.

| File | Contents |
|---|---|
| `list-a.xlsx` | 6 orders, `Pizza Lunch`, older Options format with no quantities (`Cheese Slice, Juice Box`). A blank row and a `Per Order` summary row follow the orders. Total $30. |
| `list-a.csv` | The same report as `list-a.xlsx`, as CSV. |
| `list-b-early.csv` | The first 5 orders of `list-b.csv`, as an earlier export. Total columns say $28. |
| `list-b.csv` | 7 orders, `Pizza Lunch ***revised***`, quantified Options format (`2 Cheese Slices`). Total $40. |
| `mispriced.csv` | First 3 orders of list A, except George Washington (914673169) paid $4 for a $3 order. |
| `bad-total.csv` | First 3 orders of list A ($15), with the Total Paid Amount column set to $99. |
| `expected-tally.csv` | The tally for `list-a` + `list-b`, i.e. the output of `schoolcash-tally list-a.xlsx list-b-early.csv list-b.csv`. |

Cases worth checking by eye in `expected-tally.csv`:

- **Abraham Lincoln (930228762, Macdonald)** ordered in both lists: Cheese, Pepperoni, Juice Box in A and 1 Pepperoni
  in B, so the tally row is Cheese 1, Pepperoni 2, Juice Box 1.
- **George Bush** is two students: 939845296 in Laurier's class (2 Pepperoni, 1 Juice Box) and 956218302 in
  Pearson's class (1 Cheese). They stay as separate rows.
- **Kim Campbell, Thomas Jefferson, Jean Chrétien, George Bush (Laurier)** appear in both list B exports and are counted once.

| Student | Number | Teacher | List A | List B |
|---|---|---|---|---|
| Abraham Lincoln | 930228762 | Macdonald | Cheese, Pepperoni, Juice Box | 1 Pepperoni |
| George Washington | 914673169 | Macdonald | Cheese | |
| John Diefenbaker | 910082447 | Laurier | Pepperoni, Yop | |
| Theodore Roosevelt | 943471732 | Laurier | Halal Pepperoni, Juice Box | |
| Brian Mulroney | 997075177 | Pearson | Cheese, Pepperoni | |
| John Kennedy | 938485548 | Pearson | Cheese, Yop | |
| Kim Campbell | 934124888 | Macdonald | | 2 Cheese, 1 Yop |
| Thomas Jefferson | 998083545 | Laurier | | 2 Halal Pepperoni |
| Jean Chrétien | 946742315 | Pearson | | 1 Cheese, 1 Juice Box |
| George Bush | 939845296 | Laurier | | 2 Pepperoni, 1 Juice Box |
| George Bush | 956218302 | Pearson | | 1 Cheese (not in early export) |
| Stephen Harper | 955263588 | Macdonald | | 2 Halal Pepperoni, 1 Juice Box, 1 Yop (not in early export) |
