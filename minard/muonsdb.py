from minard.db import engine_nl
from minard.detector_state import get_latest_run
import time

TZERO = 14610*24*3600

def get_muons(limit, selected_run, run_range_low, run_range_high, gold, atm):
    """
    Returns a list of muon gtids for either a run list or a selected run
    """
    conn = engine_nl.connect()

    runs = []

    if not selected_run and not run_range_high:
        current_run = get_latest_run()
        run_range = current_run - limit
        # This missed muon array can be very long, so just select on its length
        if not atm:
            result = conn.execute("SELECT DISTINCT ON (a.run) a.run, a.gtids, a.days, a.secs, a.nsecs, "
                                  "array_length(b.gtids, 1), c.gtids FROM muons AS a LEFT JOIN missed_muons "
                                  "AS b ON a.run=b.run LEFT JOIN atmospherics AS c ON a.run=c.run "
                                  "WHERE a.run >= %s ORDER BY a.run DESC, a.timestamp DESC, b.timestamp DESC, " 
                                  "c.timestamp DESC", (run_range,))
        else:
            result = conn.execute("SELECT DISTINCT ON (a.run) a.run, b.gtids, b.days, b.secs, b.nsecs, "
                                  "array_length(c.gtids, 1), a.gtids FROM atmospherics "
                                  "AS a INNER JOIN muons AS b ON a.run=b.run INNER JOIN "
                                  "missed_muons AS c ON a.run=c.run WHERE array_length(a.gtids, 1) > 0 "
                                  "AND a.run >= %s ORDER BY a.run DESC, a.timestamp DESC, b.timestamp DESC, "
                                  "c.timestamp DESC", (run_range,))
        status = conn.execute("SELECT DISTINCT ON (run) run, muon_time_in_range, missed_muon_time_in_range, "
                              "atmospheric_time_in_range FROM time_check WHERE run >= %s "
                              "ORDER BY run DESC, timestamp DESC", (run_range,))
    elif run_range_high:
        if not atm:
            result = conn.execute("SELECT DISTINCT ON (a.run) a.run, a.gtids, a.days, a.secs, a.nsecs, "
                                  "array_length(b.gtids, 1), c.gtids FROM muons AS a LEFT JOIN missed_muons "
                                  "AS b ON a.run=b.run LEFT JOIN atmospherics AS c ON a.run=c.run "
                                  "WHERE a.run >= %s AND a.run <= %s ORDER BY a.run DESC, a.timestamp DESC, "
                                  "b.timestamp DESC, c.timestamp DESC", (run_range_low, run_range_high))
        else:
            result = conn.execute("SELECT DISTINCT ON (a.run) a.run, b.gtids, b.days, b.secs, b.nsecs, "
                                  "array_length(c.gtids, 1), a.gtids FROM atmospherics "
                                  "AS a INNER JOIN muons AS b ON a.run=b.run INNER JOIN "
                                  "missed_muons AS c ON a.run=c.run WHERE array_length(a.gtids, 1) > 0 "
                                  "AND a.run >= %s AND a.run <= %s ORDER BY a.run DESC, a.timestamp DESC, "
                                  "b.timestamp DESC, c.timestamp DESC", (run_range_low, run_range_high))
        status = conn.execute("SELECT DISTINCT ON (run) run, muon_time_in_range, missed_muon_time_in_range, "
                              "atmospheric_time_in_range FROM time_check WHERE run >= %s AND "
                              "run <= %s ORDER BY run DESC, timestamp DESC", (run_range_low, run_range_high)) 
    else:
        result = conn.execute("SELECT DISTINCT ON (a.run) a.run, a.gtids, a.days, a.secs, a.nsecs, "
                              "array_length(b.gtids, 1), c.gtids FROM muons AS a LEFT JOIN missed_muons "
                              "AS b ON a.run=b.run LEFT JOIN atmospherics AS c ON a.run=c.run "
                              "WHERE a.run = %s ORDER BY a.run, a.timestamp DESC, b.timestamp DESC, " 
                              "c.timestamp DESC", (selected_run,))
        status = conn.execute("SELECT DISTINCT ON (run) run, muon_time_in_range, missed_muon_time_in_range, "
                              "atmospheric_time_in_range FROM time_check WHERE run = %s ORDER BY run, " 
                              "timestamp DESC", (selected_run,)) 

    rows = result.fetchall()

    muon_count = {}
    mmuon_count = {}
    atm_count = {}
    livetime_lost = {} 
    fake = {}
    check_time = {}

    for run, agtids, adays, asecs, ansecs, bgtids, cgtids in rows:

        # Check if the run is on the gold list
        if gold != 0 and run not in gold:
            continue

        runs.append(run)
        check_time[run] = "-"

        if agtids is None:
            continue

        # Check if we inserted a fake muon
        if len(agtids) > 0 and agtids[0] == -1:
            fake[run] = 1
        muon_count[run] = len(agtids)
        # array_length returns None for size zero arrays
        if bgtids is None:
            mmuon_count[run] = 0
        else:
            mmuon_count[run] = bgtids
        # Calculate livetime lost to muons, which are the dominant source
        livetime_lost[run] = calculate_livetime_lost(adays, asecs, ansecs)
        # Lots of unprocessed runs, so check to make sure 
        if cgtids is not None:
            atm_count[run] = len(cgtids)
            continue
        atm_count[run] = "Not Processed"

    check = status.fetchall()
    for run, muon_status, mm_status, atm_status in check:
        check_time[run] = (muon_status and mm_status and atm_status)

    return runs, muon_count, mmuon_count, atm_count, livetime_lost, fake, check_time


