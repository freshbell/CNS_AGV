import asyncio
from collections import deque
from flask_socketio import send, emit
from asyncio.windows_events import NULL
from os import name
import socketio
import random
import json
import time
import sys

# JSON 파일 open
with open('./json/client_json/Report.json', 'r', encoding='UTF-8') as f:
    STATE_JSON = json.load(f)
with open('./json/client_json/Alarm.json', 'r', encoding='UTF-8') as f:
    ALARM_JSON = json.load(f)

# 소켓 클라이언트 설정
sio = socketio.AsyncClient()

# move 위치
count,cnt = 0,0

# 알람 전송
ALARM_CD_LIST = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
ALARM_CD_USED = deque([])
temp_end_alarm = 10
temp_start_alarm = 10
ALARM_REPORT_JSON = {
    'DATA_TYPE': 'alarm',
    'AGV_NO': 'TEMP',
    'ALARMS': []
}

# 랜덤 ALARM_CD
async def random_alarm():
    global temp_end_alarm, temp_start_alarm

    temp_start_alarm = random.choice(ALARM_CD_LIST)

    ALARM_CD_LIST.remove(temp_start_alarm)
    ALARM_CD_USED.append(temp_start_alarm)
    
    # 알람이 발생하고 5초 후 해제
    if(len(ALARM_CD_USED) == 6):
        temp_end_alarm = ALARM_CD_USED.popleft()
        ALARM_CD_LIST.append(temp_end_alarm)

    ALARM_JSON['ALARMS'][temp_start_alarm]['ALARM_STATUS'] = 1
    ALARM_JSON['ALARMS'][temp_start_alarm]['OCCUR_DT'] = time.strftime('20%y%m%d %H:%M:%S')
    ALARM_JSON['ALARMS'][temp_start_alarm]['END_DT'] = None

    if(temp_end_alarm != 10):
        ALARM_REPORT_JSON['ALARMS'].append(ALARM_JSON['ALARMS'][temp_end_alarm])
        ALARM_JSON['ALARMS'][temp_end_alarm]['END_DT'] = time.strftime('20%y%m%d %H:%M:%S')
        ALARM_JSON['ALARMS'][temp_end_alarm]['ALARM_STATUS'] = 0

    ALARM_REPORT_JSON['ALARMS'].append(ALARM_JSON['ALARMS'][temp_start_alarm])

# 알람상태/해제 전송 Thread
async def send_alarm():    
    while True:        
        ALARM_REPORT_JSON['ALARMS'] = []
        await random_alarm()
        await sio.emit('alarm_report', json.dumps(ALARM_REPORT_JSON, ensure_ascii=False))
        await sio.sleep(1)

# connect되면 알람/해제 발생
@sio.event
async def connect():
    # 알람상태/해제 전송 Thread

    sio.start_background_task(send_alarm)
    
# AGV 상태요청 receive
@sio.on('state_request')
async def state(data):
    global count
    json_data = json.loads(data)
    print("----AGV 상태요청----")
    print(json_data)
    # AGV 상태보고 전송
    if json_data['DATA_TYPE'] == 'reportRqst':        
        await sio.emit('state_report', json.dumps(STATE_JSON, ensure_ascii=False))

# AGV 이동 명령 receive
@sio.on('move_request')
async def move_avg(data):
    global count, cnt    
    move_data = json.loads(data)
    length=len(move_data['BLOCKS'])
    if cnt<length:
        cnt+=1
    else:
        cnt=0
    STATE_JSON['LOCATION'] = move_data['BLOCKS'][cnt]
    print("----AGV 이동명령----")
    print(move_data)

# 서버 연결 해제
@sio.event()
async def disconnect():
    print('disconnected from server')

async def main():
    STATE_JSON['AGV_NO'] = AGV_NO
    ALARM_REPORT_JSON['AGV_NO'] = AGV_NO
    
    if server == '0':
        await sio.connect('http://localhost:5000?client=' + AGV_NO)
    else:
        await sio.connect('http://13.124.72.207:5000?client=' + AGV_NO)
    await sio.wait()

if __name__ == '__main__':
    argument = sys.argv
    AGV_NO = argument[1]
    server = argument[2]

    asyncio.run(main())