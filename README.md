# Simple Whoosh Search Engine with Streamlit

This project is a simple document search engine built with [Whoosh](https://whoosh.readthedocs.io/en/latest/) for full-text search and [Streamlit](https://streamlit.io/) for a modern web UI. It supports CRUD-like operations: search, add, delete, and view all documents.

## Features
- Full-text search with Whoosh
- Add, delete, and view documents
- Highlighted search results
- Pagination and sorting
- Streamlit-based interactive UI

## Requirements
- Python 3.7+
- See `requirements.txt` for dependencies:
  - streamlit
  - whoosh

## Installation
1. **Clone the repository**
   ```sh
   git clone <repo-url>
   cd chatbot_with_RAG
   ```
2. **Create and activate a virtual environment**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```

## Usage
1. **Run the Streamlit app**
   ```sh
   streamlit run src/main.py
   ```
2. **Open the provided local URL in your browser**

## Project Structure
```
chatbot_with_RAG/
├── src/
│   └── main.py
├── requirements.txt
├── README.md
└── venv/ (created after setup)
```

## Notes
- The index is stored in the `indexdir` directory (created automatically).
- You can add, delete, and view documents using the web UI.
- For advanced Whoosh query syntax, see the [Whoosh documentation](https://whoosh.readthedocs.io/en/latest/querylang.html).

## License
MIT
