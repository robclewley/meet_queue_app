from flask import (Flask, request, render_template, render_template_string,
     redirect, url_for, flash, session)
from flask_bootstrap import Bootstrap
import os
# support cross-domain browser interfaces avoiding AJAX limitations
from flask_jsonpify import jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import datetime
from time import sleep, time
import json
#import json # TEMP for testing
from functools import wraps
from copy import copy
from queue_app import utils
import uuid
from queue_app.logger import log
from queue_app import common as common

app = Flask("Queue management server")
Bootstrap(app)

# ------------------------------------------------------------------

# used by Limiter
def get_id():
    return request.args.get('private_id', default="None", type=str)

def get_identity():
    private_id = get_id()
    if private_id is None:
        # try from path
        private_id = request.path.split('/')[0]
        if private_id == '':
            # no id, so just use IP address
            return get_remote_address()
        elif len(private_id) == 32:
            # is it really an ID? There are no other 32-char endpoints
            # so this is good enough
            return private_id
        else:
            # not a command
            return get_remote_address()
    else:
        return private_id

limiter = Limiter(
    app,
    key_func=get_identity,
    default_limits=["{} per second".format(common.CALLS_PER_SECOND)]
)

# ==================


def get_IP(as_str=False):
    #output = '1)' + request.environ['REMOTE_ADDR'] + ' 2) ' + request.remote_addr + ' 3) ' + request.environ.get('HTTP_X_REAL_IP', request.remote_addr) + ' 4)' + request.headers['X-Forwarded-For']
    try:
        ip_addr = str(request.headers['X-Forwarded-For'])
    except:
        ip_addr = str(request.remote_addr)
    if as_str:
        return ip_addr
    else:
        return ip_addr.encode('utf-8')


