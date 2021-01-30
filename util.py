import requests
import itertools
import functools
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import config
import tqdm


# https://more-itertools.readthedocs.io/en/stable/api.html
def take   (n, iterable): return list(itertools.islice(iterable, n))
def chunked(iterable, n): return iter(functools.partial(take, n, iter(iterable)), [])


def trending_videos(api_key, regionCode='US'):
    '''regionCode: https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes'''
    print('start loading trending_videos')
    def _load():
        URL= 'https://www.googleapis.com/youtube/v3/videos'
        payload = dict(
            part='snippet,statistics',
            maxResults=50,
            key=api_key,
            chart='mostPopular',
            regionCode=regionCode,
        )
        r = requests.get(URL, params=payload).json()
        videos = r['items']
        # do while emulation
        while 'nextPageToken' in r:
            payload['pageToken'] = r['nextPageToken']
            r = requests.get(URL, params=payload).json()
            videos += r['items']
        return videos

    def _clean(videos):
        '''delete useless information'''
        V = []
        for v in videos:
            snippet = v['snippet']
            statistics = v['statistics']
            del statistics['favoriteCount']
            w = {'id': v['id'], 'title': snippet['title'], 'channelTitle': snippet['channelTitle'],
                 'viewCount':    int(statistics.get('viewCount', 0)),
                 'likeCount':    int(statistics.get('likeCount', 0)),
                 'dislikeCount': int(statistics.get('dislikeCount', 0)),
                 'commentCount': int(statistics.get('commentCount', 0)),
            }
            V.append(w)
        return V
    videos = _clean(_load())
    print('end loading trending_videos')
    return videos

def videos_info(videos, api_key):
    if isinstance(videos, list) and len(videos) > 50: # yt api limit
        _ = chunked(videos, 50)
        _ = map(lambda x: videos_info(x, api_key), _)
        _ = itertools.chain.from_iterable(_)
        _ = list(_)
        return _

    URL= 'https://www.googleapis.com/youtube/v3/videos'
    payload = dict(
        part='snippet,statistics',
        maxResults=50,
        key=api_key,
        id=','.join(videos)
    )
    r = requests.get(URL, params=payload).json()
    videos = r['items']
    # do while emulation
    while 'nextPageToken' in r:
        payload['pageToken'] = r['nextPageToken']
        r = requests.get(URL, params=payload).json()
        videos += r['items']
    return videos


def playlists(channelId, api_key):
    payload = {
        'part'       : 'snippet',
        'channelId'  : channelId,
        'maxResults' : 50,
        'key'        : api_key,
    }

    r = requests.get('https://www.googleapis.com/youtube/v3/playlists', params=payload).json()
    playlists = r['items']

    while 'nextPageToken' in r:
        payload['pageToken'] = r['nextPageToken']
        r = requests.get('https://www.googleapis.com/youtube/v3/playlistItems', params=payload).json()
        playlists += r['items']

    return playlists

def videos(playlistId, api_key):
    payload = {
        'part'       : 'snippet',
        'playlistId' : playlistId,
        'maxResults' : 50,
        'key'        : api_key,
    }

    r = requests.get('https://www.googleapis.com/youtube/v3/playlistItems', params=payload).json()
    videos = r['items']

    # do while emulation
    while 'nextPageToken' in r:
        payload['pageToken'] = r['nextPageToken']
        r = requests.get('https://www.googleapis.com/youtube/v3/playlistItems', params=payload).json()
        videos += r['items']    

    return videos


def compress(videos, compress_schema):
    return [[v.get(k) for k in compress_schema] for v in videos]
    # return list(map(lambda v: [v.get(k) for k in compress_schema], videos))


def human_format(num, round_to=1):
    '''
    >>> human_format(1876503)
    '1.9M'
    '''
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num = round(num / 1000.0, round_to)
    return '{:.{}f}{}'.format(round(num, round_to), round_to, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])


def plot(data):
    print('start plot')

    latest_top_ids = [v[0] for v in data[-1][1]]
    latest_top_ids_set = set(latest_top_ids)

    X_viewCount    = pd.DataFrame(columns=latest_top_ids, dtype='int32')

    for timestamp, videos in tqdm.tqdm(data):
        
        ts = datetime.datetime.fromtimestamp(timestamp, config.TIMEZONE)
        for id_, title, channelTitle, viewCount, likeCount, dislikeCount, commentCount in videos:
            if id_ not in latest_top_ids_set:
                continue
            X_viewCount.loc[ts, id_] = viewCount

    TOP_LIMIT = 100
    X = X_viewCount.iloc[:, :TOP_LIMIT]

    diff = X.diff().resample('5Min').sum()
    # diff = X.diff()
    diff = diff.T


    fig, ax = plt.subplots(figsize=(22, 17), facecolor='white')


    labels = []

    for i, (id_, title, channelTitle, viewCount, likeCount, dislikeCount, commentCount) in enumerate(data[-1][1][:TOP_LIMIT], start=1):

    # for i, thread in enumerate(top.index):
    #     count, title = info.get(thread, (0, 'NOT FOUND'))
        l = f'{i:>3} | {human_format(viewCount):>7} | {channelTitle[:18]:<18} | {title[:80]}'
        labels.append(l)

    # ax.imshow(diff, aspect='auto', interpolation='none')
    # ax.imshow(diff, origin='lower', aspect='auto', interpolation='none', norm=LogNorm())
    # ax.imshow(diff, origin='upper', aspect='auto', interpolation='none', norm=LogNorm())

    ax.imshow(diff, aspect='auto', interpolation='nearest', norm=LogNorm())
    # ax.imshow(diff, norm=LogNorm())

    plt.title(f'last update: {datetime.datetime.now(tz=config.TIMEZONE)}')
    ax.yaxis.tick_right()
    ax.set_yticks(range(len(labels)))
    # ax.set_yticklabels(labels, ha='left', fontname='Menlo')
    ax.set_yticklabels(labels, ha='left', fontname='monospace')

    # ''

    xticks = range(0, len(diff.columns), 20)
    ax.set_xticks(xticks)
    ax.xaxis.set_ticklabels(diff.columns.strftime('%H:%M')[xticks])

    # ax.xaxis.set_ticklabels(diff.columns, rotation=90)
    # ax.xaxis.set_major_formatter(formatter)
    # ax.xaxis.set_major_formatter(DateFormatter('%T %Z', tz=MSK))

    # plt.show()
    plt.tight_layout()
    plt.savefig(config.PLOT_PATH)
    print('end plot')
