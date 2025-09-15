import os
import streamlit as st
import pymongo
import bcrypt
from datetime import datetime, timedelta
import uuid
from bson.objectid import ObjectId
import gridfs
import io
import bson

class MongoDB:
    def __init__(self, connection_string=None):
        """Initialize MongoDB connection."""
        # Use provided connection string or default to environment variable
        self.connection_string = connection_string or os.environ.get(
            "MONGODB_URI", "mongodb://localhost:27017/"
        )
        self.client = None
        self.db = None
        self.fs = None
        self.connect()
    
    def connect(self):
        """Establish connection to MongoDB."""
        try:
            self.client = pymongo.MongoClient(self.connection_string)
            # Create or access 'rag_system' database
            self.db = self.client.rag_system
            # Initialize GridFS for file storage
            self.fs = gridfs.GridFS(self.db)
            
            # Ping the database to verify connection
            self.client.admin.command('ping')
            st.sidebar.success("Connected to MongoDB")
        except Exception as e:
            st.sidebar.error(f"MongoDB Connection Error: {str(e)}")
            self.client = None
            self.db = None
            self.fs = None
    
    # User Authentication Methods
    def create_user(self, email, password, name):
        """Create a new user with hashed password."""
        if self.client is None:
            return False, "Database connection not established"
        
        # Check if user already exists
        if self.db.users.find_one({"email": email}):
            return False, "User with this email already exists"
        
        # Hash the password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        # Create new user document
        user = {
            "email": email,
            "password": hashed_password,
            "name": name,
            "created_at": datetime.now(),
            "last_login": None,
            "documents": [],  # To store references to user's documents
            "notebooks": [],  # To store user's notebooks
            "usage_stats": {
                "total_docs": 0,
                "total_pdfs": 0,
                "total_queries": 0,
                "rag_documents": 0,
                "last_activity": datetime.now()
            }
        }
        
        try:
            result = self.db.users.insert_one(user)
            return True, str(result.inserted_id)
        except Exception as e:
            return False, str(e)
    
    def authenticate_user(self, email, password):
        """Authenticate user with email and password."""
        if self.client is None:
            return False, "Database connection not established"
        
        user = self.db.users.find_one({"email": email})
        if not user:
            return False, "Invalid email or password"
        
        # Check password
        if bcrypt.checkpw(password.encode('utf-8'), user['password']):
            # Update last login time
            self.db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"last_login": datetime.now()}}
            )
            
            # Create a session token
            session_id = str(uuid.uuid4())
            expiry = datetime.now() + timedelta(days=1)
            
            # Store session
            self.db.sessions.insert_one({
                "session_id": session_id,
                "user_id": user["_id"],
                "expiry": expiry
            })
            
            return True, {
                "user_id": str(user["_id"]),
                "name": user["name"],
                "email": user["email"],
                "session_id": session_id
            }
        else:
            return False, "Invalid email or password"
    
    def validate_session(self, session_id):
        """Validate an existing session."""
        if self.client is None:
            return False, "Database connection not established"
        
        session = self.db.sessions.find_one({
            "session_id": session_id,
            "expiry": {"$gt": datetime.now()}
        })
        
        if not session:
            return False, "Session expired or invalid"
        
        # Get user details
        user = self.db.users.find_one({"_id": session["user_id"]})
        if not user:
            return False, "User not found"
        
        return True, {
            "user_id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"]
        }
    
    def logout_user(self, session_id):
        """Invalidate a user session for logout."""
        if self.client is None:
            return False, "Database connection not established"
        
        try:
            self.db.sessions.delete_one({"session_id": session_id})
            return True, "Logged out successfully"
        except Exception as e:
            return False, str(e)
    
    # File Storage Methods
    def save_document_file(self, file_data, filename, file_type, user_id, notebook_id=None, custom_name=None):
        """Save a document file to GridFS."""
        if self.client is None or self.fs is None:
            st.error("Database connection not established")
            return False, "Database connection not established"
        
        try:
            # Store the file in GridFS
            display_name = custom_name if custom_name else filename
            file_metadata = {
                "filename": filename,
                "display_name": display_name,
                "file_type": file_type,
                "user_id": ObjectId(user_id),
                "notebook_id": notebook_id,
                "upload_date": datetime.now()
            }
            
            # Make sure file_data is bytes
            if not isinstance(file_data, bytes):
                if hasattr(file_data, 'read'):
                    file_data = file_data.read()
                else:
                    file_data = bytes(file_data)
            
            # Debug info
            st.sidebar.info(f"Saving file: {filename} ({len(file_data)} bytes)")
            
            # Save the file to GridFS
            file_id = self.fs.put(file_data, **file_metadata)
            
            # Update user document count
            self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"usage_stats.total_docs": 1}}
            )
            
            if file_type == "pdf":
                self.db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$inc": {"usage_stats.total_pdfs": 1}}
                )
            
            # If notebook_id is provided, update notebook as well
            if notebook_id:
                self.db.notebooks.update_one(
                    {"_id": ObjectId(notebook_id)},
                    {"$inc": {"document_count": 1}}
                )
            
            return True, str(file_id)
        except Exception as e:
            st.error(f"Error saving file: {str(e)}")
            return False, str(e)
    
    def get_document_file(self, file_id):
        """Retrieve a document file from GridFS."""
        if self.client is None or self.fs is None:
            return False, "Database connection not established"
        
        try:
            # Get the file from GridFS
            file_obj = self.fs.get(ObjectId(file_id))
            return True, {
                "data": file_obj.read(),
                "filename": file_obj.filename,
                "display_name": getattr(file_obj, "display_name", file_obj.filename),
                "file_type": getattr(file_obj, "file_type", "unknown"),
                "upload_date": file_obj.upload_date,
                "blockchain_verification": getattr(file_obj, "blockchain_verification", None)
            }
        except Exception as e:
            return False, str(e)
    
    def list_user_documents(self, user_id, notebook_id=None):
        """List all documents for a user, optionally filtered by notebook."""
        if self.client is None or self.fs is None:
            return False, "Database connection not established"
        
        try:
            # Build query
            query = {"user_id": ObjectId(user_id)}
            if notebook_id:
                query["notebook_id"] = notebook_id
            
            # Get files from GridFS 
            # Note: We're using fs.find() on the files collection directly, 
            # not the deprecated fs.list() method
            cursor = self.db.fs.files.find(query).sort("uploadDate", pymongo.DESCENDING)
            
            # Convert to list of dictionaries
            result = []
            for file_doc in cursor:
                result.append({
                    "file_id": str(file_doc["_id"]),
                    "filename": file_doc["filename"],
                    "display_name": file_doc.get("display_name", file_doc["filename"]),
                    "file_type": file_doc.get("file_type", "unknown"),
                    "upload_date": file_doc.get("upload_date", file_doc.get("uploadDate", datetime.now())),
                    "notebook_id": file_doc.get("notebook_id"),
                    "blockchain_verification": file_doc.get("blockchain_verification")
                })
            
            return True, result
        except Exception as e:
            st.error(f"Error listing documents: {str(e)}")
            return False, str(e)
    
    def delete_document(self, file_id, user_id):
        """Delete a document from GridFS."""
        if self.client is None or self.fs is None:
            return False, "Database connection not established"
        
        try:
            # Get the file metadata first to check ownership
            file_doc = self.db.fs.files.find_one({"_id": ObjectId(file_id)})
            if not file_doc:
                return False, "Document not found"
            
            # Check if the file belongs to the user
            if str(file_doc.get("user_id", "")) != user_id:
                return False, "You don't have permission to delete this document"
            
            # Get notebook_id and file_type for later update
            notebook_id = file_doc.get("notebook_id")
            file_type = file_doc.get("file_type", "unknown")
            
            # Delete the file from GridFS
            self.fs.delete(ObjectId(file_id))
            
            # Update user document count
            self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"usage_stats.total_docs": -1}}
            )
            
            if file_type == "pdf":
                self.db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$inc": {"usage_stats.total_pdfs": -1}}
                )
            
            # If notebook_id exists, update notebook as well
            if notebook_id:
                self.db.notebooks.update_one(
                    {"_id": ObjectId(notebook_id)},
                    {"$inc": {"document_count": -1}}
                )
            
            return True, "Document deleted successfully"
        except Exception as e:
            st.error(f"Error deleting document: {str(e)}")
            return False, str(e)

    def update_document_blockchain_verification(self, file_id, verification_data):
        """Store blockchain verification data for a document.
        
        Args:
            file_id: ID of the document file
            verification_data: Dict with blockchain verification information
            
        Returns:
            (success, result): Operation success and result/error message
        """
        if self.client is None:
            return False, "Database connection not established"
        
        try:
            # Update the file metadata in GridFS
            self.db.fs.files.update_one(
                {"_id": ObjectId(file_id)},
                {"$set": {"blockchain_verification": verification_data}}
            )
            
            return True, "Blockchain verification data stored"
        except Exception as e:
            return False, str(e)

    def log_blockchain_query(self, user_id, query, tx_hash, notebook_id=None):
        """Log a blockchain-verified query.
        
        Args:
            user_id: ID of the user
            query: The query text
            tx_hash: Blockchain transaction hash
            notebook_id: Optional notebook ID
            
        Returns:
            (success, result): Operation success and result/error message
        """
        if self.client is None:
            return False, "Database connection not established"
        
        try:
            # Create blockchain query log
            query_log = {
                "user_id": ObjectId(user_id),
                "notebook_id": notebook_id,
                "query": query,
                "tx_hash": tx_hash,
                "timestamp": datetime.now()
            }
            
            # Insert query log
            self.db.blockchain_queries.insert_one(query_log)
            
            return True, "Blockchain query logged"
        except Exception as e:
            return False, str(e)

    def get_blockchain_queries(self, user_id, notebook_id=None):
        """Get blockchain-verified queries for a user.
        
        Args:
            user_id: ID of the user
            notebook_id: Optional notebook ID to filter by
            
        Returns:
            (success, result): Operation success and list of blockchain queries
        """
        if self.client is None:
            return False, "Database connection not established"
        
        try:
            # Build query
            query = {"user_id": ObjectId(user_id)}
            if notebook_id:
                query["notebook_id"] = notebook_id
            
            # Get blockchain queries
            queries = list(self.db.blockchain_queries.find(query).sort("timestamp", -1))
            
            # Convert ObjectIds to strings for JSON serialization
            for query in queries:
                query["_id"] = str(query["_id"])
                query["user_id"] = str(query["user_id"])
                if query.get("notebook_id"):
                    query["notebook_id"] = str(query["notebook_id"])
            
            return True, queries
        except Exception as e:
            return False, str(e)

    def get_document_blockchain_status(self, file_id):
        """Get blockchain verification status for a document.
        
        Args:
            file_id: ID of the document file
            
        Returns:
            (success, result): Operation success and verification data
        """
        if self.client is None:
            return False, "Database connection not established"
        
        try:
            # Get the file metadata from GridFS
            file_doc = self.db.fs.files.find_one({"_id": ObjectId(file_id)})
            if not file_doc:
                return False, "Document not found"
            
            # Return verification data if available
            if "blockchain_verification" in file_doc:
                return True, file_doc["blockchain_verification"]
            else:
                return False, "Document not verified on blockchain"
        except Exception as e:
            return False, str(e)

    # Notebook Management Methods
    def create_notebook(self, user_id, name, description="", color="#1E88E5", metadata=None):
        """Create a new notebook.
        
        Args:
            user_id: ID of the user
            name: Notebook name
            description: Optional notebook description
            color: Notebook color code
            metadata: Additional metadata like domains
            
        Returns:
            (success, result): Tuple with success flag and result/error message
        """
        try:
            now = datetime.now()
            notebook = {
                "name": name,
                "description": description,
                "color": color,
                "user_id": user_id,
                "created_at": now,
                "last_accessed": now,
                "is_favorite": False,
                "domains": metadata.get("domains", ["General"]) if metadata else ["General"],
                "metadata": metadata or {},
                "blockchain_enabled": metadata.get("blockchain_enabled", False) if metadata else False
            }
            
            result = self.db.notebooks.insert_one(notebook)
            return True, result.inserted_id
        except Exception as e:
            return False, f"Error creating notebook: {str(e)}"
    
    def get_notebooks(self, user_id):
        """Get all notebooks for a user."""
        if self.client is None:
            return False, "Database connection not established"
            
        try:
            # Find all notebooks for this user
            notebooks = list(self.db.notebooks.find({"user_id": ObjectId(user_id)}).sort("last_accessed", -1))
            
            # Convert ObjectIds to strings for JSON serialization
            for notebook in notebooks:
                notebook["_id"] = str(notebook["_id"])
                notebook["user_id"] = str(notebook["user_id"])
            
            return True, notebooks
        except Exception as e:
            return False, str(e)
    
    def get_notebook(self, notebook_id):
        """Get a specific notebook by ID."""
        if self.client is None:
            return False, "Database connection not established"
            
        try:
            # Find the notebook
            notebook = self.db.notebooks.find_one({"_id": ObjectId(notebook_id)})
            
            if not notebook:
                return False, "Notebook not found"
                
            # Update last accessed time
            self.db.notebooks.update_one(
                {"_id": ObjectId(notebook_id)},
                {"$set": {"last_accessed": datetime.now()}}
            )
            
            # Convert ObjectIds to strings for JSON serialization
            notebook["_id"] = str(notebook["_id"])
            notebook["user_id"] = str(notebook["user_id"])
            
            return True, notebook
        except Exception as e:
            return False, str(e)
    
    def update_notebook(self, notebook_id, data):
        """Update notebook properties."""
        if self.client is None:
            return False, "Database connection not established"
        
        try:
            # Remove _id from data if present
            if "_id" in data:
                del data["_id"]
            
            # Remove user_id from data if present
            if "user_id" in data:
                del data["user_id"]
            
            # Update the notebook
            result = self.db.notebooks.update_one(
                {"_id": ObjectId(notebook_id)},
                {"$set": data}
            )
            
            if result.matched_count == 0:
                return False, "Notebook not found"
            
            return True, "Notebook updated successfully"
        except Exception as e:
            return False, str(e)
    
    def toggle_favorite_notebook(self, notebook_id):
        """Toggle favorite status for a notebook."""
        if self.client is None:
            return False, "Database connection not established"
            
        try:
            # Get current favorite status
            notebook = self.db.notebooks.find_one({"_id": ObjectId(notebook_id)})
            if not notebook:
                return False, "Notebook not found"
                
            # Toggle the status
            new_status = not notebook.get("is_favorite", False)
            
            # Update the notebook
            self.db.notebooks.update_one(
                {"_id": ObjectId(notebook_id)},
                {"$set": {"is_favorite": new_status}}
            )
            
            return True, new_status
        except Exception as e:
            return False, str(e)
    
    def delete_notebook(self, notebook_id, user_id):
        """Delete a notebook and remove reference from user."""
        if self.client is None:
            return False, "Database connection not established"
            
        try:
            # Delete the notebook
            result = self.db.notebooks.delete_one({
                "_id": ObjectId(notebook_id), 
                "user_id": ObjectId(user_id)
            })
            
            if result.deleted_count == 0:
                return False, "Notebook not found or not owned by user"
                
            # Remove reference from user
            self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$pull": {"notebooks": ObjectId(notebook_id)}}
            )
            
            # Update documents to remove notebook reference
            self.db.fs.files.update_many(
                {"notebook_id": notebook_id},
                {"$set": {"notebook_id": None}}
            )
            
            return True, "Notebook deleted successfully"
        except Exception as e:
            return False, str(e)
    
    # RAG Document Management
    def save_document_metadata(self, user_id, document_info, notebook_id=None):
        """Save metadata about processed documents."""
        if self.client is None:
            return False, "Database connection not established"
        
        try:
            # Add timestamp
            document_info["processed_at"] = datetime.now()
            
            # If notebook_id is provided, associate document with notebook
            if notebook_id:
                document_info["notebook_id"] = notebook_id
                
                # Also update the notebook document count if needed
                if "documents" in document_info:
                    document_count = len(document_info.get("documents", []))
                    self.db.notebooks.update_one(
                        {"_id": ObjectId(notebook_id)},
                        {"$inc": {"rag_document_count": document_count}}
                    )
            
            # Update user RAG document history
            self.db.rag_documents.insert_one({
                "user_id": ObjectId(user_id),
                "notebook_id": notebook_id,
                "metadata": document_info,
                "created_at": datetime.now()
            })
            
            # Update user document count
            self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"usage_stats.rag_documents": len(document_info.get("documents", []))}}
            )
            
            return True, "Document metadata saved"
        except Exception as e:
            return False, str(e)
    
    def get_rag_document_history(self, user_id, notebook_id=None):
        """Get RAG document processing history for a user."""
        if self.client is None:
            return False, "Database connection not established"
        
        try:
            # Build query
            query = {"user_id": ObjectId(user_id)}
            if notebook_id:
                query["notebook_id"] = notebook_id
            
            # Get RAG documents
            documents = list(self.db.rag_documents.find(query).sort("created_at", -1))
            
            # Convert ObjectIds to strings for JSON serialization
            for doc in documents:
                doc["_id"] = str(doc["_id"])
                doc["user_id"] = str(doc["user_id"])
                if doc.get("notebook_id"):
                    doc["notebook_id"] = str(doc["notebook_id"])
            
            return True, documents
        except Exception as e:
            return False, str(e)
    
    # Analytics Methods
    def log_query(self, user_id, query, response_time, notebook_id=None):
        """Log a query for analytics."""
        if self.client is None:
            return False, "Database connection not established"
        
        try:
            # Create query log
            query_log = {
                "user_id": ObjectId(user_id),
                "notebook_id": notebook_id,
                "query": query,
                "response_time": response_time,
                "timestamp": datetime.now()
            }
            
            # Insert query log
            self.db.query_logs.insert_one(query_log)
            
            # Update user stats
            self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$inc": {"usage_stats.total_queries": 1},
                    "$set": {"usage_stats.last_activity": datetime.now()}
                }
            )
            
            return True, "Query logged"
        except Exception as e:
            return False, str(e)
    
    def get_user_analytics(self, user_id):
        """Get analytics for a user."""
        if self.client is None:
            return False, "Database connection not established"
        
        try:
            # Get user
            user = self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                return False, "User not found"
            
            # Get usage statistics
            usage_stats = user.get("usage_stats", {})
            
            # Get query logs
            query_logs = list(self.db.query_logs.find({"user_id": ObjectId(user_id)}).sort("timestamp", -1).limit(100))
            
            # Calculate average response time
            if query_logs:
                avg_response_time = sum(log.get("response_time", 0) for log in query_logs) / len(query_logs)
            else:
                avg_response_time = 0
            
            # Get notebook statistics
            notebooks = list(self.db.notebooks.find({"user_id": ObjectId(user_id)}))
            notebook_stats = [
                {
                    "id": str(notebook["_id"]),
                    "name": notebook["name"],
                    "document_count": notebook.get("document_count", 0),
                    "rag_document_count": notebook.get("rag_document_count", 0),
                    "created_at": notebook["created_at"],
                    "last_accessed": notebook.get("last_accessed", notebook["created_at"]),
                    "blockchain_enabled": notebook.get("blockchain_enabled", False)
                }
                for notebook in notebooks
            ]
            
            # Get blockchain query stats
            blockchain_queries = self.db.blockchain_queries.count_documents({"user_id": ObjectId(user_id)})
            
            # Prepare result
            analytics = {
                "user_id": str(user["_id"]),
                "name": user["name"],
                "email": user["email"],
                "created_at": user["created_at"],
                "last_login": user.get("last_login"),
                "total_documents": usage_stats.get("total_docs", 0),
                "total_pdfs": usage_stats.get("total_pdfs", 0),
                "total_queries": usage_stats.get("total_queries", 0),
                "total_rag_documents": usage_stats.get("rag_documents", 0),
                "blockchain_queries": blockchain_queries,
                "last_activity": usage_stats.get("last_activity"),
                "avg_response_time": avg_response_time,
                "notebook_count": len(notebooks),
                "notebook_stats": notebook_stats,
                "recent_queries": [
                    {
                        "query": log["query"],
                        "timestamp": log["timestamp"],
                        "response_time": log.get("response_time", 0),
                        "notebook_id": log.get("notebook_id")
                    }
                    for log in query_logs[:10]  # Limit to 10 most recent queries
                ]
            }
            
            return True, analytics
        except Exception as e:
            return False, str(e)
    
    def get_notebook_analytics(self, notebook_id):
        """Get analytics for a specific notebook."""
        if self.client is None:
            return False, "Database connection not established"
        
        try:
            # Get notebook
            notebook = self.db.notebooks.find_one({"_id": ObjectId(notebook_id)})
            if not notebook:
                return False, "Notebook not found"
            
            # Get document count
            document_count = notebook.get("document_count", 0)
            
            # Get RAG document count
            rag_document_count = notebook.get("rag_document_count", 0)
            
            # Get query logs for this notebook
            query_logs = list(self.db.query_logs.find({"notebook_id": notebook_id}).sort("timestamp", -1))
            
            # Calculate average response time
            if query_logs:
                avg_response_time = sum(log.get("response_time", 0) for log in query_logs) / len(query_logs)
            else:
                avg_response_time = 0
            
            # Get blockchain query count for this notebook
            blockchain_queries = list(self.db.blockchain_queries.find({"notebook_id": notebook_id}))
            blockchain_query_count = len(blockchain_queries)
            
            # Prepare result
            analytics = {
                "notebook_id": str(notebook["_id"]),
                "name": notebook["name"],
                "description": notebook.get("description", ""),
                "created_at": notebook["created_at"],
                "last_accessed": notebook.get("last_accessed", notebook["created_at"]),
                "document_count": document_count,
                "rag_document_count": rag_document_count,
                "query_count": len(query_logs),
                "avg_response_time": avg_response_time,
                "blockchain_enabled": notebook.get("blockchain_enabled", False),
                "blockchain_query_count": blockchain_query_count,
                "recent_queries": [
                    {
                        "query": log["query"],
                        "timestamp": log["timestamp"],
                        "response_time": log.get("response_time", 0)
                    }
                    for log in query_logs[:10]  # Limit to 10 most recent queries
                ]
            }
            
            return True, analytics
        except Exception as e:
            return False, str(e)

    def save_faiss_index(self, notebook_id, user_id, index_binary, documents_binary, metadata=None):
        """Save FAISS index data for a notebook."""
        import datetime
        import bson
        
        try:
            # First check if an index already exists
            collection = self.db.faiss_indexes
            existing = collection.find_one({"notebook_id": notebook_id})
            
            # Prepare data - make sure to use Binary for large data
            now = datetime.datetime.now()
            data = {
                "notebook_id": notebook_id,
                "user_id": user_id,
                "faiss_index": bson.Binary(index_binary),  # Use BSON Binary type
                "has_documents": len(documents_binary) > 0,
                "metadata": metadata or {},
                "updated_at": now
            }
            
            # Only add documents if they're not empty
            if len(documents_binary) > 0:
                data["documents"] = bson.Binary(documents_binary)
            
            # Update or insert
            if existing:
                collection.update_one(
                    {"notebook_id": notebook_id}, 
                    {"$set": data}
                )
                return True, "FAISS index updated successfully"
            else:
                data["created_at"] = now
                collection.insert_one(data)
                return True, "FAISS index created successfully"
                
        except Exception as e:
            print(f"MongoDB error saving FAISS index: {str(e)}")
            return False, f"Error saving FAISS index: {str(e)}"
    
    def get_faiss_index(self, notebook_id):
        """Retrieve FAISS index data for a notebook.
        
        Args:
            notebook_id: ID of the notebook
            
        Returns:
            (success, result): Tuple with operation success flag and result/error
        """
        try:
            collection = self.db.faiss_indexes
            result = collection.find_one({"notebook_id": notebook_id})
            
            if result:
                return True, {
                    "faiss_index": result["faiss_index"],  # Already binary
                    "documents": result["documents"],      # Already binary
                    "metadata": result.get("metadata", {}),
                    "updated_at": result["updated_at"]
                }
            else:
                return False, "No FAISS index found for this notebook"
                
        except Exception as e:
            print(f"MongoDB error getting FAISS index: {str(e)}")
            return False, f"Error retrieving FAISS index: {str(e)}"