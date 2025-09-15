import streamlit as st
import os
from utils import check_password_strength

def show_login_page(mongo_db):
    """Display the login form."""
    st.header("🔐 Login")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.container(border=True):
            st.subheader("Welcome Back!")
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            
            col_b1, col_b2 = st.columns([1, 1])
            with col_b1:
                if st.button("Login", use_container_width=True):
                    if not email or not password:
                        st.error("Please enter both email and password")
                    else:
                        with st.spinner("Authenticating..."):
                            # Authenticate user
                            success, result = mongo_db.authenticate_user(email, password)
                            if success:
                                st.session_state.user = result
                                st.session_state.session_id = result['session_id']
                                st.session_state.auth_page = None  # Exit auth page
                                st.toast(f"Welcome back, {result['name']}!")
                                st.rerun()
                            else:
                                st.error(result)
    
    with col2:
        with st.container(border=True):
            st.subheader("New User?")
            st.write("Create an account to start using our GPU-Accelerated RAG system.")
            if st.button("Sign Up", use_container_width=True):
                st.session_state.auth_page = "signup"
                st.rerun()

def show_signup_page(mongo_db):
    """Display the signup form."""
    st.header("📝 Sign Up")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.container(border=True):
            st.subheader("Create Your Account")
            name = st.text_input("Full Name", key="signup_name", placeholder="John Doe")
            email = st.text_input("Email", key="signup_email", placeholder="john.doe@example.com")
            password = st.text_input("Password", type="password", key="signup_password")
            
            # Password strength indicator
            if password:
                strength, feedback = check_password_strength(password)
                if strength == "weak":
                    st.warning(feedback)
                elif strength == "medium":
                    st.info(feedback)
                else:
                    st.success(feedback)
            
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")
            
            col_b1, col_b2 = st.columns([1, 1])
            with col_b1:
                if st.button("Create Account", use_container_width=True):
                    if not name or not email or not password:
                        st.error("Please fill in all fields")
                    elif password != confirm_password:
                        st.error("Passwords do not match")
                    elif len(password) < 8:
                        st.error("Password must be at least 8 characters long")
                    else:
                        with st.spinner("Creating account..."):
                            # Create new user
                            success, result = mongo_db.create_user(email, password, name)
                            if success:
                                st.success("Account created successfully! You can now login.")
                                st.session_state.auth_page = "login"
                                st.rerun()
                            else:
                                st.error(result)
    
    with col2:
        with st.container(border=True):
            st.subheader("Already a Member?")
            st.write("Login to access your documents and notebooks.")
            if st.button("Login", use_container_width=True):
                st.session_state.auth_page = "login"
                st.rerun()

def check_session(mongo_db):
    """Check for existing user session."""
    # Check for session cookie
    if 'session_id' in st.session_state:
        session_id = st.session_state.session_id
        if mongo_db:
            success, user_data = mongo_db.validate_session(session_id)
            if success:
                st.session_state.user = user_data
                return True
    
    return False

def logout_user(mongo_db):
    """Log out the current user."""
    if 'user' in st.session_state and 'session_id' in st.session_state:
        mongo_db.logout_user(st.session_state.session_id)
        # Clear user data
        st.session_state.user = None
        st.session_state.session_id = None
        st.session_state.auth_page = "login"
        st.rerun()