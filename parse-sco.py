'''
Parse the raw csv data exported by school cash online
Creates a new csv file containing the total order per student
Sample Output:

First Name,Last Name,Teacher,Cheese,Pepperoni,Halal Pepperoni,Juice Box,Yop Yoghurt,Payment
Bob,Dole,Frizzle,2,,1,,,Online

'''
import re
import csv
import dataclasses
from typing import NamedTuple, Dict, List, Union
from pathlib import Path
from argparse import ArgumentParser

class OrderEntry(NamedTuple):
    student_number: int
    first_name: str
    last_name: str
    class_name: str
    items: list

@dataclasses.dataclass
class StudentEntry:
    first_name: str
    last_name: str
    teacher: str
    orders: Dict[str, int] = dataclasses.field(default_factory=dict)
    payment_method: str = "Online"

    def as_pretty_dict(self) -> Dict[str, Union[str,int]]:
        """
        Convert to a pretty dictionary for generating the final csv file
        """
        pretty: Dict[str, Union[str,int]] = {
            "First Name": self.first_name,
            "Last Name": self.last_name,
            "Teacher": self.teacher,
        }
        for order,count in self.orders.items():
            pretty[order] = count if count > 0 else ""

        pretty["Payment"] = self.payment_method

        return pretty


class BaseParser:
    def __init__(self, data, item_options: List[str]):
        self.data = data
        self.item_options = self._sort_item_options(item_options)

    def _sort_item_options(self, options: List[str]) -> List[str]:
        '''
        This sorts the list of orderable items into the desired order
        The desired order doesnt have to match the entries in the csv exactly.
        Just be close enough
        '''
        order = ['cheese', 'pepperoni', 'halal', 'juice', 'yop']
        order_dict: Dict[str,int] = {word.lower(): i for i, word in enumerate(order)}

        # Sorting key: find first word in each item that matches the order list
        def sort_key(item: str) -> int:
            words = item.lower().split()  # Split item into words
            for word in words:
                if word in order_dict:  # If any word is in order_dict, use its index
                    return order_dict[word]
            return len(order)  # Default to end if no match

        return list(sorted(options, key=sort_key))


    def _parse_row(self, row) -> OrderEntry:
        raise NotImplementedError('Must subclass')

    def parse_teacher_from_class_name(self, value: str) -> str:
        '''
        Crazy class names with the teacher name embedded in there somewhere
            - HRMJK-RJSKA-T-Name
            - JRM45-RGR45B-Name
            - RGR45B-Name
        '''
        parts = value.split('-')
        for part in parts:
            # Prefer the piece with lowercase letters in it. Its probably a name
            if re.search(r'[a-z]', part):
                return part.strip()

        # Default to the second part :shrug:
        # No rhyme or reason to how they structure these. its a crapshoot
        return parts[1].strip()


    def parse(self) -> Dict[int, StudentEntry]:
        """
        Parse csv data loaded as a dict into a dictionary of StudentEntry's keyed
        by student ID
        """
        output: Dict[int, StudentEntry] = {}

        for row in self.data:
            order = self._parse_row(row)

            if order.student_number in output:
                entry = output[order.student_number]
            else:
                entry = StudentEntry(
                    first_name=order.first_name,
                    last_name=order.last_name,
                    teacher=order.class_name,
                )
                for option in self.item_options:
                    entry.orders[option] = 0

            for item in order.items:
                entry.orders[item] += 1

            output[order.student_number] = entry

        return output

class Type1Parser(BaseParser):
    '''
    In this particular export format the orders are lumped together in the field "Options"
    The field contains a comma seperate list of orders
    For example:
        Cheese,Juice Box, Pepperoni
    '''
    def __init__(self, data):
        options: List[str] = []
        for row in data:
            options.extend([x.strip() for x in row['Options'].split(',')])
        super().__init__(data, list(set(options)))

    def _parse_row(self, row: Dict) -> OrderEntry:
        student_name = row['Student Name'].split(',')
        order = OrderEntry(
            student_number = row['Student Number'],
            first_name = student_name[1].strip(),
            last_name = student_name[0].strip(),
            class_name = self.parse_teacher_from_class_name(row['HomeroomName']),
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
        options: List[str] = list(set([x['choiceName'].strip() for x in data]))
        super().__init__(data, options)

    def _parse_row(self, row: Dict) -> OrderEntry:
        quantity = int(row['quantity'])
        student_name = row['studentName'].split(',')
        order = OrderEntry(
            student_number = row['studentNumber'],
            first_name = student_name[1].strip(),
            last_name = student_name[0].strip(),
            class_name = self.parse_teacher_from_class_name(row['homeroomName']),
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
        student_entries = [x.as_pretty_dict() for x in output.values()]
        writer = csv.DictWriter(f, fieldnames=student_entries[0].keys())
        writer.writeheader()
        writer.writerows(student_entries)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('-s', '--src',
                        help='Source .csv file to parse')
    parser.add_argument('-o', '--out',
                        help='Name of output .csv file to generate')

    main(parser.parse_args())