def returns_json(f):
    """Also assumes that private_id is a first argument for the endpoints.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #log.info("Entered returns_json")
        try:
            # in case provided as first part of path (see id_in_path wrapper
            # only if used)
            private_id = kwargs.pop('private_id')
            #log.info("pID from path: {}".format(private_id))
        except KeyError:
            # must then be provided as a parameter
            private_id = request.args.get('private_id', default=None)
            #log.info("pID from parameter: {}".format(private_id))
        if private_id is not None and len(private_id) != 32:
            return jsonify({"ERROR": "Invalid private id"})
        else:
            try:
                return jsonify(json.loads(f(private_id, *args, **kwargs)))
            except Exception as err:
                #raise
                return jsonify({"ERROR": str(err)})
    return decorated_function

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_admin = request.args.get('admin_code', default=0, type=int) \
              == 9134999136054730161
        if is_admin:
            try:
                data = json.loads(f(*args, **kwargs))
            except Exception as err:
                data = {"ERROR": str(err)}
            return jsonify(data)
        else:
            return ''
    return decorated_function


def no_http(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # reset last message
        app._last_msg = None
        no_http = request.args.get('cli', default=False, type=bool)
        kwargs['no_http'] = no_http
        try:
            http = f(*args, **kwargs)
            success = True
        except:
            http = ''
            success = False
        if no_http:
            if app._last_msg is None:
                data = {"success": success}
            else:
                # make a copy
                data = {}
                data.update(app._last_msg)
                log.info(f"no http data = {data}")
            # reset last message
            app._last_msg = None
            return jsonify(data)
        else:
            return http
    return decorated_function

def do_messaging(content, is_admin=False):
    content['client'] = app._this_instance
    content['_call_time'] = t0 = time()
    log.info("do_messaging content = " + str(content))
    if is_admin:
        channel = 'admin'
    else:
        channel = 'player-in'
#     log.info("*************")
#     for k, v in content.items():
#         log.info("Key: {} {}".format(k, type(k)))
#         log.info("Val: {} {}".format(v, type(v)))
    app._rq.publish(channel, json.dumps(content))
    t_wait = 0
    while t_wait < 3:
        # wait for response
        state = app._p.get_message("client-"+app._this_instance)
        if state is not None:
            data = json.loads(state['data'])
            if data['_call_time'] == content['_call_time']:
                del data['_call_time']
                #pass
                log.info("Returning a value from client {}: {}".format(app._this_instance, data))
                return json.dumps(data)
            else:
                #data['_timestamp_mismatch'] = True
                # TEMP try pulling again, assuming duplicate
                log.error("Duplicate message from client {}: {}".format(app._this_instance, state['data']))
                continue
            # TEMP: delete this _call_time check when confident
            # about message loss / duplication
            #state['data'] = json.dumps(data)
            # state['data'] is a JSON string
            #log.info("Returning a value {}".format(data))
            #return json.dumps(data) #state['data']
        else:
            t_wait = time()-t0
    log.error("Waited too long for response: t={}".format(t0))

# ================================================


# @app.route('/logs')
# @admin_only
# def logs():
#     try:
#         return jsonify(utils.read_sql("SELECT * FROM server_log;"))
#     except KeyError:
#         return 'Empty log'

# @app.route('/clear_log')
# @admin_only
# def clear_log():
#     try:
#         utils.change_sql("TRUNCATE TABLE server_log;")
#         # don't alter this sequence in the middle of other
#         # processes potentially playing with DB
#         #utils.change_sql("ALTER SEQUENCE server_log_event_index_seq RESTART WITH 1;")
#     except KeyError:
#         pass
#     return redirect(url_for('main'))

@app.route('/flush_pubsub')
@admin_only
def admin_flush():
    tries = 10  # when None
    count = 0
    while tries >= 0:
        state = app._p.get_message("client-"+app._this_instance)
        if state is None:
            tries -= 1
        else:
            count += 1
        sleep(0.1)
    return json.dumps({"States flushed": str(count)})

@app.route('/dump')
@admin_only
def admin_dump():
    content = {"dump": {}}
    return do_messaging(content, is_admin=True)

@app.route('/game/<private_id>/<game_id>')
@admin_only
def admin_game(private_id, game_id):
    content = {"game": {"private_id": private_id,
                        "game_id": game_id}}
    return do_messaging(content, is_admin=True)

@app.route('/')
#@no_http
def main(*args, **kwargs):
##    try:
##        rows = utils.read_sql("SELECT destruct_at, name, difficulty FROM current_map LIMIT 1;")[0]
##    except IndexError:
##        pass
##    else:
##        session['map_time_destruct'] = rows[0]
##        session['map_name'] = rows[1]
##        session['map_difficulty'] = rows[2]
    resp = render_template('index.html')
    return resp

@app.route('/dashboard')
def dashboard(*args, **kwargs):
    resp = render_template('dashboard.html')
    return resp

@app.route('/stats_totals')
def stats_tots(*args, **kwargs):
    num_events = utils.read_sql("SELECT COUNT(*) FROM game_event_log;")[0][0]
    num_games = utils.read_sql("SELECT COUNT(game_id) FROM game_summary;")[0][0]
    return render_template_string("There have been {} games played so far, with a total of {} API calls.".format(num_games, num_events))

# is the server up?
@app.route("/wakeupserver")
def game_wakeupserver():
    #log.info("In wakeupserver")
    #if request.method == 'POST':
    #    content = {"declare": {"private_id": None,
    #                       "level": request.form.get('level', type=int),
    #                       "IPaddress": get_IP()}}
    #else:
    content = {"wakeup": {"dummy": None}}
    try:
        return jsonify(json.loads(do_messaging(content)))
    except Exception as err:
        return jsonify({"ERROR": str(err)})

@app.route("/register_name/<private_id>/<public_id>/<name>")
@app.route("/register_name/<private_id>/<public_id>", defaults={"name": None})
@app.route("/register_name/<private_id>", defaults={"name": None,
                                                    "public_id": None})
@app.route("/register_name", defaults={"name": None,
                                                    "public_id": None,
                                                    "private_id": None})
def game_register_name(private_id, public_id, name):
    if private_id is None or public_id is None or name is None:
        return jsonify({"Error": "Invalid values for call parameters"})
    content = {"register_name": {"private_id": private_id,
                        "public_id": public_id,
                        "name": name}}
    try:
        return jsonify(json.loads(do_messaging(content)))
    except Exception as err:
        return jsonify({"ERROR": str(err)})


@app.route("/status")
@returns_json
def game_status(private_id):
    content = {"action": {"private_id": private_id,
                          "move_dx": 0}}
    return do_messaging(content)

@app.route("/cancel")
@returns_json
def game_cancel(private_id):
    content = {"cancel": {"private_id": private_id}}
    return do_messaging(content)

@app.route('/move/<distance>')
@app.route('/move', defaults={"distance": None})
@returns_json
def game_move(private_id, distance):
    if distance is None:
        return jsonify({"Error": "Invalid distance parameter"})
    content = {"action": {"private_id": private_id,
                          "move_dx": float(distance)}}
    return do_messaging(content)

@app.route('/request_game/<int:level>/<private_id>')
@app.route('/request_game/<int:level>', defaults={"private_id": None})
@app.route('/request_game', defaults={"private_id": None, "level": None})
@returns_json
def game_request_game(private_id, level):
    #log.info("In request_game")
    #log.logger.handlers[0].flush()
    # private_id always comes first (see returns_json)
    if level is None:
        raise ValueError("Difficulty level must be provided")
    else:
        try:
            L = int(level)
        except TypeError:
            return {"Error": "Path is /request_game/<int:level>/[<private_id>]"}
    content = {"declare": {"private_id": private_id,
                           "level": L,
                           "IPaddress": get_IP(as_str=True)}}
    return do_messaging(content)

# @app.route('/help', defaults={'path': ''})
# @app.route("/help/<path:path>")
# @returns_json
# def game_help(name, private_id, path=''):
#     if path == '':
#         return json.dumps(help_info)
#     else:
#         parts = path.split('/')
#         assert len(parts) == 1
#         try:
#             return json.dumps(help_specific[parts[0]])
#         except KeyError:
#             return json.dumps("No help for '{}'".format(parts[0]))

_game_commands = ["request_game", "status", "move", "cancel", "register_name"]
_admin_commands = ["game", "dump"]
# Prepended ID in path not supported in this game
#@app.route('/', defaults={'path': ''})
#@app.route('/<path:path>')
def id_in_path(path):
    """Support putting private_id as first part of route in paths
    """
    parts = path.split('/')
    # check first part for private_id (if parts is empty,
    # behavior would have defaulted to returning HTML instead of calling
    # this function)
    id_or_cmd = parts[0]
    log.info("parts = {}".format(parts))
    if id_or_cmd == "None":
        return jsonify({"ERROR": "Invalid private id {} or no such command".format(id_or_cmd)})
    elif len(parts) == 1:
        cmd = parts[0]
        args = []
        kwargs = {'private_id': None}
    elif len(parts) > 1:
        # broadcast the rest if the next part is one of the recognized commands
        if len(parts[0]) == 32:
            kwargs = {'private_id': parts[0]}
            cmd = parts[1]
            payload = parts[2:] # may be empty
        else:
            kwargs = {'private_id': None}
            cmd = parts[0]
            payload = parts[1:] # may be empty
        if payload == []:
            args = payload
        else:
            # Assumption: payload in same order as function signature
            if len(payload) == 1:
                args = payload
            else:
                # loop through and extract values in order (always pairs)
                # Assumption: no mixture of named param and non-named param
                assert len(payload) % 2 == 0
                args = payload[1::2]
    log.info("cmd = {}, args = {}, kwargs = {}".format(cmd, args, kwargs))
    if cmd in _game_commands:
        # it's going to call through the returns_json wrapper
        # regardless, so set it up to not try to fetch private_id from
        # a URL parameter
        return globals()['game_'+cmd](*args, **kwargs)
    else:
        return jsonify({"ERROR": f"Invalid command {cmd}"})


# ==========

@app.errorhandler(404)
#@no_http
def page_not_found(e, *args, **kwargs):
    return jsonify({"help": "TBD"})

# For WSGI init
def setup_app(app):
    log.make_log(app)
    log.info("Starting up instance of app")
    app._this_instance = uuid.uuid4().hex
    settings = 'dev_settings' #'production_settings'
    log.info("Using " + settings)
    # essential to get everything started with WSGI
    app.config.from_object(settings)

setup_app(app)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # make it public, ensure DEBUG off to prevent remote python code execution
    #from scout_apm.flask import ScoutApm # in-app monitoring
    #ScoutApm(app)
    #app.config['SCOUT_MONITOR'] = True
    #app.config['SCOUT_KEY']     = ""
    #app.config['SCOUT_NAME']    = ""
    app.run(host="0.0.0.0", port=port, debug=True)
    # web: #python aping_pong/flask_server.py
    # gunicorn -b 0.0.0.0:$PORT -w 3 -k gevent wsgi:application --log-file -
