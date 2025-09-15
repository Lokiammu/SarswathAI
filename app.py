import streamlit as st
import os
import atexit

# Import modules
from database import MongoDB
from auth import show_login_page, show_signup_page, check_session, logout_user
from rag import EnhancedRAG
from notebooks import show_notebooks_page, show_notebook_detail_page, show_document_view_page
from settings import show_settings_page
from chat import show_chat_page
from utils import init_session_state, cleanup_temp_files, set_page_style

def main():
    """Main application entry point."""
    # Configure page
    st.set_page_config(
        page_title="GPU-Accelerated RAG System",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Apply custom styling
    set_page_style()
    
    # Initialize session state
    init_session_state()
    
    # Initialize MongoDB connection
    if not st.session_state.mongo_db:
        # Set MongoDB connection string from environment variable or default
        connection_string = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
        st.session_state.mongo_db = MongoDB(connection_string)
    
    # Check for existing user session
    logged_in = check_session(st.session_state.mongo_db)
    
    # Show authentication page if not logged in
    if not logged_in and st.session_state.user is None:
        # Display app title for non-logged in users
        st.title("🚀 Advanced RAG System with Multiple Modes")
        
        if st.session_state.auth_page == "login":
            show_login_page(st.session_state.mongo_db)
        else:
            show_signup_page(st.session_state.mongo_db)
        return  # Exit early to show only the auth page
    
    # User is logged in, show navigation sidebar
    with st.sidebar:
        st.title("WELCOME ")
        st.markdown(f"Welcome, **{st.session_state.user['name']}**!")
        
        # Navigation options
        st.header("📌 Navigation")
        nav_options = {
            "chat": "💬 Chat",
            "notebooks": "📚 Notebooks",
            "settings": "⚙️ Settings"
        }
        
        selected_nav = st.radio(
            "Go to",
            options=list(nav_options.keys()),
            format_func=lambda x: nav_options[x],
            key="nav_selection",
            index=list(nav_options.keys()).index(st.session_state.page) if st.session_state.page in nav_options else 0
        )
        
        # Update the page if navigation changed
        if selected_nav != st.session_state.page and st.session_state.page in nav_options:
            st.session_state.page = selected_nav
            st.rerun()
        
        # Blockchain Configuration
        st.header("🔗 Blockchain")
        
        # Check if blockchain config exists in session state
        if "blockchain_enabled" not in st.session_state:
            st.session_state.blockchain_enabled = False
        if "blockchain_url" not in st.session_state:
            st.session_state.blockchain_url = "http://localhost:7545"
        if "blockchain_contract" not in st.session_state:
            st.session_state.blockchain_contract = ""
        if "blockchain_private_key" not in st.session_state:
            st.session_state.blockchain_private_key = ""
        if "blockchain_chain_id" not in st.session_state:
            st.session_state.blockchain_chain_id = 1337
            
        # Blockchain toggle
        st.session_state.blockchain_enabled = st.toggle(
            "Enable Blockchain Verification", 
            value=st.session_state.blockchain_enabled,
            key="sidebar_blockchain_toggle"
        )
        
        # Blockchain configuration
        if st.session_state.blockchain_enabled:
            with st.expander("Blockchain Configuration", expanded=False):
                st.session_state.blockchain_url = st.text_input(
                    "Blockchain URL", 
                    value=st.session_state.blockchain_url,
                    key="sidebar_blockchain_url"
                )
                
                st.session_state.blockchain_contract = st.text_input(
                    "Contract Address",
                    value=st.session_state.blockchain_contract,
                    key="sidebar_contract_address"
                )
                
                st.session_state.blockchain_private_key = st.text_input(
                    "Private Key (without 0x prefix)",
                    value=st.session_state.blockchain_private_key,
                    type="password",
                    key="sidebar_private_key"
                )
                
                # Add Chain ID field
                st.session_state.blockchain_chain_id = st.number_input(
                    "Chain ID",
                    value=st.session_state.blockchain_chain_id,
                    step=1,
                    min_value=1,
                    help="Network chain ID (e.g., 1 for Ethereum Mainnet, 1337 for local networks)",
                    key="sidebar_chain_id"
                )
                
                # Display blockchain status
                if (st.session_state.blockchain_contract and 
                    st.session_state.blockchain_private_key):
                    st.success("✅ Blockchain configuration ready")
                else:
                    st.warning("⚠️ Contract address and private key required")
                
                st.warning("⚠️ Never share your private key. For production, use secure key management.")
        
        # Add logout button
        st.button("Logout", on_click=logout_user, args=(st.session_state.mongo_db,), key="logout_button")
    
    # Display different pages based on selection
    if st.session_state.page == "notebooks":
        show_notebooks_page(st.session_state.mongo_db, st.session_state.user['user_id'])
    elif st.session_state.page == "notebook_detail":
        show_notebook_detail_page(
            st.session_state.mongo_db, 
            st.session_state.user['user_id'],
            EnhancedRAG
        )
    elif st.session_state.page == "document_view":
        show_document_view_page(st.session_state.mongo_db, st.session_state.user['user_id'])
    elif st.session_state.page == "settings":
        show_settings_page(st.session_state.mongo_db, st.session_state.user['user_id'])
    else:  # Default to chat page
        show_chat_page(
            st.session_state.mongo_db, 
            st.session_state.user['user_id'],
            EnhancedRAG
        )

if __name__ == "__main__":
    # Register cleanup function
    atexit.register(cleanup_temp_files)
    
    # Start the app
    main()