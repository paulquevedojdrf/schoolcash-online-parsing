'''
Takes a csv file of the total school orders and
groups them alphabetically by first name per class

Adds the total order per class to the end of the file
'''
import csv
from pathlib import Path
from collections import defaultdict
from argparse import ArgumentParser
from pprint import pprint
try:
    from teacher_order import teacher_order
except ImportError:
    teacher_order = []

def make_empty_entry(template):
    empty = {}
    for key in template.keys():
        empty[key] = ''
    return empty

def main(args):
    with open(Path(args.src).resolve()) as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]

    teacher_order_map = {name: i for i, name in enumerate(teacher_order)}

    # Filter out entries we dont care about
    data = [x for x in data if x['Teacher'] not in ("",None) and x['First Name'] not in ("",None)]
    # Sort by teacher, then by first name and finally by last name
    data = sorted(
        data,
        key=lambda x: (
            teacher_order_map.get(x['Teacher'], len(teacher_order)),
            x['First Name'],
            x['Last Name']
        )
    )

    # Split the list into a list per class (keyed on teacher name)
    by_teacher = defaultdict(list)
    for d in data:
        by_teacher[d['Teacher']].append(d)

    # Get the total order count per class
    class_totals = []
    for teacher,cls in by_teacher.items():
        sums = defaultdict(int)
        for student in cls:
            for key,value in student.items():
                try:
                    count = int(value)
                    if count:
                        sums[key] += count
                except:
                    pass

        cls.append(make_empty_entry(cls[0]))
        cls.append(make_empty_entry(cls[0]))

        summary = make_empty_entry(cls[0])
        summary.update(sums)
        summary['Teacher'] = teacher
        class_totals.append(summary)

    with open(Path(args.out).resolve(), 'w') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        for cls in by_teacher.values():
            writer.writerows(cls)
        writer.writerows(class_totals)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('-s', '--src',
                        help='Source .csv file to parse')
    parser.add_argument('-o', '--out',
                        help='Name of output .csv file to generate')

    main(parser.parse_args())
