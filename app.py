from threading import Lock
from flask import Flask, render_template, session, request, copy_current_request_context
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect
from engineio.payload import Payload
from flask_cors import CORS
import json
import random
import sys
import time

Payload.max_decode_packets = 101

thread = None
thread_lock = Lock()
async_mode = None
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins='*')

# JSON 파일 open
with open('./json/server_json/Request.json', 'r', encoding='UTF-8') as f:
    STATE_REQUEST = json.load(f)
with open('./json/server_json/Move.json', 'r', encoding='UTF-8') as f:
    MOVE_JSON = json.load(f)

now = time.strftime('20%y%m%d %H%M%S')
alarm_f = open("./log/alarm_log/alarm" + now + ".txt","w", encoding='utf-8')
state_f = open("./log/state_log/state" + now + ".txt","w", encoding='utf-8')

clients = {}

def make_route():
    # 맵 크기
    MAX_N = MAX_M = 30 
    direction_x = [1,0,-1,0]
    direction_y = [0,1,0,-1]

    x = random.sample(range(1, 31),1)[0]
    y = random.sample(range(1, 31),1)[0]
    BLOCKS = [str(x).zfill(4) + str(y).zfill(4)]

    x, y = random.sample(range(1,31),1)[0], random.sample(range(1,31),1)[0]
    for _ in range(random.sample(range(20, 30),1)[0]):
        while True:
            direction = random.sample(range(0,3),1)[0]
            if 0 < x + direction_x[direction] <= MAX_N and 0 < y + direction_y[direction] <= MAX_M:
                x, y = x + direction_x[direction], y + direction_y[direction]
                break
        BLOCKS.append(str(x).zfill(4) + str(y).zfill(4))

    return BLOCKS

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/monitoring")
def monitor():
    return render_template('monitoring.html')

# 상태요청, 이동명령 요청
def background_thread():
    while True:
        socketio.sleep(0.05)
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
    global thread
    print(request)
    client = request.args.get('client')
    if client == 'monitor':     #모니터 connect 
        print('Monitor connected')
    else:
        print(str(client) + ' connected')
        clients[client] = {}
        clients[client]['sid'] = request.sid
        clients[client]['AGV_NO'] = client
        clients[client]['blocks'] = make_route()
        clients[client]['destination'] = clients[client]['blocks'][-1]

        with thread_lock:
            if thread is None:
                thread = socketio.start_background_task(background_thread)

# 상태 보고서 수신
@socketio.on('state_report')
def state(data):
    state_f.write(str(data) + "\n")
    socketio.emit('state_to_monitor', data)
    print("----AGV 상태보고----")
    print(data)

# 알람 보고서 수신
@socketio.on('alarm_report')
def alarm(data):
    alarm_f.write(str(data) + "\n")
    socketio.emit('alarm_to_monitor', data)
    print("----알람 발생/해제 보고----")
    print(data)

# 연결 해제
@socketio.on('disconnect')
def disconnect():
    client = request.args.get('client')
    socketio.emit('agv_disconnect_to_monitor', clients[client]['AGV_NO'])
    del clients[client]

if __name__=="__main__":
    argument = sys.argv
    host = argument[1] if len(argument) == 2 else 'localhost'

    socketio.run(app, host=host)