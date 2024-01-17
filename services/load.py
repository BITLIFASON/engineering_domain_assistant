import os
import time
import json

from langchain.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from db import load_document, processing_content, add_document


with open('../credentials.json', 'r') as f:
    credentials = json.load(f)

OPENAI_API_KEY = credentials["OPENAI_API_KEY"]


def main():

    start = time.time()

    DOCS_PATH = '../docs'
    DB_DIR = '../db'

    file_paths = os.listdir(DOCS_PATH)

    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    retriever_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    embeddings = HuggingFaceEmbeddings(model_name=retriever_name)
    # embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

    vectorstore = Chroma(collection_name='engineering_store',
                         embedding_function=embeddings,
                         persist_directory="../db")

    collection = vectorstore.get()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000,
                                                   chunk_overlap=100,
                                                   add_start_index=True)

    if len(collection['ids']) == 0:

        for path in file_paths:
            add_document(vectorstore, text_splitter, DOCS_PATH, path)

        vectorstore.persist()

    end = time.time()
    print(end - start, 'seconds')


if __name__ == '__main__':
    main()