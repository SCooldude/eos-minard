from minard.db import engine_nl, engine
from minard.detector_state import get_latest_run
from minard.polling import pmt_type, PMT_TYPES

def get_channel_flags(limit, run_range_low, run_range_high, summary, gold):
    """
    Returns a list of runs and 5 dictionaries using the run number as the keys.
    The dictionaries keep track of the number of sync16s, number of syn24s,
    number of out-of-sync channels, and number of missed count channels.
    """
    conn = engine_nl.connect()


    if not run_range_high:
        current_run = get_latest_run()
        result = conn.execute("SELECT DISTINCT ON (run) run, sync16, sync24, resync, timestamp, "
                              "missed_count_burst FROM channel_flags WHERE run > %s "
                              "ORDER BY run DESC, timestamp DESC", \
                              (current_run - limit))
        result_all = conn.execute("SELECT DISTINCT ON (crate, slot, channel, run) run, "
                              "cmos_sync16, cgt_sync24, missed_count, cmos_sync16_pr, "
                              "cgt_sync24_pr, crate, slot, channel, timestamp FROM channel_flags "
                              "WHERE run > %s ORDER BY crate, slot, channel, "
                              "run DESC, timestamp DESC", \
                              (current_run - limit))
    else:
        result = conn.execute("SELECT DISTINCT ON (run) run, sync16, sync24, resync, timestamp, "
                              "missed_count_burst FROM channel_flags WHERE run >= %s AND run <= %s "
                              "ORDER BY run DESC, timestamp DESC", \
                              (run_range_low, run_range_high))
        result_all = conn.execute("SELECT DISTINCT ON (crate, slot, channel, run) run, "
                              "cmos_sync16, cgt_sync24, missed_count, cmos_sync16_pr, "
                              "cgt_sync24_pr, crate, slot, channel, timestamp FROM channel_flags "
                              "WHERE run >= %s AND run <= %s ORDER BY crate, slot, channel, "
                              "run DESC, timestamp DESC", \
                              (run_range_low, run_range_high))


    rows = result.fetchall()

    # Keep track of the number of out-of-sync and missed count channels
    # by run number. Also looks at the type of PMT that has the issue.
    runs = []
    nsync16 = {}
    nsync24 = {}
    nresyncs = {}
    count_sync16 = {}
    count_sync24 = {}
    missed_count_burst = {}
    count_missed = {}
    count_sync16_pr = {}
    count_sync24_pr = {}
    count_normal = {}
    count_owl = {}
    count_other = {}
    timestamp = {}

    for run, sync16, sync24, resync, time, burst in rows:
        # Gold run selection
        if gold != 0 and run not in gold:
            continue
        runs.append(run)
        nsync16[run] = sync16
        nsync24[run] = sync24
        timestamp[run] = time
        nresyncs[run] = resync
        if burst is not None:
            missed_count_burst[run] = len(burst)
        else:
            missed_count_burst[run] = None


        # Start with 0 counts of each type
        count_sync16[run] = 0
        count_sync24[run] = 0
        count_missed[run] = 0
        count_sync16_pr[run] = 0
        count_sync24_pr[run] = 0
        count_normal[run] = 0
        count_owl[run] = 0
        count_other[run] = 0

    rows = result_all.fetchall()

    # Grab the PMT type if its asked for
    if not summary:
        detector_conn = engine.connect()
        types = pmt_type(detector_conn)

    for run, cmos_sync16, cgt_sync24, missed_count, cmos_sync16_pr, cgt_sync24_pr, crate, slot, channel, time in rows:
        # Gold run selection
        if gold != 0 and run not in gold:
            continue
        # Only the most recent information, per run
        if time != timestamp[run]:
            continue
        # Crate is None when no flags in the run
        if crate is not None and not summary:
            # PMT type indexed by lcn
            lcn = crate*512+slot*32+channel
            if types[lcn] in (PMT_TYPES['LOWG'], PMT_TYPES['FECD'], \
                              PMT_TYPES['BUTT'], PMT_TYPES['NONE']):
                count_other[run] += 1
            if types[lcn] in (PMT_TYPES['OWL'], PMT_TYPES['NECK']):
                count_owl[run] += 1
            if types[lcn] in (PMT_TYPES['HQE'], PMT_TYPES['NORMAL']):
                count_normal[run] += 1
        # Count the number of each issue
        if cmos_sync16 != 0 and cmos_sync16 is not None:
            count_sync16[run] += 1
        if cgt_sync24 != 0 and cgt_sync24 is not None:
            count_sync24[run] += 1
        if missed_count != 0 and missed_count is not None:
            count_missed[run] += 1
        if cmos_sync16_pr != 0 and cmos_sync16_pr is not None:
            count_sync16_pr[run] += 1
        if cgt_sync24_pr != 0 and cgt_sync24_pr is not None:
            count_sync24_pr[run] += 1

    return runs, nsync16, nsync24, nresyncs, count_sync16, count_sync24, count_missed, missed_count_burst, count_sync16_pr, count_sync24_pr, count_normal, count_owl, count_other