def get_muon_info_by_run(selected_run):
    '''
    Get the GTID and time for each identified muon in the run
    '''
    conn = engine_nl.connect()

    result = conn.execute("SELECT DISTINCT ON (a.run) a.gtids, a.days, a.secs, a.nsecs, "
                          "b.gtids, b.days, b.secs, b.nsecs, c.gtids, c.days, c.secs, "
                          "c.nsecs, c.followers FROM muons AS a LEFT JOIN missed_muons "
                          "AS b ON a.run=b.run LEFT JOIN atmospherics AS c ON a.run=c.run "
                          "WHERE a.run = %s ORDER BY a.run, a.timestamp DESC, "
                          "b.timestamp DESC, c.timestamp DESC",  (selected_run,))

    rows = result.fetchall()

    muons = []
    mmuons = []
    atm = []

    for agtids, adays, asecs, ansecs, \
        bgtids, bdays, bsecs, bnsecs, \
        cgtids, cdays, csecs, cnsecs, cfollowers in rows:

        muons  = make_info(adays, asecs, ansecs, agtids)
        mmuons = make_info(bdays, bsecs, bnsecs, bgtids)
        atm    = make_info(cdays, csecs, cnsecs, cgtids, cfollowers)

    return muons, mmuons, atm 


def make_info(days, secs, nsecs, gtids, followers=None):
    """
    Append all the information to a single array
    """
    array = []
    if gtids is None:
        array.append(('Not Processed', '-'))
        return array
    for t in range(len(days)):
        total_secs = TZERO + days[t]*24*3600 + secs[t] + float(nsecs[t])/1e9
        stime = time.strftime("%Y/%m/%d %H:%M:%S ", time.localtime(total_secs))
        if followers:
            array.append((gtids[t], stime, followers[t]))
            continue
        array.append((gtids[t], stime))

    return array


def calculate_livetime_lost(days, secs, nsecs):
    """
    Calculate the livetime lost to muons. Account for overlap.
    """
    livetime_lost = 0
    livetime = []
    for t in range(len(days)):
        time = days[t]*24*3600 + secs[t] + float(nsecs[t])/1e9
        livetime.append(time)
        if t == 0:
            livetime_lost = 20
        elif(livetime[t] > livetime[t-1] + 20):
            livetime_lost += 20
        else:
            livetime_lost += int((livetime[t] - livetime[t-1]))

    return livetime_lost


