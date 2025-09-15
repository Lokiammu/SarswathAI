import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import time

def show_settings_page(mongo_db, user_id):
    """Display the settings page with about, analytics, and user preferences."""
    st.title("⚙️ Settings & Analytics")
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Analytics", "🔧 Preferences", "🔗 Blockchain", "ℹ️ About"])
    
    # Analytics Tab
    with tab1:
        show_analytics(mongo_db, user_id)
    
    # Preferences Tab
    with tab2:
        show_preferences(mongo_db, user_id)
    
    # Blockchain Tab
    with tab3:
        show_blockchain_settings(mongo_db, user_id)
    
    # About Tab
    with tab4:
        show_about()

def show_analytics(mongo_db, user_id):
    """Display analytics information."""
    st.header("Usage Analytics")
    
    # Get user analytics
    success, analytics = mongo_db.get_user_analytics(user_id)
    
    if not success:
        st.error(f"Error fetching analytics: {analytics}")
        return
        
    # Overview section
    st.subheader("Overview")
    
    st.markdown("""
        <style>
            div[data-testid="stMetric"] {
            background-color: black;
            color: white;
            padding: 10px;
            border-radius: 5px;
            }
            div[data-testid="stMetric"] > div {
            color: white !important;
            }
            div[data-testid="stMetric"] > div:first-child {
            color: white !important;
            }
            div[data-testid="stMetric"] label {
            color: white !important;
            }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Documents", analytics.get("total_documents", 0))
    with col2:
        st.metric("PDFs", analytics.get("total_pdfs", 0))
    with col3:
        st.metric("RAG Documents", analytics.get("total_rag_documents", 0))
    with col4:
        st.metric("Total Queries", analytics.get("total_queries", 0))
    
    # Add blockchain metrics
    if st.session_state.get('blockchain_enabled', False):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Verified Documents", analytics.get("blockchain_verified_docs", 0))
        with col2:
            st.metric("Verified Queries", analytics.get("blockchain_queries", 0))
    
    # Response time metric
    st.subheader("Performance")
    col1, col2 = st.columns(2)
    with col1:
        avg_time = round(analytics.get("avg_response_time", 0), 2)
        st.metric("Average Response Time", f"{avg_time}s")
    
    # Create timestamp data for time series chart
    if analytics.get("recent_queries"):
        # Extract query times and timestamps
        query_data = []
        for query in analytics["recent_queries"]:
            query_data.append({
                "timestamp": query["timestamp"],
                "response_time": query["response_time"]
            })
        
        # Create a DataFrame
        if query_data:
            df = pd.DataFrame(query_data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")
            
            # Plot response time trend
            with col2:
                fig = px.line(df, x="timestamp", y="response_time", 
                             title="Recent Query Response Times",
                             labels={"response_time": "Response Time (s)", "timestamp": "Time"})
                st.plotly_chart(fig, use_container_width=True)
    
    # Notebooks section
    st.subheader("Notebooks")
    
    if analytics.get("notebook_stats"):
        notebook_data = analytics["notebook_stats"]
        
        # Create a DataFrame
        notebook_df = pd.DataFrame(notebook_data)
        
        # Bar chart for document counts by notebook
        fig = px.bar(
            notebook_df, 
            y="name", 
            x=["document_count", "rag_document_count"],
            title="Documents by Notebook",
            labels={"name": "Notebook", "value": "Count", "variable": "Type"},
            barmode="group",
            color_discrete_map={"document_count": "#1E87E5", "rag_document_count": "#4CDF50"},
            orientation='h'  # Horizontal bars
        )
        fig.update_layout(legend_title_text="Document Type")
        st.plotly_chart(fig, use_container_width=True)
        
        # Show which notebooks have blockchain enabled
        blockchain_notebooks = [nb for nb in notebook_data if nb.get("blockchain_enabled", False)]
        if blockchain_notebooks:
            st.subheader("Blockchain-Enabled Notebooks")
            for nb in blockchain_notebooks:
                with st.container(border=True):
                    st.markdown(f"### {nb['name']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption(f"Documents: {nb['document_count']}")
                        st.caption(f"Created: {nb['created_at'].strftime('%Y-%m-%d')}")
                    with col2:
                        st.caption(f"Last accessed: {nb['last_accessed'].strftime('%Y-%m-%d')}")
    
    # Recent activity
    st.subheader("Recent Activity")
    
    if analytics.get("recent_queries"):
        with st.expander("Recent Queries", expanded=True):
            for idx, query in enumerate(analytics["recent_queries"]):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{idx+1}. {query['query']}**")
                with col2:
                    st.caption(f"{query['timestamp'].strftime('%Y-%m-%d %H:%M')}")
                st.caption(f"Response Time: {query['response_time']:.2f}s")
                
                # Display notebook name if available
                if query.get("notebook_id"):
                    for nb in analytics.get("notebook_stats", []):
                        if nb.get("id") == query.get("notebook_id"):
                            st.caption(f"Notebook: {nb.get('name', 'Unknown')}")
                            break
                
                st.divider()
    else:
        st.info("No queries have been made yet.")

def show_preferences(mongo_db, user_id):
    """Display user preferences settings."""
    st.header("User Preferences")
    
    # RAG System Preferences
    st.subheader("RAG System Preferences")
    
    # Model preferences
    col1, col2 = st.columns(2)
    with col1:
        llm_model = st.selectbox(
            "Default LLM Model",
            options=["llama3.2:latest", "llama3:latest", "mistral:latest", "phi3.5:3.8b", "dolphin-phi:latest", "samantha-mistral:latest"],
            index=0,
            key="pref_llm_model"
        )
        st.session_state.llm_model = llm_model
    
    with col2:
        embedding_model = st.selectbox(
            "Default Embedding Model",
            options=[
                "sentence-transformers/all-mpnet-base-v2",
                "sentence-transformers/all-MiniLM-L6-v2",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            ],
            index=1,
            key="pref_embedding_model"
        )
        st.session_state.embedding_model = embedding_model
    
    # GPU usage
    use_gpu = st.checkbox("Use GPU Acceleration (if available)", value=True, key="pref_use_gpu")
    st.session_state.use_gpu = use_gpu
    
    # Advanced RAG settings
    with st.expander("Advanced RAG Settings"):
        col1, col2 = st.columns(2)
        with col1:
            chunk_size = st.slider("Chunk Size", 100, 2000, 1000, key="pref_chunk_size")
            st.session_state.chunk_size = chunk_size
        with col2:
            chunk_overlap = st.slider("Chunk Overlap", 0, 500, 200, key="pref_chunk_overlap")
            st.session_state.chunk_overlap = chunk_overlap
    
    # UI Preferences
    st.subheader("UI Preferences")
    
    # Theme preferences
    theme = st.selectbox(
        "Theme",
        options=["Light", "Dark", "System default"],
        index=2,
        key="pref_theme"
    )
    
    # Default page
    default_page = st.selectbox(
        "Default Page",
        options=["Chat", "Notebooks", "Settings"],
        index=0,
        key="pref_default_page"
    )
    
    # Add a diagnostic section for vector storage
    st.subheader("Vector Storage Diagnostics")
    
    if st.button("Check Vector Storage", key="pref_check_vectors"):
        with st.spinner("Checking vector storage..."):
            # Get all notebooks
            success, notebooks = mongo_db.get_notebooks(user_id)
            
            if success and notebooks:
                # Create a table to display vector storage status
                data = []
                for notebook in notebooks:
                    # Check if vectors exist for this notebook
                    vector_success, vector_result = mongo_db.get_faiss_index(notebook['_id'])
                    if vector_success:
                        status = "✅ Vectors stored"
                        metadata = vector_result.get("metadata", {})
                        doc_count = metadata.get("document_count", "Unknown")
                        size = metadata.get("index_size_bytes", 0)
                        size_formatted = f"{size/1024/1024:.2f} MB" if size else "Unknown"
                        last_updated = vector_result.get("updated_at", "Unknown")
                    else:
                        status = "❌ No vectors"
                        doc_count = "-"
                        size_formatted = "-"
                        last_updated = "-"
                        
                    data.append({
                        "Notebook": notebook['name'],
                        "Status": status,
                        "Documents": doc_count,
                        "Size": size_formatted,
                        "Last Updated": last_updated
                    })
                
                # Display as DataFrame
                df = pd.DataFrame(data)
                st.table(df)
            else:
                st.error("Could not fetch notebooks")
    
    # Save preferences button
    if st.button("Save Preferences", use_container_width=True, key="pref_save_btn"):
        st.success("Preferences saved successfully!")
        time.sleep(1)  # Brief pause for success message to show
        st.rerun()

def show_blockchain_settings(mongo_db, user_id):
    """Display blockchain settings and configuration."""
    st.header("Blockchain Configuration")
    
    # Blockchain explanation
    st.markdown("""
    ### What is Blockchain Verification?
    
    Blockchain verification provides tamper-proof record-keeping for your documents and queries:
    
    - **Document Integrity**: Each document is cryptographically hashed and recorded on the blockchain
    - **Query Auditing**: All queries and answers are immutably logged
    - **Transparency**: Create verifiable audit trails of all interactions
    - **Trust**: Ensure the integrity of your data and queries
    """)
    
    # Blockchain status
    is_enabled = st.session_state.get('blockchain_enabled', False)
    if is_enabled:
        st.success("✅ Blockchain verification is enabled")
    else:
        st.warning("⚠️ Blockchain verification is disabled")
    
    # Toggle blockchain
    new_status = st.toggle("Enable Blockchain Verification", value=is_enabled, key="bc_toggle_enable")
    if new_status != is_enabled:
        st.session_state.blockchain_enabled = new_status
        if new_status:
            st.success("Blockchain verification enabled!")
        else:
            st.info("Blockchain verification disabled.")
        time.sleep(1)  # Brief pause
        st.rerun()
    
    # Connection settings
    st.subheader("Connection Settings")
    
    blockchain_url = st.text_input(
        "Blockchain URL", 
        value=st.session_state.get('blockchain_url', 'http://localhost:7545'),
        key="bc_url_input"
    )
    
    contract_address = st.text_input(
        "Contract Address",
        value=st.session_state.get('blockchain_contract', ''),
        key="bc_contract_input"
    )
    
    private_key = st.text_input(
        "Private Key (without 0x prefix)",
        value=st.session_state.get('blockchain_private_key', ''),
        type="password",
        key="bc_privkey_input"
    )
    
    if st.button("Save Blockchain Configuration", use_container_width=True, key="bc_save_config"):
        st.session_state.blockchain_url = blockchain_url
        st.session_state.blockchain_contract = contract_address
        st.session_state.blockchain_private_key = private_key
        
        if contract_address and private_key:
            st.success("Blockchain configuration saved successfully!")
        else:
            st.warning("Contract address and private key are required for full functionality.")
            
        time.sleep(1)  # Brief pause
        st.rerun()
    
    # Blockchain verification statistics
    st.subheader("Blockchain Verification Statistics")
    
    # Try to get blockchain query count
    try:
        success, blockchain_queries = mongo_db.get_blockchain_queries(user_id)
        if success:
            blockchain_query_count = len(blockchain_queries)
        else:
            blockchain_query_count = 0
            
        # Get verified document count
        verified_count = 0
        success, notebooks = mongo_db.get_notebooks(user_id)
        if success:
            for notebook in notebooks:
                success, docs = mongo_db.list_user_documents(user_id, notebook["_id"])
                if success:
                    verified_count += len([doc for doc in docs if doc.get('blockchain_verification')])
        
        # Display metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Verified Documents", verified_count)
        with col2:
            st.metric("Verified Queries", blockchain_query_count)
            
        # Show recent blockchain transactions if any
        if success and blockchain_queries:
            st.subheader("Recent Blockchain Transactions")
            with st.expander("View Transaction History", expanded=True):
                for query in blockchain_queries[:5]:  # Show last 5
                    with st.container(border=True):
                        st.markdown(f"**Query:** {query['query']}")
                        st.caption(f"Time: {query['timestamp'].strftime('%Y-%m-%d %H:%M')}")
                        st.caption(f"Transaction Hash: {query['tx_hash']}")
        
    except Exception as e:
        st.error(f"Error fetching blockchain statistics: {str(e)}")
    
    # Warning about storing private keys
    st.warning("""
    ⚠️ **Security Warning**: Private keys should be properly secured in a production environment.
    
    - Never share your private key
    - Consider using environment variables or a key management service
    - Ensure your blockchain node is properly secured
    """)

def show_about():
    """Display information about the application."""
    st.header("About GPU-Accelerated RAG System")
    
    # App description
    st.markdown("""
    This advanced document management and question answering system uses 
    state-of-the-art Retrieval Augmented Generation (RAG) technology to help you organize,
    search, and extract insights from your documents.
    
    Built with GPU acceleration for faster processing and response times.
    """)
    
    # Version information
    st.subheader("Version Information")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Application Version:** 1.1.0")
        st.write("**RAG Engine:** LangChain + FAISS")
        st.write("**UI Framework:** Streamlit")
    with col2:
        st.write("**Database:** MongoDB")
        st.write("**LLM Backend:** Ollama")
        st.write("**Blockchain:** Web3 + Ethereum")
    
    # Features
    st.subheader("Key Features")
    st.markdown("""
    - **Notebook Organization**: Create and manage document collections
    - **GPU Acceleration**: Faster processing and response times
    - **Document Management**: Upload and organize PDFs, Word documents, and text files
    - **Intelligent Search**: Ask questions in natural language about your documents
    - **Blockchain Verification**: Tamper-proof document and query verification
    - **Detailed Analytics**: Track usage and performance metrics
    - **Custom Document Naming**: Organize documents with your preferred names
    - **Document Viewer**: Read your documents without leaving the application
    """)
    
    # Credits
    st.subheader("Credits")
    st.markdown("""
    Created with ❤️ using:
    - Streamlit
    - LangChain
    - FAISS
    - Ollama
    - HuggingFace Transformers
    - MongoDB
    - Web3.py
    - PyPDF2
    - python-docx
    """)
    
    # Contact
    st.subheader("Need Help?")
    st.markdown("""
    For support or feature requests, please reach out to the development team.
    """)