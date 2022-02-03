# these tables are created by wsgi.py if not existing
# can be reset from reset_DB.py

# timestamp format: 2014-10-18 21:31:12

create_enq_events_query = """CREATE TABLE IF NOT EXISTS enq_events (
index     SERIAL PRIMARY KEY,
name      VARCHAR(10) NOT NULL,
hash_ip   VARCHAR(32) NOT NULL,
anon_ip   VARCHAR(15) NOT NULL,
timestamp VARCHAR(19) NOT NULL
);
"""

enq_query_base = ("INSERT INTO _events (type, hash_ip, anon_ip,"
                      "timestamp) VALUES ('{name}', '{hash_ip}', '{anon_ip}',"
                      "'{timestamp}');")

