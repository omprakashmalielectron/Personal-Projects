import os
from pathlib import Path
from google import genai
from openai import OpenAI
import sentence_transformers
from dotenv import load_dotenv
from transformers import AutoTokenizer
from docling.chunking import HybridChunker
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc.document import ImageRefMode
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.transforms.serializer.markdown import MarkdownTableSerializer , MarkdownParams
from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider
)
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    PictureDescriptionApiOptions,
    TableStructureOptions,
    TesseractCliOcrOptions
)

load_dotenv("C:/Users/ompra/OneDrive/Documents/omprakash/untitledx31/.env")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
############################################################################################
######################## GROUND SETUP ENDS HERE ########################
###########################################################################################
print("############# Setup for ingestion is done ############")

def convert_with_images_tables_and_ocr(input_doc_path):
    api_key = os.environ.get("OPENAI_API_KEY")
    picture_desc_api_option = PictureDescriptionApiOptions(
        url="https://api.openai.com/v1/chat/completions",
        prompt=(
            "Describe this image in clear, factual sentences in a single paragraph. "
            "Focus on what is visible and relevant to a scientific document."
        ),
        params={
            "model": "gpt-4.1-mini",
        },
        headers={
            "Authorization": f"Bearer {api_key}",
        },
        timeout=60
    )

    pipeline_options = PdfPipelineOptions()
    
    pipeline_options.do_ocr = True
    pipeline_options.ocr_options = TesseractCliOcrOptions(
        force_full_page_ocr=True
    )
    
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=True
    )

    pipeline_options.do_picture_description = True
    pipeline_options.picture_description_options = picture_desc_api_option
    pipeline_options.generate_picture_images = True
    pipeline_options.images_scale = 2
    pipeline_options.enable_remote_services = True
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options
            )
        }
    )
    doc=converter.convert(input_doc_path)
    return doc
########################################################################################
###################### Creating docling document ends here #################
########################################################################################
def set_hybrid_chunker(
        tokenizer_model_id: str="sentence-transformers/all-MiniLM-L6-v2",
        max_token : int=512,
        image_mode :  ImageRefMode = ImageRefMode.PLACEHOLDER,
        image_placeholder: str = "[IMAGE]",
        mark_annotations: bool = True,
        include_annotations: bool = True,
        )->HybridChunker :
        tokenizer=HuggingFaceTokenizer(
        tokenizer=AutoTokenizer.from_pretrained(tokenizer_model_id),
        max_tokens=max_token
        )       
        class CustomSerializerProvider(ChunkingSerializerProvider):
                def get_serializer(self, doc):
                        return ChunkingDocSerializer(
                                doc=doc,
                                table_serializer=MarkdownTableSerializer(),
                                params=MarkdownParams(
                                image_mode=image_mode,
                                image_placeholder=image_placeholder,
                                mark_annotation=mark_annotations,
                                include_annotations=include_annotations
                                )
                        )
        return HybridChunker(
                tokenizer=tokenizer,
                max_tokens=max_token,
                serializer_provider=CustomSerializerProvider(),
                merge_peers=True
        )
############################################################################################
########################## Creation of hybrid chunker ends here #############
############################################################################################
def langchain_document_converter(file_path:str,namespace:str):
    print("### Creating docling_doc ###")
    docling_doc=convert_with_images_tables_and_ocr(file_path)
    print("### Creation of Docling_doc ends here ####")
    chunker = set_hybrid_chunker()
    chunks = chunker.chunk(docling_doc.document)
    documents = []
    for chunk in chunks:
        txt=chunker.contextualize(chunk)
        page_num=sorted({prov.page_no 
                         for item in chunk.meta.doc_items 
                         for prov in item.prov
                         if hasattr(prov, "page_no")})
        has_table = "|" in txt and "---" in txt
        has_image = "[IMAGE]" in txt
        metadata = {
            "source": str(file_path),
            "namespace": namespace,
            "page_numbers":",".join(map(str, page_num)),
            "has_table": has_table,
            "has_image": has_image,
        }
        documents.append(
            Document(
                page_content=txt,
                metadata=metadata,
            )
        )
    return documents
#############################################################################################
################ Creation of langchain document #################
#############################################################################################
embedding_model=HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    encode_kwargs={
        "normalize_embeddings":True,
        "batch_size":32
    }
)
def create_chroma_store(documents,persist_directory:str,collection_name:str):
    vectordb=Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        collection_name=collection_name,
        persist_directory=persist_directory
    )
    vectordb.persist()
    return vectordb
def ingest_pdf(
    pdf_path: str,
    namespace: str = "biomedical",
    persist_directory: str = "./chroma_store",
    collection_name: str = "Biomedical_Research_Papers",
):
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    documents = langchain_document_converter(
        file_path=str(pdf_path),
        namespace=namespace,
    )
    print("Document content for sureity")
    doc = documents[0]
    print(doc.page_content)
    print(doc.metadata)
    vectordb = create_chroma_store(
        documents=documents,
        persist_directory=persist_directory,
        collection_name=collection_name,
    )
    print("Ingestion complete")
    print(f"Collection: {collection_name}")
    print(f"Stored at: {persist_directory}")
    return vectordb
####################################################################################################
##################  Embeddings and text get's stored in Vector db ##############
####################################################################################################
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Ingest biomedical PDF into ChromaDB"
    )
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--namespace", default="biomedical")
    args = parser.parse_args()
    ingest_pdf(
        pdf_path=args.pdf_path,
        namespace=args.namespace,
    )