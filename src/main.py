from whoosh import index
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from hoosh.analysis import StemmingAnalyzer
import os

scheama = Schema(
    title=TEXT(stored=True, analyzer=StemmingAnalyzer()),
    content=TEXT(stored=True, analyzer=StemmingAnalyzer()),
    path=ID(stored=True, unique=True)
)

if not os.path.exists("indexdir"):
    os.mkdir("indexdir")

ix = index.create_in("indexdir", scheama)

writer = ix.writer()

writer.add_document(title=u"First document", content=u"This is the first document we've added!", path=u"/a")
writer.add_document(title=u"Second document", content=u"The second one is even more interesting!", path=u"/b")
writer.add_document(title=u"Third document", content=u"And this is the third one, which is also quite interesting.", path=u"/c")
writer.commit()