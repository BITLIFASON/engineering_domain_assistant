import os
import sqlite3
import requests
from bs4 import BeautifulSoup
from db import create_db, update_db


def verify(session, name_doc):

    params_res = {'searchString': name_doc,
                  'searchcatalogbtn': 'Искать'}
    url = 'https://www.gostinfo.ru/catalog/gostlist'
    r = session.get(url,params=params_res)
    soup = BeautifulSoup(r.text, 'lxml')

    id_ = soup.find_all('h2', class_='H2SearchResultsTitle')[0].a['id'][4:]

    params_res = {'id': id_}
    url = 'https://www.gostinfo.ru/catalog/Details/'
    r = session.get(url,params=params_res)
    soup = BeautifulSoup(r.text, 'lxml')

    desc = soup.find_all('tr')

    doc = desc[10].h3.text
    status = desc[21].h3.text

    if status != 'Действует':
        doc = desc[15].h3.text
        status = desc[23].h3.text

    return doc, status


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
        _, status = verify(session, doc[:-4])
        update_db(cursor, doc[:-4], status)

    connection.commit()
    connection.close()


if __name__ == '__main__':
    main()