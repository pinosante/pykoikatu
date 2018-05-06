# Modified from https://github.com/CirnoIsTheStrongest/BiriCrawler

from utils_crawler import *


def main():
    start_time = time.time()

    parser = argparse.ArgumentParser(description='*Booru image crawler!')
    parser.add_argument(
        '-b',
        '--booru',
        type=str,
        choices=[
            'konachan', 'oreno', 'danbooru', 'sankaku', 'nekobooru',
            'gelbooru', 'illusioncards'
        ],
        default='illusioncards',
        help='choose your booru')
    parser.add_argument(
        '-t', '--tags', type=str, default='koikatu', help='tags to download')
    parser.add_argument(
        '-l',
        '--limit',
        type=int,
        default=20,
        help='maximum number of images per page')
    parser.add_argument(
        '-p',
        '--pages',
        type=int,
        default=10,
        help='maximum number of pages to download')
    parser.add_argument(
        '-c',
        '--num_conn',
        type=int,
        default=8,
        help='max number of threads to use')
    parser.add_argument(
        '-r',
        '--rating',
        type=int,
        choices=[1, 2, 3],
        default=3,
        help='desired rating for images')
    parser.add_argument(
        '-x',
        '--parse_type',
        type=str,
        choices=['x', 'j'],
        default='x',
        help='desired parsing type, xml or json')
    parser.add_argument(
        '-o', '--out_dir', type=str, default='tmp', help='output directory')
    args = parser.parse_args()

    boorus_xml = {
        'konachan': 'http://konachan.com/post/index.xml',
        'oreno': 'http://oreno.imouto.org/post/index.xml',
        'danbooru': 'http://danbooru.donmai.us/post/index.xml',
        'nekobooru': 'http://nekobooru.net/post/index.xml',
        'gelbooru': 'http://gelbooru.com/index.php',
        'illusioncards': 'http://illusioncards.booru.org/index.php',
    }
    boorus_json = {
        'konachan': 'http://konachan.com/post/index.json',
        'oreno': 'http://oreno.imouto.org/post/index.json',
        'danbooru': 'http://danbooru.donmai.us/post/index.json',
        'sankaku': 'http://chan.sankakucomplex.com/post/index.json',
        'nekobooru': 'http://nekobooru.net/post/index.json',
    }

    md5_path = os.path.join(os.path.dirname(__file__), 'md5.pickle')
    try:
        md5_dict = md5_unpickle(md5_path)
    except IOError:
        md5_dict = {}
    md5_queue = queue.Queue()

    out_dir = args.out_dir
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    try:
        if args.parse_type == 'x':
            dl_url = boorus_xml[args.booru.lower()]
        elif args.parse_type == 'j':
            dl_url = boorus_json[args.booru.lower()]
        else:
            raise Exception('Unknown booru/parse_type: {} {}'.format(
                args.booru, args.parse_type))
    except KeyError:
        raise Exception('Unknown booru/parse_type: {} {}'.format(
            args.booru, args.parse_type))

    n_args = (args.booru, args.pages, args.limit, args.tags, args.rating,
              md5_dict, out_dir)

    if args.parse_type == 'x':
        dl_queue = xml_parser(dl_url, n_args)
    elif args.parse_type == 'j':
        dl_queue = json_parser(dl_url, n_args)

    threads = []
    for count in range(args.num_conn):
        t = DownloadThread(dl_queue, md5_queue)
        t.start()
        threads.append(t)
    for thread in threads:
        thread.join()

    while True:
        try:
            md5, file_name = md5_queue.get_nowait()
            md5_dict[md5] = file_name
        except queue.Empty:
            break

    md5_pickle(md5_path, md5_dict)
    time_elapsed = time.time() - start_time
    print('All files downloaded! Total time elapsed: {:.3f} seconds'.format(
        time_elapsed))


if __name__ == '__main__':
    main()
