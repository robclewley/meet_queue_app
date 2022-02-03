#!/usr/bin/env python
from queue_app import sql_defs as sql
from queue_app import utils
import sys

def reset_DBs(db_url):
    """Running outside of app will need an explicit DB url
    """
    drop_query_template = "DROP TABLE {};"
    tables = ['enq_events']
    for tab in tables:
        utils.change_sql(drop_query_template.format(tab), db_url)
    utils.change_sql(sql.create_enq_events_query, db_url)

if __name__ == "__main__":
    try:
        reset_DBs(sys.argv[1])
    except KeyError:
        print("Invalid arguments. Must pass full DB url to file")
        sys.exit(2)
    else:
        print("All DBs reset")
