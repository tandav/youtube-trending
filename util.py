import requests
import itertools
import functools
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from sklearn.preprocessing import MinMaxScaler
import config
import tqdm
import dateutil.parser
import dateutil.tz

# https://more-itertools.readthedocs.io/en/stable/api.html
def take   (n, iterable): return list(itertools.islice(iterable, n))
def chunked(iterable, n): return iter(functools.partial(take, n, iter(iterable)), [])

def ago(e):
    # e: pass timedelta between timestamps in 1579812524 format
    e *= 1000 # convert to 1579812524000 format
    t = round(e / 1000)
    n = round(t /   60)
    r = round(n /   60)
    o = round(r /   24)
    i = round(o /   30)
    a = round(i /   12)
    if   e <  0: return              'just now'
    elif t < 10: return              'just now'
    elif t < 45: return str(t) + ' seconds ago'
    elif t < 90: return          'a minute ago'
    elif n < 45: return str(n) + ' minutes ago'
    elif n < 90: return           'an hour ago' 
    elif r < 24: return str(r) +   ' hours ago'
    elif r < 36: return             'a day ago'
    elif o < 30: return str(o) +    ' days ago'
    elif o < 45: return           'a month ago'
    elif i < 12: return str(i) +  ' months ago'
    elif i < 18: return            'a year ago'
    else:        return str(a) +   ' years ago'



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
                 'publishedAt': snippet['publishedAt'],
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


def plot(data, published_at):
    print('start plot')

    labels = []
    latest_top_ids = []
    id_2_index = {}

    latest_ts, latest_videos = data[-1]
    latest_videos = latest_videos[:config.TOP_LIMIT]
    
    for i, (id_, title, channelTitle, viewCount, likeCount, dislikeCount, commentCount) in enumerate(latest_videos):
        published_ago = ago((datetime.datetime.now(datetime.timezone.utc) - dateutil.parser.parse(published_at[i])).total_seconds())
        l = f'{i+1:>3} | {published_ago:>12} |{human_format(viewCount):>7} | {channelTitle[:18]:<18} | {title[:80]}'
        labels.append(l)
        latest_top_ids.append(id_)
        id_2_index[id_] = i

    df_data = []
    df_index = []

    for timestamp, videos in tqdm.tqdm(data):
        row = [0] * len(id_2_index)
        ts = datetime.datetime.fromtimestamp(timestamp, config.TIMEZONE)
        for id_, title, channelTitle, viewCount, likeCount, dislikeCount, commentCount in videos:
            index = id_2_index.get(id_)
            if index is None:
                continue

            row[index] = viewCount

        df_data.append(row)
        df_index.append(ts)

    X_viewCount = pd.DataFrame(df_data, df_index, columns=latest_top_ids, dtype='int32')
    
    X = X_viewCount
    diff = X.diff().resample('5Min').sum()
    diff = pd.DataFrame(MinMaxScaler().fit_transform(diff), diff.index, diff.columns)
    # diff = X.diff()
    diff = diff.T


    fig, ax = plt.subplots(figsize=(9, 8), facecolor='white')


    # ax.imshow(diff, aspect='auto', interpolation='none')
    # ax.imshow(diff, origin='lower', aspect='auto', interpolation='none', norm=LogNorm())
    # ax.imshow(diff, origin='upper', aspect='auto', interpolation='none', norm=LogNorm())

    # ax.imshow(diff, aspect='auto', interpolation='nearest', norm=LogNorm())
    ax.imshow(diff, aspect='auto', interpolation='nearest')
    # ax.imshow(diff, norm=LogNorm())

    ax.set_title(f'last update: {datetime.datetime.now(tz=config.TIMEZONE)}', fontsize= 5)
    ax.yaxis.tick_right()
    ax.set_yticks(range(len(labels)))
    # ax.set_yticklabels(labels, ha='left', fontname='Menlo')
    ax.set_yticklabels(labels, ha='left', fontname='monospace', fontsize=4)

    xticks = range(0, len(diff.columns), 40)
    ax.set_xticks(xticks)
    ax.xaxis.set_ticklabels(diff.columns.strftime('%H:%M')[xticks], fontsize=6)

    # ax.xaxis.set_ticklabels(diff.columns, rotation=90)
    # ax.xaxis.set_major_formatter(formatter)
    # ax.xaxis.set_major_formatter(DateFormatter('%T %Z', tz=MSK))

    # plt.show()
    plt.tight_layout()
    plt.savefig(config.PLOT_PATH)
    plt.close(fig) # trying fix memory leak https://stackoverflow.com/a/33343289/4204843
    print('end plot')


def drop_old(data):
    DAY_SECONDS = 60 * 60 * 24
    now = datetime.datetime.now().timestamp()
    out = itertools.dropwhile(lambda x: now - x[0] > DAY_SECONDS, data)
    out = list(out)
    return out


