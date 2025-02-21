'''
Parse the raw csv data exported by school cash online
Creates a new csv file containing the total order per student
Sample Output:

First Name,Last Name,Teacher,Cheese,Pepperoni,Halal Pepperoni,Juice Box,Yop Yoghurt,Payment
Bob,Dole,Frizzle,2,,1,,,Online

'''
import csv
from pathlib import Path
from argparse import ArgumentParser

def sort_order_options(items):
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

    return sorted(items, key=sort_key)

def parse_order_options(row):
    '''
    Gets the list of items ordered.
    This is expected to be in the field "Options"
    The field contains a comma seperate list of orders
    For example:
        Cheese,Juice Box, Pepperoni
    '''
    return [x.strip() for x in row['Options'].split(',')]

def main(args):
    with open(Path(args.src).resolve()) as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]

    # Get the set of all unique order options that can be made by a student
    order_options = []
    for row in data:
        order_options.extend(parse_order_options(row))
    order_options = sort_order_options(set(order_options))

    # Accumulate the total order for every student in the school
    # Keep only the fields that are of actual interest, strip the rest
    # of the noise and garbage in the SCO output
    output = {}
    for row in data:
        student_number = row['Student Number']
        if student_number in output:
            entry = output[student_number]
        else:
            student_name = row['Student Name'].split(',')
            entry = {
                'First Name': student_name[1].strip(),
                'Last Name': student_name[0].strip(),
                'Teacher':  row['HomeroomName'].split('-')[1].strip(),
            }
            for option in order_options:
                entry[option] = 0
            entry['Payment'] = 'Online'

        for order in parse_order_options(row):
            entry[order] += 1

        output[student_number] = entry

    # Replace zero orders with empty strings
    for entry in output.values():
        for order in order_options:
            if entry[order] == 0:
                entry[order] = ''

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
