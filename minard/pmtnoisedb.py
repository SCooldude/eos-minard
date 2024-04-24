from minard.db import engine_nl
from datetime import datetime
from minard.tools import total_seconds

SECOND_PER_DAY = 24*60*60
SECOND_PER_MICROSECOND = 1e-6

# turn a sql result into a list of dicts
def dictify(rows):
    keys = rows.keys()
    rv = []
    for row in rows:
        d = {}
        for k in keys:
            d[k] = row[k]
        rv.append(d)
    return rv

def get_noise_results(limit=100, offset=0):
    epoch = datetime(1970, 1, 1)
    conn = engine_nl.connect()
    rows = conn.execute('SELECT * FROM pmtnoise '
                        'ORDER BY run_number DESC '
                        'LIMIT %s OFFSET %s;', (limit, offset))
    rows = dictify(rows)
    for row in rows:
        row['display_time'] = str(row['timestamp'])[:-6]
        delta = (row['timestamp'].replace(tzinfo=None) - row['timestamp'].utcoffset() - epoch)
        row['plot_time'] = total_seconds(delta)
    return rows

def get_run_by_number(run):
    conn = engine_nl.connect()
    rows = conn.execute('SELECT * FROM pmtnoise WHERE %s = run_number;', \
                        (int(run)))
    return dictify(rows)
