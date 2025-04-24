'''
Parse the raw csv data exported by school cash online
Creates a new csv file containing the total order per student
Sample Output:

First Name,Last Name,Teacher,Cheese,Pepperoni,Halal Pepperoni,Juice Box,Yop Yoghurt,Payment
Bob,Dole,Frizzle,2,,1,,,Online

'''
import csv
from typing import NamedTuple
from pathlib import Path
from argparse import ArgumentParser

class OrderEntry(NamedTuple):
    student_number: int
    first_name: str
    last_name: str
    class_name: str
    items: list


class BaseParser:
    def __init__(self, data, item_options):
        self.data = data
        self.item_options = self._sort_item_options(item_options)

    def _sort_item_options(self, options):
        '''
        This sorts the list of orderable items into the desired order
        The desired order doesnt have to match the entries in the csv exactly.
        Just be close enough
        '''
        order = ['cheese', 'pepperoni', 'halal', 'juice', 'yop']
        order_dict = {word.lower(): i for i, word in enumerate(order)}

        # Sorting key: find first word in each item that matches the order list
        def sort_key(item):
            words = item.lower().split()  # Split item into words
            for word in words:
                if word in order_dict:  # If any word is in order_dict, use its index
                    return order_dict[word]
            return len(order)  # Default to end if no match

        return sorted(options, key=sort_key)


    def _parse_row(self, row) -> OrderEntry:
        raise NotImplementedError('Must subclass')

    def parse(self):
        output = {}

        for row in self.data:
            order = self._parse_row(row)

            if order.student_number in output:
                entry = output[order.student_number]
            else:
                entry = {
                    'First Name': order.first_name,
                    'Last Name': order.last_name,
                    'Teacher':  order.class_name,
                }
                for option in self.item_options:
                    entry[option] = 0

                entry['Payment'] = 'Online'

            for item in order.items:
                entry[item] += 1

            output[order.student_number] = entry

        # Replace zero orders with empty strings
        for entry in output.values():
            for option in self.item_options:
                if entry[option] == 0:
                    entry[option] = ''

        return output

class Type1Parser(BaseParser):
    '''
    In this particular export format the orders are lumped together in the field "Options"
    The field contains a comma seperate list of orders
    For example:
        Cheese,Juice Box, Pepperoni
    '''
    def __init__(self, data):
        options = []
        for row in data:
            options.extend([x.strip() for x in row['Options'].split(',')])
        super().__init__(data, list(set(options)))

    def _parse_row(self, row) -> OrderEntry:
        student_name = row['Student Name'].split(',')
        order = OrderEntry(
            student_number = row['Student Number'],
            first_name = student_name[1].strip(),
            last_name = student_name[0].strip(),
            class_name = row['HomeroomName'].split('-')[1].strip(),
            items = [x.strip() for x in row['Options'].split(',')]
        )
        return order

class Type2Parser(BaseParser):
    '''
    In this particular export format the orders are grouped by the field 'choiceName'
    which contains only a single item type. Each order has a specified 'quantity'.

    For example:
        , choiceName, quantity,
        , Juice Box, 2
    '''
    def __init__(self, data):
        options = list(set([x['choiceName'].strip() for x in data]))
        super().__init__(data, options)

    def _parse_row(self, row) -> OrderEntry:
        quantity = int(row['quantity'])
        student_name = row['studentName'].split(',')
        order = OrderEntry(
            student_number = row['studentNumber'],
            first_name = student_name[1].strip(),
            last_name = student_name[0].strip(),
            class_name = row['homeroomName'].split('-')[1].strip(),
            items = [row['choiceName']] * quantity,
        )
        return order


def main(args):
    with open(Path(args.src).resolve()) as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]

    if 'Options' in data[0].keys():
        parser = Type1Parser(data)
    elif 'choiceName' in data[0].keys():
        parser = Type2Parser(data)
    else:
        print(data[0])
        raise RuntimeError('unknown formatting')

    output = parser.parse()

    with open(Path(args.out).resolve(), 'w') as f:
        output = list(output.values())
        writer = csv.DictWriter(f, fieldnames=output[0].keys())
        writer.writeheader()
        writer.writerows(output)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('-s', '--src',
                        help='Source .csv file to parse')
    parser.add_argument('-o', '--out',
                        help='Name of output .csv file to generate')

    main(parser.parse_args())
