import requests
import time
import json
import datetime
import collections
from credentials import api_key
import config
import util
from pathlib import Path
import dateutil


def load_data():
    p = Path(config.FILE)
    if p.exists():
        with p.open() as fd: data = json.load(fd)
    else:
        data = []
    data = collections.deque(data, maxlen=config.SECONDS_IN_DAY//config.TIME_LAG)
    return data

def save_data(data):
    print('start save_data')
    with open(config.FILE, 'w') as fd: json.dump(list(data), fd, ensure_ascii=False, separators=(',', ':'))

    print('end save_data')



data = load_data()
MSK = dateutil.tz.gettz('Europe/Moscow')


while True:
    t0 = time.time()
    videos = util.trending_videos(api_key, regionCode='RU')
    videos = util.compress(videos, config.COMPRESS_SCHEMA)
    now = datetime.datetime.now(tz=MSK)
    timestamp = int(now.timestamp())
    data.append([timestamp, videos])
    save_data(data)
    util.plot(data)
    t_elapsed = time.time() - t0
    print(now, f'elapsed in {t_elapsed}')

    sleep_time = config.TIME_LAG - t_elapsed
    if sleep_time > 0:
        print(f'sleep for {sleep_time}')
        time.sleep(sleep_time)


