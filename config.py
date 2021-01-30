import dateutil.tz

COMPRESS_SCHEMA = 'id', 'title', 'channelTitle', 'viewCount', 'likeCount', 'dislikeCount', 'commentCount'
FILE = 'data.json'
API_REQUESTS_QUOTA_PER_DAY = 10_000
SECONDS_IN_DAY = 60 * 60 * 24
# SECONDS_IN_DAY / QUOTA_PER_DAY # 8.64
# TIME_LAG = 10 # only if 1 region, if 2 (US, RU) : use 20 seconds
TIME_LAG = 60
# anyway you'll do resampling (youtube updates stats no very often) -> so use bigger time lag
PLOT_PATH = 'image.pdf'
TIMEZONE = dateutil.tz.gettz('Europe/Moscow')
