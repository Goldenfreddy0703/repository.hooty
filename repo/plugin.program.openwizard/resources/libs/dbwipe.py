################################################################################
#  Empty the tables of a SQLite cache database, all-or-nothing.                #
#  Pure Python (no Kodi imports) so it can be unit-tested outside Kodi.        #
################################################################################

import pathlib
import sqlite3


def _table_names(con):
    return [row[0] for row in con.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'") if row[0]]


def count_rows(path):
    """Total rows over all tables of the database, read-only; None if it cannot be read."""
    try:
        con = sqlite3.connect(pathlib.Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=2)
    except sqlite3.Error:
        return None
    try:
        return sum(con.execute('SELECT COUNT(*) FROM "{0}"'.format(name.replace('"', '""'))).fetchone()[0]
                   for name in _table_names(con))
    except sqlite3.Error:
        return None
    finally:
        con.close()


def wipe_db(path, log=None, timeout=5):
    """Delete every row of every table in one transaction, then VACUUM.

    Returns the number of rows deleted, or None if nothing was deleted (the
    database could not be opened, was locked, or the transaction failed and was
    rolled back). A failing VACUUM is only logged: the rows are already gone.
    log, if given, is called as log(level, message) with level 'failed' or 'warning'.
    """
    def say(level, message):
        if log:
            log(level, message)

    try:
        # mode=rw: never create a missing file
        con = sqlite3.connect(pathlib.Path(path).resolve().as_uri() + '?mode=rw', uri=True,
                              timeout=timeout, isolation_level=None)
    except sqlite3.Error as e:
        say('failed', 'cannot open {0}: {1}'.format(path, e))
        return None
    try:
        tables = _table_names(con)
        deleted = 0
        con.execute('BEGIN IMMEDIATE')
        try:
            for name in tables:
                deleted += max(con.execute('DELETE FROM "{0}"'.format(name.replace('"', '""'))).rowcount, 0)
            con.execute('COMMIT')
        except sqlite3.Error:
            try:
                con.execute('ROLLBACK')
            except sqlite3.Error:
                pass
            raise
        try:
            con.execute('VACUUM')
        except sqlite3.Error as e:
            say('warning', 'rows deleted but VACUUM failed on {0}: {1}'.format(path, e))
        return deleted
    except sqlite3.Error as e:
        say('failed', 'nothing deleted from {0}: {1}'.format(path, e))
        return None
    finally:
        con.close()
