"""Build a per-student order tally from School Cash Online item order reports.

Each input report (.xlsx or .csv) holds one row per order with the ordered items encoded in the
``Options`` column, e.g. ``2 Cheese Slices, 1 'Yop' Yogurt Drink``. Orders are coalesced by student
number so that students sharing a name are never merged. When one report is a subset of another
(e.g. an earlier export of a revised list) the subset is ignored so its orders are not counted twice.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Sequence

import openpyxl

Row = dict[str, str]

COL_STUDENT_NUMBER = 'Student Number'
COL_STUDENT_NAME = 'Student Name'
COL_HOMEROOM = 'HomeroomName'
COL_OPTIONS = 'Options'
COL_PAID = 'Paid Amount'
COL_TOTAL_PAID = 'Total Paid Amount'

# Report-level summary columns repeat the same value on every row and differ between exports of the
# same list, so they are excluded when deciding whether two rows describe the same order.
SUMMARY_COLUMN_PREFIX = 'Total '

# Output item columns mapped to the lowercase text that identifies them in the Options column.
# Order matters: "halal pepperoni" must be tested before "pepperoni".
ITEM_PATTERNS: tuple[tuple[str, str], ...] = (
    ('Halal Pepperoni', 'halal pepperoni'),
    ('Pepperoni', 'pepperoni'),
    ('Cheese', 'cheese'),
    ('Juice Box', 'juice'),
    ('Yop Yoghurt', 'yop'),
)

PRICES: dict[str, Decimal] = {
    'Cheese': Decimal(3),
    'Pepperoni': Decimal(3),
    'Halal Pepperoni': Decimal(3),
    'Juice Box': Decimal(1),
    'Yop Yoghurt': Decimal(2),
}

ITEMS: tuple[str, ...] = ('Cheese', 'Pepperoni', 'Halal Pepperoni', 'Juice Box', 'Yop Yoghurt')
OUTPUT_COLUMNS: tuple[str, ...] = ('First Name', 'Last Name', 'Teacher') + ITEMS

_QUANTITY_RE = re.compile(r'^(\d+)\s+(.*)$')


@dataclass
class Report:
    """One input file and its order rows."""

    path: Path
    rows: list[Row]

    def signatures(self) -> set[tuple[tuple[str, str], ...]]:
        """Return the set of order identities in this report, ignoring report-level summary columns."""
        return {order_signature(row) for row in self.rows}


@dataclass
class StudentTally:
    """Accumulated item counts for one student."""

    first_name: str
    last_name: str
    teacher: str
    counts: dict[str, int] = field(default_factory=lambda: {item: 0 for item in ITEMS})
    order_count: int = 0

    def as_output_row(self) -> dict[str, str | int]:
        """Return the tally as a row keyed by OUTPUT_COLUMNS, with zero counts left blank."""
        counts = {item: qty or '' for item, qty in self.counts.items()}
        return {'First Name': self.first_name, 'Last Name': self.last_name, 'Teacher': self.teacher, **counts}


@dataclass
class ValidationResult:
    """Outcome of checking the tally against the amounts paid."""

    tally_total: Decimal
    paid_total: Decimal
    row_mismatches: list[str]
    report_mismatches: list[str]

    @property
    def ok(self) -> bool:
        """True when every order and report reconciles and the grand totals agree."""
        return self.tally_total == self.paid_total and not self.row_mismatches and not self.report_mismatches


def _cell_to_str(value: object) -> str:
    """Normalise a spreadsheet cell so xlsx and csv inputs compare equal."""
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _rows_from_table(table: Iterable[Sequence[object]]) -> list[Row]:
    """Convert a header-first table into row dicts, dropping rows without a student number."""
    iterator = iter(table)
    try:
        header = [_cell_to_str(cell) for cell in next(iterator)]
    except StopIteration:
        return []
    rows = []
    for raw in iterator:
        row = {name: _cell_to_str(cell) for name, cell in zip(header, raw) if name}
        if row.get(COL_STUDENT_NUMBER):
            rows.append(row)
    return rows


def load_report(path: Path) -> Report:
    """Load an order report from an .xlsx (first worksheet) or .csv file."""
    suffix = path.suffix.lower()
    if suffix in ('.xlsx', '.xlsm'):
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            rows = _rows_from_table(workbook.worksheets[0].iter_rows(values_only=True))
        finally:
            workbook.close()
    elif suffix == '.csv':
        with path.open(newline='', encoding='utf-8-sig') as handle:
            rows = _rows_from_table(csv.reader(handle))
    else:
        raise ValueError(f'{path}: unsupported file type {suffix!r}; expected .xlsx or .csv')
    return Report(path=path, rows=rows)


def order_signature(row: Row) -> tuple[tuple[str, str], ...]:
    """Identity of an order, built from every column except report-level summary columns."""
    return tuple(sorted((k, v) for k, v in row.items() if not k.startswith(SUMMARY_COLUMN_PREFIX)))


def drop_subset_reports(reports: Sequence[Report]) -> tuple[list[Report], list[Report]]:
    """Split reports into (kept, dropped), dropping any report whose orders all appear in another kept report.

    When two reports hold exactly the same orders, the first one given is kept.
    """
    signatures = [report.signatures() for report in reports]
    kept: list[Report] = []
    dropped: list[Report] = []
    for i, report in enumerate(reports):
        is_subset = any(
            j != i and signatures[i] <= signatures[j] and (signatures[i] != signatures[j] or j < i)
            for j in range(len(reports))
        )
        (dropped if is_subset else kept).append(report)
    return kept, dropped


def parse_options(options: str) -> dict[str, int]:
    """Parse an Options string such as ``2 Cheese Slices, 1 Juice Box`` into item counts.

    An entry without a leading quantity counts as one.
    """
    counts = {item: 0 for item in ITEMS}
    for entry in options.split(','):
        entry = entry.strip()
        if not entry:
            continue
        match = _QUANTITY_RE.match(entry)
        quantity, name = (int(match.group(1)), match.group(2)) if match else (1, entry)
        lowered = name.lower()
        item = next((item for item, pattern in ITEM_PATTERNS if pattern in lowered), None)
        if item is None:
            raise ValueError(f'unrecognised item {entry!r} in options {options!r}')
        counts[item] += quantity
    return counts


def order_cost(counts: dict[str, int]) -> Decimal:
    """Price an order's item counts using PRICES."""
    return sum((PRICES[item] * qty for item, qty in counts.items()), Decimal(0))


