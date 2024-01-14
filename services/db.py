import os
import sqlite3

from langchain.document_loaders import PDFMinerLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain.docstore.document import Document


def create_db(db_path):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute(
        """CREATE TABLE docs(id INTEGER PRIMARY KEY,
                             name VARCHAR(50),
                             status VARCHAR(20))"""
    )

    connection.commit()
    connection.close()


def insert_db(cursor, name_doc, status):

    cursor.execute("SELECT MAX(id) FROM docs LIMIT 1")
    id_ = cursor.fetchall()[0][0]

    if id_ is not None:
        id_ += 1
    else:
        id_ = 0

    cursor.execute(
        "INSERT INTO docs (id, name, status) VALUES (?, ?, ?)",
        (id_, name_doc, status),
    )


def update_db(cursor, name_doc, status):

    cursor.execute(f"SELECT id FROM docs WHERE name='{name_doc}'")
    id_ = cursor.fetchone()

    if id_ is None:
        insert_db(cursor, name_doc, status)
    else:
        cursor.execute(
            "UPDATE docs SET name=?, status=? WHERE id=?",
            (id_, name_doc, status, id_),
        )


def load_document(file_path: str) -> Document:
    loader = PDFMinerLoader(file_path)
    return loader.load()[0]


def processing_content(content: str) -> str:
    return content\
        .replace("  ", " ") \
        .replace("\xad\n\n", "") \
        .replace("\xad\n", "") \
        .replace(" \n\n", " ") \
        .replace(" \n", " ") \
        .replace("\x0c", "\n")


def add_document(vectorstore, data_path, path):

    collection = vectorstore.get()
    names_docs = set(list(map(lambda x: x["source"].split("\\")[-1],
                              collection["metadatas"])))

    if path.split("\\")[-1] in names_docs:
        return False

    source_document = load_document(os.path.join(data_path, path))
    source_document.page_content = processing_content(source_document.page_content)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000,
                                                   chunk_overlap=100,
                                                   add_start_index=True)
    documents = text_splitter.split_documents(source_document)

    for doc in documents:
        vectorstore.add_documents([doc])

    return True


def update_document(vectorstore, data_path, path):

    collection = vectorstore.get()

    filter_doc = list(map(lambda x: x["source"].split("\\")[-1] == path.split("\\")[-1],
                          collection["metadatas"]))
    ids_doc = [ids for i, ids in enumerate(collection["ids"]) if filter_doc[i]]

    vectorstore.delete(ids_doc)

    add_document(vectorstore, data_path, path)

    return True
