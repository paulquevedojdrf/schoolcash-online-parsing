"""Unit tests for schoolcash_parsing.tally.

Report fixtures live in tests/data; see tests/data/README.md for what each file exercises.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from schoolcash_parsing import tally

DATA = Path(__file__).parent / 'data'


def load(name: str) -> tally.Report:
    """Load a fixture report from tests/data."""
    return tally.load_report(DATA / name)


def test_parse_options_with_quantities() -> None:
    """Quantified, pluralised entries are counted by their leading number."""
    # Given: an Options string with quantities and plural item names
    options = "2 Cheese Slices, 1 Halal Pepperoni Slice, 3 Pepperoni Slices, 1 Juice Box, 2 'Yop' Yogurt Drinks"

    # When: it is parsed
    counts = tally.parse_options(options)

    # Then: each item gets its stated quantity and halal is not counted as plain pepperoni
    assert counts == {'Cheese': 2, 'Pepperoni': 3, 'Halal Pepperoni': 1, 'Juice Box': 1, 'Yop Yoghurt': 2}


def test_parse_options_without_quantities() -> None:
    """Entries with no leading number count as one each, and repeats accumulate."""
    # Given: the older Options format that lists each item once per unit with no quantity
    options = "Cheese Slice, Pepperoni Slice, Pepperoni Slice, 'Yop' Yogurt Drink"

    # When: it is parsed
    counts = tally.parse_options(options)

    # Then: every mention counts as one unit
    assert counts == {'Cheese': 1, 'Pepperoni': 2, 'Halal Pepperoni': 0, 'Juice Box': 0, 'Yop Yoghurt': 1}


def test_parse_options_rejects_unknown_item() -> None:
    """An item the tally has no column for is an error rather than silently dropped."""
    # Given: an Options string containing an item not on the menu
    options = '1 Cheese Slice, 1 Garlic Bread'

    # When: it is parsed
    # Then: a ValueError names the unrecognised entry
    with pytest.raises(ValueError, match='Garlic Bread'):
        tally.parse_options(options)


@pytest.mark.parametrize(
    ('homeroom', 'teacher'),
    [(' HRM01-KT2A-Macdonald', 'Macdonald'), ('HRM02-KTK1A-C-Pearson', 'Pearson'), ('Laurier', 'Laurier')],
)
def test_teacher_from_homeroom(homeroom: str, teacher: str) -> None:
    """The teacher is the final dash-separated segment of the homeroom code."""
    # Given: a homeroom code, possibly with leading whitespace or extra segments
    # When: the teacher is extracted
    result = tally.teacher_from_homeroom(homeroom)

    # Then: only the trailing surname is returned
    assert result == teacher


def test_load_report_reads_orders_and_skips_trailer() -> None:
    """The six orders in list-a.xlsx load, and the blank and 'Per Order' rows below them are skipped."""
    # Given: list-a.xlsx, six orders followed by a blank row and a summary row with no student number
    # When: it is loaded
    report = load('list-a.xlsx')

    # Then: only the six orders remain, with numbers as text and the homeroom's leading space stripped
    assert len(report.rows) == 6
    first = report.rows[0]
    assert first['Student Number'] == '930228762'
    assert first['Student Name'] == 'Lincoln, Abraham'
    assert first['HomeroomName'] == 'HRM01-KT2A-Macdonald'
    assert first['Paid Amount'] == '7'


def test_csv_and_xlsx_inputs_load_identically() -> None:
    """The same report loads to identical rows whether exported as CSV or Excel."""
    # Given: list-a as both .csv and .xlsx
    # When: both files are loaded
    from_csv = load('list-a.csv')
    from_xlsx = load('list-a.xlsx')

    # Then: the parsed rows are identical
    assert from_csv.rows == from_xlsx.rows


def test_load_report_rejects_unknown_extension(tmp_path: Path) -> None:
    """Only .xlsx and .csv inputs are accepted."""
    # Given: a file with an unsupported extension
    path = tmp_path / 'orders.txt'
    path.write_text('x')

    # When: it is loaded
    # Then: a ValueError explains the supported types
    with pytest.raises(ValueError, match='unsupported file type'):
        tally.load_report(path)


def test_subset_report_is_dropped() -> None:
    """list-b-early.csv is an earlier export of list-b.csv and is ignored."""
    # Given: list A, the early export of list B (5 orders, total 28) and the final list B (7 orders, total 40)
    reports = [load('list-a.csv'), load('list-b-early.csv'), load('list-b.csv')]

    # When: subset reports are removed
    kept, dropped = tally.drop_subset_reports(reports)

    # Then: the early export is dropped despite its different total columns, and the rest are kept
    assert [r.path.name for r in kept] == ['list-a.csv', 'list-b.csv']
    assert [r.path.name for r in dropped] == ['list-b-early.csv']


def test_overlapping_reports_are_both_kept() -> None:
    """Reports that each hold orders the other lacks are both kept."""
    # Given: list B, and a report holding list B's first 5 orders plus Abraham Lincoln's list A order
    list_a, list_b = load('list-a.csv'), load('list-b.csv')
    mixed = tally.Report(Path('mixed.csv'), list_b.rows[:5] + list_a.rows[:1])

    # When: subset reports are removed
    kept, dropped = tally.drop_subset_reports([mixed, list_b])

    # Then: neither is dropped
    assert kept == [mixed, list_b]
    assert not dropped


def test_identical_reports_keep_first() -> None:
    """Two exports with exactly the same orders are counted once."""
    # Given: list-a as xlsx and as csv, which hold the same orders
    first, second = load('list-a.xlsx'), load('list-a.csv')

    # When: subset reports are removed
    kept, dropped = tally.drop_subset_reports([first, second])

    # Then: the first is kept and the duplicate dropped
    assert kept == [first]
    assert dropped == [second]


def test_orders_for_same_student_are_summed() -> None:
    """Abraham Lincoln (930228762) has an order in list A and in list B, which coalesce into one row."""
    # Given: list A (Cheese, Pepperoni, Juice Box) and list B (1 Pepperoni) orders for 930228762
    rows = load('list-a.csv').rows + load('list-b.csv').rows

    # When: the tally is built
    result = tally.build_tally(rows)

    # Then: one entry holds both orders' items
    entry = result['930228762']
    assert entry.order_count == 2
    assert entry.counts == {'Cheese': 1, 'Pepperoni': 2, 'Halal Pepperoni': 0, 'Juice Box': 1, 'Yop Yoghurt': 0}


def test_students_sharing_a_name_stay_separate() -> None:
    """The two students named George Bush have different student numbers and are not merged."""
    # Given: list B, with George Bush 939845296 (Laurier) and George Bush 956218302 (Pearson)
    rows = load('list-b.csv').rows

    # When: the tally is built
    result = tally.build_tally(rows)

    # Then: each student number keeps its own teacher and items
    laurier, pearson = result['939845296'], result['956218302']
    assert (laurier.first_name, laurier.last_name, laurier.teacher) == ('George', 'Bush', 'Laurier')
    assert (pearson.first_name, pearson.last_name, pearson.teacher) == ('George', 'Bush', 'Pearson')
    assert laurier.counts == {'Cheese': 0, 'Pepperoni': 2, 'Halal Pepperoni': 0, 'Juice Box': 1, 'Yop Yoghurt': 0}
    assert pearson.counts == {'Cheese': 1, 'Pepperoni': 0, 'Halal Pepperoni': 0, 'Juice Box': 0, 'Yop Yoghurt': 0}


def test_validate_passes_when_prices_match() -> None:
    """List A ($30) and list B ($40) reconcile with their tally."""
    # Given: list A and list B, every order paid at the correct price
    reports = [load('list-a.csv'), load('list-b.csv')]

    # When: the tally is built and validated
    result = tally.validate(reports, tally.build_tally(r for report in reports for r in report.rows))

    # Then: the tally value equals the $70 paid and nothing is flagged
    assert result.ok
    assert result.tally_total == result.paid_total == Decimal(70)


def test_validate_flags_mispriced_order() -> None:
    """An order whose paid amount disagrees with its items is reported."""
    # Given: mispriced.csv, where George Washington (914673169) paid $4 for one $3 Cheese Slice
    report = load('mispriced.csv')

    # When: the tally is built and validated
    result = tally.validate([report], tally.build_tally(report.rows))

    # Then: validation fails and names only that student
    assert not result.ok
    assert len(result.row_mismatches) == 1
    assert '914673169' in result.row_mismatches[0]


def test_validate_flags_report_total_mismatch() -> None:
    """A report whose declared Total Paid Amount disagrees with its orders is reported."""
    # Given: bad-total.csv, whose orders sum to $15 but whose Total Paid Amount says $99
    report = load('bad-total.csv')

    # When: the tally is built and validated
    result = tally.validate([report], tally.build_tally(report.rows))

    # Then: the report-level mismatch is flagged and no order is
    assert not result.ok
    assert not result.row_mismatches
    assert len(result.report_mismatches) == 1


def test_zero_counts_render_blank() -> None:
    """Items a student did not order are written as empty cells rather than 0."""
    # Given: a tally entry with one item ordered and the rest at zero
    entry = tally.StudentTally('George', 'Washington', 'Macdonald')
    entry.counts['Pepperoni'] = 2

    # When: it is rendered as an output row
    row = entry.as_output_row()

    # Then: the ordered item shows its count and every other item is blank
    assert row['Pepperoni'] == 2
    assert all(row[item] == '' for item in tally.ITEMS if item != 'Pepperoni')


def test_main_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Mixed xlsx and csv inputs with a subset revision produce exactly expected-tally.csv."""
    # Given: list-a.xlsx, list-b-early.csv and list-b.csv
    inputs = [DATA / 'list-a.xlsx', DATA / 'list-b-early.csv', DATA / 'list-b.csv']
    output = tmp_path / 'tally.csv'

    # When: the command line entry point runs over all three inputs
    exit_code = tally.main([str(p) for p in inputs] + ['-o', str(output)])

    # Then: it succeeds, ignores the early export, and writes the expected tally
    assert exit_code == 0
    assert 'ignoring list-b-early.csv' in capsys.readouterr().err
    expected = (DATA / 'expected-tally.csv').read_text(encoding='utf-8')
    assert output.read_text(encoding='utf-8') == expected
