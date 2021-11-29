from threading import Lock
from flask import Flask, render_template, session, request, copy_current_request_context
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect
from engineio.payload import Payload
import json
import random
import sys
import time
import logging
import threading

Payload.max_decode_packets = 101

async_mode = None
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins='*')

connect_chk = False

# JSON 파일 open
with open('./json/server_json/Request.json', 'r', encoding='UTF-8') as f:
    STATE_REQUEST = json.load(f)
with open('./json/server_json/Move.json', 'r', encoding='UTF-8') as f:
    MOVE_JSON = json.load(f)

now = time.strftime('20%y%m%d %H%M%S')
alarm_f = open("./log/alarm_log/alarm" + now + ".txt","w", encoding='utf-8')
state_f = open("./log/state_log/state" + now + ".txt","w", encoding='utf-8')
logging.basicConfig(filename='./log/debug' + now + '.log',level=logging.DEBUG, encoding='utf-8')

clients = {}
def make_route():
    # 맵 크기
    MAX_N = MAX_M = 30 
    direction_x = [1,0,-1,0]
    direction_y = [0,1,0,-1]

    x, y = random.sample(range(1,31),1)[0], random.sample(range(1,31),1)[0]
    BLOCKS = [str(x).zfill(4) + str(y).zfill(4)]
    for _ in range(random.sample(range(20, 30),1)[0]):
        while True:
            direction = random.sample(range(0,3),1)[0]
            if 0 < x + direction_x[direction] <= MAX_N and 0 < y + direction_y[direction] <= MAX_M:
                x, y = x + direction_x[direction], y + direction_y[direction]
                break
        BLOCKS.append(str(x).zfill(4) + str(y).zfill(4))

    return BLOCKS

def make_route_to_dest(agv_no, dest):
    # 맵 크기
    MAX_N = MAX_M = 30 
    dx = [1,0,-1,0]
    dy = [0,1,0,-1]
    x_dest = int(dest[0:4])
    y_dest = int(dest[4:8])
    start = clients[agv_no]['blocks'][-1]
    print(start)
    x_start = int(start[0:4])
    y_start = int(start[4:8])

    x_change = 1
    y_change = 1
    if x_start > x_dest:
        x_change = -1
    if y_start > y_dest:
        y_change = -1

    cur_x = x_start
    cur_y = y_start
    while cur_x != x_dest:
        cur_x += x_change
        clients[agv_no]['blocks'].append(str(cur_x).zfill(4) + str(y_start).zfill(4))
    while cur_y != y_dest:
        cur_y += y_change
        clients[agv_no]['blocks'].append(str(x_dest).zfill(4) + str(cur_y).zfill(4))

    return

@socketio.on('move_request_from_monitor')
def move_request_from_monitor(data):
    agv_no = data['AGV_NO']
    dest = data['LOCATION']
    clients[agv_no]['destination'] = dest
    print(str(clients[agv_no]['blocks'][-1] + str(agv_no)))
    route = make_route_to_dest(agv_no, dest)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/monitoring")
def monitor():
    return render_template('monitoring.html')

# 상태요청, 이동명령 요청
temp = 0
def background_thread():
    global temp
    while True:
        time.sleep(0.05)       
        for AGV in clients.keys():
            MOVE_JSON['AGV_NO'] = AGV
            MOVE_JSON['BLOCKS'] = clients[AGV]['blocks']
            MOVE_JSON['DESTINATION'] = clients[AGV]['destination']
            STATE_REQUEST['AGV_NO'] = AGV

            socketio.emit('move_request',json.dumps(MOVE_JSON), room=clients[AGV]['sid'])
            socketio.emit('state_request',json.dumps(STATE_REQUEST), room=clients[AGV]['sid'])

# 연결
@socketio.on('connect')
def connect():
    global connect_chk
    print(request)
    client = request.args.get('client')
    if client == 'monitor':     #모니터 connect 
        print('Monitor connected')
    elif client is not None:
        print(str(client) + ' connected')
        clients[client] = {}
        clients[client]['sid'] = request.sid
        clients[client]['AGV_NO'] = client
        clients[client]['blocks'] = make_route()
        clients[client]['destination'] = clients[client]['blocks'][-1]
        socketio.emit('agv_connect_to_monitor', clients[client]['AGV_NO'])

# 상태 보고서 수신
@socketio.on('state_report')
def state(data):
    state_f.write(str(data) + "\n")
    socketio.emit('state_to_monitor', data)
    logging.info(data)

# 알람 보고서 수신
@socketio.on('alarm_report')
def alarm(data):
    alarm_f.write(str(data) + "\n")
    socketio.emit('alarm_to_monitor', data)
    logging.info(data)

# 연결 해제
@socketio.on('disconnect')
def disconnect():
    client = request.args.get('client')
    if client == 'monitor':
        print("monitor disconnect")
    else:
        socketio.emit('agv_disconnect_to_monitor', clients[client]['AGV_NO'])
        del clients[client]

if __name__=="__main__":
    argument = sys.argv
    host = argument[1] if len(argument) == 2 else 'localhost'

    thread = threading.Thread(target=background_thread)
    thread.start()

    socketio.run(app, host=host, debug=True)

    thread.join()