def get_channel_flags_by_run(run):
    """
    Returns a list of the missed count and out-of-sync channels
    for a requested run
    """
    conn = engine_nl.connect()
    detector_conn = engine.connect()

    # Find all of the out-of-sync and missed-count channels for the run selected
    result = conn.execute("SELECT DISTINCT ON (crate, slot, channel) crate, slot, channel, "
                          "cmos_sync16, cgt_sync24, missed_count, cmos_sync16_pr, "
                          "cgt_sync24_pr, missed_count_burst FROM channel_flags "
                          "WHERE run = %s ORDER BY crate, slot, channel, run DESC, timestamp DESC", \
                          int(run))

    rows = result.fetchall()

    list_sync16 = []
    list_sync24 = []
    list_missed = []
    list_sync16_pr = []
    list_sync24_pr = []
    missed_counts_burst = []
    count_normal = {}
    count_owl = {}
    count_other = {}
    count_normal[run] = 0
    count_owl[run] = 0
    count_other[run] = 0

    types = pmt_type(detector_conn)

    for crate, slot, channel, sync16, sync24, missed, sync16_pr, sync24_pr, missed_burst in rows:
        if crate is not None:
            lcn = crate*512+slot*32+channel
            if types[lcn] in (PMT_TYPES['LOWG'], PMT_TYPES['FECD'], \
                              PMT_TYPES['BUTT'], PMT_TYPES['NONE']):
                count_other[run] += 1
            if types[lcn] in (PMT_TYPES['OWL'], PMT_TYPES['NECK']):
                count_owl[run] += 1
            if types[lcn] in (PMT_TYPES['HQE'], PMT_TYPES['NORMAL']):
                count_normal[run] += 1
        if missed != 0 and missed is not None:
            list_missed.append((crate, slot, channel, missed))
        if sync16 != 0 and sync16 is not None:
            list_sync16.append((crate, slot, channel, sync16))
        if sync24 != 0 and sync24 is not None:
            list_sync24.append((crate, slot, channel, sync24))
        if sync16_pr != 0 and sync16_pr is not None:
            list_sync16_pr.append((crate, slot, channel, sync16_pr))
        if sync24_pr != 0 and sync24_pr is not None:
            list_sync24_pr.append((crate, slot, channel, sync24_pr))
        if missed_burst is not None:
            missed_counts_burst = missed_burst
        else:
            missed_counts_burst = []

    return list_missed, list_sync16, list_sync24, list_sync16_pr, list_sync24_pr, missed_counts_burst, count_normal, count_owl, count_other


def get_number_of_syncs(run):
    '''
    Get the number of sync16 and sync24s in a selected run
    '''

    conn = engine_nl.connect()

    result = conn.execute("SELECT run, sync16, sync24, resync FROM channel_flags "
                          "WHERE run = %s ORDER BY timestamp DESC limit 1", (run))

    rows = result.fetchall()

    nsync16s = -1
    nsync24s = -1
    resyncs = -1
    for run, sync16, sync24, resync in rows:
        nsync16s = sync16
        nsync24s = sync24
        resyncs = resync

    return nsync16s, nsync24s, resyncs

