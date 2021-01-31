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
import gc


def load_data():
    p = Path(config.FILE)
    if p.exists():
        with p.open() as fd: data = json.load(fd)
    else:
        data = []
    data = util.drop_old(data)
    return data

def save_data(data):
    print('start save_data')
    with open(config.FILE, 'w') as fd: json.dump(list(data), fd, ensure_ascii=False, separators=(',', ':'))

    print('end save_data')



data = load_data()


while True:
    t0 = time.time()
    videos = util.trending_videos(api_key, regionCode='RU')
    published_at = [v.pop('publishedAt') for v in videos]
    videos = util.compress(videos, config.COMPRESS_SCHEMA)
    now = datetime.datetime.now(tz=config.TIMEZONE)
    timestamp = int(now.timestamp())
    data.append([timestamp, videos])
    data = util.drop_old(data)
    save_data(data)
    util.plot(data, published_at)
    gc.collect()
    t_elapsed = time.time() - t0
    print(now, f'elapsed in {t_elapsed}')

    sleep_time = config.TIME_LAG - t_elapsed
    if sleep_time > 0:
        print(f'sleep for {sleep_time}')
        time.sleep(sleep_time)


