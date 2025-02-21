# Overview

A set of simple python scripts to summarize the order counts per student given a SchoolCash Online CSV report.

Parse the csv file exported from SCO

```sh
python3 parse-sco.py --src sco.csv --out orders.csv
```

Sample Output:
```csv
First Name,Last Name,Teacher,Cheese,Pepperoni,Halal Pepperoni,Juice Box,Yop Yoghurt,Payment
Nick,Carter,Frazzle,1,1,,,,Online
Bob,Dole,Frizzle,2,,1,,,Online
Richard,Nixon,Frazzle,,3,,2,,Online
```

Group all students in the generated report by classroom teacher and summarize the order totals
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
