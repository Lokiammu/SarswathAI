import streamlit as st
import time
from datetime import datetime
import document_viewer
from utils import get_file_icon

def show_notebooks_page(mongo_db, user_id):
    """Show the notebooks management page with enhanced UI."""
    st.title("📚 My Notebooks")
    
    # Create new notebook section
    with st.expander("➕ Create New Notebook", expanded=False):
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            notebook_name = st.text_input("Notebook Name", placeholder="E.g., Research Papers, Project Notes...")
        with col2:
            # Generate a random color if not set
            if "notebook_color" not in st.session_state:
                st.session_state.notebook_color = "#1E88E5"  # Default blue
                
            # Color options
            colors = {
                "Blue": "#1E88E5",
                "Green": "#4CAF50",
                "Purple": "#9C27B0",
                "Orange": "#FF9800",
                "Red": "#F44336",
                "Teal": "#009688",
                "Pink": "#E91E63",
                "Brown": "#795548"
            }
            
            selected_color = st.selectbox(
                "Color",
                options=list(colors.keys()),
                format_func=lambda x: x,
                index=0
            )
            st.session_state.notebook_color = colors[selected_color]
            
        with col3:
            st.write("##")  # Spacing
            st.color_picker("Custom Color", st.session_state.notebook_color, key="notebook_color_picker")
            
        # Add domain tagging
        domain_options = ["Machine Learning", "Data Science", "Programming", 
                         "Finance", "Healthcare", "General"]
        selected_domains = st.multiselect(
            "Domains/Topics",
            options=domain_options,
            default=["General"],
            help="Select relevant domains for this notebook"
        )
        
        notebook_desc = st.text_area("Description (optional)", placeholder="Add details about this notebook...")
        
        # Add blockchain support option
        blockchain_enabled = st.checkbox(
            "Enable Blockchain Verification", 
            value=st.session_state.get("blockchain_enabled", False),
            help="Verify documents and queries using blockchain for immutable record-keeping"
        )
        
        if blockchain_enabled:
            # Check if blockchain configuration is available
            has_config = (
                "blockchain_url" in st.session_state and
                "blockchain_contract" in st.session_state and
                "blockchain_private_key" in st.session_state and
                st.session_state.blockchain_contract and
                st.session_state.blockchain_private_key
            )
            
            if not has_config:
                st.warning("⚠️ Blockchain configuration not set. Please configure it in Settings.")
        
        if st.button("Create Notebook", use_container_width=True):
            if not notebook_name:
                st.error("Please enter a notebook name")
            else:
                with st.spinner("Creating notebook..."):
                    # Add blockchain enabled flag to metadata
                    metadata = {
                        "domains": selected_domains,
                        "blockchain_enabled": blockchain_enabled
                    }
                    
                    success, result = mongo_db.create_notebook(
                        user_id,
                        notebook_name,
                        notebook_desc,
                        st.session_state.notebook_color_picker,
                        metadata
                    )
                    if success:
                        st.success(f"Notebook '{notebook_name}' created!")
                        time.sleep(1)  # Brief pause for the success message to be seen
                        st.rerun()
                    else:
                        st.error(f"Error creating notebook: {result}")
    
    # Get all notebooks for the user
    success, notebooks = mongo_db.get_notebooks(user_id)
    
    if not success:
        st.error(f"Error fetching notebooks: {notebooks}")
        return
    
    # Display notebooks
    if not notebooks:
        st.info("You don't have any notebooks yet. Create one to get started!")
        st.image("https://img.freepik.com/free-vector/empty-concept-illustration_114360-1188.jpg", width=300)
    else:
        # Add filtering/sorting options
        col1, col2 = st.columns(2)
        with col1:
            sort_by = st.selectbox(
                "Sort by",
                options=["Last accessed", "Name", "Created date", "Document count"],
                index=0
            )
        with col2:
            filter_option = st.selectbox(
                "View",
                options=["All notebooks", "Favorites only", "Recently used", "Blockchain enabled"],
                index=0
            )
        
        # Apply sorting
        if sort_by == "Name":
            notebooks.sort(key=lambda x: x["name"])
        elif sort_by == "Created date":
            notebooks.sort(key=lambda x: x["created_at"], reverse=True)
        elif sort_by == "Document count":
            notebooks.sort(key=lambda x: x.get("document_count", 0), reverse=True)
        # Default is "Last accessed" which is already sorted from the database query
        
        # Apply filtering
        if filter_option == "Favorites only":
            notebooks = [nb for nb in notebooks if nb.get('is_favorite', False)]
        elif filter_option == "Recently used":
            # Get notebooks accessed in the last 7 days
            now = datetime.now()
            recent_notebooks = []
            for nb in notebooks:
                last_accessed = nb.get('last_accessed', nb['created_at'])
                days_diff = (now - last_accessed).days
                if days_diff <= 7:
                    recent_notebooks.append(nb)
            notebooks = recent_notebooks
        elif filter_option == "Blockchain enabled":
            notebooks = [nb for nb in notebooks if nb.get('blockchain_enabled', False)]
            
        if not notebooks and filter_option != "All notebooks":
            st.info(f"No notebooks match your '{filter_option}' filter.")
        
        # Display favorite notebooks first if showing all
        if filter_option == "All notebooks":
            favorites = [nb for nb in notebooks if nb.get('is_favorite', False)]
            if favorites:
                st.subheader("⭐ Favorite Notebooks")
                display_notebook_grid(favorites, mongo_db, user_id)
            
            # Display all other notebooks
            regular_notebooks = [nb for nb in notebooks if not nb.get('is_favorite', False)]
            if regular_notebooks:
                st.subheader("All Notebooks")
                display_notebook_grid(regular_notebooks, mongo_db, user_id)
        else:
            # Just display all notebooks that match the filter
            display_notebook_grid(notebooks, mongo_db, user_id)
            
