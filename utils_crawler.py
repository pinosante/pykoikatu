import argparse
import hashlib
import json
import os
import pickle
import queue
import re
import shutil
import sys
import threading
import time
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup


def hash_sum(file_path):
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()


def fetch_url(file_url, file_path):
    with urllib.request.urlopen(urllib.request.Request(file_url)) as r, open(
            file_path, 'wb') as f:
        shutil.copyfileobj(r, f, length=8192)


def md5_pickle(md5_path, md5_dict):
    with open(md5_path, 'wb') as f:
        pickle.dump(md5_dict, f)


def md5_unpickle(md5_path):
    with open(md5_path, 'rb') as f:
        md5_dict = pickle.load(f)
    return md5_dict


def xml_parser(url, n_args):
    (args_booru, args_pages, args_limit, args_tags, args_rating, md5_dict,
     out_dir) = n_args

    ratings = {
        's': 1,
        'q': 2,
        'e': 3,
        'Safe': 1,
        'Questionable': 2,
        'Explicit': 3
    }

    if args_booru == 'gelbooru':
        page = 'pid'
        data = {
            'page': 'dapi',
            's': 'post',
            'q': 'index',
            'tags': args_tags,
            'limit': args_limit,
            'pid': 1,
        }
    elif args_booru == 'illusioncards':
        page = 'pid'
        data = {
            'page': 'post',
            's': 'list',
            'tags': args_tags,
            'pid': 1,
        }
    else:
        page = 'page'
        data = {
            'tags': args_tags,
            'limit': args_limit,
            'page': 1,
        }

    xml_queue = queue.Queue()
    for current_page in range(1, args_pages + 1):
        print('Parsing page {}'.format(current_page))

        if args_booru == 'illusioncards':
            data[page] = (current_page - 1) * 20
        else:
            data[page] = current_page
        request_data = urllib.parse.urlencode(data)

        if args_booru == 'konachan':
            time.sleep(2)
        req = urllib.request.Request(url + '?' + request_data)
        with urllib.request.urlopen(req) as response:
            soup = BeautifulSoup(response, 'lxml')

        for img in soup.find_all('img'):
            if img.get('alt') != 'post':
                continue

            rating_str = re.compile('rating:(.*)').findall(img['title'])[0]
            rating = ratings[rating_str]
            if rating > args_rating:
                continue

            # Not really MD5
            md5 = re.compile('thumbnail_(.*).png').findall(img['src'])[0]
            if md5 in md5_dict:
                continue

            file_url = img['src']
            file_url = file_url.replace('thumbnail_', '')
            file_url = file_url.replace('thumbnail', 'image')
            file_url = file_url.replace('thumbs', 'img')
            file_extension = os.path.splitext(file_url)[1]
            file_name = md5 + file_extension
            file_path = os.path.join(out_dir, file_name)
            # file_tags = img['title'].split('  ')[0].strip().split()
            xml_queue.put([file_url, file_path, md5])

    print('Total images: {}'.format(xml_queue.qsize()))
    return xml_queue


def json_parser(url, n_args):
    (args_booru, args_pages, args_limit, args_tags, args_rating, md5_dict,
     out_dir) = n_args

    ratings = {
        's': 1,
        'q': 2,
        'e': 3,
        'Safe': 1,
        'Questionable': 2,
        'Explicit': 3
    }

    json_queue = queue.Queue()
    for current_page in range(1, args_pages + 1):
        print('Parsing page {}'.format(current_page))

        request_data = urllib.parse.urlencode({
            'tags': args_tags,
            'limit': args_limit,
            'page': current_page
        }).encode()

        if args_booru == 'konachan':
            time.sleep(2)
        req = urllib.request.Request(url + '?' + request_data)
        with urllib.request.urlopen(req) as response:
            query_results = json.load(response)

        for result in query_results:
            rating = ratings[result['rating']]
            if rating > args_rating:
                continue

            md5 = result['md5']
            if md5 in md5_dict:
                continue

            file_url = result['file_url']
            file_extension = os.path.splitext(file_url)[1]
            file_name = md5 + file_extension
            file_path = os.path.join(out_dir, file_name)
            # file_tags = result['tags'].split()
            json_queue.put([file_url, file_path, md5])

    print('Total images: {}'.format(json_queue.qsize()))
    return json_queue


class DownloadThread(threading.Thread):
    def __init__(self, dl_queue, md5_queue):
        threading.Thread.__init__(self)
        self.dl_queue = dl_queue
        self.md5_queue = md5_queue

    def run(self):
        while True:
            try:
                count = 0
                file_url, file_path, md5 = self.dl_queue.get_nowait()
                file_extension = os.path.splitext(file_url)[1]
                file_name = md5 + file_extension
                while count < 3:
                    count += 1
                    fetch_url(file_url, file_path)
                    if len(md5) != 32 or md5 == hash_sum(file_path):
                        self.md5_queue.put_nowait([md5, file_name])
                        break
                else:
                    print('Failed to download {}'.format(file_name))
                qsize = self.dl_queue.qsize()
                if qsize > 0:
                    print('Remaining images: {}'.format(qsize))
            except queue.Empty:
                break
