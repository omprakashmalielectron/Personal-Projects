# omprakash.malli
Capstone projects for omprakash.malli@neuleap.ai

In this i have done ingestion part using Docling. Docling takes a pdf and parses it into a docling file which can be configured as per requirements also it provides flexibility of handling images via local or API based VLM. IT also have ability to integrate with OCR so over all highly custmoizeable pipline to take various file types as input and convert them to a docling file(docling uses lightweight vision model to do layout detection in pdf pages along with detection of images and tables to preserve their structure while parsing pdf page by page). This docling file then can be exported as markdown or json or further document transformation can be done on docling file itself like docling provides rich set of libraries to do various type of chnuking like hybrid chunking or hirearchial chunking which is also customizable(along with metadata about chunk).Then this chunks is converted to Langchain document object so that it can be stored into vectordb supported by langchain.

In retriveal part i have tried to implement it in two ways one which keeps track of previous converation and one which doesn't.

FURTHER SCOPE OF IMPROVEMENTS:

1) Currently hybrid chunker is doing token based chunking while respecting the input context length of embedding model but this also causes chunks to be not so ideal or respect the hierarchy of the document which can be imporvoed by using llama modles to to chunk and store hierarchial chnuks which help us avoid creating chunks that  splits tables from middle or give chunks with very ununiform sizes like some chunks are way big(upto context length of embedding models) and some are way small(they don't have any semantic meaning).
2) Even retriver part can be modified docling provides a way to contextualize each chunk which can help in creating chunks with rich metadata and the we can modifiy our retriver to do hybrid search along with ability to do metadata based filtering. This would help in answer question like can you tell me what is abstract of xyz.pdf.
