import streamlit as st
from whoosh import index
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from whoosh.query import Every # Corrected: Every is from whoosh.query
from whoosh.analysis import StemmingAnalyzer
from whoosh import highlight
import os
import uuid
from datetime import datetime

# --- Configuration ---
INDEX_DIR = "indexdir"

# --- 1. Schema Definition with enhancements ---
schema = Schema(
    title=TEXT(stored=True, analyzer=StemmingAnalyzer(), sortable=True),
    content=TEXT(stored=True, analyzer=StemmingAnalyzer()),
    # path is crucial for unique identification and deletion
    path=ID(stored=True, unique=True)
)

# --- 2. Robust Index Loading ---
@st.cache_resource
def get_or_create_index(dir_name, _schema_obj):
    """
    Initializes or opens the Whoosh index.
    Uses Streamlit's cache_resource to ensure the index is only loaded/created once.
    The _schema_obj argument is ignored by the cache.
    """
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)
        st.info(f"Directory '{dir_name}' created.")

    try:
        ix = index.open_dir(dir_name)
        st.success(f"Opened existing index in '{dir_name}'.")
    except index.EmptyIndexError:
        st.warning(f"Index in '{dir_name}' is empty or corrupt. Creating a new one.")
        ix = index.create_in(dir_name, _schema_obj)
    except Exception as e:
        st.error(f"Error opening index: {e}. Attempting to create a new one.")
        ix = index.create_in(dir_name, _schema_obj)
    return ix

# Initialize the index (this will run only once due to @st.cache_resource)
ix = get_or_create_index(INDEX_DIR, schema)


# --- Whoosh Operations ---

def add_document_to_index(index_obj, title, content, path=None):
    """Adds a new document to the index."""
    if not path:
        current_year = datetime.now().year
        path = f"/docs/{current_year}/{uuid.uuid4()}"
    writer = index_obj.writer()
    try:
        writer.add_document(title=title, content=content, path=path)
        writer.commit()
        st.success(f"Document '{title}' added successfully with path: {path}")
    except Exception as e:
        writer.abort()
        st.error(f"Error adding document: {e}")

def delete_document_from_index(index_obj, path_to_delete):
    """Deletes a document from the index by its path."""
    writer = index_obj.writer()
    try:
        from whoosh.query import Term
        q = Term("path", path_to_delete) # Create a Term query for exact match on 'path'
        
        deleted_count = writer.delete_by_query(q)
        writer.commit()
        if deleted_count > 0:
            st.success(f"Document with path '{path_to_delete}' deleted successfully.")
        else:
            st.warning(f"No document found with path '{path_to_delete}' to delete.")
    except Exception as e:
        writer.abort()
        st.error(f"Error deleting document: {e}")

def get_all_documents(index_obj):
    """Retrieves all documents from the index for traversal/listing."""
    documents = []
    with index_obj.searcher() as searcher:
        results = searcher.search(Every(), limit=None)
        for hit in results:
            documents.append(dict(hit)) # <--- CORRECTED LINE HERE
    return documents


# --- Initial Document Population (on startup if index is empty) ---
def add_initial_documents_on_startup(index_obj):
    documents_to_add = [
        {u"title": u"Whoosh Introduction", u"content": u"This document introduces the Whoosh library for Python. It covers basic indexing and searching concepts.", u"path": u"/docs/intro"},
        {u"title": u"Advanced Whoosh Searching", u"content": u"Learn about advanced search techniques in Whoosh, including boolean operators, phrase searching, and wildcards. It's truly interesting for developers.", u"path": u"/docs/advanced"},
        {u"title": u"Python Programming Basics", u"content": u"Fundamental concepts of Python programming are discussed here. This is a basic introduction.", u"path": u"/docs/python_basics"},
        {u"title": u"Interesting Algorithms", u"content": u"Explore various interesting algorithms and data structures. This topic is quite interesting for computer science students.", u"path": u"/docs/algorithms"},
        {u"title": u"Data Science with Python", u"content": u"An overview of data science methodologies and how Python is used in this field.", u"path": u"/docs/data_science"}
    ]

    if index_obj.is_empty():
        st.info("Adding initial documents to the index...")
        writer = index_obj.writer()
        for doc in documents_to_add:
            writer.add_document(**doc)
        writer.commit()
        st.success("Initial documents added and committed.")
    else:
        st.info("Index already contains documents. Skipping initial document addition.")

# Add documents on startup if the index is empty
add_initial_documents_on_startup(ix)


# ------- Streamlit UI -------
st.set_page_config(page_title="Whoosh Search Engine", layout="wide")
st.title("📚 Simple Whoosh Search Engine with CRUD-like Operations")

# --- Tabs for different actions ---
tab1, tab2, tab3, tab4 = st.tabs(["Search", "Add Document", "Delete Document", "View All Documents"])

