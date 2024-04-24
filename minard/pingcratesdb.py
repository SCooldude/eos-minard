from minard.db import engine_nl
from minard.detector_state import get_latest_run, get_mtc_state_for_run

def ping_crates_list(limit, selected_run, run_range_low, run_range_high, gold):
    '''
    Returns a list of ping crates information
    '''
    conn = engine_nl.connect()

    if not selected_run and not run_range_high:
        # Get all ping crates information from the nearline database since (run - limit)
        latest_run = get_latest_run()
        run = latest_run - limit
        result = conn.execute("SELECT DISTINCT ON (run) timestamp, run,  n100_crates_failed, "
                              "n20_crates_failed, n100_crates_warned, n20_crates_warned, "
                              "status FROM ping_crates WHERE run > %s "
                              "ORDER BY run, timestamp DESC", (run,))
    elif run_range_high:
        # Get all ping crates information from the nearline database over run range
        result = conn.execute("SELECT DISTINCT ON (run) timestamp, run,  n100_crates_failed, "
                              "n20_crates_failed, n100_crates_warned, n20_crates_warned, "
                              "status FROM ping_crates WHERE run >= %s AND run <= %s "
                              "ORDER BY run, timestamp DESC", (run_range_low, run_range_high))
    else:
        # Get all ping crates information from the nearline database for a selected run
        result = conn.execute("SELECT DISTINCT ON (run) timestamp, run,  n100_crates_failed, "
                              "n20_crates_failed, n100_crates_warned, n20_crates_warned, "
                              "status FROM ping_crates WHERE run = %s "
                              "ORDER BY run, timestamp DESC", (selected_run,))


    ping_info = []
    for timestamp, run, n100, n20, n100w, n20w, status in result:
        if gold != 0 and run not in gold:
            continue

        # Messages for the crate failures
        n100_fail_str=""
        n20_fail_str=""
        n100_warn_str=""
        n20_warn_str=""

        for i in range(len(n100)):
            n100_fail_str+=str(n100[i]) + ", "

        for i in range(len(n100w)):
            n100_warn_str+=str(n100w[i]) + ", "

        for i in range(len(n20)):
            n20_fail_str+=str(n20[i]) + ", " 

        for i in range(len(n20w)):
            n20_warn_str+=str(n20w[i]) + ", " 

        # Reformatting of the messages
        if n100_fail_str == "":
            n100_fail_str = "None"
        else:
            n100_fail_str = n100_fail_str[0:-2]

        if n20_fail_str == "":
            n20_fail_str = "None"
        else:
            n20_fail_str = n20_fail_str[0:-2]

        if n100_warn_str == "":
            n100_warn_str = "None"
        else:
            n100_warn_str = n100_warn_str[0:-2]

        if n20_warn_str == "":
            n20_warn_str = "None"
        else:
            n20_warn_str = n20_warn_str[0:-2]

        # parse timestamp format a little
        timestamp = str(timestamp)
        timestamp = timestamp[0:19]

        # A list of all the ping crates information
        ping_info.append((timestamp,int(run),n100_fail_str,n20_fail_str,n100_warn_str,n20_warn_str,status))

    # Sort by run-number, for display purposes
    ping_info = sorted(ping_info,key=lambda l:l[1], reverse=True)

    return ping_info

