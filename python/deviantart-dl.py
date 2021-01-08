#!/usr/bin/env python3
"""
DeviantArt downloader by @hatkidchan

Requirements:
    pip install rich deviantart requests
"""
from os.path import join, splitext, split as splitpath, exists
from concurrent.futures import ThreadPoolExecutor
from argparse import ArgumentParser
from urllib.parse import urlparse
from traceback import format_exc
from os import mkdir, environ
from time import sleep
from json import dumps
from rich.progress import BarColumn, DownloadColumn, TransferSpeedColumn
from rich.progress import TimeRemainingColumn, Progress
from requests import get as GET
from deviantart import Api

__description__ = '''\
Tags downloader from DeviantArt.
'''


class DeviantArtDownloader:
    def __init__(self, client_id, client_secret):
        self.api = Api(client_id, client_secret)
        self.progress = Progress(
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            DownloadColumn(),
            TransferSpeedColumn(),
            "[bold blue]{task.fields[filename]}",
        )
        self.all_t = self.progress.add_task('All', filename='All', start=0)
        self.total_length = 0;

    def download_worker(self, task_id, url, path):
        with open(path, 'wb') as f, GET(url, stream=True) as rq:
            length = int(rq.headers.get('Content-Length', 0))
            self.progress.start_task(task_id)
            self.progress.update(task_id, total=length)
            self.total_length += length
            self.progress.update(self.all_t, total=self.total_length)
            for chunk in rq.iter_content(chunk_size=4096):
                f.write(chunk)
                self.progress.update(task_id, advance=len(chunk))
                self.progress.update(self.all_t, advance=len(chunk))
        return task_id
    
    def search_content(self, tag, max_items=-1):
        n_items = 0
        offset = 0
        while True:
            data = self.api.browse('tags', tag=tag, offset=offset)
            for item in data['results']:
                yield item
                n_items += 1
                if n_items > max_items and max_items > 0:
                    return
            if not data['has_more']:
                break
            offset = data['next_offset']
            
    @staticmethod
    def _make_filename(item):
        src = item.content['src']
        ext = splitext(urlparse(src).path)[1]
        return splitpath(item.url)[1] + ext

    def download(self,
                 tag,
                 out_dir='.',
                 max_items=-1,
                 max_workers=8,
                 list_path=None):
        if not exists(out_dir):
            mkdir(out_dir)
        with self.progress, ThreadPoolExecutor(max_workers=max_workers) as pool:
            self.progress.start_task(self.all_t)
            futures = []
            for item in self.search_content(tag, max_items):
                if list_path:
                    with open(list_path, 'a') as flist:
                        flist.write(item.url + '\n')
                if not item.content:
                    continue
                filename = join(out_dir, self._make_filename(item))
                task_id = self.progress.add_task(
                        'download',
                        filename=item.title,
                        start=0)

                url = item.content['src']
                f = pool.submit(self.download_worker, task_id, url, filename)
                futures.append(f)
                while len(futures) >= max_workers:
                    for f in futures:
                        if f.done():
                            futures.remove(f)
                            self.progress.remove_task(f.result())
                    sleep(0.1)

if __name__ == '__main__':
    p = ArgumentParser(description=__description__)
    p.add_argument('--out-dir', dest='out_dir', default='.',
                   help='Folder to save files into')
    p.add_argument('--out-list', dest='out_list', default='',
                   help='File to save links into')
    p.add_argument('--client-id', dest='client_id',
                   default=environ.get('DA_CLIENT_ID'),
                   help='DeviantArt client id (defaults to $DA_CLIENT_ID)')
    p.add_argument('--client-secret', dest='client_secret',
                   default=environ.get('DA_CLIENT_SECRET'),
                   help='DeviantArt client key (defaults to $DA_CLIENT_SECRET)')
    p.add_argument('--max-items', dest='max_items', type=int, default=0,
                   help='Download at most N items. 0 means no limit')
    p.add_argument('--max-workers', dest='max_workers', type=int, default=8,
                   help='Maximum number of active download workers')
    p.add_argument('tag', help='Tag to search for downloading')
    args = p.parse_args()
    
    dl = DeviantArtDownloader(args.client_id, args.client_secret)
    dl.download(tag=args.tag,
                out_dir=args.out_dir,
                max_items=args.max_items,
                max_workers=args.max_workers,
                list_path=args.out_list or None)