with tab1:
    st.header("Search Documents")
    search_query_str = st.text_input(
        "Enter your search query:",
        placeholder="e.g., 'python', 'interesting AND advanced', '\"data science\"', 'algo*', 'title:python'",
        key="search_input" # Unique key for this widget
    )

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        results_per_page = st.slider("Results per page", min_value=1, max_value=10, value=3, key="search_pagelen")
    with col2:
        sort_option = st.selectbox("Sort results by", ["relevance", "title"], key="search_sort")
    with col3:
        default_search_field = st.selectbox("Default search field", ["content", "title"], key="search_field")

    search_button = st.button("Search", key="do_search_button")

    if search_button and search_query_str:
        st.markdown("---")
        try:
            parser = QueryParser(default_search_field, ix.schema)
            query = parser.parse(search_query_str)

            st.write(f"Searching for: `{query}` (Default field: `{default_search_field}`)")

            with ix.searcher() as searcher:
                if sort_option == 'title':
                    from whoosh import sorting
                    results = searcher.search(query, limit=None, sortedby="title")
                else:
                    results = searcher.search(query, limit=None)

                if not results:
                    st.warning("No results found.")
                else:
                    st.subheader(f"Found {results.total} results:")

                    total_pages = (results.total + results_per_page - 1) // results_per_page
                    
                    # Reset page to 1 if search query changes or current page is out of bounds
                    if 'current_page' not in st.session_state or st.session_state.get('last_query') != search_query_str:
                        st.session_state.current_page = 1
                        st.session_state.last_query = search_query_str
                    
                    # Ensure current_page doesn't exceed total_pages after a new search
                    if st.session_state.current_page > total_pages:
                        st.session_state.current_page = 1 

                    pagination_cols = st.columns([1, 2, 1])
                    with pagination_cols[0]:
                        if st.session_state.current_page > 1:
                            if st.button("Previous Page", key="search_prev_button"):
                                st.session_state.current_page -= 1
                                st.rerun()

                    with pagination_cols[1]:
                        st.markdown(f"<div style='text-align: center; font-weight: bold;'>Page {st.session_state.current_page} of {total_pages}</div>", unsafe_allow_html=True)
                    
                    with pagination_cols[2]:
                        if st.session_state.current_page < total_pages:
                            if st.button("Next Page", key="search_next_button"):
                                st.session_state.current_page += 1
                                st.rerun()

                    start_idx = (st.session_state.current_page - 1) * results_per_page
                    end_idx = start_idx + results_per_page

                    displayed_results = results[start_idx:end_idx]

                    for i, result in enumerate(displayed_results):
                        st.markdown(f"---", unsafe_allow_html=True)
                        st.markdown(f"**Title**: {result['title']}")
                        st.markdown(f"**Path**: `{result['path']}`")
                        st.markdown(f"**Content**: {result['content']}")
                        
                        st.markdown("---")
                        st.markdown("**Highlights**:")
                        formatter = highlight.HtmlFormatter(tagname="em", classname="highlight")
                        highlighted_content = result.highlights("content", formatter=formatter)
                        st.markdown(f"<div>{highlighted_content}</div>", unsafe_allow_html=True)
                        st.markdown("---")

                    st.markdown("""
                    <style>
                        .highlight {
                            background-color: yellow;
                            font-weight: bold;
                        }
                    </style>
                    """, unsafe_allow_html=True)


        except Exception as e:
            st.error(f"Error during search: {e}")
            st.info("""
            **Common query syntax examples:**
            - Single word: `document`
            - Multiple words (AND by default): `whoosh python`
            - Boolean operators: `whoosh AND interesting`, `python OR algorithms`, `NOT basic`
            - Phrase search: `\"data science\"`
            - Wildcard search: `interes*` (prefix wildcard), `*ing` (suffix wildcard - generally slow)
            - Fuzzy search: `algorithmn~` (searches for similar spellings)
            - Field-specific search: `title:python`
            - Combining: `title:whoosh AND (interesting OR basic)`
            """)

with tab2:
    st.header("Add New Document (Insertion)")
    st.markdown("Enter details to add a new document to the index.")
    new_title = st.text_input("Document Title:", key="add_title")
    new_content = st.text_area("Document Content:", key="add_content")
    # Provide a hint for automatic path generation
    new_path = st.text_input("Document Path (optional, unique ID will be generated if left blank):", key="add_path", 
                             placeholder=f"e.g., /docs/{datetime.now().year}/my_unique_id")

    add_doc_button = st.button("Add Document", key="do_add_button")

    if add_doc_button:
        if new_title and new_content:
            # Clear Streamlit's cache for get_or_create_index so new docs are visible immediately
            get_or_create_index.clear()
            add_document_to_index(ix, new_title, new_content, new_path if new_path else None)
            st.rerun()
        else:
            st.warning("Please provide both a title and content for the new document.")

with tab3:
    st.header("Delete Document")
    st.markdown("To delete a document, enter its exact `path` (ID). You can find paths in the 'View All Documents' tab or search results.")
    path_to_delete = st.text_input("Enter the Path/ID of the document to delete:", key="delete_path_input")
    delete_button = st.button("Delete Document", key="do_delete_button")

    if delete_button:
        if path_to_delete:
            get_or_create_index.clear() # Clear cache to ensure index is re-opened/re-read
            delete_document_from_index(ix, path_to_delete)
            st.rerun()
        else:
            st.warning("Please enter a document path/ID to delete.")

with tab4:
    st.header("All Indexed Documents (Traversal)")
    st.info("This section displays all documents currently in the index. Use the 'Path' for deletion.")
    
    # The list of all documents should be retrieved fresh whenever this tab is active or refreshed
    # Adding a button to explicitly refresh for user control, though rerun() also triggers it.
    refresh_all_docs_button = st.button("Refresh All Documents List", key="refresh_all_docs")

    # This call will rerun if any button is clicked or input changes, due to Streamlit's rerunning mechanism
    all_docs = get_all_documents(ix)
    
    if all_docs:
        st.write(f"Total documents in index: {len(all_docs)}")
        for i, doc in enumerate(all_docs):
            st.markdown(f"--- **Document {i+1}** ---", unsafe_allow_html=True)
            st.markdown(f"**Title**: {doc.get('title', 'N/A')}")
            st.markdown(f"**Path**: `{doc.get('path', 'N/A')}`") # Display path prominently
            st.markdown(f"**Content**: {doc.get('content', 'N/A')}")
        st.markdown("---")
    else:
        st.info("No documents found in the index.")