import os
import streamlit as st
import tempfile
import re

def init_session_state():
    """Initialize Streamlit session state variables."""
    # Core state variables
    if "rag" not in st.session_state:
        st.session_state.rag = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "temp_dir" not in st.session_state:
        st.session_state.temp_dir = None
    if "mongo_db" not in st.session_state:
        st.session_state.mongo_db = None
    if "user" not in st.session_state:
        st.session_state.user = None
    if "auth_page" not in st.session_state:
        st.session_state.auth_page = "login"  # Default to login page
        
    # Navigation state variables
    if "page" not in st.session_state:
        st.session_state.page = "chat"  # Options: chat, notebooks, notebook_detail, document_view, settings
    if "current_notebook" not in st.session_state:
        st.session_state.current_notebook = None
    if "viewing_document" not in st.session_state:
        st.session_state.viewing_document = None
        
    # RAG system preferences
    if "llm_model" not in st.session_state:
        st.session_state.llm_model = "llama3.2:latest"
    if "embedding_model" not in st.session_state:
        st.session_state.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    if "chunk_size" not in st.session_state:
        st.session_state.chunk_size = 1000
    if "chunk_overlap" not in st.session_state:
        st.session_state.chunk_overlap = 200
    if "use_gpu" not in st.session_state:
        st.session_state.use_gpu = True

def remove_directory_recursively(directory_path):
    """Recursively remove a directory and all its contents using os module."""
    if not os.path.exists(directory_path):
        return
        
    # First, delete all files in the directory
    for root, dirs, files in os.walk(directory_path, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error removing file {file_path}: {e}")
                
        # Then delete the directories
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                os.rmdir(dir_path)
            except Exception as e:
                print(f"Error removing directory {dir_path}: {e}")
    
    # Finally, remove the top directory
    try:
        os.rmdir(directory_path)
    except Exception as e:
        print(f"Error removing top directory {directory_path}: {e}")

def cleanup_temp_files():
    """Clean up temporary files when application exits."""
    if st.session_state.get('temp_dir') and os.path.exists(st.session_state.temp_dir):
        try:
            remove_directory_recursively(st.session_state.temp_dir)
            print(f"Cleaned up temporary directory: {st.session_state.temp_dir}")
        except Exception as e:
            print(f"Error cleaning up temporary directory: {e}")

def check_password_strength(password):
    """Check password strength and return feedback."""
    # Initialize score
    score = 0
    feedback = ""
    
    # Length check
    if len(password) < 8:
        feedback = "Password is too short. Use at least 8 characters."
        return "weak", feedback
    elif len(password) >= 12:
        score += 2
    elif len(password) >= 8:
        score += 1
    
    # Check for mixed case
    if re.search(r'[A-Z]', password) and re.search(r'[a-z]', password):
        score += 1
    else:
        feedback += "Add both uppercase and lowercase letters. "
    
    # Check for digits
    if re.search(r'\d', password):
        score += 1
    else:
        feedback += "Add numbers. "
    
    # Check for special characters
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    else:
        feedback += "Add special characters. "
    
    # Determine strength based on score
    if score >= 4:
        return "strong", "Strong password"
    elif score >= 2:
        return "medium", "Medium strength. " + feedback
    else:
        return "weak", "Weak password. " + feedback

def format_file_size(size_bytes):
    """Format file size from bytes to appropriate unit."""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def create_temp_directory():
    """Create a temporary directory and store its path in session state."""
    temp_dir = tempfile.mkdtemp()
    st.session_state.temp_dir = temp_dir
    return temp_dir

def get_file_icon(file_type):
    """Get an appropriate icon for a file type."""
    file_icons = {
        "pdf": "📕",
        "docx": "📘",
        "doc": "📘",
        "txt": "📄",
        "unknown": "📁"
    }
    return file_icons.get(file_type.lower(), "📁")

def display_error_message(error, suggestion=None):
    """Display a styled error message with optional suggestion."""
    st.error(f"**Error:** {error}")
    if suggestion:
        st.info(f"**Suggestion:** {suggestion}")

def set_page_style():
    """Set global page styling."""
    st.markdown("""
    <style>
        /* Improved card styling */
        [data-testid="stExpander"] {
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        /* Custom styling for metrics */
        [data-testid="stMetric"] {
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        
        /* Notebook card styling */
        .notebook-card {
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            padding: 16px;
            margin-bottom: 16px;
            transition: all 0.3s ease;
        }
        
        .notebook-card:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }
        
        /* Button styling */
        .stButton button {
            border-radius: 4px;
            font-weight: 500;
        }
    </style>
    """, unsafe_allow_html=True)