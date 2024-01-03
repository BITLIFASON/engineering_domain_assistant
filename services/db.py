import os

from langchain.document_loaders import PDFMinerLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain.docstore.document import Document


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
