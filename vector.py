import json
from langchain_chroma import Chroma
from langchain_core.documents import Document
import os
from uuid import uuid4
from langchain_ollama import OllamaEmbeddings
import uuid

def get_id():
    return str(uuid.uuid4())

embeddings = OllamaEmbeddings(model = "qwen3-embedding:0.6b")

db_location = "./chroma_langchain_db"
add_documents = not os.path.exists(db_location)


def remove_spaces(s: str):
    return " ".join(s.split())

with open("archive\CUAD_v1\CUAD_v1.json", "r") as f:
        dataset = json.load(f)

if add_documents:
    

    documents = []
    ids = []
    for i in range(400, 510):
        item = dataset["data"][i]
        title = item.get("title", "Unknown Contract")

        for paragraph in item["paragraphs"]:
            base_id = get_id()
            base_document = Document(
                page_content = remove_spaces(paragraph["context"]),
                metadata = {
                    "source": title,
                    "type": "full_context"
                },
                id = base_id
            )
            documents.append(base_document)
            ids.append(base_id)

            for qa in paragraph["qas"]:
                if qa["is_impossible"]:
                    continue
                risk_category = qa["question"].split("\"")[1]
                answers = ""
                answers = answers + " " + " ".join(answer["text"] for answer in qa["answers"])
                answers = remove_spaces(answers)
                risk_id = get_id()
                risk_document = Document(
                    page_content = f"Clause type: {risk_category}\nContent: {answers}",
                    metadata = {
                        "source": title,
                        "is_risk_clause": True 
                    },
                    id = risk_id
                )
                documents.append(risk_document)
                ids.append(risk_id)

vector_store = Chroma(
    collection_name="legal_auditor",
    persist_directory=db_location,
    embedding_function=embeddings
)

if add_documents:
    vector_store.add_documents(documents = documents, ids = ids)

retriever = vector_store.as_retriever(
    search_kwargs={"k": 10}
)

