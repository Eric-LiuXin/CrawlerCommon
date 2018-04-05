import os
import re
import urlparse
import pickle
import shutil
import zlib
from datetime import datetime, timedelta

class DiskCache:
    """
    cache_dir: the root level folder for the cache
    expires: timedelta of amount of time before a cache entry is considered expired
    compress: whether to compress data in the cache
    """
    def __init__(self, cache_dir='cache', expires=timedelta(days=30), compress=True):
        self.cache_dir = cache_dir
        self.expires = expires
        self.compress = compress

    # Load data from disk for this URL
    def __getitem__(self, url):
        path = self.url_to_path(url)
        if os.path.exists(path):
            with open(path, 'rb') as fp:
                data = fp.read()
                if self.compress:
                    data = zlib.decompress(data)
                result, timestamp = pickle.loads(data)
                if self.has_expired(timestamp):
                    raise KeyError(url + ' has expired')
                return result
        else:
            # URL has not yet been cached
            raise KeyError(url + ' does not exist')

    # Save data to disk for this url
    def __setitem__(self, url, result):
        path = self.url_to_path(url)
        folder = os.path.dirname(path)
        if not os.path.exists(folder):
            os.makedirs(folder)

        data = pickle.dumps((result, datetime.utcnow()))
        if self.compress:
            data = zlib.compress(data)
        with open(path, 'wb') as fp:
            fp.write(data)

    # Remove the value at this key and any empty parent sub-directories
    def __delitem__(self, url):
        path = self.url_to_path(url)
        try:
            os.remove(path)
            os.removedirs(os.path.dirname(path))
        except OSError:
            pass

    # Create file system path for this URL
    def url_to_path(self, url):
        components = urlparse.urlsplit(url)
        path = components.path

        #append index.html to empty paths
        if not path:
            path = '/index.html'
        elif path.endswith('/'):
            path += 'index.html'

        filename = components.netloc + path + components.query
        # replace invalid characters
        filename = re.sub('[^/0-9a-zA-Z\-.,;_ ]', '_', filename)
        # restrict maximum of characters
        filename = '/'.join(segment[:255] for segment in filename.split('/'))

        return os.path.join(self.cache_dir, filename)

    # Return whether this timestamp has expired
    def has_expired(self, timestamp):
        return datetime.utcnow() > timestamp + self.expires

    # Remove all the cached values
    def clear(self):
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)