def display_notebook_grid(notebooks, mongo_db, user_id):
    """Display notebooks in a grid layout with enhanced UI."""
    # Show notebooks in rows of 3
    cols_per_row = 3
    for i in range(0, len(notebooks), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(notebooks):
                notebook = notebooks[i + j]
                with cols[j]:
                    # Get notebook color or use default
                    color = notebook.get('color', "#1E88E5")
                    
                    # Create stylish notebook card
                    with st.container(border=True):
                        # Colored header bar
                        header_content = f"""
                        <div style="background-color: {color}; padding: 10px; border-radius: 5px 5px 0 0; margin-bottom: 10px;">
                            <h3 style="color: white; margin: 0;">{notebook['name']}</h3>
                        </div>
                        """
                        
                        # Add blockchain badge if enabled
                        if notebook.get('blockchain_enabled', False):
                            header_content = header_content.replace('</div>', f'<span style="background-color: #4CAF50; color: white; padding: 2px 5px; border-radius: 3px; font-size: 0.7em; float: right;">🔗 BLOCKCHAIN</span></div>')
                            
                        st.markdown(header_content, unsafe_allow_html=True)
                        
                        # Notebook metadata
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            if notebook.get('description'):
                                desc = notebook['description']
                                if len(desc) > 100:
                                    desc = desc[:97] + "..."
                                st.markdown(f"*{desc}*")
                            
                            st.caption(f"Created: {notebook['created_at'].strftime('%Y-%m-%d')}")
                            st.caption(f"Documents: {notebook.get('document_count', 0)}")
                            
                        with col2:
                            # Favorite toggle
                            if notebook.get('is_favorite', False):
                                if st.button("⭐", key=f"unfav_{notebook['_id']}"):
                                    mongo_db.toggle_favorite_notebook(notebook['_id'])
                                    st.rerun()
                            else:
                                if st.button("☆", key=f"fav_{notebook['_id']}"):
                                    mongo_db.toggle_favorite_notebook(notebook['_id'])
                                    st.rerun()
                        
                        # Action buttons - now adding Chat button
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("Open", key=f"open_{notebook['_id']}", use_container_width=True):
                                st.session_state.current_notebook = notebook['_id']
                                st.session_state.page = "notebook_detail"
                                st.rerun()
                        with col2:
                            # Add new Chat button for direct chatting
                            if st.button("💬 Chat", key=f"chat_{notebook['_id']}", use_container_width=True):
                                st.session_state.current_notebook = notebook['_id']
                                st.session_state.page = "notebook_detail"
                                st.session_state.active_tab = "chat"  # Set active tab to chat
                                st.rerun()
                        with col3:
                            if st.button("Delete", key=f"del_{notebook['_id']}", use_container_width=True):
                                # Add confirmation dialog
                                if 'delete_confirm' not in st.session_state:
                                    st.session_state.delete_confirm = {}
                                
                                if notebook['_id'] not in st.session_state.delete_confirm:
                                    st.session_state.delete_confirm[notebook['_id']] = True
                                    st.warning(f"Are you sure you want to delete '{notebook['name']}'? This cannot be undone.")
                                    col3, col4 = st.columns(2)
                                    with col3:
                                        if st.button("Yes, Delete", key=f"confirm_del_{notebook['_id']}", use_container_width=True):
                                            mongo_db.delete_notebook(notebook['_id'], user_id)
                                            del st.session_state.delete_confirm[notebook['_id']]
                                            st.success("Notebook deleted successfully!")
                                            time.sleep(1)  # Brief pause
                                            st.rerun()
                                    with col4:
                                        if st.button("Cancel", key=f"cancel_del_{notebook['_id']}", use_container_width=True):
                                            del st.session_state.delete_confirm[notebook['_id']]
                                            st.rerun()

def show_notebook_detail_page(mongo_db, user_id, rag_system=None):
    """Show the detail page for a specific notebook with enhanced UI."""
    if not st.session_state.current_notebook:
        st.error("No notebook selected")
        st.session_state.page = "notebooks"
        st.rerun()
        return
    
    # Get notebook details
    success, notebook = mongo_db.get_notebook(st.session_state.current_notebook)
    
    if not success:
        st.error(f"Error fetching notebook: {notebook}")
        st.session_state.page = "notebooks"
        st.rerun()
        return
    
    # Notebook color
    color = notebook.get('color', "#1E88E5")
    
    # Header with back button and styled title
    col1, col2, col3 = st.columns([1, 10, 1])
    with col1:
        if st.button("←"):
            st.session_state.page = "notebooks"
            st.rerun()
    with col2:
        header_html = f"""
        <div style="background-color: {color}; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
            <h1 style="color: white; margin: 0; text-align: center;">📓 {notebook['name']}</h1>
        """
        
        # Add blockchain badge if enabled
        if notebook.get('blockchain_enabled', False):
            header_html += f"""
            <div style="text-align: center; margin-top: 5px;">
                <span style="background-color: #4CAF50; color: white; padding: 3px 8px; border-radius: 3px; font-size: 0.8em;">
                    🔗 BLOCKCHAIN VERIFIED
                </span>
            </div>
            """
            
        header_html += "</div>"
        st.markdown(header_html, unsafe_allow_html=True)
    with col3:
        if notebook.get('is_favorite', False):
            if st.button("⭐"):
                mongo_db.toggle_favorite_notebook(notebook['_id'])
                st.rerun()
        else:
            if st.button("☆"):
                mongo_db.toggle_favorite_notebook(notebook['_id'])
                st.rerun()
    
    # Display notebook description
    if notebook.get('description'):
        st.markdown(f"*{notebook['description']}*")
    
    # Check blockchain status and show info if enabled
    is_blockchain_enabled = notebook.get('blockchain_enabled', False)
    if is_blockchain_enabled:
        # Check if blockchain config is available
        has_config = (
            "blockchain_url" in st.session_state and
            "blockchain_contract" in st.session_state and
            "blockchain_private_key" in st.session_state and
            st.session_state.blockchain_contract and
            st.session_state.blockchain_private_key
        )
        
        if has_config:
            st.info("🔗 This notebook uses blockchain verification for document integrity and query auditing.")
        else:
            st.warning("⚠️ Blockchain verification is enabled but not configured. Please set configuration in Settings.")
    
    # Tabs for different sections - check for active_tab in session state
    active_tab_index = 0
    if st.session_state.get('active_tab') == 'chat':
        active_tab_index = 1
        # Clear the active tab so it's not sticky
        st.session_state.active_tab = None
    
    tab1, tab2, tab3, tab4 = st.tabs(["📚 Documents", "💬 Chat", "📊 Analytics", "🔗 Blockchain"])
    
    # Set the active tab
    if active_tab_index == 1:
        tab2.active = True
    
    # Documents Tab
    with tab1:
        # Get documents in this notebook
        success, documents = mongo_db.list_user_documents(user_id, notebook['_id'])
        
        # Upload button that shows/hides the upload form
        if "show_upload_form" not in st.session_state:
            st.session_state.show_upload_form = False
        
        col1, col2 = st.columns([1, 20])
        with col1:
            if st.button("➕", help="Upload new documents"):
                st.session_state.show_upload_form = not st.session_state.show_upload_form
        with col2:
            st.write("Add Documents" if st.session_state.show_upload_form else "")
        
        # Upload documents section (conditionally shown)
        if st.session_state.show_upload_form:
            with st.container(border=True):
                st.subheader("Upload Documents")
                col1, col2 = st.columns([3, 1])
                with col1:
                    custom_name = st.text_input("Custom Document Name (optional)", 
                                            placeholder="Leave blank to use original filename",
                                            key=f"custom_name_{notebook['_id']}")
                with col2:
                    st.write("##")  # Spacing
                    use_rag = st.checkbox("Process with RAG", value=True, 
                                        help="Enable to process document for question answering")
                
                # Blockchain verification info
                if is_blockchain_enabled:
                    st.info("🔗 Documents will be verified on blockchain for tamper-proof integrity.")
                
                # Document upload interface
                uploaded_files = st.file_uploader(
                    "Select files to add to this notebook", 
                    type=["pdf", "docx", "doc", "txt"],
                    accept_multiple_files=True,
                    key=f"upload_{notebook['_id']}"
                )
                
                if uploaded_files:
                    if st.button("Upload Files", key=f"process_{notebook['_id']}", use_container_width=True):
                        with st.spinner("Uploading and processing files..."):
                            upload_success = False
                            saved_files = []  # Keep track of saved files for blockchain verification
                            
                            # Save files to MongoDB
                            for file in uploaded_files:
                                file_type = "unknown"
                                if file.name.lower().endswith('.pdf'):
                                    file_type = "pdf"
                                elif file.name.lower().endswith(('.docx', '.doc')):
                                    file_type = "docx"
                                elif file.name.lower().endswith('.txt'):
                                    file_type = "txt"
                                
                                # Save the file
                                file.seek(0)  # Reset file pointer
                                display_name = custom_name if custom_name else file.name
                                success, result = mongo_db.save_document_file(
                                    file.getbuffer(),
                                    file.name,
                                    file_type,
                                    user_id,
                                    notebook['_id'],
                                    display_name
                                )
                                
                                if success:
                                    upload_success = True
                                    st.sidebar.success(f"Uploaded: {display_name}")
                                    saved_files.append({
                                        'file_id': result,  # This is the file ID
                                        'name': file.name,
                                        'data': file.getbuffer()
                                    })
                                else:
                                    st.sidebar.error(f"Failed to upload {file.name}: {result}")
                            
                            # Verify files on blockchain if enabled
                            if is_blockchain_enabled and upload_success and 'blockchain_contract' in st.session_state and st.session_state.blockchain_contract:
                                # Initialize RAG system if needed
                                if 'rag' not in st.session_state or st.session_state.rag is None:
                                    with st.spinner("Initializing RAG system for blockchain verification..."):
                                        # Get configuration values from session state or use defaults
                                        llm_model = st.session_state.get('llm_model', "llama3.2:latest")
                                        embedding_model = st.session_state.get('embedding_model', "sentence-transformers/all-MiniLM-L6-v2")
                                        chunk_size = st.session_state.get('chunk_size', 1000)
                                        chunk_overlap = st.session_state.get('chunk_overlap', 200)
                                        use_gpu = st.session_state.get('use_gpu', True)
                                        
                                        st.session_state.rag = rag_system(
                                            llm_model_name=llm_model,
                                            embedding_model_name=embedding_model,
                                            chunk_size=chunk_size,
                                            chunk_overlap=chunk_overlap,
                                            use_gpu=use_gpu
                                        )
                                
                                # Initialize blockchain if not done already
                                if not hasattr(st.session_state.rag, 'use_blockchain') or not st.session_state.rag.use_blockchain:
                                    try:
                                        st.session_state.rag.initialize_blockchain(
                                            blockchain_url=st.session_state.blockchain_url,
                                            contract_address=st.session_state.blockchain_contract,
                                            private_key=st.session_state.blockchain_private_key
                                        )
                                    except Exception as e:
                                        st.error(f"Error initializing blockchain: {str(e)}")
                                
                                if hasattr(st.session_state.rag, 'use_blockchain') and st.session_state.rag.use_blockchain:
                                    for file_info in saved_files:
                                        try:
                                            with st.spinner(f"Verifying {file_info['name']} on blockchain..."):
                                                # Create a unique document ID
                                                document_id = f"{file_info['name']}_{notebook['_id']}_{user_id}"
                                                verification = st.session_state.rag.verify_document_blockchain(
                                                    file_info['data'], document_id
                                                )
                                                
                                                if verification:
                                                    # Update document with blockchain verification
                                                    mongo_db.update_document_blockchain_verification(
                                                        file_info['file_id'], verification
                                                    )
                                                    st.success(f"✅ {file_info['name']} verified on blockchain")
                                                else:
                                                    st.warning(f"⚠️ Failed to verify {file_info['name']} on blockchain")
                                        except Exception as e:
                                            st.error(f"Error verifying on blockchain: {str(e)}")
                            
                            # Process with RAG if selected
                            if use_rag and rag_system and upload_success:
                                try:
                                    # Initialize RAG system if needed
                                    if 'rag' not in st.session_state or st.session_state.rag is None:
                                        # Get configuration values from session state or use defaults
                                        llm_model = st.session_state.get('llm_model', "llama3.2:latest")
                                        embedding_model = st.session_state.get('embedding_model', "sentence-transformers/all-MiniLM-L6-v2")
                                        chunk_size = st.session_state.get('chunk_size', 1000)
                                        chunk_overlap = st.session_state.get('chunk_overlap', 200)
                                        use_gpu = st.session_state.get('use_gpu', True)
                                        
                                        st.session_state.rag = rag_system(
                                            llm_model_name=llm_model,
                                            embedding_model_name=embedding_model,
                                            chunk_size=chunk_size,
                                            chunk_overlap=chunk_overlap,
                                            use_gpu=use_gpu
                                        )
                                    
                                    # Reset file pointers
                                    for file in uploaded_files:
                                        file.seek(0)
                                    
                                    # Process with nested flag to avoid expander nesting issue
                                    st.session_state.rag.process_files(
                                        uploaded_files, 
                                        user_id=user_id,
                                        mongodb=mongo_db,
                                        notebook_id=notebook['_id'],
                                        is_nested=True
                                    )
                                    
                                except Exception as e:
                                    st.error(f"Error processing files with RAG: {str(e)}")
                                    st.info("Files were uploaded but could not be processed for question answering.")
                            
                            if upload_success:
                                st.success(f"{len(uploaded_files)} files uploaded successfully!")
                                st.session_state.show_upload_form = False  # Hide form after upload
                                time.sleep(1)  # Brief pause
                                st.rerun()
        
        # Display documents in this notebook
        if success and documents:
            st.subheader(f"Documents ({len(documents)})")
            
            # Group by file type
            file_types = {}
            for doc in documents:
                file_type = doc.get('file_type', 'unknown')
                if file_type not in file_types:
                    file_types[file_type] = []
                file_types[file_type].append(doc)
            
            # Display by file type
            for file_type, docs in file_types.items():
                type_icon = get_file_icon(file_type)
                with st.expander(f"{type_icon} {file_type.upper()} Files ({len(docs)})", expanded=True):
                    # Create a grid of document cards for better UI
                    docs_per_row = 2
                    for i in range(0, len(docs), docs_per_row):
                        cols = st.columns(docs_per_row)
                        
                        for j in range(docs_per_row):
                            if i + j < len(docs):
                                doc = docs[i + j]
                                with cols[j]:
                                    with st.container(border=True):
                                        # Document name and icon
                                        doc_title = f"### {type_icon} {doc.get('display_name', doc['filename'])}"
                                        
                                        # Add blockchain badge if verified
                                        if doc.get('blockchain_verification'):
                                            st.markdown(f"{doc_title} <span style='background-color: #4CAF50; color: white; padding: 2px 5px; border-radius: 3px; font-size: 0.7em;'>✅ VERIFIED</span>", unsafe_allow_html=True)
                                        else:
                                            st.markdown(doc_title)
                                        
                                        # Document metadata
                                        st.caption(f"Uploaded: {doc['upload_date'].strftime('%Y-%m-%d %H:%M')}")
                                        
                                        # Show blockchain details if available
                                        if doc.get('blockchain_verification'):
                                            verification = doc['blockchain_verification']
                                            st.caption(f"🔗 TX: {verification['tx_hash'][:10]}... | Block: {verification['block_number']}")
                                        
                                        # Action buttons
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            if st.button("📄 View", key=f"view_{doc['file_id']}", use_container_width=True):
                                                st.session_state.viewing_document = doc['file_id']
                                                st.session_state.page = "document_view"
                                                st.rerun()
                                        with col2:
                                            if st.button("🗑️ Delete", key=f"delete_{doc['file_id']}", use_container_width=True):
                                                # Delete the document
                                                success, result = mongo_db.delete_document(doc['file_id'], user_id)
                                                if success:
                                                    st.success("Document deleted!")
                                                    time.sleep(1)  # Brief pause
                                                    st.rerun()
                                                else:
                                                    st.error(f"Error deleting document: {result}")
        else:
            with st.container(border=True):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown("### 📂")
                with col2:
                    st.markdown("### No documents yet")
                    st.write("Click the + button above to add documents to this notebook.")
    
    # Chat Tab
    with tab2:
        st.subheader("Ask Questions About Your Documents")
        
        # Initialize message history for this notebook if not exists
        notebook_msg_key = f"messages_{notebook['_id']}"
        if notebook_msg_key not in st.session_state:
            st.session_state[notebook_msg_key] = []
        
        # Initialize RAG system and try to load saved vectors
        if rag_system and ('rag' not in st.session_state or st.session_state.rag is None):
            with st.spinner("Initializing RAG system..."):
                # Get configuration values from session state or use defaults
                llm_model = st.session_state.get('llm_model', "llama3.2:latest")
                embedding_model = st.session_state.get('embedding_model', "sentence-transformers/all-MiniLM-L6-v2")
                chunk_size = st.session_state.get('chunk_size', 1000)
                chunk_overlap = st.session_state.get('chunk_overlap', 200)
                use_gpu = st.session_state.get('use_gpu', True)
                
                # Initialize the RAG system
                st.session_state.rag = rag_system(
                    llm_model_name=llm_model,
                    embedding_model_name=embedding_model,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    use_gpu=use_gpu
                )
                
                # Initialize blockchain if notebook has it enabled and config is available
                if notebook.get('blockchain_enabled', False):
                    has_config = (
                        "blockchain_url" in st.session_state and
                        "blockchain_contract" in st.session_state and
                        "blockchain_private_key" in st.session_state and
                        st.session_state.blockchain_contract and
                        st.session_state.blockchain_private_key
                    )
                    
                    if has_config:
                        try:
                            st.session_state.rag.initialize_blockchain(
                                blockchain_url=st.session_state.blockchain_url,
                                contract_address=st.session_state.blockchain_contract,
                                private_key=st.session_state.blockchain_private_key
                            )
                        except Exception as e:
                            st.error(f"Error initializing blockchain: {str(e)}")
                
                # Try to load saved vectors for this notebook
                st.session_state.rag.load_vector_store(mongo_db, notebook['_id'])
        
        # Display chat messages for this notebook
        for message in st.session_state[notebook_msg_key]:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.markdown(message["content"])
                else:
                    if isinstance(message["content"], dict):
                        st.markdown(message["content"]["answer"])
                        
                        if "query_time" in message["content"]:
                            st.caption(f"Response time: {message['content']['query_time']:.2f} seconds")
                        
                        # Display blockchain verification if available
                        if "blockchain_log" in message["content"] and message["content"]["blockchain_log"]:
                            blockchain_log = message["content"]["blockchain_log"]
                            st.success(f"✅ Query verified on blockchain | TX: {blockchain_log['tx_hash'][:10]}...")
                        
                        # Display sources in expander
                        if "sources" in message["content"] and message["content"]["sources"]:
                            with st.expander("📄 View Sources"):
                                for i, source in enumerate(message["content"]["sources"]):
                                    st.markdown(f"**Source {i+1}: {source['source']}**")
                                    
                                    # Show blockchain verification if available
                                    if "blockchain_verification" in source:
                                        verification = source["blockchain_verification"]
                                        st.success(f"✅ Document verified on blockchain | TX: {verification['tx_hash'][:10]}...")
                                    
                                    st.text(source["content"])
                                    st.divider()
                    else:
                        st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input(f"Ask a question about {notebook['name']}..."):
            # Add user message to chat
            st.session_state[notebook_msg_key].append({"role": "user", "content": prompt})
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Get response if vector store is ready
            with st.chat_message("assistant"):
                try:
                    response = st.session_state.rag.ask(
                        prompt, 
                        user_id=user_id,
                        mongodb=mongo_db,
                        notebook_id=notebook['_id']
                    )
                    st.session_state[notebook_msg_key].append({"role": "assistant", "content": response})
                    
                    if isinstance(response, dict):
                        st.markdown(response["answer"])
                        
                        if "query_time" in response:
                            st.caption(f"Response time: {response['query_time']:.2f} seconds")
                        
                        # Display blockchain verification if available
                        if "blockchain_log" in response and response["blockchain_log"]:
                            blockchain_log = response["blockchain_log"]
                            st.success(f"✅ Query verified on blockchain | TX: {blockchain_log['tx_hash'][:10]}...")
                        
                        # Display sources in expander
                        if "sources" in response and response["sources"]:
                            with st.expander("📄 View Sources"):
                                for i, source in enumerate(response["sources"]):
                                    st.markdown(f"**Source {i+1}: {source['source']}**")
                                    
                                    # Show blockchain verification if available
                                    if "blockchain_verification" in source:
                                        verification = source["blockchain_verification"]
                                        st.success(f"✅ Document verified on blockchain | TX: {verification['tx_hash'][:10]}...")
                                    
                                    st.text(source["content"])
                                    st.divider()
                    else:
                        st.markdown(response)
                except Exception as e:
                    error_message = f"Error generating answer: {str(e)}"
                    st.error(error_message)
                    st.session_state[notebook_msg_key].append({"role": "assistant", "content": error_message})
    
    # Analytics Tab
    with tab3:
        st.subheader("Notebook Analytics")
        
        # Get analytics for this notebook
        success, analytics = mongo_db.get_notebook_analytics(notebook['_id'])
        
        if success:
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
            # Display top-level metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Documents", analytics.get("document_count", 0))
            with col2:
                st.metric("RAG Documents", analytics.get("rag_document_count", 0))
            with col3:
                st.metric("Queries", analytics.get("query_count", 0))
            with col4:
                avg_time = round(analytics.get("avg_response_time", 0), 2)
                st.metric("Avg. Response Time", f"{avg_time}s")
            
            # Add blockchain metrics if enabled
            if notebook.get('blockchain_enabled', False):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Blockchain Verified Documents", 
                            analytics.get("blockchain_document_count", 0))
                with col2:
                    st.metric("Blockchain Verified Queries", 
                            analytics.get("blockchain_query_count", 0))
            
            # Recent queries
            if analytics.get("recent_queries"):
                st.subheader("Recent Queries")
                for query in analytics["recent_queries"]:
                    with st.container(border=True):
                        st.write(f"**{query['query']}**")
                        st.caption(f"Time: {query['timestamp'].strftime('%Y-%m-%d %H:%M')} • Response Time: {query['response_time']:.2f}s")
            else:
                st.info("No queries have been made in this notebook yet.")
        else:
            st.error(f"Error fetching analytics: {analytics}")
    
    # Blockchain Tab - only show if blockchain is enabled
    with tab4:
        if notebook.get('blockchain_enabled', False):
            st.subheader("Blockchain Verification")
            
            # Check if blockchain config is available
            has_config = (
                "blockchain_url" in st.session_state and
                "blockchain_contract" in st.session_state and
                "blockchain_private_key" in st.session_state and
                st.session_state.blockchain_contract and
                st.session_state.blockchain_private_key
            )
            
            if has_config:
                st.success("✅ Blockchain verification is enabled and configured")
                
                # Add blockchain information section
                st.markdown("""
                ### What is Blockchain Verification?
                
                Blockchain verification provides tamper-proof record-keeping for:
                
                - **Document Integrity**: Each document is hashed and recorded on blockchain
                - **Query Auditing**: All questions and answers are immutably stored
                - **Verification**: Cryptographic proof that content hasn't been modified
                """)
                
                # Get blockchain-verified documents
                success, documents = mongo_db.list_user_documents(user_id, notebook['_id'])
                verified_docs = [doc for doc in documents if doc.get('blockchain_verification')]
                
                # Get blockchain-verified queries
                success, verified_queries = mongo_db.get_blockchain_queries(user_id, notebook['_id'])
                
                if verified_docs:
                    st.subheader(f"Verified Documents ({len(verified_docs)})")
                    with st.expander("View Verified Documents", expanded=True):
                        for doc in verified_docs:
                            with st.container(border=True):
                                # Document info
                                st.markdown(f"**{doc.get('display_name', doc['filename'])}**")
                                verification = doc['blockchain_verification']
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.caption(f"Transaction Hash: {verification['tx_hash']}")
                                    st.caption(f"Document Hash: {verification['document_hash'][:20]}...")
                                with col2:
                                    st.caption(f"Block Number: {verification['block_number']}")
                                    st.caption(f"Timestamp: {verification['timestamp']}")
                else:
                    st.info("No blockchain-verified documents in this notebook yet.")
                
                if success and verified_queries:
                    st.subheader(f"Verified Queries ({len(verified_queries)})")
                    with st.expander("View Verified Queries", expanded=True):
                        for query in verified_queries:
                            with st.container(border=True):
                                st.markdown(f"**{query['query']}**")
                                st.caption(f"Transaction Hash: {query['tx_hash']}")
                                st.caption(f"Timestamp: {query['timestamp']}")
                else:
                    st.info("No blockchain-verified queries in this notebook yet.")
            else:
                st.warning("⚠️ Blockchain verification is enabled but not configured. Please set configuration in Settings.")
                st.markdown("""
                ### Configuration Required
                
                To use blockchain verification, please configure:
                
                1. Go to Settings
                2. Enter your blockchain URL
                3. Enter the contract address for verification
                4. Enter your private key for signing transactions
                """)
        else:
            st.warning("Blockchain verification is not enabled for this notebook.")
            
            # Offer to enable it
            if st.button("Enable Blockchain Verification"):
                # Update notebook to enable blockchain
                success, result = mongo_db.update_notebook(
                    notebook['_id'], 
                    {"blockchain_enabled": True}
                )
                
                if success:
                    st.success("Blockchain verification enabled! Please configure settings.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Error enabling blockchain: {result}")

def show_document_view_page(mongo_db, user_id):
    """Show the document viewer page."""
    if not st.session_state.get('viewing_document'):
        st.error("No document selected")
        st.session_state.page = "notebooks"
        st.rerun()
        return
    
    # Get document
    success, result = mongo_db.get_document_file(st.session_state.viewing_document)
    
    if not success:
        st.error(f"Error fetching document: {result}")
        st.session_state.page = "notebooks"
        st.rerun()
        return
    
    # Add back button
    if st.button("← Back to Notebook"):
        st.session_state.page = "notebook_detail"
        st.rerun()
    
    # Add blockchain verification badge if available
    if result.get("blockchain_verification"):
        verification = result["blockchain_verification"]
        st.success(f"✅ This document is verified on blockchain | Transaction: {verification['tx_hash'][:10]}...")
    
    # Display the document
    document_viewer.display_document(result["data"], result)