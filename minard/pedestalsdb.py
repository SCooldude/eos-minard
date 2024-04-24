from minard.db import engine

def get_pedestals(crate, slot, channel):
    '''
    Get the average QHS/QHL/QLX for a give C/C/C to post to the channel status.
    '''
    conn = engine.connect()

    result = conn.execute("SELECT DISTINCT ON (crate, slot, channel, cell) "
        "qhs_avg, qhl_avg, qlx_avg FROM pedestals WHERE "
        "crate = %s AND slot = %s AND channel = %s ORDER "
        "BY crate, slot, channel, cell, timestamp DESC", (crate, slot, channel))

    rows = result.fetchall()

    qhs_ped = []
    qhl_ped = []
    qlx_ped = []
    for qhs, qhl, qlx in rows:
        qhs_ped.append(qhs)
        qhl_ped.append(qhl)
        qlx_ped.append(qlx)

    return qhs_ped, qhl_ped, qlx_ped

def qhs_by_channel(crate, slot, channel, cell):
    '''
    Get the QHS values for every pedestal, which is histogrammed.
    '''
    conn = engine.connect()

    result = conn.execute("SELECT DISTINCT ON (crate, slot, channel, cell) "
        "qhs, slot, channel, cell FROM pedestals WHERE crate = %s  "
        "ORDER BY crate, slot, channel, cell, timestamp DESC", (crate,))

    rows = result.fetchall()

    qhs_ = []
    for qhs, s, ch, ce in rows:
        if slot != -1 and s != slot:
            continue
        if channel != -1 and ch != channel:
            continue
        if cell != -1 and ce != cell:
            continue
        for i in qhs:
            qhs_.append(i)

    return qhs_

def bad_pedestals(crate, slot, channel, cell, charge_type, qmax, qmin, limit):
    '''
    Get information about the pedestals outside a given range for QHS/QHL/QLX.
    '''
    conn = engine.connect()

    result = conn.execute("SELECT DISTINCT ON (crate, slot, channel, cell) "
        "crate, slot, channel, cell, qhs_avg, qhl_avg, qlx_avg, num_events FROM pedestals "
        "WHERE (%s > %d OR %s < %d) AND crate = %d ORDER BY crate, slot, channel, cell, "
        "timestamp DESC LIMIT %d" % (charge_type, qmax, charge_type, qmin, crate, limit))

    rows = result.fetchall()

    bad_pedestals = []
    for c, s, ch, ce, qhs, qhl, qlx, npeds in rows:
        if slot != -1 and s != slot:
            continue
        if channel != -1 and ch != channel:
            continue
        if cell != -1 and ce != cell:
            continue
        bad_pedestals.append((c, s, ch, ce, qhs, qhl, qlx, npeds))

    return bad_pedestals
