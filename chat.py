import streamlit as st
import torch
import time
from rag import EnhancedRAG

def show_chat_page(mongo_db, user_id, rag_system=EnhancedRAG):
    """Show the main chat interface with enhanced features."""
    st.title("💬 Advanced Chat with Your Documents")
    st.markdown("Upload files and ask questions with multiple answer modes")
    
    # Sidebar for configuration and file upload
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # GPU Detection
        gpu_available = torch.cuda.is_available()
        if gpu_available:
            gpu_info = torch.cuda.get_device_properties(0)
            st.success(f"GPU detected: {gpu_info.name} ({gpu_info.total_memory / 1024**3:.1f} GB)")
        else:
            st.warning("No GPU detected. Running in CPU mode.")
        
        # Model selection
        llm_model = st.selectbox(
            "LLM Model",
            options=["llama3.2:latest","gemma3:4b","llama3:latest","phi3.5:3.8b","dolphin-phi:latest","samantha-mistral:latest","dolphin-mistral:latest",],
            index=0,
            key="chat_llm_model"
        )
        st.session_state.llm_model = llm_model
        
        embedding_model = st.selectbox(
            "Embedding Model",
            options=[
                "sentence-transformers/all-mpnet-base-v2",
                "sentence-transformers/all-MiniLM-L6-v2",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            ],
            index=1,
            key="chat_embedding_model"
        )
        st.session_state.embedding_model = embedding_model
        
        use_gpu = st.checkbox("Use GPU Acceleration", value=gpu_available, key="chat_use_gpu")
        st.session_state.use_gpu = use_gpu
        
        # Blockchain Configuration
        st.header("🔗 Blockchain")
        use_blockchain = st.checkbox(
            "Enable Blockchain Verification",
            value=st.session_state.get("blockchain_enabled", False),
            key="chat_blockchain_enabled"
        )
        
        # Update session state
        st.session_state.blockchain_enabled = use_blockchain
        
        if use_blockchain:
            # Check if we have all required config
            has_config = (
                "blockchain_url" in st.session_state and
                "blockchain_contract" in st.session_state and
                "blockchain_private_key" in st.session_state and
                st.session_state.blockchain_contract and
                st.session_state.blockchain_private_key
            )
            
            if has_config:
                st.success("✅ Blockchain verification enabled")
                
                # Allow viewing config
                with st.expander("View Blockchain Configuration"):
                    st.text_input(
                        "Blockchain URL", 
                        value=st.session_state.blockchain_url, 
                        disabled=True,
                        key="chat_blockchain_url_view"
                    )
                    st.text_input(
                        "Contract Address", 
                        value=st.session_state.blockchain_contract, 
                        disabled=True,
                        key="chat_contract_view"
                    )
                    st.text_input(
                        "Private Key", 
                        value="*" * 20, 
                        disabled=True,
                        key="chat_privkey_view"
                    )
            else:
                st.warning("⚠️ Blockchain configuration missing. Set it in Settings.")
                
                # Quick setup option
                with st.expander("Quick Blockchain Setup"):
                    st.session_state.blockchain_url = st.text_input(
                        "Blockchain URL", 
                        value=st.session_state.get("blockchain_url", "http://localhost:7545"),
                        key="chat_blockchain_url_input"
                    )
                    
                    st.session_state.blockchain_contract = st.text_input(
                        "Contract Address",
                        value=st.session_state.get("blockchain_contract", ""),
                        key="chat_contract_input"
                    )
                    
                    st.session_state.blockchain_private_key = st.text_input(
                        "Private Key (without 0x prefix)",
                        value=st.session_state.get("blockchain_private_key", ""),
                        type="password",
                        key="chat_privkey_input"
                    )
                    
                    st.session_state.blockchain_chain_id = st.number_input(
                        "Chain ID",
                        value=st.session_state.get("blockchain_chain_id", 1337),
                        step=1,
                        min_value=1,
                        help="Network chain ID (e.g., 1 for Ethereum Mainnet, 1337 for local networks)",
                        key="chat_chain_id_input"
                    )
                    
                    if st.button("Save Blockchain Configuration", key="chat_save_blockchain"):
                        if st.session_state.blockchain_contract and st.session_state.blockchain_private_key:
                            st.success("Blockchain configuration saved")
                        else:
                            st.error("Contract address and private key are required")
        
        # Advanced options
        with st.expander("Advanced Options"):
            chunk_size = st.slider("Chunk Size", 100, 2000, 1000, key="chat_chunk_size")
            st.session_state.chunk_size = chunk_size
            
            chunk_overlap = st.slider("Chunk Overlap", 0, 500, 200, key="chat_chunk_overlap")
            st.session_state.chunk_overlap = chunk_overlap
        
        if st.button("Initialize System", key="chat_init_system"):
            with st.spinner("Initializing Enhanced RAG system..."):
                st.session_state.rag = rag_system(
                    llm_model_name=llm_model,
                    embedding_model_name=embedding_model,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    use_gpu=use_gpu and gpu_available
                )
                
                # Initialize blockchain if enabled
                if st.session_state.get('blockchain_enabled', False):
                    has_config = (
                        "blockchain_url" in st.session_state and
                        "blockchain_contract" in st.session_state and
                        "blockchain_private_key" in st.session_state and
                        st.session_state.blockchain_contract and
                        st.session_state.blockchain_private_key
                    )
                    
                    if has_config:
                        # Initialize blockchain
                        try:
                            blockchain_success = st.session_state.rag.initialize_blockchain(
                                blockchain_url=st.session_state.blockchain_url,
                                contract_address=st.session_state.blockchain_contract,
                                private_key=st.session_state.blockchain_private_key,
                                chain_id=st.session_state.get("blockchain_chain_id", 1337)  # Use default 1337 if not specified
                            )
                            
                            if blockchain_success:
                                st.success("Blockchain verification enabled successfully")
                            else:
                                st.warning("Failed to initialize blockchain")
                        except Exception as e:
                            st.error(f"Error initializing blockchain: {str(e)}")
                
                st.success(f"System initialized with {embedding_model} on {st.session_state.rag.device}")
                time.sleep(1)  # Brief pause
                st.rerun()
        
        st.header("📄 Upload Documents")
        
        # Get user's notebooks for selection
        success, notebooks = mongo_db.get_notebooks(user_id)
        if success and notebooks:
            notebook_options = [("None", None)] + [(nb["name"], nb["_id"]) for nb in notebooks]
            selected_notebook = st.selectbox(
                "Add to Notebook",
                options=notebook_options,
                format_func=lambda x: x[0],
                key="upload_notebook"
            )
            selected_notebook_id = selected_notebook[1] if selected_notebook else None
            
            # Show blockchain status if notebook is selected
            if selected_notebook_id:
                # Find the selected notebook
                for nb in notebooks:
                    if nb["_id"] == selected_notebook_id:
                        if nb.get("blockchain_enabled", False):
                            st.info("🔗 Selected notebook has blockchain verification enabled")
                            
                            # Make sure blockchain is enabled in session state too
                            if not st.session_state.get("blockchain_enabled", False):
                                st.session_state.blockchain_enabled = True
                                st.warning("Blockchain verification automatically enabled for this notebook")
                                st.rerun()
                        break
            
            # Add option for custom name
            use_custom_name = st.checkbox("Use custom name", value=False, key="chat_use_custom_name")
            if use_custom_name:
                custom_name = st.text_input("Custom Document Name", placeholder="Enter custom name", key="chat_custom_doc_name")
            else:
                custom_name = None
        else:
            st.write("No notebooks available. Create one in the Notebooks section.")
            selected_notebook_id = None
            custom_name = None
            
        uploaded_files = st.file_uploader("Select Files", 
                                         type=["pdf", "docx", "doc", "txt"], 
                                         accept_multiple_files=True,
                                         key="chat_file_uploader")
        
        if uploaded_files and st.button("Process Files", key="chat_process_files"):
            with st.spinner("Processing files..."):
                saved_files = []  # Track saved files for blockchain verification
                
                # Save files to MongoDB if a notebook is selected
                if selected_notebook_id:
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
                        success, file_id = mongo_db.save_document_file(
                            file.getbuffer(),
                            file.name,
                            file_type,
                            user_id,
                            selected_notebook_id,
                            custom_name
                        )
                        
                        if success:
                            saved_files.append({
                                'file_id': file_id,
                                'name': file.name,
                                'data': file.getbuffer()
                            })
                
                # Initialize rag system if needed
                if not st.session_state.get('rag'):
                    st.session_state.rag = rag_system(
                        llm_model_name=llm_model,
                        embedding_model_name=embedding_model,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        use_gpu=use_gpu and gpu_available
                    )
                    
                    # Initialize blockchain if enabled
                    if st.session_state.get('blockchain_enabled', False):
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
                                    private_key=st.session_state.blockchain_private_key,
                                    chain_id=st.session_state.get("blockchain_chain_id", 1337)  # Use default 1337 if not specified
                                )
                            except Exception as e:
                                st.error(f"Error initializing blockchain: {str(e)}")
                
                # Process files through RAG
                success = st.session_state.rag.process_files(
                    uploaded_files, 
                    user_id=user_id,
                    mongodb=mongo_db,
                    notebook_id=selected_notebook_id
                )
                
                # Perform blockchain verification if enabled
                if st.session_state.get('blockchain_enabled', False) and success and saved_files:
                    if hasattr(st.session_state.rag, 'use_blockchain') and st.session_state.rag.use_blockchain:
                        for file_info in saved_files:
                            try:
                                with st.spinner(f"Verifying {file_info['name']} on blockchain..."):
                                    # Create a unique document ID
                                    document_id = f"{file_info['name']}_{selected_notebook_id}_{user_id}"
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
                
                if success:
                    metrics = st.session_state.rag.get_performance_metrics()
                    if metrics:
                        st.success("Files processed successfully!")
                        with st.expander("💹 Performance Metrics"):
                            st.markdown(f"**Documents processed:** {metrics['documents_processed']} chunks")
                            st.markdown(f"**Index building time:** {metrics['index_building_time']:.2f} seconds")
                            st.markdown(f"**Total processing time:** {metrics['total_processing_time']:.2f} seconds")
                            st.markdown(f"**Memory used:** {metrics['memory_used_gb']:.2f} GB")
                            st.markdown(f"**Device used:** {metrics['device']}")
                            
                            # Show blockchain status
                            if metrics.get('blockchain_enabled', False):
                                st.markdown(f"**Blockchain verification:** Enabled")
                            else:
                                st.markdown(f"**Blockchain verification:** Disabled")
                                
                        time.sleep(1)  # Brief pause
                        st.rerun()
    
    # Mode selection in main area
    st.subheader("Select Answer Mode")
    
    if "rag_mode" not in st.session_state:
        st.session_state.rag_mode = "direct_retrieval"
    
    mode_description = {
        "direct_retrieval": "Directly retrieve answers from documents (fastest)",
        "enhanced_rag": "Enhanced RAG with multi-stage pipeline for improved answers",
        "hybrid": "Hybrid approach combining document retrieval and web search (most comprehensive)"
    }
    
    mode_cols = st.columns(3)
    with mode_cols[0]:
        direct_mode = st.button("📄 Direct Retrieval", 
                               use_container_width=True,
                               help="Fastest mode, directly uses document content to answer",
                               key="direct_retrieval_btn")
        st.caption(mode_description["direct_retrieval"])
        
    with mode_cols[1]:
        enhanced_mode = st.button("🔄 Enhanced RAG", 
                                 use_container_width=True,
                                 help="Improves answers with a multi-stage refinement process",
                                 key="enhanced_rag_btn")
        st.caption(mode_description["enhanced_rag"])
        
    with mode_cols[2]:
        hybrid_mode = st.button("🌐 Hybrid Search", 
                               use_container_width=True,
                               help="Combines document content with simulated web searches",
                               key="hybrid_btn")
        st.caption(mode_description["hybrid"])
    
    if direct_mode:
        st.session_state.rag_mode = "direct_retrieval"
    elif enhanced_mode:
        st.session_state.rag_mode = "enhanced_rag"
    elif hybrid_mode:
        st.session_state.rag_mode = "hybrid"
    
    # Blockchain Badge
    if st.session_state.get('blockchain_enabled', False):
        if hasattr(st.session_state, 'rag') and st.session_state.rag and hasattr(st.session_state.rag, 'use_blockchain') and st.session_state.rag.use_blockchain:
            st.info(f"🔗 Current mode: {st.session_state.rag_mode} with **Blockchain Verification** - {mode_description[st.session_state.rag_mode]}")
        else:
            st.info(f"Current mode: {st.session_state.rag_mode} - {mode_description[st.session_state.rag_mode]}")
            st.warning("Blockchain verification is enabled but not active. Try reinitializing the system.")
    else:
        st.info(f"Current mode: {st.session_state.rag_mode} - {mode_description[st.session_state.rag_mode]}")
    
    # Main chat area
    st.subheader("Ask Questions About Your Documents")
    
    # Initialize chat message history if not exists
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(message["content"])
            else:
                if isinstance(message["content"], dict):
                    st.markdown(message["content"]["answer"])
                    
                    # Display mode info
                    if "mode" in message["content"]:
                        mode_name = message["content"]["mode"]
                        mode_icons = {
                            "direct_retrieval": "📄",
                            "enhanced_rag": "🔄",
                            "hybrid": "🌐"
                        }
                        icon = mode_icons.get(mode_name, "ℹ️")
                        st.caption(f"{icon} Answer mode: {mode_name}")
                    
                    if "query_time" in message["content"]:
                        st.caption(f"⏱️ Response time: {message['content']['query_time']:.2f} seconds")
                    
                    # Display blockchain info if present
                    if "blockchain_log" in message["content"] and message["content"]["blockchain_log"]:
                        blockchain_log = message["content"]["blockchain_log"]
                        st.success(f"✅ Query verified on blockchain | TX: {blockchain_log['tx_hash'][:10]}...")
                    
                    # Display pipeline info for enhanced RAG
                    if message["content"].get("mode") == "enhanced_rag" and "initial_answer" in message["content"]:
                        with st.expander("🔄 View Enhancement Process"):
                            st.subheader("Initial Answer")
                            st.markdown(message["content"]["initial_answer"])
                            st.divider()
                            st.subheader("Enhanced Answer")
                            st.markdown(message["content"]["answer"])
                    
                    # Display source info for hybrid mode
                    if message["content"].get("mode") == "hybrid":
                        if "doc_sources_count" in message["content"] and "web_sources_count" in message["content"]:
                            st.caption(f"Combined {message['content']['doc_sources_count']} document sources and {message['content']['web_sources_count']} web sources")
                    
                    # Display sources in expander
                    if "sources" in message["content"] and message["content"]["sources"]:
                        with st.expander("📄 View Sources"):
                            for i, source in enumerate(message["content"]["sources"]):
                                if source.get("file_type") == "web":
                                    st.markdown(f"**Source {i+1}: 🌐 {source['source']}**")
                                else:
                                    st.markdown(f"**Source {i+1}: 📄 {source['source']}**")
                                    
                                    # Show blockchain verification if available
                                    if "blockchain_verification" in source:
                                        verification = source["blockchain_verification"]
                                        st.success(f"✅ Document verified on blockchain | TX: {verification['tx_hash'][:10]}...")
                                
                                st.text(source["content"])
                                st.divider()
                else:
                    st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Check if system is initialized
        if not st.session_state.get('rag'):
            with st.spinner("Initializing system..."):
                st.session_state.rag = rag_system(
                    llm_model_name=llm_model,
                    embedding_model_name=embedding_model,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    use_gpu=use_gpu and gpu_available
                )
                
                # Initialize blockchain if enabled
                if st.session_state.get('blockchain_enabled', False):
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
                                private_key=st.session_state.blockchain_private_key,
                                chain_id=st.session_state.get("blockchain_chain_id", 1337)  # Use default 1337 if not specified
                            )
                        except Exception as e:
                            st.error(f"Error initializing blockchain: {str(e)}")
        
        # Get response - RAG system will try to auto-load vectors by domain
        with st.chat_message("assistant"):
            try:
                with st.spinner(f"Processing with {st.session_state.rag_mode} mode..."):
                    response = st.session_state.rag.ask(
                        prompt,
                        mode=st.session_state.rag_mode,
                        user_id=user_id,
                        mongodb=mongo_db
                    )
                
                # If response indicates no vectors found but domain was detected
                if isinstance(response, str) and "Please upload and process documents first" in response:
                    # Try to detect domain from query
                    potential_domains = st.session_state.rag.detect_query_domain(prompt)
                    if potential_domains:
                        st.info(f"You seem to be asking about {potential_domains[0]}. Please upload relevant documents first.")
                    else:
                        st.markdown(response)
                else:
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    # Regular response rendering
                    if isinstance(response, dict):
                        st.markdown(response["answer"])
                        
                        # Display mode info
                        if "mode" in response:
                            mode_name = response["mode"]
                            mode_icons = {
                                "direct_retrieval": "📄",
                                "enhanced_rag": "🔄",
                                "hybrid": "🌐"
                            }
                            icon = mode_icons.get(mode_name, "ℹ️")
                            st.caption(f"{icon} Answer mode: {mode_name}")
                        
                        if "query_time" in response:
                            st.caption(f"⏱️ Response time: {response['query_time']:.2f} seconds")
                        
                        # Display blockchain info if present
                        if "blockchain_log" in response and response["blockchain_log"]:
                            blockchain_log = response["blockchain_log"]
                            st.success(f"✅ Query verified on blockchain | TX: {blockchain_log['tx_hash'][:10]}...")
                        
                        # Display pipeline info for enhanced RAG
                        if response.get("mode") == "enhanced_rag" and "initial_answer" in response:
                            with st.expander("🔄 View Enhancement Process"):
                                st.subheader("Initial Answer")
                                st.markdown(response["initial_answer"])
                                st.divider()
                                st.subheader("Enhanced Answer")
                                st.markdown(response["answer"])
                        
                        # Display source info for hybrid mode
                        if response.get("mode") == "hybrid":
                            if "doc_sources_count" in response and "web_sources_count" in response:
                                st.caption(f"Combined {response['doc_sources_count']} document sources and {response['web_sources_count']} web sources")
                        
                        # Display sources in expander
                        if "sources" in response and response["sources"]:
                            with st.expander("📄 View Sources"):
                                for i, source in enumerate(response["sources"]):
                                    if source.get("file_type") == "web":
                                        st.markdown(f"**Source {i+1}: 🌐 {source['source']}**")
                                    else:
                                        st.markdown(f"**Source {i+1}: 📄 {source['source']}**")
                                        
                                        # Show blockchain verification if available
                                        if "blockchain_verification" in source:
                                            verification = source["blockchain_verification"]
                                            st.success(f"✅ Document verified on blockchain | TX: {verification['tx_hash'][:10]}...")
                                    
                                    st.text(source["content"])
                                    st.divider()
            except Exception as e:
                error_message = f"Error generating answer: {str(e)}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})