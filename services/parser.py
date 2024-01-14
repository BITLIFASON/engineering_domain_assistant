import os
import time
import sqlite3
import requests
from bs4 import BeautifulSoup
from db import create_db, update_db


dict_urls = {'ГОСТ': 'gostlist',
             'СП': 'splist'}


def verify(session, name_doc):

    print(name_doc)

    params_res = {'searchString': name_doc,
                  'searchcatalogbtn': 'Искать'}

    type_doc = dict_urls.get(name_doc.split(' ')[0])
    if type_doc is None:
        return 'Не известен'

    url = f'https://www.gostinfo.ru/catalog/{type_doc}/'
    r = session.get(url,params=params_res)
    soup = BeautifulSoup(r.text, 'lxml')

    id_ = soup.find_all('h2', class_='H2SearchResultsTitle')[0].a['id'][4:]

    params_res = {'id': id_}
    url = 'https://www.gostinfo.ru/catalog/Details/'
    r = session.get(url,params=params_res)
    soup = BeautifulSoup(r.text, 'lxml')

    desc = soup.find_all('tr')

    status = 'Не известен'
    for i in range(len(desc)):
        if desc[i].th.text == 'Статус':
            status = desc[i].h3.text
            break


    return status


def main():

    DOCS_PATH = '../docs'
    DB_DIR = '../db'

    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    DB_PATH = DB_DIR + "/" + "docs.sqlite"
    if not os.path.exists(DB_PATH):
        create_db(DB_PATH)

    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; en-US; rv:76.0) Gecko/20100101 Firefox/76.0'}
    session.headers.update(headers)

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    for doc in os.listdir(DOCS_PATH):
        status = verify(session, doc[:-4])
        update_db(cursor, doc[:-4], status)
        time.sleep(1)

    connection.commit()
    connection.close()


if __name__ == '__main__':
    main()