import re
from langchain_community.document_loaders import TextLoader
pattern=re.compile(r'[^\S\n]|(\n{2,})', re.MULTILINE)
txt=TextLoader("./folder/气象与气候学.txt",encoding="utf-8").load()
for doc in txt:
    doc.page_content=re.sub(pattern,lambda match: '\n' if match.group(1) else '',doc.page_content)
for doc in txt:
    print(doc.page_content[:1000])
