from aping_pong.flask_server import app as application
from aping_pong.sql_defs import (create_game_event_query,
             create_game_summary_query, create_players_query,
             create_anon_IP_event_query)
from flask_cors import CORS
from scout_apm.flask import ScoutApm # in-app monitoring

import os
import redis
import aping_pong.utils as utils

application.config['SCOUT_MONITOR'] = True
application.config['SCOUT_KEY']     = "ZYmwhSYt2DpZc0CISjaX"
application.config['SCOUT_NAME']    = "APIng pong"

ScoutApm(application)

cors = CORS(application, resources={r"/*": {"origins": "*"}})
utils.change_sql(create_game_event_query)
utils.change_sql(create_game_summary_query)
utils.change_sql(create_players_query)
utils.change_sql(create_anon_IP_event_query)
#utils.change_sql("TRUNCATE TABLE players;")
#utils.change_sql("ALTER SEQUENCE players_index_seq RESTART WITH 1;")
#utils.change_sql("TRUNCATE TABLE game_summary;")
#utils.change_sql("ALTER SEQUENCE game_summary_index_seq RESTART WITH 1;")
#utils.change_sql("TRUNCATE TABLE game_event_log;")
#utils.change_sql("ALTER SEQUENCE game_event_log_index_seq RESTART WITH 1;")
#utils.change_sql("TRUNCATE TABLE anon_ip_events;")
#utils.change_sql("ALTER SEQUENCE anon_ip_events_index_seq RESTART WITH 1;")