def parse_money(text: str) -> Decimal:
    """Parse an amount such as ``7``, ``7.00`` or ``$7.00``."""
    return Decimal(text.replace('$', '').replace(',', '').strip() or '0')


def split_name(student_name: str) -> tuple[str, str]:
    """Split ``Last, First`` into (first, last). A name without a comma is treated as a last name."""
    last, _, first = student_name.partition(',')
    return first.strip(), last.strip()


def teacher_from_homeroom(homeroom: str) -> str:
    """Return the teacher surname, the final dash-separated segment of the homeroom code."""
    return homeroom.strip().rsplit('-', 1)[-1].strip()


def build_tally(rows: Iterable[Row]) -> dict[str, StudentTally]:
    """Coalesce order rows into one tally per student number."""
    tally: dict[str, StudentTally] = {}
    for row in rows:
        student_number = row[COL_STUDENT_NUMBER]
        entry = tally.get(student_number)
        if entry is None:
            first, last = split_name(row.get(COL_STUDENT_NAME, ''))
            entry = StudentTally(first, last, teacher_from_homeroom(row.get(COL_HOMEROOM, '')))
            tally[student_number] = entry
        for item, qty in parse_options(row.get(COL_OPTIONS, '')).items():
            entry.counts[item] += qty
        entry.order_count += 1
    return tally


def validate(reports: Sequence[Report], tally: dict[str, StudentTally]) -> ValidationResult:
    """Check the tally against the amounts paid, per order, per report and in total."""
    row_mismatches = []
    report_mismatches = []
    paid_total = Decimal(0)
    for report in reports:
        report_paid = Decimal(0)
        for row in report.rows:
            paid = parse_money(row.get(COL_PAID, ''))
            cost = order_cost(parse_options(row.get(COL_OPTIONS, '')))
            if cost != paid:
                row_mismatches.append(
                    f'{report.path.name}: student {row[COL_STUDENT_NUMBER]} options {row.get(COL_OPTIONS)!r} '
                    f'cost {cost} but paid {paid}'
                )
            report_paid += paid
        declared = report.rows[0].get(COL_TOTAL_PAID) if report.rows else None
        if declared and parse_money(declared) != report_paid:
            report_mismatches.append(f'{report.path.name}: {COL_TOTAL_PAID} {declared} but orders sum to {report_paid}')
        paid_total += report_paid
    tally_total = sum((order_cost(entry.counts) for entry in tally.values()), Decimal(0))
    return ValidationResult(tally_total, paid_total, row_mismatches, report_mismatches)


def write_tally(tally: dict[str, StudentTally], output: Path) -> None:
    """Write the tally as CSV, sorted by teacher then student name."""
    entries = sorted(tally.values(), key=lambda e: (e.teacher, e.last_name, e.first_name))
    with output.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(entry.as_output_row() for entry in entries)


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point. Returns 0 when the tally reconciles with the amounts paid, else 1."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('inputs', nargs='+', type=Path, help='order reports (.xlsx or .csv)')
    parser.add_argument('-o', '--output', type=Path, required=True, help='tally CSV to write')
    args = parser.parse_args(argv)

    reports = [load_report(path) for path in args.inputs]
    kept, dropped = drop_subset_reports(reports)
    for report in dropped:
        print(f'ignoring {report.path.name}: every order in it appears in another input', file=sys.stderr)

    rows = [row for report in kept for row in report.rows]
    tally = build_tally(rows)
    write_tally(tally, args.output)

    for number, entry in tally.items():
        if entry.order_count > 1:
            print(
                f'note: student {number} ({entry.first_name} {entry.last_name}) has {entry.order_count} orders, summed',
                file=sys.stderr,
            )

    result = validate(kept, tally)
    for message in result.row_mismatches + result.report_mismatches:
        print(f'MISMATCH {message}', file=sys.stderr)
    totals = {item: sum(entry.counts[item] for entry in tally.values()) for item in ITEMS}
    print(f'wrote {len(tally)} students to {args.output}')
    print('item totals: ' + ', '.join(f'{item} {qty}' for item, qty in totals.items()))
    print(f'tally value ${result.tally_total}, paid ${result.paid_total}: {"OK" if result.ok else "MISMATCH"}')
    return 0 if result.ok else 1


if __name__ == '__main__':
    sys.exit(main())
