# -*- coding: utf-8 -*-

import sys
import os
import re
import datetime
import time
import json
import io
import hashlib

import xbmc
import xbmcgui
import xbmcplugin

from urllib.parse import urlencode
from urllib.parse import quote_plus
from urllib.parse import parse_qs
from PIL import Image

try:
    from sqlite3 import dbapi2 as sqlite
except Exception:
    from pysqlite2 import dbapi2 as sqlite

from resources.lib.common import *
from resources.lib.downloader import Downloader


class Browse:

    def __init__(self, query='bc=all&genre=all'):
        self.query = query
        self.args, _ = self.update_query(self.query)
        self.downloader = Downloader()

    def update_query(self, query, values=None):
        args = parse_qs(query, keep_blank_values=True)
        for key in args.keys():
            args[key] = args[key][0]
        args.update(values or {})
        return args, urlencode(args)

    def show_top(self):
        # 検索:日付
        self.__add_directory_item(name=Const.STR(
            30933), query='', action='setdate', iconimage=Const.CALENDAR)
        # 検索:チャンネル
        self.__add_directory_item(name=Const.STR(
            30934), query='', action='setchannel', iconimage=Const.RADIO_TOWER)
        # 検索:ジャンル
        self.__add_directory_item(name=Const.STR(
            30935), query='', action='setgenre', iconimage=Const.CATEGORIZE)
        # ダウンロード
        self.downloader.top(Const.DOWNLOADS)
        # end of directory
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def show_date(self):
        # すべての日付
        name = Const.STR(30820)
        # 月,火,水,木,金,土,日
        w = Const.STR(30920).split(',')
        w_en = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        # 次のアクション
        if self.args.get('bc') is None:
            action = 'setchannel'
        elif self.args.get('genre') is None:
            action = 'setgenre'
        else:
            action = 'search'
        _, query = self.update_query(self.query, {'date': ''})
        self.__add_directory_item(
            name, query, action, iconimage=Const.CALENDAR)
        # 曜日のメニューを追加
        for wd in range(7):
            date1 = w[wd]
            if wd == 6:
                name = '[COLOR red]%s[/COLOR]' % date1
            elif wd == 5:
                name = '[COLOR blue]%s[/COLOR]' % date1
            else:
                name = date1
            _, query = self.update_query(self.query, {'date': w_en[wd]})
            self.__add_directory_item(
                name, query, action, iconimage=Const.CALENDAR)
        # end of directory
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def show_channel(self):
        bc_list = [
            ('', Const.STR(30810)),
            ('nns', Const.STR(30811)),
            ('exnetwork', Const.STR(30812)),
            ('jnn', Const.STR(30813)),
            ('txn', Const.STR(30814)),
            ('fns', Const.STR(30815)),
            ('nhknet', Const.STR(30816)),
        ]
        for id, name in bc_list:
            # 次のアクション
            if self.args.get('genre') is None:
                action = 'setgenre'
            elif self.args.get('date') is None:
                action = 'setdate'
            else:
                action = 'search'
            _, query = self.update_query(self.query, {'bc': id})
            self.__add_directory_item(
                name, query, action, iconimage=Const.RADIO_TOWER)
        # end of directory
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def show_genre(self):
        genre_list = [
            ('drama', Const.STR(30801)),
            ('variety', Const.STR(30802)),
            ('news_documentary', Const.STR(30803)),
            ('anime', Const.STR(30804)),
            ('sport', Const.STR(30805)),
            ('other', Const.STR(30806)),
        ]
        for id, name in genre_list:
            # 次のアクション
            if self.args.get('bc') is None:
                action = 'setchannel'
            elif self.args.get('date') is None:
                action = 'setdate'
            else:
                action = 'search'
            _, query = self.update_query(self.query, {'genre': id})
            self.__add_directory_item(
                name, query, action, iconimage=Const.CATEGORIZE)
        # end of directory
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def search(self):
        # トークンを取得
        url = 'https://platform-api.tver.jp/v2/api/platform_users/browser/create'
        buf = urlread(url, ('data', b'device_type=pc'),
                      ('Origin', 'https://s.tver.jp'),
                      ('Referer', 'https://s.tver.jp/'),
                      ('Content-Type', 'application/x-www-form-urlencoded'))
        jso = json.loads(buf)
        platform_uid = jso.get('result', []).get('platform_uid')
        platform_token = jso.get('result', []).get('platform_token')
        Const.SET('platform_uid', platform_uid)
        Const.SET('platform_token', platform_token)
        filter_key = list(
            filter(None, [self.args.get('date'), self.args.get('bc')]))
        # 番組検索
        url = 'https://platform-api.tver.jp/service/api/v1/callTagSearch/%s?filterKey=%s&sortKey=open_at&require_data=later&platform_uid=%s&platform_token=%s' % (
            self.args.get('genre'), ','.join(filter_key), platform_uid, platform_token)
        buf = urlread(url, ('Origin', 'https://s.tver.jp'),
                      ('Referer', 'https://s.tver.jp/'),
                      ('x-tver-platform-type', 'web'))
        datalist = json.loads(buf).get('result', []).get('contents', [])
        datadict = {}
        for data in sorted(datalist, key=lambda item: self.__date(item), reverse=True):
            '''
            {
                "bool": {
                    "cast": 1
                },
                "catchup_id": "f0058710",
                "date": "7月14日(火)放送分",
                "expire": "10月21日(水) 00:53 終了予定",
                "ext": {
                    "adconfigid": null,
                    "allow_scene_share": true,
                    "catch": "",
                    "episode_number": "598",
                    "is_caption": false,
                    "live_lb_type": null,
                    "multiple_catchup": false,
                    "share_secret": "c950d127003629617cc5fffbcbde3c95",
                    "site_catch": "",
                    "stream_id": null,
                    "yospace_id": null
                },
                "href": "/feature/f0058710",
                "images": [
                    {
                        "image": "https://api-cdn.tver.jp/s3/@202010/image/@20201007/638c1baf-3a27-47f2-92f0-54038255ab77.jpg",
                        "large": "https://api-cdn.tver.jp/s3/@202010/large/@20201007/2444cd40-0558-4d18-923a-3496745ebbf0.jpg",
                        "right": "(C) ytv",
                        "small": "https://api-cdn.tver.jp/s3/@202010/small/@20201007/07009320-8d91-4308-85c4-7277758f03b3.jpg",
                        "type": "e_cut"
                    }
                ],
                "media": "読売テレビ",
                "mylist_id": "f0009802",
                "player": "videocloud",
                "pos": "/search",
                "publisher_id": "5330942432001",
                "reference_id": "Niketsu_598_200715",
                "service": "ts_ytv",
                "subtitle": "ジュニア衝撃ぬるいカップ麺＆芸人名言",
                "title": "にけつッ!!",
                "type": "catchup",
                "url": "http://www.ytv.co.jp/niketsu/"
            }
            '''
            # 表示
            self.__add_item(data)
        # end of directory
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def play(self, url):
        url = self.__extract_url(url)
        # xbmc.executebuiltin('PlayMedia(%s)' % url)
        xbmcplugin.setResolvedUrl(
            int(sys.argv[1]), succeeded=True, listitem=xbmcgui.ListItem(path=url))

    def download(self, url, contentid):
        url = self.__extract_url(url)
        self.downloader.download(url, contentid)

    def __extract_url(self, url):
        # 番組詳細を取得
        #
        # https://tver.jp/episode/77607556
        #
        vid = url.replace('https://tver.jp/episodes/', '')
        url = 'https://platform-api.tver.jp/service/api/v1/callEpisode/%s?platform_uid=%s&platform_token=%s' % (
            vid, Const.GET('platform_uid'), Const.GET('platform_token'))
        buf = urlread(url, ('Origin', 'https://s.tver.jp'),
                      ('Referer', 'https://s.tver.jp/'),
                      ('x-tver-platform-type', 'web'))
        episode_content = json.loads(buf)['result']['episode']['content']
        url = 'https://statics.tver.jp/content/episode/%s.json?v=%s' % (
            vid, episode_content['version'])
        episode_json = json.loads(
            urlread(url,
                    ('Origin', 'https://s.tver.jp'),
                    ('Referer', 'https://s.tver.jp/')))
        args = episode_json['video']
        # ポリシーキーを取得
        #
        # https://players.brightcove.net/4394098882001/TtyB0eZ4Y_default/index.min.js?_=1602300285436
        #
        url = 'https://players.brightcove.net/%s/%s_default/index.min.js' % (
            args['accountID'], args['playerID'])
        buf = urlread(url)
        #
        # options:{accountId:"4394098882001",policyKey:"BCpkADawqM1l5pA4XtMLusHj72LGzFewqKZzldpmNYTUQdoKnFL_GHhN3dg5FRnNQ5V7SOUKBl-tYFMt8CpSzuSzFAPhIHtVwmMz6F52VnMfu2UjDmeYfvvUqk0CWon46Yh-CZwIVp5vfXrZ"}
        #
        pk = re.search(
            r'options:\{accountId:"(.*?)",policyKey:"(.*?)"\}', buf.decode()).group(2)
        # HLSマスターのURLを取得
        if episode_json['broadcastProviderID'] != 'tx':
            ref_id = 'ref:' + args['videoRefID']
        else:
            ref_id = args['videoID']
        #
        # https://edge.api.brightcove.com/playback/v1/accounts/5102072603001/videos/ref%3Asunday_variety_episode_code_6950
        #
        url = 'https://edge.api.brightcove.com/playback/v1/accounts/%s/videos/%s' % (
            args['accountID'], ref_id)
        buf = urlread(url, ('Accept', 'application/json;pk=%s' % pk))
        jso = json.loads(buf)
        src = jso.get('sources')[3].get('src')
        #
        # https://manifest.prod.boltdns.net/manifest/v1/hls/v4/aes128/4394098882001/15157782-1259-4ba1-b9e6-ee7298b261f6/10s/master.m3u8?fastly_token=NWZhNjY1MTVfNGIyZjQzZDc0ZTg0YmY3NTg0OTE1YThjOGQzZjk2NDk5NTcyMzU4N2ViYzFiZDY2NDBjN2QwZWMxNTIwYjZmNw%3D%3D
        #
        return src

    def __date(self, item):
        # データの時刻情報
        itemdate = item.get('broadcastDateLabel', '')
        # 現在時刻
        now = datetime.datetime.now()
        year0 = now.strftime('%Y')
        date0 = now.strftime('%m-%d')
        # 日時を抽出
        date = '0000-00-00'
        m = re.match(r'(20[0-9]{2})年', itemdate)
        if m:
            date = '%s-00-00' % (m.group(1))
        m = re.match(r'([0-9]{1,2})月([0-9]{1,2})日', itemdate)
        if m:
            date1 = '%02d-%02d' % (int(m.group(1)), int(m.group(2)))
            date = '%04d-%s' % (int(year0) - 1 if date1 >
                                date0 else int(year0), date1)
        m = re.match(r'([0-9]{1,2})/([0-9]{1,2})', itemdate)
        if m:
            date1 = '%02d-%02d' % (int(m.group(1)), int(m.group(2)))
            date = '%04d-%s' % (int(year0) if date1 <
                                date0 else int(year0) - 1, date1)
        # 抽出結果
        return date

    def __labeldate(self, date):
        # listitem.date用に変換
        m = re.search('^([0-9]{4})-([0-9]{2})-([0-9]{2})', date)
        if m:
            date = '%s.%s.%s' % (m.group(3), m.group(2), m.group(1))
        return date

    def __contentid(self, item):
        return item['content']['id']

    def __thumbnail(self, item):
        # ファイルパス
        imagefile = os.path.join(
            Const.CACHE_PATH, '%s.png' % self.__contentid(item))
        if os.path.isfile(imagefile) and os.path.getsize(imagefile) < 1000:
            # delete imagefile
            os.remove(imagefile)
            # delete from database
            conn = sqlite.connect(Const.CACHE_DB)
            c = conn.cursor()
            # c.execute("SELECT cachedurl FROM texture WHERE url = '%s';" % imagefile)
            c.execute("DELETE FROM texture WHERE url = '%s';" % imagefile)
            conn.commit()
            conn.close()
        if os.path.isfile(imagefile):
            pass
        else:
            buffer = urlread(
                'https://statics.tver.jp/images/content/thumbnail/episode/small/%s.jpg' % item['content']['id'])
            image = Image.open(io.BytesIO(buffer))  # 320x180
            image = image.resize((216, 122))
            background = Image.new('RGB', (216, 216), (0, 0, 0))
            background.paste(image, (0, 47))
            background.save(imagefile, 'PNG')
        return imagefile

    def __add_item(self, item):
        # 番組情報を付加
        s = item['_summary'] = {
            'title': item['content'].get('seriesTitle', '') + item['content'].get('title', 'n/a'),
            'url': 'https://tver.jp/episodes/%s' % item['content']['id'],
            'date': self.__date(item),
            'description': item['content'].get('seriesTitle', '') + item['content'].get('title', 'n/a'),
            'source': item.get('media', 'n/a'),
            'category': '',
            'duration': '',
            'thumbnail': 'https://statics.tver.jp/images/content/thumbnail/episode/small/%s.jpg' % item['content']['id'],
            'thumbfile': self.__thumbnail(item),
            'contentid': self.__contentid(item),
        }
        # listitem
        labels = {
            'title': s['title'],
            'plot': '%s\n%s' % (s['date'], s['description']),
            'plotoutline': s['description'],
            'studio': s['source'],
            'date': self.__labeldate(s['date']),
        }
        listitem = xbmcgui.ListItem(s['title'])
        listitem.setArt(
            {'icon': s['thumbnail'], 'thumb': s['thumbnail'], 'poster': s['thumbnail']})
        listitem.setInfo(type='video', infoLabels=labels)
        listitem.setProperty('IsPlayable', 'true')
        # context menu
        contextmenu = []
        contextmenu += [(Const.STR(30938), 'Action(Info)')]  # 詳細情報
        contextmenu += self.downloader.contextmenu(item)  # ダウンロード追加/削除
        # トップに戻る
        contextmenu += [(Const.STR(30936),
                         'Container.Update(%s,replace)' % sys.argv[0])]
        # アドオン設定
        contextmenu += [(Const.STR(30937),
                         'RunPlugin(%s?action=settings)' % sys.argv[0])]
        listitem.addContextMenuItems(contextmenu, replaceItems=True)
        # add directory item
        url = '%s?action=%s&url=%s' % (
            sys.argv[0], 'play', quote_plus(s['url']))
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, listitem, False)

    def __add_directory_item(self, name, query, action, iconimage=''):
        # listitem
        listitem = xbmcgui.ListItem(name)
        listitem.setArt({'icon': iconimage})
        # context menu
        contextmenu = []
        if query:
            # トップに戻る
            contextmenu += [(Const.STR(30936),
                             'Container.Update(%s,replace)' % sys.argv[0])]
        # アドオン設定
        contextmenu += [(Const.STR(30937),
                         'RunPlugin(%s?action=settings)' % sys.argv[0])]
        listitem.addContextMenuItems(contextmenu, replaceItems=True)
        # add directory item
        url = '%s?action=%s&query=%s' % (
            sys.argv[0], action, quote_plus(query))
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, listitem, True)
