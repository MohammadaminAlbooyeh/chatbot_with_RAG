import streamlit as st
from whoosh import index
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from whoosh.analysis import StemmingAnalyzer
from whoosh import highlight
import os
# import uuid # Not directly used in the current version, but kept for reference

# --- Configuration ---
INDEX_DIR = "indexdir"

# --- 1. Schema Definition with enhancements ---
# Make 'title' sortable if you plan to sort by it
schema = Schema(
    title=TEXT(stored=True, analyzer=StemmingAnalyzer(), sortable=True),
    content=TEXT(stored=True, analyzer=StemmingAnalyzer()),
    path=ID(stored=True, unique=True)
)

# --- Custom Analyzer with Stop Words (Reference only, StemmingAnalyzer has its own) ---
# You can define a custom list of stop words if StemmingAnalyzer's default is not sufficient.
# For Persian, you'd need to provide a list of common Persian stop words.
# Example English stop words (StemmingAnalyzer already handles many common English ones):
# custom_stop_words = frozenset([
#     "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
#     "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
#     "to", "was", "were", "will", "with", "you"
# ])

# If you wanted a totally custom analyzer with specific filters:
# from whoosh.analysis import StopFilter, RegexTokenizer, LowercaseFilter, StemFilter
# my_custom_analyzer = RegexTokenizer() | LowercaseFilter() | StopFilter(stoplist=custom_stop_words) | StemFilter()
# Then use: content=TEXT(stored=True, analyzer=my_custom_analyzer)
# For now, we stick with StemmingAnalyzer as it's generally good for English.

# --- 2. Robust Index Loading ---
@st.cache_resource
def get_or_create_index(dir_name, _schema_obj): # Added '_' to _schema_obj for Streamlit caching
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

# --- 3. Adding Documents (only if the index is new/empty) ---
# This function should ideally be called in a separate indexing script,
# or triggered by a button in the UI for initial setup.
# For simplicity, we'll put it directly here, but it only runs if the index is empty.
def add_initial_documents(index_obj):
    documents_to_add = [
        {u"title": u"Whoosh Introduction", u"content": u"This document introduces the Whoosh library for Python. It covers basic indexing and searching concepts.", u"path": u"/docs/intro"},
        {u"title": u"Advanced Whoosh Searching", u"content": u"Learn about advanced search techniques in Whoosh, including boolean operators, phrase searching, and wildcards. It's truly interesting for developers.", u"path": u"/docs/advanced"},
        {u"title": u"Python Programming Basics", u"content": u"Fundamental concepts of Python programming are discussed here. This is a basic introduction.", u"path": u"/docs/python_basics"},
        {u"title": u"Interesting Algorithms", u"content": u"Explore various interesting algorithms and data structures. This topic is quite interesting for computer science students.", u"path": u"/docs/algorithms"},
        {u"title": u"Data Science with Python", u"content": u"An overview of data science methodologies and how Python is used in this field.", u"path": u"/docs/data_science"}
    ]

    if index_obj.is_empty():
        writer = index_obj.writer()
        st.info("Adding initial documents to the index...")
        for doc in documents_to_add:
            writer.add_document(**doc)
        writer.commit()
        st.success("Initial documents added and committed.")
    else:
        st.info("Index already contains documents. Skipping initial document addition.")

# Add documents on startup if the index is empty
add_initial_documents(ix)


# --- Streamlit UI ---
st.set_page_config(page_title="Whoosh Search Engine", layout="wide")
st.title("📚 Simple Whoosh Search Engine")

# Search Input
search_query_str = st.text_input(
    "Enter your search query:",
    placeholder="e.g., 'python', 'interesting AND advanced', '\"data science\"', 'algo*', 'title:python'"
)

# Search Options
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    results_per_page = st.slider("Results per page", min_value=1, max_value=10, value=3)
with col2:
    sort_option = st.selectbox("Sort results by", ["relevance", "title"])
with col3:
    default_search_field = st.selectbox("Default search field", ["content", "title"])

# Search Button
search_button = st.button("Search")

if search_button and search_query_str:
    st.markdown("---")
    try:
        # Define the parser for the chosen default field
        parser = QueryParser(default_search_field, ix.schema)
        query = parser.parse(search_query_str)

        st.write(f"Searching for: `{query}` (Default field: `{default_search_field}`)")

        with ix.searcher() as searcher:
            if sort_option == 'title':
                from whoosh import sorting
                # Using limit=None to get all results, then manual pagination for display
                results = searcher.search(query, limit=None, sortedby="title")
            else:
                results = searcher.search(query, limit=None)

            if not results:
                st.warning("No results found.")
            else:
                st.subheader(f"Found {results.total} results:")

                # Streamlit doesn't have built-in pagination like Whoosh's search_page for UI.
                # We'll implement a simple manual pagination for display.
                total_pages = (results.total + results_per_page - 1) // results_per_page
                
                # Use Streamlit's session state for current page
                if 'current_page' not in st.session_state:
                    st.session_state.current_page = 1
                
                # Adjust current_page if it's out of bounds after a new search
                if st.session_state.current_page > total_pages:
                    st.session_state.current_page = 1 # Reset to first page if new search has fewer pages

                # Display pagination controls
                pagination_cols = st.columns([1, 2, 1])
                with pagination_cols[0]:
                    if st.session_state.current_page > 1:
                        if st.button("Previous Page", key="prev_button"):
                            st.session_state.current_page -= 1
                            st.rerun() # Rerun to update results

                with pagination_cols[1]:
                    st.markdown(f"<div style='text-align: center; font-weight: bold;'>Page {st.session_state.current_page} of {total_pages}</div>", unsafe_allow_html=True)
                
                with pagination_cols[2]:
                    if st.session_state.current_page < total_pages:
                        if st.button("Next Page", key="next_button"):
                            st.session_state.current_page += 1
                            st.rerun() # Rerun to update results

                # Calculate start and end index for current page
                start_idx = (st.session_state.current_page - 1) * results_per_page
                end_idx = start_idx + results_per_page

                displayed_results = results[start_idx:end_idx]

                for i, result in enumerate(displayed_results):
                    st.markdown(f"---", unsafe_allow_html=True)
                    st.markdown(f"**Title**: {result['title']}")
                    st.markdown(f"**Path**: `{result['path']}`")
                    st.markdown(f"**Content**: {result['content']}")
                    
                    st.markdown("---") # Separator for highlights
                    st.markdown("**Highlights**:")
                    formatter = highlight.HtmlFormatter(tagname="em", classname="highlight")
                    highlighted_content = result.highlights("content", formatter=formatter)
                    st.markdown(f"<div>{highlighted_content}</div>", unsafe_allow_html=True)
                    st.markdown("---") # Separator after highlights

                # Add some custom CSS for highlights (optional)
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