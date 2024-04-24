from minard.db import engine_nl
from minard.detector_state import get_latest_run

def crate_gain_monitor(limit, selected_run, run_range_low, run_range_high, gold):
    """
    Returns a list of runs and the QHS peak by crate for a given set of runs
    """
    conn = engine_nl.connect()

    if not selected_run and not run_range_high:
        latest_run = get_latest_run()
        run = latest_run - limit
        result = conn.execute("SELECT DISTINCT ON (run, crate) "
            "run, crate, qhs_peak, qhs_peak_error FROM gain_monitor "
            "WHERE run > %s ORDER BY run DESC", (run,))
    elif run_range_high:
        result = conn.execute("SELECT DISTINCT ON (run, crate) "
            "run, crate, qhs_peak, qhs_peak_error FROM gain_monitor "
            "WHERE run >= %s AND run <=%s ORDER BY run DESC", \
            (run_range_low, run_range_high))
    else:
        result = conn.execute("SELECT DISTINCT ON (run, crate) "
            "run, crate, qhs_peak, qhs_peak_error "
            "FROM gain_monitor WHERE run = %s", (selected_run,))

    rows = result.fetchall()

    runs = []
    qhs_array = {}
    crate_array = {}
    for run, crate, qhs_peak, qhs_peak_error in rows:
        if gold != 0 and run not in gold:
            continue
        if run not in runs:
            runs.append(run)
        qhs_peak = round(qhs_peak, 1)
        qhs_peak_error = round(qhs_peak_error, 1)
        qhs_array[(run, crate)] = [qhs_peak, qhs_peak_error]
        # Keep track of which crates have data for which runs
        # This deals with offline crates.
        try:
            crate_array[run].append(crate)
        except Exception:
            crate_array[run] = [crate]

    return runs, qhs_array, crate_array

def crate_average(selected_run, run_limit):
    """
    Checks the gain of each crate based on the average.
    Returns a map of [run, crate] for runs where the crate
    QHS peak falls outside the average QHS peak
    calculated over run_limit runs.
    """
    conn = engine_nl.connect()

    SIGMA = 3
    run = selected_run - run_limit
    result = conn.execute("SELECT DISTINCT ON (run, crate) "
        "run, crate, qhs_peak, qhs_peak_error FROM gain_monitor "
        "WHERE run >= %s ORDER BY run DESC LIMIT 19*100", (run,))

    rows = result.fetchall()

    runs = []
    qhs_sum = [0]*19
    qhs_error_sum = [0]*19
    count = [0]*19
    qhs_run = {}

    for run, crate, qhs_peak, qhs_peak_error in rows:
        if run not in runs:
            runs.append(run)
        qhs_run[(run, crate)] = qhs_peak
        qhs_sum[crate] += qhs_peak
        qhs_error_sum[crate] += qhs_peak_error
        count[crate] += 1

    qhs_change = {}    

    for run in runs:
        for crate in range(19):
            try:
                qhs_average = qhs_sum[crate]/count[crate]
                qhs_average_error = qhs_error_sum[crate]/count[crate]
                qhs_diff = abs(qhs_run[(run, crate)] - qhs_average)
                if qhs_diff > SIGMA*qhs_average_error:
                    qhs_change[(run, crate)] = 1
            # Crate had no hits
            except KeyError:
                continue
            except ZeroDivisionError:
                continue

    return qhs_change

def crate_gain_history(run_range_low, run_range_high, crate, qhs_low, qhs_max):
    """
    Return a list of [run, qhs peak] for a specific crate
    and run range
    """
    conn = engine_nl.connect()

    result = conn.execute("SELECT DISTINCT ON (run, crate) "
        "run, qhs_peak FROM gain_monitor WHERE run >= %s AND "
        "run <= %s AND crate = %s ORDER BY run DESC ", \
        (run_range_low, run_range_high, crate))

    rows = result.fetchall()

    data = []
    for run, qhs_peak in rows:
        if qhs_peak > qhs_max or qhs_peak < qhs_low:
            continue
        data.append([int(run), qhs_peak])
 
    return data

