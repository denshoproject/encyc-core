from collections import OrderedDict
import unicodecsv
import sys

## Some files' XMP data is wayyyyyy too big
unicodecsv.field_size_limit(sys.maxsize)
CSV_DELIMITER = ','
CSV_QUOTECHAR = '"'
CSV_QUOTING = unicodecsv.QUOTE_ALL

def csv_reader(csvfile):
    """Get a csv.reader object for the file.
    
    @param csvfile: A file object.
    """
    reader = unicodecsv.reader(
        csvfile,
        delimiter=CSV_DELIMITER,
        quoting=CSV_QUOTING,
        quotechar=CSV_QUOTECHAR,
    )
    return reader

def make_row_dict(headers, row):
    """Turns CSV row into a dict with the headers as keys
    
    >>> headers0 = ['id', 'created', 'lastmod', 'title', 'description']
    >>> row0 = ['id', 'then', 'now', 'title', 'descr']
    {'title': 'title', 'description': 'descr', 'lastmod': 'now', 'id': 'id', 'created': 'then'}

    @param headers: List of header field names
    @param row: A single row (list of fields, not dict)
    @returns: OrderedDict
    """
    d = OrderedDict()
    for n in range(0, len(row)):
        d[headers[n]] = row[n]
    return d

def make_rowds(rows, row_start=0, row_end=9999999):
    """Takes list of rows (from csv lib) and turns into list of rowds (dicts)
    
    @param rows: list
    @returns: (headers, list of OrderedDicts)
    """
    headers = rows.pop(0)
    return headers, [make_row_dict(headers, row) for row in rows[row_start:row_end]]
