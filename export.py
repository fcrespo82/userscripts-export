#!/usr/bin/python
#coding: utf-8
from __future__ import print_function
import requests
import re
import os
from bs4 import BeautifulSoup
from pprint import pprint
import json
import md5
from datetime import datetime
from threading import Thread

DEBUG = False
VERBOSE = True

#-----------------------------------------------------------------------------

base_url = u'http://userscripts.org:8080'
details_url = u'http://userscripts.org:8080/scripts/show/{id}'
list_url = u'http://userscripts.org:8080/scripts?page={page}'
versions_url = u'http://userscripts.org:8080/scripts/versions/{id}?page={page}'
download_url = u'http://userscripts.org:8080/scripts/source/{id}.user.js'
version_download_url = u'http://userscripts.org:8080/scripts/version/{id_pai}/'

def _get_scripts_from_page(page):
    scripts = {}
    url = list_url.format(page = page)
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content)
        scripts_from_page = soup.findAll(u'tr', attrs={u'id': re.compile(u'scripts')})
        scripts_from_page = scripts_from_page[:2] if DEBUG else scripts_from_page #DEBUG limit
        total_scripts_from_page = len(scripts_from_page)
        for i, script_row in enumerate(scripts_from_page):
            print(u'{i} of {total} scripts in page {page}'.format(i=i+1, total=total_scripts_from_page, page = page))
            _id = re.sub(r'\D',u'',script_row.attrs[u'id'])
            if VERBOSE:
                print('Getting script id ' + str(_id))
                pass
            a = script_row.find('a', attrs={'class':'title'})
            #link = a.attrs[u'href']
            _title = a.attrs[u'title']
            script = {
                u'id':_id,
                u'title':_title,
                u'latest_version':download_url.format(id = _id),
                u'downloaded':False
            }
            script.update(_get_script_details(script[u'id']))

            _hash = md5.md5(json.dumps(script))
            _hash = _hash.hexdigest()
            script.update({u'hash_without_versions':_hash})

            if not scripts.has_key(_id) or (scripts.has_key(_id) and scripts[_id].has_key(u'hash_without_versions') and scripts[_id][u'hash_without_versions'] != _hash):
                script.update(_get_script_versions(script[u'id']))
                _hash = md5.md5(json.dumps(script))
                _hash = _hash.hexdigest()
                script.update({u'hash_with_versions':_hash})
            scripts.update({_id: script})
    _download_all_scripts(scripts)
    return scripts

def _get_script_details(id):
    url = details_url.format(id = id)
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content)
        _summary = soup.find('div', attrs={u'class':u'script_summary'}).p.contents[-1].strip()
    return {u'summary':_summary}

def _get_script_versions(id):
    _all_versions = []
    pages = 1 if DEBUG else 100 #DEBUG limit
    for page in xrange(1, pages):
        if VERBOSE:
            #print('Getting versions from page ' + str(page))
            pass
        _versions = _get_script_versions_page(id, page)
        if len(_versions) != 0:
            _all_versions.extend(_versions)
        else:
            break
    return {u'versions':_all_versions}

def _get_script_versions_page(_id, _page):
    url = versions_url.format(id = _id, page = _page)
    response = requests.get(url)
    _versions = []
    if response.status_code == 200:
        soup = BeautifulSoup(response.content)
        for version in soup.findAll('ul')[-1].findAll('li'):
            _link = base_url + version.find('a').attrs['href']
            _link = _link.replace(version_download_url.format(id_pai = _id), u'')
            _versions.append(_link)
    return _versions

def _get_pages():
    url = list_url.format(page = 1)
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content)
        last_page = soup.find(attrs={u'class':u'pagination'}).findAll(u'a')[-2].string
    return int(last_page)

def _get_scripts(scripts):
    pages = 2 if DEBUG else 10000 #DEBUG limit
    for page in xrange(1, pages):
        if VERBOSE:
            #print('Getting scripts from page ' + str(page))
            pass
        _scripts = _get_scripts_from_page(scripts, page)
        if len(_scripts) != 0:
            scripts.update(_scripts)
            _save(scripts)
        else:
            break
    return scripts

def _make_dir(_dir):
    _dir = os.path.realpath(_dir)
    if not os.path.exists(_dir):
        os.mkdir(_dir)

def _prepare_paths(_id):
    _base_path = u'./scripts/'
    _make_dir(_base_path)
    _script_path = u'./scripts/{0}/'.format(_id)
    _make_dir(_script_path)
    _versions_path = u'./scripts/{0}/versions/'.format(_id)
    _make_dir(_versions_path)
    return _base_path, _script_path, _versions_path

def _download_script(script):
    _id = script[u'id']
    _paths = _prepare_paths(_id)
    _description_file = os.path.join(_paths[1], script[u'id'] + '.md')
    with open(_description_file, 'w') as _file:
        _text = u'# {id} - {title}'.format(
            id = script[u'id'],
            title = script[u'title'].encode(u'ascii', 'replace'))
        _file.write(_text)
    _userscript_file = os.path.join(_paths[1], script[u'id'] + '.user.js')
    if not os.path.exists(_userscript_file):
        with open(_userscript_file, 'w') as _file:
            _file.write(requests.get(script[u'latest_version']).content)
    total_versions = len(script[u'versions'])
    for i, remote_file_version in enumerate(script[u'versions']):
        remote_file_version = version_download_url.format(id_pai = _id) + remote_file_version
        #print(u'({script})\t{i} of {total} script versions'.format(i=i+1, total=total_versions, script=_id))
        _version_file = os.path.join(_paths[2], os.path.basename(remote_file_version))
        if not os.path.exists(_version_file):
            with open(_version_file, 'w') as _file:
                _file.write(requests.get(remote_file_version).content)

def _download_all_scripts(script_dict):
    total_scripts = len(script_dict)
    for i, _id in enumerate(script_dict):
        script = script_dict[str(_id)]
        print(u'{i} of {total} scripts'.format(i=i+1, total=total_scripts))
        _download_script(script)
        script_dict[_id][u'downloaded'] = True

def _save(script_dict):
    script_dict.update({u'date':datetime.now().strftime(u'%Y-%m-%d_%H-%M-%S')})
    with open(u'saved_dict.txt', 'w') as _file:
        json.dump(script_dict, _file, sort_keys=True)

def _load(script_dict_file):
    _dict = {}
    with open(script_dict_file, 'r') as _file:
        _dict = json.load(_file)
    return _dict


def threaded():
    from Queue import Queue
    from threading import Thread, Lock

    def job():
        while True:
            global _all
            args = q.get()
            l = Lock()
            l.acquire()
            _all = _get_scripts_from_page(args)
            l.release()
            _save(_all)
            #print(u'DONE '*30)
            q.task_done()


    q = Queue()
    _pages = 3 if DEBUG else _get_pages() #DEBUG limit
    for x in xrange(1, _pages):
        q.put(x)

    _threads = 2 if DEBUG else 10 #DEBUG limit
    for x in xrange(1, _threads):
        th=Thread(target=job)
        th.daemon = True
        th.start()

    q.join()

def not_threaded():
    global _all
    _pages = 2 if DEBUG else _get_pages() #DEBUG limit
    for x in xrange(1, _pages):
        _all = _get_scripts_from_page(_all, x)
        _download_all_scripts(_all)


_ini = datetime.now()
#if os.path.exists(u'saved_dict.txt'):
#    _all = _load(u'saved_dict.txt')
#else:
#    _all = {}
_all = {}
#not_threaded()
threaded()
_fim = datetime.now()
#print(_fim - _ini)
_save(_all)