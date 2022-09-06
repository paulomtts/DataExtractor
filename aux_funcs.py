from xlsxwriter.utility import xl_col_to_name
from dateutil import parser as dtpr
from datetime import datetime
from re import findall

# FORMATTING ##############################################
def format_date(date: str):  
    if date is not None:
        try:
            date = dtpr.parse(date)
            return datetime.strptime(datetime.isoformat(date), '%Y-%m-%dT%H:%M:%S').date()
        except:
            raise TypeError(f'Coult not format input into a date.')


def format_number(number: str):
    ptt = '((?P<numbers>[0-9]{0,3})*)'
    lst = [num for num, _ in findall(ptt, number) if num != '']
    try:
        return float(''.join(lst[:-1]) + '.' + lst[-1])
    except:
        raise TypeError(f"Input {number!r} is not a number or contains no numbers.")