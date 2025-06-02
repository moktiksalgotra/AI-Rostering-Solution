import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.optimizer import RosterOptimizer
from utils.data_handler import DataHandler
import json
from datetime import datetime, timedelta
import calendar
import os
import time
import io
from dotenv import load_dotenv
import base64
from utils.chatbot import RosteringChatbot

# Load environment variables
load_dotenv()

# Define OPENROUTER_API_KEY after loading environment variables
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    st.error("OpenRouter API key not found. Please check your .env file.")
    st.stop()

# Initialize session state variables
if 'data_handler' not in st.session_state:
    st.session_state.data_handler = DataHandler()

if 'optimizer' not in st.session_state:
    st.session_state.optimizer = RosterOptimizer()

if 'roster_df' not in st.session_state:
    st.session_state.roster_df = None

if 'current_page' not in st.session_state:
    st.session_state.current_page = "🏠 Home"

if 'editing_staff_id' not in st.session_state:
    st.session_state.editing_staff_id = None

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'leave_requests' not in st.session_state:
    st.session_state.leave_requests = []

if 'chatbot' not in st.session_state:
    try:
        st.session_state.chatbot = RosteringChatbot(OPENROUTER_API_KEY, st.session_state.data_handler, st.session_state.optimizer)
    except Exception as e:
        st.error(f"Failed to initialize chatbot: {str(e)}")
        st.stop()

def format_date(date_str):
    """Format date string to a professional format with weekday."""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%A, %B %d, %Y')  # e.g., "Monday, March 25, 2024"
    except:
        return date_str

def get_short_date(date_str):
    """Format date string to a shorter format with weekday."""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%a, %b %d')  # e.g., "Mon, Mar 25"
    except:
        return date_str

def _format_staff_list(staff_list):
    """Format staff list for display in calendar view."""
    if not staff_list:
        return '<span class="no-staff">No staff assigned</span>'
    return '<br>'.join(f"• {staff}" for staff in staff_list)

# Set page config with a modern theme
st.set_page_config(
    page_title="AI Rostering Solution",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed" # Collapse sidebar by default
)

# Add this after set_page_config and before sidebar content:
st.markdown("""
<style>
section[data-testid="stSidebar"] {
    background: linear-gradient(to bottom right, rgba(30,64,175,0.1), rgba(0,0,0,0)) !important;
}
</style>
""", unsafe_allow_html=True)

# Import Lato font from Google Fonts and apply general styling
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Lato:wght@400;700&display=swap" rel="stylesheet">
<style>
body {
    font-family: 'Lato', sans-serif !important;
    background-color: var(--background);
    color: var(--text-primary);
    line-height: 1.5;
}
* {
    font-family: 'Lato', sans-serif !important;
}
/* Custom CSS for the horizontal header navigation */
.horizontal-header {
    display: flex;
    align-items: center;
    padding: 0.5rem 1rem;
    background-color: #FFFFFF;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 1rem;
}
.header-logo-container {
    display: flex;
    align-items: center;
    margin-right: 2rem;
}
.header-nav-links {
    display: flex;
    gap: 1.5rem;
}
/* Back button styling */
button[data-testid="baseButton-back_button"] {
    background: none !important; /* Remove background */
    color: #FFFFFF !important; /* White color for dark mode */
    border: 2px solid #FFFFFF !important; /* White border */
    padding: 0 !important; /* Remove padding */
    font-size: 1.5em !important; /* Adjust size */
    font-weight: 700 !important; /* Bold font weight */
    cursor: pointer;
    transition: color 0.2s ease, border-color 0.2s ease;
    width: 40px !important; /* Fixed width */
    height: 40px !important; /* Fixed height */
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    border-radius: 50% !important; /* Make it circular */
    min-width: 0 !important; /* Override min-width */
}
button[data-testid="baseButton-back_button"]:hover {
    color: #D10000 !important; /* Red on hover */
    border-color: #D10000 !important; /* Red border on hover */
    background-color: rgba(209,0,0,0.1) !important; /* Subtle red background on hover */
}
.header-nav-link button {
    background: none !important;
    color: #000000 !important; /* Black text for links */
    border: none !important;
    padding: 0 !important; /* Remove button padding */
    font-size: 1em !important;
    font-weight: 400 !important; /* Regular font weight */
    cursor: pointer;
    transition: color 0.2s ease;
}
.header-nav-link button:hover {
    color: #1e40af !important; /* Blue on hover */
    border-color: #1e40af !important; /* Blue border on hover */
    background-color: rgba(30,64,175,0.1) !important; /* Subtle blue background on hover */
}
.header-nav-link button.active {
    font-weight: 700 !important; /* Bold for active link */
    color: #1e40af !important; /* Blue color for active link */
}
</style>
""", unsafe_allow_html=True)

# Define the path to your logo image
logo_path = os.path.join("assets", "Logo Dark.png")

# Horizontal Header Navigation (using columns for better control)
header_cols = st.columns([0.3, 1, 0.3]) # Adjust column widths as needed

with header_cols[0]:
    # Logo and Title
    try:
        with open(logo_path, 'rb') as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        st.markdown("""
        <div style='display: flex; align-items: center; padding: 0rem 0rem; margin-bottom: 0rem;'>
            <img src='data:image/png;base64,{}' style='height: 100px; margin-right: -10px;'/>
            <span style='font-size: 1.9rem; font-weight: 700; color: #FFFFFF;'>QuantAI</span>
        </div>
        """.format(logo_base64), unsafe_allow_html=True)
    except FileNotFoundError:
        # Fallback to text-only header if logo is not found
        st.markdown("""
        <div style='display: flex; align-items: center; padding: 0rem 0rem; margin-bottom: 0rem;'>
            <span style='font-size: 1.9rem; font-weight: 700; color: #FFFFFF;'>QuantAI</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Navigation (Back button if not on Home) - Moved here
    if st.session_state.current_page != "🏠 Home":
        st.markdown("<div style='display: flex; justify-content: center; margin-top: 0.5rem;'>", unsafe_allow_html=True)
        if st.button("←", key="back_button", use_container_width=False):
            st.session_state.current_page = "🏠 Home"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

with header_cols[1]:
    # Placeholder for center alignment if needed, otherwise can be empty
    st.markdown("<div style='display: flex; align-items: center; height: 100%;'></div>", unsafe_allow_html=True)

with header_cols[2]:
    # Get Started Button
    # Only show the "Get Started" button on the Home page
    pass  # Removed the Get Started button from the header

# === SIDEBAR NAVIGATION ===
st.sidebar.markdown("""
    <div style='padding-top: 1.5rem; padding-bottom: 0.5rem;'>
        <span style='font-size: 1.3rem; font-weight: 800; color: #fff; letter-spacing: -1px;'>Q-Roster</span>
        <div style='font-size: 0.95rem; color: #b0b0b0; font-style: italic; margin-top: 0.2rem; margin-bottom: 1.5rem;'>
            Your intelligent scheduling partner
        </div>
    </div>
""", unsafe_allow_html=True)

sidebar_choice = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Home",
        "👥 Staff Management",
        "📅 Roster Generation",
        "📋 Leave Management",
        "💬 AI Assistant"
    ],
    index=[
        "🏠 Home",
        "👥 Staff Management",
        "📅 Roster Generation",
        "📋 Leave Management",
        "💬 AI Assistant"
    ].index(st.session_state.current_page) if "current_page" in st.session_state else 0,
    label_visibility="collapsed"
)

if sidebar_choice != st.session_state.current_page:
    st.session_state.current_page = sidebar_choice
    st.rerun()
# === END SIDEBAR NAVIGATION ===

# Conditional Page Display
if st.session_state.current_page == "🏠 Home":
    st.markdown("""
        <div class="main-title-container" style="padding: 2.5rem 2rem; margin-bottom: 2rem; text-align: center;">
            <h1 style=\"font-size: 2.8rem; letter-spacing: -0.5px; margin-bottom: 0.75rem; color: #ffffff;\">AI-Powered Rostering Solution</h1>
            <p style=\"font-size: 1.1rem; font-style: italic; color:rgb(183, 191, 202); font-weight: 400; margin-bottom: 1.5rem; max-width: 800px; margin-left: auto; margin-right: auto;\">
                Optimize your hospital's workforce with AI. Streamline staff scheduling, create efficient clinical rosters, manage leave, and gain insights for a productive environment.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Move Get Started button here
    # Center Get Started button
    # REMOVE THESE LINES
    # col1, col2, col3 = st.columns([1, 1, 1]) # Use columns for centering
    # with col2:
    #     if st.button("Get Started", key="get_started_btn", use_container_width=True):
    #         st.session_state.current_page = "📅 Roster Generation"
    #         st.rerun()

    # Static feature cards
    feature_cols = st.columns(3)
    features = [
        {"icon": "👥", "title": "Smart Staff Management", "desc": "Easily add, edit, and organize staff profiles. Filter and search with advanced criteria to find the right personnel quickly."},
        {"icon": "📅", "title": "Optimal Roster Generation", "desc": "AI-driven rostering considers skills, preferences, fairness, and operational needs to create balanced schedules."},
        {"icon": "📋", "title": "Efficient Leave Tracking", "desc": "Manage leave requests and visualize team availability with an integrated calendar and approval workflow."}
    ]
    for i, feature in enumerate(features):
        with feature_cols[i]:
            st.markdown(f"""
            <div class="metric-card" style="height: 100%; background: none; border: 1px solid rgba(255, 255, 255, 0.2); text-align: center; padding: 1.5rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="font-size: 3rem; margin-bottom: 1.25rem; color: #ffffff; text-align:center;">{feature["icon"]}</div>
                    <h3 style="color: #ffffff; margin-bottom: 1rem; font-size: 1.3rem; text-align:center;">{feature["title"]}</h3>
                </div>
                <p style="color: #e2e8f0; font-size: 0.95rem; line-height: 1.6; text-align: left; margin: 0;">{feature["desc"]}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    feature_cols2 = st.columns(3)
    features2 = [
        {"icon": "💬", "title": "AI Assistant Support", "desc": "Interact with an AI chatbot for quick answers, data insights, task automation, and operational support via text."},
        {"icon": "📤", "title": "Seamless Roster Export", "desc": "Easily export your generated rosters to Excel for sharing, reporting, and record-keeping with just one click."},
        {"icon": "📱", "title": "Modern & Responsive UI", "desc": "Enjoy a user-friendly, intuitive interface designed for ease of use and accessibility on any device."}
    ]

    for i, feature in enumerate(features2):
        with feature_cols2[i]:
            st.markdown(f"""
            <div class="metric-card" style="height: 100%; background: none; border: 1px solid rgba(255, 255, 255, 0.2); text-align: center; padding: 1.5rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; flex-direction: column; justify-content: space-between;">
                  <div>
                      <div style="font-size: 3rem; margin-bottom: 1.25rem; color: #ffffff; text-align:center;">{feature["icon"]}</div>
                      <h3 style="color: #ffffff; margin-bottom: 1rem; font-size: 1.3rem; text-align:center;">{feature["title"]}</h3>
                  </div>
                  <p style="color: #e2e8f0; font-size: 0.95rem; line-height: 1.6; text-align: left; margin: 0;">{feature["desc"]}</p>
              </div>
              """, unsafe_allow_html=True)

   

    # Create two columns for About and Benefits sections
    about_col, benefits_col = st.columns(2)
    
    with about_col:
        st.markdown("""
            <div class="about-section" style="padding: 2.5rem; margin: 1.5rem 0; border-radius: 12px; height: 100%;">
                <h2 style="font-size: 2rem; font-weight: 700; color: #ffffff; margin-bottom: 1.5rem; text-align: center;">About</h2>
                <p style="font-size: 1.1rem; line-height: 1.8; color: #e2e8f0; text-align: justify; margin-bottom: 0; font-style: italic;">
                    <strong>QuantAI's</strong> AI-Powered Rostering Solution uses advanced AI to optimize hospital staff scheduling, ensuring proper coverage across departments and shifts while balancing clinician availability, specialties, and workload—resulting in better patient care, reduced burnout, and greater efficiency.
                </p>
            </div>
        """, unsafe_allow_html=True)
    
    with benefits_col:
        st.markdown("""
            <div class="benefits-section" style="padding: 2.5rem; margin: 1.5rem 0; border-radius: 12px; height: 100%;">
                <h2 style="font-size: 2rem; font-weight: 700; color: #ffffff; margin-bottom: 1.5rem; text-align: center;">Benefits for Your Business</h2>
                <ul style="list-style: none; padding: 0; margin: 0;">
                    <li style="font-size: 1.1rem; line-height: 1.8; color: #e2e8f0; margin-bottom: 1rem; display: flex; align-items: flex-start;">
                        <span style="color: #1e40af; margin-right: 0.75rem;">✓</span>
                        Reduce scheduling time by up to 80%
                    </li>
                    <li style="font-size: 1.1rem; line-height: 1.8; color: #e2e8f0; margin-bottom: 1rem; display: flex; align-items: flex-start;">
                        <span style="color: #1e40af; margin-right: 0.75rem;">✓</span>
                        Lower labor costs through optimized staffing
                    </li>
                    <li style="font-size: 1.1rem; line-height: 1.8; color: #e2e8f0; margin-bottom: 1rem; display: flex; align-items: flex-start;">
                        <span style="color: #1e40af; margin-right: 0.75rem;">✓</span>
                        Improve employee satisfaction with fair, transparent scheduling
                    </li>
                    <li style="font-size: 1.1rem; line-height: 1.8; color: #e2e8f0; margin-bottom: 1rem; display: flex; align-items: flex-start;">
                        <span style="color: #1e40af; margin-right: 0.75rem;">✓</span>
                        Enhance customer service with properly staffed shifts
                    </li>
                </ul>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="padding: 3rem 2rem; margin-top: 2.5rem; margin-bottom: 2.5rem; text-align: center; background: #0e1d4b; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="text-align: center; color:rgb(255, 255, 255); margin-bottom: 1rem; font-size: 2rem; font-weight: 700;">Ready to Optimize Your Workforce?</h2>
    </div>
    <style>
    @keyframes bounce {
        0%, 20%, 50%, 80%, 100% {
            transform: translateY(0) rotate(45deg);
        }
        40% {
            transform: translateY(-6px) rotate(45deg);
        }
        60% {
            transform: translateY(-3px) rotate(45deg);
        }
    }
    .arrow-down:hover {
        border-color: #ffffff;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Add custom CSS for gradient buttons
    st.markdown("""
    <style>
    /* Gradient button styles */
    div[data-testid="stButton"] button {
        background: linear-gradient(to bottom right, rgba(30,64,175,0.1), rgba(0,0,0,0)) !important;
        border: 1.5px solid #1e3a8a !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        padding: 0.75rem 1.5rem !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    
    div[data-testid="stButton"] button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2) !important;
        background: linear-gradient(to bottom right, rgba(30,64,175,0.2), rgba(0,0,0,0.1)) !important;
    }
    
    /* Primary button specific styles */
    div[data-testid="stButton"] button[kind="primary"] {
        background: linear-gradient(to bottom right, rgba(30,64,175,0.2), rgba(0,0,0,0.1)) !important;
        border: 1.5px solid #1e3a8a !important;
    }
    
    /* Secondary button specific styles */
    div[data-testid="stButton"] button[kind="secondary"] {
        background: linear-gradient(to bottom right, rgba(30,64,175,0.1), rgba(0,0,0,0)) !important;
        border: 1.5px solid #1e3a8a !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # REMOVE quick links from main area (the four button columns)
    # (Remove lines from quick_links_cols = st.columns([1,1,1,1]) through the four with-blocks)

    # Centered Get Started button below the box
    get_started_col1, get_started_col2, get_started_col3 = st.columns([1,2,1])
    with get_started_col2:
        if st.button("Get Started", key="get_started_btn_home_center", use_container_width=True):
            st.session_state.current_page = "📅 Roster Generation"
            st.rerun()

elif st.session_state.current_page == "👥 Staff Management": # Staff Management Tab
    st.markdown("""
    <div style='text-align: center; margin-top: 2.5rem; margin-bottom: 2rem;'>
        <span style='font-size: 2.2rem; font-weight: 800; display: block; margin-bottom: 0.3rem; padding-left: 1.5rem; color: #FFFFFF;'>👥 Smart Staff Management</span>
        <div style='color: #B0B0B0; font-size: 1.08rem; font-style: italic; display: block; max-width: 600px; margin: 0 auto;'>
            Efficiently manage your workforce with our advanced staff management system.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Add custom CSS for the enhanced staff management UI
    st.markdown("""
    <style>
    /* Enhanced Staff Management UI Styles */
    .staff-management-container {
    }
    
    .staff-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    
    .staff-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #FFFFFF;
    }
    
    .staff-actions {
        display: flex;
        gap: 1rem;
    }
    
    .staff-filter-bar {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.5rem;
        padding: 1.5rem;
        background: rgba(255,255,255,0.05);
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .staff-card {
        background: linear-gradient(to bottom right, rgba(30,64,175,0.1), rgba(0,0,0,0));
        border: 1.5px solid #1e3a8a;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .staff-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        background: linear-gradient(to bottom right, rgba(30,64,175,0.2), rgba(0,0,0,0.1));
    }
    
    .staff-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.8rem; /* Reduced from 1rem */
    }
    
    .staff-avatar {
        width: 36px; /* Reduced from 48px */
        height: 36px; /* Reduced from 48px */
        border-radius: 50%;
        background: #1e40af;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem; /* Reduced from 1.2rem */
        font-weight: 600;
    }
    
    .staff-info {
        flex: 1;
        margin-left: 0.8rem; /* Reduced from 1rem */
    }
    
    .staff-name {
        font-size: 1.1rem; /* Reduced from 1.2rem */
        font-weight: 600;
        color: #FFFFFF;
        margin-bottom: 0.2rem; /* Reduced from 0.25rem */
    }
    
    .staff-role {
        font-size: 0.85rem; /* Reduced from 0.9rem */
        color: #B0B0B0;
    }
    
    .staff-skills {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem; /* Reduced from 0.5rem */
        margin-top: 0.8rem; /* Reduced from 1rem */
    }
    
    .skill-tag {
        background: rgba(30,64,175,0.2);
        color: #FFFFFF;
        padding: 0.3rem 0.6rem; /* Reduced from 0.4rem 0.8rem */
        border-radius: 15px;
        font-size: 0.8rem; /* Reduced from 0.85rem */
        border: 1px solid rgba(30,64,175,0.3);
    }
    
    .staff-stats {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.8rem; /* Reduced from 1rem */
        margin-top: 0.8rem; /* Reduced from 1rem */
        padding-top: 0.8rem; /* Reduced from 1rem */
        border-top: 1px solid rgba(255,255,255,0.1);
    }
    
    .stat-item {
        text-align: center;
    }
    
    .stat-value {
        font-size: 1.1rem; /* Reduced from 1.2rem */
        font-weight: 600;
        color: #FFFFFF;
    }
    
    .stat-label {
        font-size: 0.75rem; /* Reduced from 0.8rem */
        color: #B0B0B0;
    }
    
    .staff-actions {
        display: flex;
        gap: 0.5rem;
    }
    
    .action-btn {
        background: rgba(255,255,255,0.1);
        color: #FFFFFF;
        border: 1px solid rgba(255,255,255,0.2);
        padding: 0.5rem 1rem;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .action-btn:hover {
        background: rgba(255,255,255,0.2);
    }
    
    .action-btn.edit {
        background: rgba(30,64,175,0.2);
        border-color: rgba(30,64,175,0.3);
    }
    
    .action-btn.delete {
        background: rgba(220,38,38,0.2);
        border-color: rgba(220,38,38,0.3);
    }
    
    .action-btn.edit:hover {
        background: rgba(30,64,175,0.3);
    }
    
    .action-btn.delete:hover {
        background: rgba(220,38,38,0.3);
    }
    
    /* Enhanced form styling */
    .staff-form {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 2rem;
        margin-top: 2rem;
    }
    
    .form-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #FFFFFF;
        margin: 2rem 0 1.5rem 0;
        padding: 1rem 0;
        /* Removed border-bottom property */
    }
    
    .staff-form {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 2rem;
        margin: 2rem 0;
    }
    
    .form-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1.5rem;
        margin-bottom: 1.5rem;
    }
    
    .form-field {
        margin-bottom: 1.2rem;
    }
    
    .form-field label {
        display: block;
        margin-bottom: 0.5rem;
        color: #FFFFFF;
        font-weight: 500;
    }
    
    .form-actions {
        display: flex;
        justify-content: flex-end;
        gap: 1rem;
        margin-top: 2rem;
        padding-top: 1.5rem;
        border-top: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Style for form inputs */
    .stTextInput input, .stSelectbox select {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 8px !important;
        padding: 0.8rem 1rem !important;
        color: #FFFFFF !important;
        font-size: 1rem !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
    }
    
    .stTextInput input:focus, .stSelectbox select:focus {
        border-color: rgba(255,255,255,0.2) !important;
        box-shadow: none !important;
    }
    
    /* Style for multiselect */
    .stMultiSelect [data-baseweb="select"] {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 8px !important;
        padding: 0.8rem 1rem !important;
    }
    
    .stMultiSelect [data-baseweb="select"]:hover {
        border-color: rgba(255,255,255,0.2) !important;
    }
    
    .stMultiSelect [data-baseweb="select"]:focus-within {
        border-color: rgba(255,255,255,0.2) !important;
        box-shadow: none !important;
    }
    
    /* Ensure no red border on focus for specific Streamlit components */
    div[data-testid="stMultiSelect"] > div > label + div[data-baseweb="select"] > div {
        border-color: rgba(255,255,255,0.1) !important;
    }
    
    div[data-testid="stMultiSelect"] > div > label + div[data-baseweb="select"] > div:focus-within {
        border-color: rgba(255,255,255,0.2) !important;
        box-shadow: none !important;
    }
    
    /* Also target the control button div */
    div[data-testid="stMultiSelect"] > div > label + div[data-baseweb="select"] > div > div[data-baseweb="select"] {
        border-color: rgba(255,255,255,0.1) !important;
    }
    
    div[data-testid="stMultiSelect"] > div > label + div[data-baseweb="select"] > div > div[data-baseweb="select"]:focus-within {
        border-color: rgba(255,255,255,0.2) !important;
        box-shadow: none !important;
    }
    
    /* And the value container */
    div[data-testid="stMultiSelect"] > div > label + div[data-baseweb="select"] > div > div[data-baseweb="select"] > div[data-baseweb="selectvaluecontainer"] {
         border-color: rgba(255,255,255,0.1) !important;
    }
    
    div[data-testid="stMultiSelect"] > div > label + div[data-baseweb="select"] > div > div[data-baseweb="select"] > div[data-baseweb="selectvaluecontainer"]:focus-within {
         border-color: rgba(255,255,255,0.2) !important;
         box-shadow: none !important;
    }
    
    /* Style for form buttons */
    .form-submit-btn {
        padding: 0.8rem 2rem !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }
    
    .form-submit-btn.primary {
        background: #1e40af !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    
    .form-submit-btn.secondary {
        background: rgba(255,255,255,0.1) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
    }
    
    .form-submit-btn:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
    }
    
    .filter-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #FFFFFF;
        margin-bottom: 1rem;
    }

    /* Enhanced search input styling */
    .search-input {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
        padding: 0.75rem 1rem !important;
    }

    .search-input:focus {
        border-color: rgba(255,255,255,0.2) !important;
        box-shadow: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    
    
    # Header with title and actions
    st.markdown("""
    <div class='staff-header'>
        <div class='staff-title'>Staff Directory</div>
        <div class='staff-actions'>
            
    </div>
    """, unsafe_allow_html=True)

    # Filter Bar
    if st.session_state.data_handler.staff_data is not None and not st.session_state.data_handler.staff_data.empty:
        staff_df = st.session_state.data_handler.staff_data
        
        st.markdown("<div class='filter-container'>", unsafe_allow_html=True)
        
        
        filter_cols = st.columns([2, 2, 1])
        with filter_cols[0]:
            role_filter = st.multiselect(
                "Filter by Role",
                options=staff_df['role'].unique(),
                key="role_filter_multiselect"
            )
        with filter_cols[1]:
            all_skills = set()
            if 'skills' in staff_df.columns:
                for skills_list in staff_df['skills'].dropna():
                    all_skills.update([skill.strip() for skill in skills_list.split(',') if skill.strip()])
            skill_filter = st.multiselect(
                "Filter by Skills",
                options=sorted(list(all_skills)),
                key="skill_filter_multiselect"
            )
        with filter_cols[2]:
            search_query = st.text_input("Search by name...", key="search_staff_input")
        st.markdown("</div>", unsafe_allow_html=True)

        # Apply filters
        filtered_data = staff_df.copy()
        if role_filter:
            filtered_data = filtered_data[filtered_data['role'].isin(role_filter)]
        if skill_filter:
            filtered_data = filtered_data[filtered_data['skills'].apply(lambda x: any(skill_in_filter in x for skill_in_filter in skill_filter))]
        if search_query:
            filtered_data = filtered_data[filtered_data['name'].str.contains(search_query, case=False, na=False)]

        if filtered_data.empty:
            st.info("ℹ️ No staff members match the current filters.")
        else:
            # Display staff cards
            for index, staff in filtered_data.iterrows():
                staff_id = staff.get('id', index)
                initials = ''.join([name[0] for name in staff['name'].split()])
                skills_list = [skill.strip() for skill in staff['skills'].split(',') if skill.strip()]
                total_shifts = len(st.session_state.roster_df[st.session_state.roster_df['Staff'].str.contains(staff['name'], na=False)]) if st.session_state.roster_df is not None else 0

                st.markdown(f"""
                <div class='staff-card'>
                    <div class='staff-card-header'>
                        <div style='display: flex; align-items: center;'>
                            <div class='staff-avatar'>{initials}</div>
                            <div class='staff-info'>
                                <div class='staff-name'>{staff["name"]}</div>
                                <div class='staff-role'>{staff["role"]}</div>
                            </div>
                        </div>
                    </div>
                    <div class='staff-skills'>
                        {''.join([f'<span class="skill-tag">{skill}</span>' for skill in skills_list])}
                    </div>
                    <div class='staff-stats'>
                        <div class='stat-item'>
                            <div class='stat-value'>{total_shifts}</div>
                            <div class='stat-label'>Total Shifts</div>
                        </div>
                        <div class='stat-item'>
                            <div class='stat-value'>{len(skills_list)}</div>
                            <div class='stat-label'>Skills</div>
                        </div>
                        <div class='stat-item'>
                            <div class='stat-value'>{staff["role"]}</div>
                            <div class='stat-label'>Role</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Hidden buttons for edit and delete actions
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✏️", key=f"edit_{staff_id}", help="Edit staff member", type="secondary", use_container_width=True):
                        st.session_state.editing_staff_id = staff_id
                        st.rerun()
                with col2:
                    if st.button("🗑️", key=f"delete_{staff_id}", help="Delete staff member", type="secondary", use_container_width=True):
                        if st.session_state.data_handler.db.delete_staff(staff_id):
                            st.success(f"✅ Staff member {staff['name']} deleted successfully!")
                            st.session_state.data_handler.staff_data = st.session_state.data_handler.db.get_all_staff()
                            st.rerun()
                        else:
                            st.error(f"❌ Error deleting staff member {staff['name']}.")
    else:
        st.info("ℹ️ The staff directory is currently empty. Please add staff members or load data.")

    # Add/Edit Staff Form
    
    st.markdown("<div class='form-title'>🆕 Data Management</div>", unsafe_allow_html=True)
    
    if st.session_state.editing_staff_id is not None:
        staff_to_edit = staff_df[staff_df['id'] == st.session_state.editing_staff_id].iloc[0]
        submit_label = "Update Staff"
        default_name = staff_to_edit['name']
        default_role_index = ["Senior Doctor", "Doctor", "Senior Nurse", "Nurse", "Specialist"].index(staff_to_edit['role'])
        default_skills = staff_to_edit['skills'].split(',') if staff_to_edit['skills'] else []
    else:
        submit_label = "Add Staff"
        default_name = ""
        default_role_index = 0
        default_skills = []

    with st.form(key="add_edit_staff_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name", value=default_name, key="staff_name_input")
        with col2:
            role_options = ["Senior Doctor", "Doctor", "Senior Nurse", "Nurse", "Specialist"]
            role = st.selectbox("Role", options=role_options, index=default_role_index, key="staff_role_selectbox")
        
        skills_options = ["Emergency", "ICU", "General", "Surgery", "Pediatrics"]
        skills = st.multiselect("Skills (Select multiple)", options=skills_options, default=default_skills, key="staff_skills_multiselect")
        
        st.markdown("<div class='form-actions'>", unsafe_allow_html=True)
        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            submit = st.form_submit_button(submit_label, use_container_width=True)
        with btn_col2:
            cancel = st.form_submit_button("Cancel Edit", use_container_width=True) if st.session_state.editing_staff_id is not None else None
        st.markdown("</div>", unsafe_allow_html=True)

    if submit:
        if name and role and skills:
            skills_str = ','.join(skills)
            if st.session_state.editing_staff_id is not None:
                if st.session_state.data_handler.update_staff_member(
                    st.session_state.editing_staff_id, name, role, skills_str
                ):
                    st.success(f"✅ Staff member {name} updated successfully!")
                    st.session_state.editing_staff_id = None
                    st.session_state.data_handler.staff_data = st.session_state.data_handler.db.get_all_staff()
                    st.session_state.chatbot = RosteringChatbot(OPENROUTER_API_KEY, st.session_state.data_handler, st.session_state.optimizer)
                    st.rerun()
                else:
                    st.error(f"❌ Error updating staff member {name}.")
            else:
                if st.session_state.data_handler.add_staff_member(name, role, skills_str):
                    st.success(f"✅ Staff member {name} added successfully!")
                    st.session_state.data_handler.staff_data = st.session_state.data_handler.db.get_all_staff()
                    st.session_state.chatbot = RosteringChatbot(OPENROUTER_API_KEY, st.session_state.data_handler, st.session_state.optimizer)
                    st.rerun()
                else:
                    st.error(f"❌ Error adding staff member {name}.")
        else:
            st.error("❌ Please fill in all required fields (Name, Role, Skills).")
    
    if cancel:
        st.session_state.editing_staff_id = None
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # Close staff-form
    st.markdown("</div>", unsafe_allow_html=True)  # Close staff-management-container

    # Data Management Section
    st.markdown("<div class='staff-management-container' style='margin-top: 2rem;'>", unsafe_allow_html=True)

    # Add title for file uploader
    st.markdown("<div class='data-status-title'>Upload Staff Data</div>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload Staff Excel File", type=['xlsx'], label_visibility="collapsed")
    if uploaded_file is not None:
        try:
            staff_data = st.session_state.data_handler.load_staff_data(uploaded_file)
            st.success("✅ Staff data loaded successfully!")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

    # Data Status Section
    if st.session_state.data_handler.staff_data is not None:
        st.markdown("""
        <div class='data-status-container'>
            <div class='data-status-title'>Current Data Status</div>
            <div class='data-stats-grid'>
                <div class='data-stat-item'>
                    <div class='stat-value'>{}</div>
                    <div class='stat-label'>Total Staff</div>
                </div>
                <div class='data-stat-item'>
                    <div class='stat-value'>{}</div>
                    <div class='stat-label'>Unique Roles</div>
                </div>
                <div class='data-stat-item'>
                    <div class='stat-value'>{}</div>
                    <div class='stat-label'>Total Skills</div>
                </div>
            </div>
        </div>
        """.format(
            len(st.session_state.data_handler.staff_data),
            len(st.session_state.data_handler.staff_data['role'].unique()),
            len(set([s.strip() for skills in st.session_state.data_handler.staff_data['skills'] for s in skills.split(',')]))
        ), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True) # Close data-management-section
    st.markdown("</div>", unsafe_allow_html=True)  # Close staff-management-container

    # --- Role Summary Table ---
    if st.session_state.data_handler.staff_data is not None and not st.session_state.data_handler.staff_data.empty:
        staff_df = st.session_state.data_handler.staff_data
        nurse_count = staff_df[staff_df['role'].str.contains('Nurse', case=False, na=False)].shape[0]
        doctor_count = staff_df[staff_df['role'].str.contains('Doctor', case=False, na=False)].shape[0]

       

    # --- End Role Summary Table ---

elif st.session_state.current_page == "📋 Leave Management":
    st.markdown("""
    <div style='text-align: center; margin-top: 2.5rem; margin-bottom: 2rem;'>
        <span style='font-size: 2.2rem; font-weight: 800; display: block; margin-bottom: 0.3rem; padding-left: 1.5rem;'>📋 Leave Management</span>
        <div style='color: #4B5563; font-size: 1.08rem; font-style: italic; display: block; max-width: 600px; margin: 0 auto;'>
            Manage leave requests, track staff absences, and keep your roster up to date.
        </div>
    </div>
    """, unsafe_allow_html=True)
    # Initialize leave_requests in session state if not present
    if 'leave_requests' not in st.session_state:
        st.session_state.leave_requests = st.session_state.data_handler.db.get_all_leave_requests()

    # Add custom CSS for red and white theme without hover effects
    st.markdown("""
    <style>
    /* Red and white theme for Leave Management */
    .leave-container {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
    }
    
    .leave-header {
        color: #FFFFFF; /* Changed to black */
        font-weight: 700;
        margin-bottom: 15px;
        font-size: 1.2rem;
    }
    
    .leave-form {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
    }
    
    /* Red buttons */
    .leave-btn {
        background-color: #1e40af !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 4px !important;
    }
    
    /* Status tags */
    .leave-status {
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .leave-status-approved {
        background-color: #1e40af;
        color: #FFFFFF;
    }
    
    .leave-status-pending {
        background-color: #F0F0F0;
        color: #666666;
        border: 1px solid #D0D0D0;
    }
    
    .leave-status-rejected {
        background-color: #1e40af;
        color: #FFFFFF;
    }
    
    /* Leave type tags */
    .leave-type-tag {
        background-color: #F0F0F0;
        color: #1e40af;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
        border: 1px solid #1e40af;
    }
    
    /* Calendar styling */
    .leave-calendar {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 20px;
    }
    
    /* Override Streamlit button styles */
    .stButton > button {
        background-color: #1e40af !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 4px !important;
    }
    
    /* Table styling */
    .leave-table {
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        overflow: hidden;
    }
    
    .leave-table th {
        background-color: #1e40af !important;
        color: #FFFFFF !important;
    }
    
    .leave-table tr:nth-child(even) {
        background-color: #F9F9F9;
    }
    </style>
    """, unsafe_allow_html=True)

    staff_names = st.session_state.data_handler.staff_data['name'].tolist() if st.session_state.data_handler.staff_data is not None else []
    leave_types = ["Annual Leave", "Sick Leave", "Personal Leave"]

    
    st.markdown("<div class='leave-header'>📝 Submit Leave Request</div>", unsafe_allow_html=True)
    
    with st.form(key="leave_request_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            staff_member = st.selectbox("Staff Member", staff_names, key="leave_staff_select")
            leave_type = st.selectbox("Leave Type", leave_types, key="leave_type_select")
        with col2:
            start_date = st.date_input("Start Date", key="leave_start_date")
            end_date = st.date_input("End Date", key="leave_end_date")
        reason = st.text_area("Reason (optional)", key="leave_reason_input")
        submit_leave = st.form_submit_button("Submit")
        
    # Handle form submission (both manual and chatbot-triggered)
    if submit_leave or st.session_state.get('trigger_leave_submit', False):  # Allow chatbot to trigger submission
        if staff_member and leave_type and start_date and end_date:
            duration = (end_date - start_date).days + 1
            success = st.session_state.data_handler.db.add_leave_request(
                staff_member, leave_type, str(start_date), str(end_date), duration, reason
            )
            if success:
                st.success("Leave request submitted!")
                st.session_state.leave_requests = st.session_state.data_handler.db.get_all_leave_requests()
                # Clear the trigger after processing
                if 'trigger_leave_submit' in st.session_state:
                    del st.session_state.trigger_leave_submit
                st.rerun()
            else:
                st.error("Failed to submit leave request.")
        else:
            st.warning("Please fill all required fields.")
    st.markdown("</div>", unsafe_allow_html=True)

    
    st.markdown("<div class='leave-header'>📋 All Leave Requests</div>", unsafe_allow_html=True)
    
    leave_df = pd.DataFrame(st.session_state.leave_requests)
    if not leave_df.empty:
        # Format dates for display
        leave_df['start_date'] = leave_df['start_date'].apply(format_date)
        leave_df['end_date'] = leave_df['end_date'].apply(format_date)
        
        # Display leave requests in a table
        st.dataframe(
            leave_df[['staff_member', 'start_date', 'end_date', 'leave_type']],
            use_container_width=True,
            hide_index=True
        )
        
        # Action buttons for each request
        st.markdown("<div class='leave-header' style='margin-top: 20px;'>Leave Request Actions</div>", unsafe_allow_html=True)
        
        for idx, row in leave_df.iterrows():
            st.markdown(f"""
            <div class='leave-request-card' style='display: flex; align-items: center; justify-content: space-between; gap: 1.5rem; margin-bottom: 1.2rem;'>
                <div class='leave-request-info' style='flex: 1;'>
                    <strong>{row['staff_member']}</strong> - {row['leave_type']}<br>
                    {row['start_date']} to {row['end_date']}
                </div>
                <div style='flex-shrink: 0;'>
                    <form action="#" method="post" style="margin: 0;">
                        <!-- Streamlit button will render here -->
                    </form>
                </div>
            </div>
            """, unsafe_allow_html=True)
            # Place the button after the markdown so it appears in the right spot
            if st.button("🗑️", key=f"delete_{idx}", help="Delete this leave request"):
                # Delete leave request from DB
                conn = st.session_state.data_handler.db.get_connection()
                cursor = conn.cursor()
                
                # Get the original request data which has unformatted dates
                original_request_data = st.session_state.leave_requests[idx]
                
                cursor.execute('DELETE FROM leave_requests WHERE staff_member = ? AND start_date = ? AND end_date = ? AND leave_type = ?', 
                             (original_request_data['staff_member'], original_request_data['start_date'], original_request_data['end_date'], original_request_data['leave_type']))
                conn.commit()
                conn.close()
                st.session_state.leave_requests = st.session_state.data_handler.db.get_all_leave_requests()
                st.success(f"Leave request deleted.")
                st.rerun()
    else:
        st.info("No leave requests found.")
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.current_page == "📅 Roster Generation": # Roster Generation Tab
    st.markdown("""
    <div style='text-align: center; margin-top: 2.5rem; margin-bottom: 2rem;'>
        <span style='font-size: 2.2rem; font-weight: 800; display: block; margin-bottom: 0.3rem;'>📅 Roster Generation</span>
        <div style='color: #4B5563; font-size: 1.08rem; font-style: italic; display: block; max-width: 600px; margin: 0 auto;'>
            Create, optimize, and visualize your staff schedules with AI-powered rostering. Adjust constraints, review coverage, and download your optimal roster.
        </div>
    </div>
    """, unsafe_allow_html=True)
    # Roster Parameters (was in sidebar)
    st.markdown("""
    
    """, unsafe_allow_html=True)
    st.subheader("Schedule Settings")
    num_days = st.number_input("Planning Period (Days)", min_value=1, value=7)
    shifts_per_day = st.number_input("Shifts per Day", min_value=1, value=3)
    min_staff_per_shift = st.number_input("Minimum Staff per Shift", min_value=1, value=2)
    max_shifts_per_week = st.number_input("Maximum Shifts per Week", min_value=1, value=5)
    st.subheader("Optimization Preferences")
    st.checkbox("Consider Staff Preferences", value=True)
    st.checkbox("Enable Fair Distribution", value=True)
    st.checkbox("Allow Shift Swaps", value=True)

    if st.session_state.data_handler.staff_data is not None:
        # Show current constraints
        st.subheader("Current Constraints")
        constraints_col1, constraints_col2 = st.columns(2)
        with constraints_col1:
            st.markdown(f"""
            <div style='background: none; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 12px; padding: 1.5rem 1.5rem 1.2rem 1.5rem; margin-bottom: 1rem;'>
                <div style='color: #ffffff; font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem;'>📋 Roster Parameters:</div>
                <ul style='color: #e2e8f0; font-size: 1rem; margin-top: 0.5rem; margin-bottom: 0;'>
                    <li>Planning Period: {num_days} days</li>
                    <li>Shifts per Day: {shifts_per_day}</li>
                    <li>Min. Staff per Shift: {min_staff_per_shift}</li>
                    <li>Max. Shifts per Week: {max_shifts_per_week}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        with constraints_col2:
            st.markdown(f"""
            <div style='background: none; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 12px; padding: 1.5rem 1.5rem 1.2rem 1.5rem; margin-bottom: 1rem;'>
                <div style='color: #ffffff; font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem;'>👥 Staff Coverage:</div>
                <ul style='color: #e2e8f0; font-size: 1rem; margin-top: 0.5rem; margin-bottom: 0;'>
                    <li>Total Staff: {len(st.session_state.data_handler.staff_data)}</li>
                    <li>Roles: {len(st.session_state.data_handler.staff_data['role'].unique())}</li>
                    <li>Skills: {len(set([s.strip() for skills in st.session_state.data_handler.staff_data['skills'] for s in skills.split(',')]))}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("Generate Optimal Roster", key="gen_roster"):
                try:
                    # Show custom circular spinner
                    spinner_placeholder = st.empty()
                    spinner_placeholder.markdown("""
                        <div class="thinking-animation">
                            <div class="thinking-circle"></div>
                        </div>
                        <style>
                        .thinking-animation {
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            padding: 8px;
                            margin: 12px 0 24px 0;
                            width: fit-content;
                            margin-left: auto;
                            margin-right: auto;
                        }
                        .thinking-circle {
                            width: 36px;
                            height: 36px;
                            border: 3px solid rgba(30, 64, 175, 0.18);
                            border-top: 3px solid #1e40af;
                            border-radius: 50%;
                            animation: spin 0.8s linear infinite;
                        }
                        @keyframes spin {
                            0% { transform: rotate(0deg);}
                            100% { transform: rotate(360deg);}
                        }
                        </style>
                    """, unsafe_allow_html=True)
                    # Get approved leaves for the roster period
                    approved_leaves = [
                        request for request in st.session_state.leave_requests
                        if request['status'] == 'Approved'
                    ] if hasattr(st.session_state, 'leave_requests') else None
                    roster_df, success = st.session_state.optimizer.optimize_roster(
                        st.session_state.data_handler.staff_data,
                        num_days,
                        shifts_per_day,
                        min_staff_per_shift,
                        max_shifts_per_week,
                        st.session_state.data_handler.get_staff_preferences(),
                        leave_requests=approved_leaves
                    )
                    spinner_placeholder.empty()
                    if success:
                        st.session_state.roster_df = roster_df
                        st.session_state.last_update = datetime.now()
                        st.markdown('<div style="background: linear-gradient(to bottom right, rgba(30,64,175,0.1), rgba(0,0,0,0)); color: #fff; padding: 1.2rem 1.5rem; border-radius: 10px; margin-bottom: 1rem; font-size: 1.15rem; font-weight: 400; text-align: left;">✅ Roster generated successfully!</div>', unsafe_allow_html=True)
                        metrics = st.session_state.optimizer.calculate_roster_metrics(roster_df)
                        staff_on_leave = len([
                            leave for leave in approved_leaves
                            if leave['status'] == 'Approved'
                        ]) if approved_leaves else 0
                        st.markdown(f'''<div style="background: linear-gradient(to bottom right, rgba(30,64,175,0.1), rgba(0,0,0,0)); color: #fff; padding: 1.2rem 1.5rem; border-radius: 10px; margin-bottom: 1.5rem; font-size: 1.08rem; font-weight: 400; text-align: left;">
    <span style="font-size: 1.15rem; font-weight: 600; color: #fff;">📊 Roster Metrics:</span><br><br>
    Staff Utilization: <span style=\"color: #fff; font-weight: 400;\">{metrics['staff_utilization']:.1f}%</span><br>
    Coverage: <span style=\"color: #fff; font-weight: 400;\">{metrics['coverage']:.1f}%</span><br>
    Preference Satisfaction: <span style=\"color: #fff; font-weight: 400;\">{metrics['preference_satisfaction']:.1f}%</span><br>
    Staff on Leave: <span style=\"color: #fff; font-weight: 400;\">{staff_on_leave}</span>
    </div>''', unsafe_allow_html=True)
                    else:
                        error_message = getattr(st.session_state.optimizer, 'last_error', 'Unknown error occurred')
                        spinner_placeholder.empty()
                        st.error(f"""
                        ❌ Could not generate a valid roster with current constraints.
                        
                        Error details: {error_message}
                        
                        Suggested solutions:
                        1. Reduce minimum staff per shift (current: {min_staff_per_shift})
                        2. Increase maximum shifts per week (current: {max_shifts_per_week})
                        3. Add more staff members (current: {len(st.session_state.data_handler.staff_data)})
                        4. Reduce the planning period (current: {num_days} days)
                        5. Review approved leave requests that might affect staffing levels
                        """)
                except Exception as e:
                    spinner_placeholder.empty()
                    st.error(f"""
                    ❌ An error occurred while generating the roster:
                    {str(e)}
                    
                    Please try again with different parameters.
                    """)
        
        with col2:
            if st.session_state.roster_df is not None:
                # Create Excel file in memory
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    st.session_state.roster_df.to_excel(writer, index=False, sheet_name='Roster')
                    # Auto-adjust columns' width
                    worksheet = writer.sheets['Roster']
                    for idx, col in enumerate(st.session_state.roster_df.columns):
                        series = st.session_state.roster_df[col]
                        max_len = max(
                            series.astype(str).map(len).max(),  # len of largest item
                            len(str(series.name))  # len of column name/header
                        ) + 1  # adding a little extra space
                        worksheet.set_column(idx, idx, max_len)  # set column width

                st.download_button(
                    "📥 Download Roster (Excel)",
                    data=buffer.getvalue(),
                    file_name=f"roster_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.ms-excel"
                )
        
        if st.session_state.roster_df is not None:
            # Show roster in different views
            view_type = st.radio(
                "Select View",
                ["Table View", "Calendar View", "Staff View"],
                horizontal=True
            )
            
            if view_type == "Table View":
                st.subheader("Current Roster")
                
                # Create a more professional table view with formatted dates
                if st.session_state.roster_df is not None:
                    # Create a copy of the dataframe for display
                    display_df = st.session_state.roster_df.copy()
                    
                    # Add formatted date and day columns
                    display_df['Day_Name'] = pd.to_datetime(display_df['Date']).dt.strftime('%A')
                    display_df['Formatted_Date'] = display_df['Date'].apply(format_date)
                    
                    # Reorder columns for better presentation
                    display_df = display_df[[
                        'Day', 'Day_Name', 'Formatted_Date', 'Shift_Time', 
                        'Staff', 'Staff_Count'
                    ]]
                    
                    # Rename columns for display
                    display_df.columns = [
                        'Day #', 'Weekday', 'Date', 'Shift Time', 
                        'Assigned Staff', 'Staff Count'
                    ]
                    
                    # Add custom styling
                    st.markdown("""
                    <style>
                    .roster-table {
                        margin: 20px 0;
                    }
                    .stDataFrame {
                        background-color: white;
                        border-radius: 8px;
                        padding: 10px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }
                    .roster-stats {
                        display: flex;
                        gap: 20px;
                        margin-bottom: 20px;
                        flex-wrap: wrap;
                    }
                    .stat-card {
                        background: linear-gradient(to bottom right, rgba(30,64,175,0.22), rgba(0,0,0,0.18)) !important; /* Slightly darker gradient */
                        border: 1.5px solid #1e3a8a !important;
                        border-radius: 8px;
                        padding: 1rem;
                        margin-bottom: 0.8rem;
                        transition: transform 0.2s ease, box-shadow 0.2s ease;
                    }
                    .stat-card:hover {
                        transform: translateY(-2px);
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                        background: linear-gradient(to bottom right, rgba(30,64,175,0.2), rgba(0,0,0,0.1)) !important;
                    }
                    .stat-title {
                        color: #e2e8f0; /* Light text for dark background */
                        font-size: 0.9em;
                        margin-bottom: 5px;
                         font-weight: 600; /* Make title bold */
                    }
                    .stat-value {
                        color: #ffffff; /* White color for dark background */
                        font-size: 1.5em;
                        font-weight: bold;
                    }
                    </style>
                    """, unsafe_allow_html=True)

                    # Add roster statistics
                    total_shifts = len(display_df)
                    total_staff_assigned = display_df['Staff Count'].sum()
                    unique_staff = len(set([staff for staffs in display_df['Assigned Staff'].str.split(',') for staff in staffs]))
                    avg_staff_per_shift = display_df['Staff Count'].mean()

                    st.markdown("""
                    <div class="roster-stats">
                        <div class="stat-card">
                            <div class="stat-title">Total Shifts</div>
                            <div class="stat-value">{}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-title">Total Staff Assignments</div>
                            <div class="stat-value">{}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-title">Unique Staff Members</div>
                            <div class="stat-value">{}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-title">Avg. Staff per Shift</div>
                            <div class="stat-value">{:.1f}</div>
                        </div>
                    </div>
                    """.format(
                        total_shifts,
                        total_staff_assigned,
                        unique_staff,
                        avg_staff_per_shift
                    ), unsafe_allow_html=True)

                    # Display the table with custom formatting
                    st.markdown('<div class="roster-table">', unsafe_allow_html=True)
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Day #": st.column_config.NumberColumn(
                                "Day #",
                                help="Day number in the roster",
                                format="%d"
                            ),
                            "Weekday": st.column_config.Column(
                                "Weekday",
                                help="Day of the week",
                                width="medium"
                            ),
                            "Date": st.column_config.Column(
                                "Date",
                                help="Full date",
                                width="large"
                            ),
                            "Shift Time": st.column_config.Column(
                                "Shift Time",
                                help="Shift timing",
                                width="medium"
                            ),
                            "Assigned Staff": st.column_config.Column(
                                "Assigned Staff",
                                help="Staff members assigned to this shift",
                                width="large"
                            ),
                            "Staff Count": st.column_config.NumberColumn(
                                "Staff Count",
                                help="Number of staff members assigned",
                                format="%d"
                            )
                        }
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
            
            elif view_type == "Calendar View":
                st.subheader("Calendar View")
                
                # Add week navigation
                current_week_start = datetime.strptime(min(st.session_state.roster_df['Date']), '%Y-%m-%d')
                week_dates = [(current_week_start + timedelta(days=x)).strftime('%Y-%m-%d') 
                            for x in range(7)]
                
                
                
                # Group the data by day and shift
                calendar_data = {}
                for _, row in st.session_state.roster_df.iterrows():
                    date_obj = datetime.strptime(row['Date'], '%Y-%m-%d')
                    weekday = date_obj.strftime('%A')
                    day_key = f"Day {row['Day']}"
                    date_str = row['Date']
                    
                    if day_key not in calendar_data:
                        calendar_data[day_key] = {
                            'date': date_str,
                            'weekday': weekday,
                            'shifts': {
                                "Morning": {"time": "07:00-15:00", "staff": []},
                                "Evening": {"time": "15:00-23:00", "staff": []},
                                "Night": {"time": "23:00-07:00", "staff": []}
                            }
                        }
                    
                    shift_map = {
                        "07:00-15:00": "Morning",
                        "15:00-23:00": "Evening",
                        "23:00-07:00": "Night"
                    }
                    shift_key = shift_map[row['Shift_Time']]
                    staff_list = [name.strip() for name in row['Staff'].split(',')]
                    calendar_data[day_key]['shifts'][shift_key]['staff'].extend(staff_list)

                # Update CSS for calendar styling
                st.markdown("""
                <style>
                    .calendar-container {
                        margin: 20px 0;
                    }
                    .calendar-day {
                        background: linear-gradient(to bottom right, rgba(30,64,175,0.1), rgba(0,0,0,0)); /* Gradient background */
                        border: 1.5px solid #1e3a8a; /* Matching border */
                        border-radius: 12px; /* Matching border radius */
                        padding: 1.5rem; /* Consistent padding */
                        margin: 5px; /* Reduced margin */
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1); /* Matching shadow */
                        transition: box-shadow 0.2s ease, border-color 0.2s ease, transform 0.2s ease; /* Add transform to transition */
                    }
                    .calendar-day:hover {
                        box-shadow: 0 8px 16px rgba(0,0,0,0.2); /* Slightly more pronounced hover shadow */
                        border-color: #1e40af; /* Blue border on hover */
                        transform: translateY(-3px); /* Subtle upward animation */
                        background: linear-gradient(to bottom right, rgba(30,64,175,0.2), rgba(0,0,0,0.1)); /* Subtle background change on hover */
                    }
                    .day-header {
                        font-weight: 700;
                        color: #FFFFFF; /* Dark grey/black text */
                        border-bottom: 1px solid rgba(255,255,255,0.1); /* Light grey separator line */
                        padding-bottom: 10px; /* Adjusted padding */
                        margin-bottom: 10px; /* Adjusted margin */
                        text-align: center;
                        position: relative;
                    }
                    .day-header::after {
                        content: none; /* Remove the accent line below header */
                    }
                    .weekday {
                        color: #FFFFFF; /* Changed to black */
                        font-size: 1.1em; /* Slightly smaller font */
                        margin-bottom: 2px; /* Reduced margin */
                        font-weight: 700;
                    }
                    .date {
                        color: #B0B0B0; /* Grey color for date */
                        font-size: 0.9em;
                    }
                    .shift-block {
                        margin: 8px 0; /* Reduced margin */
                        padding: 10px; /* Reduced padding */
                        border-radius: 8px; /* Slightly less rounded corners */
                        transition: all 0.2s ease;
                        background: rgba(255,255,255,0.05); /* Very light grey background for shifts */
                        border: 1px solid rgba(255,255,255,0.1); /* Light grey border for shifts */
                    }
                    .shift-block:hover {
                        transform: none; /* Remove hover transform */
                        box-shadow: 0 1px 4px rgba(0,0,0,0.08); /* Subtle hover shadow */
                        border-color: #1e40af; /* Red border on hover */
                    }
                    .shift-morning {
                        /* Specific styles for morning shift if needed, otherwise inherit */
                    }
                    .shift-evening {
                         /* Specific styles for evening shift if needed, otherwise inherit */
                    }
                    .shift-night {
                        /* Specific styles for night shift if needed, otherwise inherit */
                    }
                    .shift-title {
                        font-weight: 600; /* Slightly less bold */
                        margin-bottom: 5px; /* Reduced margin */
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        color: #FFFFFF; /* Dark grey/black text */
                        font-size: 1em; /* Slightly smaller font */
                    }
                    .shift-time {
                        font-size: 0.8em; /* Smaller font size */
                        color: #B0B0B0; /* Grey color */
                    }
                    .staff-list {
                        margin-top: 5px; /* Adjusted margin */
                        font-size: 0.85em; /* Smaller font size */
                        line-height: 1.4; /* Adjusted line height */
                        color: #e2e8f0; /* Grey color */
                    }
                    .no-staff {
                        color: #B0B0B0; /* Keep grey for no staff */
                        font-style: italic;
                    }
                    .calendar-day.today { /* Highlight for current day in calendar */
                        border: 1px solid rgba(255,255,255,0.2); /* Changed to light grey border */
                        box-shadow: none; /* Remove the shadow for today highlight */
                         background: linear-gradient(to bottom right, rgba(30,64,175,0.15), rgba(0,0,0,0.05)); /* Subtle background for today */
                    }
                     .calendar-day.today:hover { /* Add hover effects for the 'Today' card */
                        border: 1px solid #1e40af; /* Red border on hover */
                        box-shadow: 0 4px 10px rgba(0,0,0,0.1); /* Subtle shadow on hover */
                        transform: translateY(-3px); /* Subtle upward animation on hover */
                         background: linear-gradient(to bottom right, rgba(30,64,175,0.25), rgba(0,0,0,0.15)); /* Subtle background change on hover */
                    }
                     .today::before { /* Style and position the 'Today' label */
                        content: "Today";
                        position: absolute;
                        top: 5px; /* Adjusted position from top */
                        right: 5px; /* Adjusted position from right */
                        background: #1e40af; /* Solid red background */
                        color: white;
                        padding: 2px 8px; /* Adjusted padding */
                        border-radius: 12px; /* Slightly less rounded pill shape */
                        font-size: 0.7em; /* Slightly smaller font */
                        font-weight: 600;
                        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* Subtle shadow */
                        z-index: 1; /* Ensure it's above other content */
                    }
                </style>
                """, unsafe_allow_html=True)

                # Create calendar grid
                num_columns = min(3, len(calendar_data))  # Show 3 days per row
                for i in range(0, len(calendar_data), num_columns):
                    cols = st.columns(num_columns)
                    for j in range(num_columns):
                        if i + j < len(calendar_data):
                            day_key = list(calendar_data.keys())[i + j]
                            day_data = calendar_data[day_key]
                            
                            # Check if this is today
                            is_today = day_data['date'] == datetime.now().strftime('%Y-%m-%d')
                            today_class = 'today' if is_today else ''
                            
                            with cols[j]:
                                st.markdown(f"""
                                <div class="calendar-day {today_class}">
                                    <div class="day-header">
                                        <div class="weekday">{day_data['weekday']}</div>
                                        <div class="date">{get_short_date(day_data['date'])}</div>
                                    </div>
                                """, unsafe_allow_html=True)

                                # Morning Shift
                                st.markdown(f"""
                                <div class="shift-block shift-morning">
                                    <div class="shift-title">
                                        <span>Morning Shift</span>
                                        <span class="shift-time">07:00-15:00</span>
                                    </div>
                                    <div class="staff-list">
                                        {_format_staff_list(day_data['shifts']['Morning']['staff'])}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                                # Evening Shift
                                st.markdown(f"""
                                <div class="shift-block shift-evening">
                                    <div class="shift-title">
                                        <span>Evening Shift</span>
                                        <span class="shift-time">15:00-23:00</span>
                                    </div>
                                    <div class="staff-list">
                                        {_format_staff_list(day_data['shifts']['Evening']['staff'])}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                                # Night Shift
                                st.markdown(f"""
                                <div class="shift-block shift-night">
                                    <div class="shift-title">
                                        <span>Night Shift</span>
                                        <span class="shift-time">23:00-07:00</span>
                                    </div>
                                    <div class="staff-list">
                                        {_format_staff_list(day_data['shifts']['Night']['staff'])}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
            
            else:  # Staff View
                st.subheader("Staff Schedule")
                # Group by staff member
                staff_list = st.session_state.data_handler.staff_data['name'].tolist()
                selected_staff = st.selectbox("Select Staff Member", staff_list)
                
                staff_schedule = st.session_state.roster_df[
                    st.session_state.roster_df['Staff'].str.contains(selected_staff, na=False)
                ]
                
                if not staff_schedule.empty:
                    # Add formatted date column
                    staff_schedule['Formatted_Date'] = staff_schedule['Date'].apply(format_date)
                    
                    # Show schedule in a more professional format with new styling
                    st.markdown("""
                    <style>
                    .staff-schedule {
                        margin: 20px 0;
                    }
                    .schedule-day {
                        background: linear-gradient(to bottom right, rgba(30,64,175,0.1), rgba(0,0,0,0)); /* Updated to gradient background */
                        padding: 15px 20px; /* Increased padding */
                        border: 1.5px solid #1e3a8a; /* Updated to matching border */
                        border-radius: 8px; /* Rounded corners */
                        margin-bottom: 12px; /* Space between cards */
                        box-shadow: 0 1px 4px rgba(0,0,0,0.05); /* Subtle shadow */
                        transition: transform 0.2s ease, box-shadow 0.2s ease; /* Add transition */
                        position: relative; /* For potential absolute positioning */
                        overflow: hidden; /* Clean corners */
                    }
                     .schedule-day::before { /* Red accent line on the left */
                        content: "";
                        position: absolute;
                        top: 0;
                        left: 0;
                        width: 5px; /* Width of the accent line */
                        height: 100%;
                        background-color: #1e40af; /* Changed to blue */
                    }
                    .schedule-day:hover {
                        transform: translateY(-3px); /* Subtle upward animation */
                        box-shadow: 0 4px 10px rgba(0,0,0,0.1); /* More pronounced shadow on hover */
                         border-color: #1e40af; /* Changed to blue border on hover */
                    }

                    .schedule-date {
                        font-weight: bold;
                        color: #FFFFFF; /* Changed to white */
                        margin-bottom: 5px;
                        font-size: 1.05em;
                        padding-left: 10px; /* Space for the accent line */
                    }
                    .schedule-shift {
                        color: #e2e8f0; /* Changed to light grey */
                        font-size: 0.95em;
                        padding-left: 10px; /* Space for the accent line */
                    }
                    /* Remove old styling */
                     .staff-schedule .schedule-day {
                        border-left: none; /* Ensure old left border is gone */
                     }
                    </style>
                    """, unsafe_allow_html=True)

                    st.markdown('<div class="staff-schedule">', unsafe_allow_html=True)
                    for _, row in staff_schedule.iterrows():
                        st.markdown(f"""
                        <div class="schedule-day">
                            <div class="schedule-date">{row['Formatted_Date']}</div>
                            <div class="schedule-shift">{row['Shift_Time']} Shift</div>
                        </div>
                        """, unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Show schedule statistics with better formatting
                    total_shifts = len(staff_schedule)
                    morning_shifts = len(staff_schedule[staff_schedule['Shift_Time'] == "07:00-15:00"])
                    evening_shifts = len(staff_schedule[staff_schedule['Shift_Time'] == "15:00-23:00"])
                    night_shifts = len(staff_schedule[staff_schedule['Shift_Time'] == "23:00-07:00"])
                    
                    st.markdown("""
                    <style>
                    .stats-container {
                        background: linear-gradient(to bottom right, rgba(30,64,175,0.1), rgba(0,0,0,0)); /* Updated background to gradient */
                        padding: 20px;
                        border-radius: 8px;
                        margin-top: 20px;
                        border: 1.5px solid #1e3a8a; /* Added border */
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1); /* Added subtle shadow */
                    }
                    .stats-header {
                        color: #ffffff; /* Changed to white */
                        font-weight: bold;
                        margin-bottom: 15px;
                    }
                    .stats-item {
                        margin: 10px 0;
                        display: flex;
                        justify-content: space-between;
                        padding: 5px 0;
                        border-bottom: 1px solid rgba(255,255,255,0.1); /* Changed to lighter separator */
                    }
                    .stats-label {
                        color: #e2e8f0; /* Changed to light grey */
                    }
                    .stats-value {
                        font-weight: bold;
                        color: #ffffff !important; /* Ensure white color with !important */
                    }
                    </style>
                    """, unsafe_allow_html=True)

                    st.markdown(f"""
                    <div class="stats-container">
                        <div class="stats-header">📊 Schedule Statistics for {selected_staff}</div>
                        <div class="stats-item">
                            <span class="stats-label">Total Shifts:</span>
                            <span class="stats-value">{total_shifts}</span>
                        </div>
                        <div class="stats-item">
                            <span class="stats-label">Shifts per Week:</span>
                            <span class="stats-value">{total_shifts / ((num_days + 6) // 7):.1f}</span>
                        </div>
                        <div class="stats-item">
                            <span class="stats-label">Morning Shifts:</span>
                            <span class="stats-value">{morning_shifts}</span>
                        </div>
                        <div class="stats-item">
                            <span class="stats-label">Evening Shifts:</span>
                            <span class="stats-value">{evening_shifts}</span>
                        </div>
                        <div class="stats-item">
                            <span class="stats-label">Night Shifts:</span>
                            <span class="stats-value">{night_shifts}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning(f"No shifts scheduled for {selected_staff}")

elif st.session_state.current_page == "💬 AI Assistant":
    st.markdown("""
    <style>
        /* Style for Streamlit's text input when focused */
        .stTextArea textarea:focus {
            border-color: #1e40af !important;
            box-shadow: 0 0 0 1px #1e40af !important;
        }

        /* Wrapper for the entire chat section on the page */
        .ai-chat-page-container {
            padding: 0;
            margin-top: -0.5rem; /* Reduced margin to remove gap */
        }

        .ai-chat-container .ai-chat-history {
            flex-grow: 1;
            padding: 15px; /* Adjusted padding */
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 15px; /* Adjusted gap */
            background: transparent; /* Remove gradient background */
            border: none; /* Remove border */
            border-radius: 0; /* Remove rounded corners */
            margin: 0; /* Remove margin outside the container */
        }
        .ai-chat-header {
            background: linear-gradient(135deg, #1e40af 0%, #1a368b 100%); /* Gradient red header */
            color: white;
            padding: 0.6rem 1rem; /* Reduced padding */
            text-align: left;
            font-size: 1.1rem; /* Slightly smaller */
            font-weight: 600;
            border-bottom: 1px solid #112d6a;
            display: flex;
            align-items: center;
        }
        .ai-chat-header-icon {
            font-size: 1.3rem; /* Slightly smaller */
            margin-right: 0.5rem; /* Reduced margin */
        }
        .ai-message-row {
            display: flex;
            align-items: flex-end;
            margin-bottom: 0.2rem;
        }
        .ai-message-row.user {
            justify-content: flex-end;
        }
        .ai-message-row.assistant {
            justify-content: flex-start;
        }
        .ai-message-bubble {
            max-width: 75vw;
            padding: 10px 15px; /* Adjusted padding */
            border-radius: 18px; /* Slightly rounded corners */
            font-size: 1em; /* Adjusted font size */
            box-shadow: none; /* Removed box shadow */
            margin-bottom: 2px;
            word-break: break-word;
            position: relative;
            line-height: 1.5;
        }
        .ai-user-message {
            background: #1e40af; /* Blue background */
            color: #fff; /* White text */
            border-radius: 18px 18px 2px 18px; /* Bubble shape */
        }
        .ai-assistant-message {
            background: rgba(255, 255, 255, 0.05); /* Subtle dark background */
            color: #e2e8f0; /* Light text color */
            border: none; /* Removed border */
            border-radius: 18px 18px 18px 2px; /* Bubble shape */
        }
        .ai-message-time {
            font-size: 0.75em; /* Adjusted font size */
            color: #999; /* Darker grey color */
            margin-top: 4px;
            margin-bottom: 2px;
            font-weight: 400;
            display: block; /* Ensure it's on its own line */
            clear: both; /* Clear any floats */
        }
        .ai-message-row.user .ai-message-time {
            text-align: right;
            margin-right: 8px;
            padding-right: 4px;
        }
        .ai-message-row.assistant .ai-message-time {
            text-align: left;
            margin-left: 8px;
            padding-left: 4px;
        }
        .ai-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: #6C47FF;
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2em;
            font-weight: 700;
            margin: 0 10px;
        }
        .ai-avatar.user {
            background: linear-gradient(135deg, #1e40af 0%, #4b6cb7 100%);
            color: #fff;
        }
        .ai-avatar.assistant {
            background: rgba(255, 255, 255, 0.1); /* Subtle dark background */
            color: #3a86ff; /* Blue color */
            border: none; /* Removed border */
        }
        /* Option buttons (suggested replies) */
        .ai-option-buttons {
            display: flex;
            gap: 0.7rem;
            margin-top: 0.7rem;
        }
        .ai-option-btn {
            background: #fff;
            color: #1e40af;
            border: 1.5px solid #1e40af;
            border-radius: 18px;
            padding: 7px 18px;
            font-size: 1em;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.15s, color 0.15s;
        }
        .ai-option-btn.selected, .ai-option-btn:hover {
            background: #1e40af;
            color: #fff;
        }

        /* Enhanced Welcome Message */
        .empty-chat-prompt-new {
            text-align: center;
            padding: 2.5rem 1.5rem;
            margin: auto;
            background: linear-gradient(to bottom right, rgba(30,64,175,0.1), rgba(0,0,0,0));
            border: 1px solid #1e3a8a;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            max-width: 70%;
        }
        .empty-chat-prompt-new h3 {
            color: #ffffff;
            margin-bottom: 1rem;
            font-weight: 700;
            font-size: 1.6rem;
        }
        .empty-chat-prompt-new p {
            color: #e2e8f0;
            margin: 0.5rem 0 0 0;
            font-size: 1.1rem;
            font-weight: 400;
            line-height: 1.6;
        }
        /* Remove list styling as it's no longer needed */
        .empty-chat-prompt-new ul {
            display: none;
        }
        /* New chat history styling */
        .chat-row {
            display: flex;
            align-items: flex-start; /* Align items to the top */
            margin-bottom: 15px; /* Increased margin */
            width: 100%;
        }
        .chat-row.user {
            flex-direction: row-reverse;
            justify-content: flex-end;
        }
        .chat-row.assistant {
            flex-direction: row;
            justify-content: flex-start;
        }
        .chat-avatar-real {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3em;
            font-weight: bold;
            margin: 0 10px; /* Adjusted margin */
            background: #e9e9e9;
            box-shadow: none; /* Removed box shadow */
            flex-shrink: 0; /* Prevent shrinking */
        }
        .chat-avatar-real.user {
            background: linear-gradient(135deg, #1e40af 0%, #4b6cb7 100%);
            color: #fff;
        }
        .chat-avatar-real.assistant {
            background: rgba(255, 255, 255, 0.1); /* Subtle dark background */
            color: #3a86ff; /* Blue color */
            border: none; /* Removed border */
        }
        .bubble {
            max-width: 70vw;
            padding: 10px 15px; /* Adjusted padding */
            border-radius: 18px; /* Slightly rounded corners */
            font-size: 1em; /* Adjusted font size */
            line-height: 1.5;
            word-break: break-word;
            position: relative;
            margin-bottom: 0; /* Removed margin */
            box-shadow: none; /* Removed box shadow */
            flex-grow: 0; /* Prevent stretching */
        }
        .chat-row.user .bubble {
            background: #1e40af; /* Blue background */
            color: #fff; /* White text */
            border-radius: 18px 18px 2px 18px; /* Bubble shape */
            margin-right: 0; /* Removed margin */
        }
        .chat-row.assistant .bubble {
            background: rgba(255, 255, 255, 0.05); /* Subtle dark background */
            color: #e2e8f0; /* Light text color */
            border: none; /* Removed border */
            border-radius: 18px 18px 18px 2px; /* Bubble shape */
            margin-left: 0; /* Removed margin */
        }
        .bubble-tail {
            display: none; /* Remove bubble tails for cleaner look */
        }
        .chat-timestamp {
            font-size: 0.75em; /* Adjusted font size */
            color: #999; /* Darker grey color */
            margin-top: 5px; /* Adjusted margin */
            margin-bottom: 0; /* Removed margin */
            padding: 0; /* Removed padding */
            opacity: 0.8;
        }
        .chat-row.user .chat-timestamp {
            text-align: right;
             margin-right: 10px; /* Adjusted margin */
        }
        .chat-row.assistant .chat-timestamp {
            text-align: left;
            margin-left: 10px; /* Adjusted margin */
        }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<div class='ai-chat-page-container'>", unsafe_allow_html=True)
    st.markdown("<div class='ai-chat-container'>", unsafe_allow_html=True)
    st.markdown("<div class='ai-chat-history' id='chat-history'>", unsafe_allow_html=True)
    if not st.session_state.chat_history:
        st.markdown("""<div class='empty-chat-prompt-new'>
                        <h3>Welcome to Q-Roster AI Assistant</h3>
                        <p>Your intelligent partner for efficient workforce scheduling and management. <br>How may I assist you today?</p>
                    </div>""", unsafe_allow_html=True)
    else:
        for message in st.session_state.chat_history:
            sender = message["role"]
            is_user = sender == "user"
            avatar = "🧑" if is_user else "🤖"
            avatar_class = "user" if is_user else "assistant"
            row_class = "user" if is_user else "assistant"
            st.markdown(f"""
            <div class='chat-row {row_class}'>
                <div class='chat-avatar-real {avatar_class}'>{avatar}</div>
                <div style='display: flex; flex-direction: column; align-items: {'flex-end' if is_user else 'flex-start'};'>
                    <div class='bubble'>
                        {message["content"]}
                        <span class='bubble-tail'></span>
                    </div>
                    <div class='chat-timestamp'>{message.get("time", "")}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Input area - structure using st.columns for better control within the flex container
    st.markdown("""
    <style>
    .ai-chat-input-row {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        gap: 0.7rem;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .ai-chat-send-btn, .ai-chat-clear-btn {
        height: 44px !important;
        min-width: 56px;
        font-size: 1.1em;
        border-radius: 8px !important;
        font-weight: 600 !important;
        box-shadow: none !important;
        padding: 0 1.5em !important;
        transition: background 0.2s, color 0.2s;
    }
    .ai-chat-send-btn {
        background: #1e40af !important;
        color: #fff !important;
        border: none !important;
    }
    .ai-chat-send-btn:hover {
        background: #1a368b !important;
        color: #fff !important;
    }
    .ai-chat-clear-btn {
        background: #fff !important;
        color: #1e40af !important;
        border: 2px solid #1e40af !important;
    }
    .ai-chat-clear-btn:hover {
        background: #f0f4ff !important;
        color: #1e40af !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Chat input area
    st.markdown("<div class='ai-chat-input-area'>", unsafe_allow_html=True)
    with st.form(key="ai_chat_form_enhanced", clear_on_submit=True):
        user_input = st.text_area(
            "Message",
            placeholder="Type your message...",
            label_visibility="collapsed",
            key="ai_user_input_enhanced_key",
            height=68 # Changed from 44 to 68 to meet minimum requirement
        )
        # Button row
        st.markdown("<div class='ai-chat-input-row'>", unsafe_allow_html=True)
        send_col, clear_col = st.columns([1,1])
        with send_col:
            send_button = st.form_submit_button(
                label="➤",
                help="Send Message",
                use_container_width=True,
                type="primary"
            )
        with clear_col:
            clear_button = st.form_submit_button(
                label="🗑️",
                help="Clear chat history",
                use_container_width=True,
                type="secondary"
            )
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Handle form submission for text input (must be outside the columns where form is defined)
    if send_button and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input.strip(), "time": datetime.now().strftime("%H:%M:%S")})
        try:
            # Custom thinking animation
            thinking_container = st.empty()
            thinking_container.markdown("""
                <div class="thinking-animation">
                    <div class="thinking-circle"></div>
                </div>
            """, unsafe_allow_html=True)
            
            response = st.session_state.chatbot.chat(user_input.strip())
            thinking_container.empty()  # Clear the thinking animation
            st.session_state.chat_history.append({"role": "assistant", "content": response, "time": datetime.now().strftime("%H:%M:%S")})
            if st.session_state.get('trigger_rerun_for_roster', False):
                st.session_state.trigger_rerun_for_roster = False
                st.success("Roster updated. Check 'Roster Generation'.")
        except Exception as e:
            thinking_container.empty()  # Clear the thinking animation
            st.session_state.chat_history.append({"role": "assistant", "content": f"Error: {str(e)}", "time": datetime.now().strftime("%H:%M:%S")})
        st.rerun()
    elif clear_button:
        st.session_state.chat_history = []
        st.rerun()
    elif send_button and not user_input.strip():
        st.warning("Please enter a message.")
        st.rerun()

# Simple footer with just "Powered by QuantAI" text
st.markdown("""
<div style="text-align: center; padding: 1.5rem 0; margin-top: 2rem; color: #ffffff;">
    <p style="font-size: 1.2em; font-family: 'Lato', sans-serif; color: #ffffff;">Powered by QuantAI</p>
</div>
""", unsafe_allow_html=True)

# === NEW STAFF DIRECTORY STYLING (RED & WHITE) ===
st.markdown("""
<style>
.new-staff-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); /* Adjusted minmax */
    gap: 1.5rem; /* Consistent gap */
    margin-top: 2rem;
}

.new-staff-card {
    background: linear-gradient(135deg, #1e40af 0%, #1a368b 100%); /* Gradient background */
    border: 1px solid rgba(255, 255, 255, 0.1); /* Subtle white border */
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    position: relative;
    overflow: hidden;
}

.new-staff-card::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 5px;
    background: linear-gradient(90deg, #3b82f6 0%, #1e40af 100%); /* Gradient accent line */
}

.new-staff-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 16px rgba(0,0,0,0.2);
}

.new-staff-header {
    display: flex;
    align-items: center;
    margin-bottom: 1rem;
    padding-top: 0.5rem;
}

.new-staff-avatar {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%); /* Gradient avatar background */
    color: #FFFFFF;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5em;
    font-weight: bold;
    margin-right: 1rem;
    border: 2px solid rgba(255, 255, 255, 0.2);
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.new-staff-info {
    flex-grow: 1;
}

.new-staff-name {
    font-size: 1.3em;
    font-weight: bold;
    color: #FFFFFF;
    margin-bottom: 0.25rem;
}

.new-staff-role {
    font-size: 1em;
    color: rgba(255, 255, 255, 0.8);
}

.new-staff-skills-section {
    margin: 1rem 0;
}

.skills-label {
    font-size: 0.9em;
    color: rgba(255, 255, 255, 0.8);
    margin-bottom: 0.5rem;
}

.new-skill-tag {
    display: inline-block;
    background: rgba(255, 255, 255, 0.1);
    color: #FFFFFF;
    padding: 0.4rem 0.8rem;
    border-radius: 15px;
    font-size: 0.85em;
    margin: 0 0.5rem 0.5rem 0;
    border: 1px solid rgba(255, 255, 255, 0.2);
}

.new-staff-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.stat-item {
    text-align: center;
}

.stat-value {
    font-size: 1.4em;
    font-weight: bold;
    color: #FFFFFF;
    margin-bottom: 0.25rem;
}

.stat-label {
    font-size: 0.8em;
    color: rgba(255, 255, 255, 0.8);
}

.new-staff-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 1rem;
}

.new-staff-actions button {
    background: rgba(255, 255, 255, 0.1);
    color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.2);
    padding: 0.5rem 1rem;
    border-radius: 5px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.new-staff-actions button:hover {
    background: rgba(15, 39, 177, 0.7);
    transform: translateY(-2px);
}
</style>
""", unsafe_allow_html=True)

# Add to the main CSS block (at the top or with other custom CSS)
st.markdown("""
<style>
.new-staff-actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid #eee;
}
.new-staff-edit-btn {
    background: #fff;
    color: #1e40af;
    border: 2px solid #1e40af;
    border-radius: 6px;
    padding: 0.6em 1.5em;
    font-size: 1em;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s, color 0.2s, box-shadow 0.2s;
    margin-right: 0.5rem;
}
.new-staff-edit-btn:hover {
    background: #1e40af;
    color: #fff;
    box-shadow: 0 2px 8px rgba(30,64,175,0.08);
}
.new-staff-delete-btn {
    background: #1e40af;
    color: #fff;
    border: 2px solid #1e40af;
    border-radius: 6px;
    padding: 0.6em 1.5em;
    font-size: 1em;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s, color 0.2s, box-shadow 0.2s;
}
.new-staff-delete-btn:hover {
    background: #fff;
    color: #1e40af;
    box-shadow: 0 2px 8px rgba(30,64,175,0.08);
}
.icon-btn {
    background: #fff;
    border: 2px solid #1e40af;
    color: #1e40af;
    border-radius: 50%;
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3em;
    font-weight: bold;
    cursor: pointer;
    transition: background 0.2s, color 0.2s, box-shadow 0.2s;
    margin-right: 0.5rem;
    outline: none;
}
.icon-btn:last-child { margin-right: 0; }
.icon-btn:hover, .icon-btn:focus {
    background: #1e40af;
    color: #fff;
    box-shadow: 0 2px 8px rgba(30,64,175,0.08);
}
.icon-btn-edit {
    /* No extra styles for now, but can be customized */
}
.icon-btn-delete {
    /* No extra styles for now, but can be customized */
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    /* Style for the Send button */
    button[data-testid="baseButton-send_btn"] {
        background-color: #1e40af !important;  /* Blue */
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.7em 2em !important;
        transition: background 0.2s;
    }
    button[data-testid="baseButton-send_btn"]:hover {
        background-color: #1a368b !important;  /* Darker blue */
        color: #fff !important;
    }

    /* Style for the Clear Chat button */
    button[data-testid="baseButton-clear_btn"] {
        background-color: #fff !important;
        color: #1e40af !important;
        border: 2px solid #1e40af !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.7em 2em !important;
        transition: background 0.2s;
    }
    button[data-testid="baseButton-clear_btn"]:hover {
        background-color: #f0f4ff !important;
        color: #1e40af !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Consolidated Style for Send and Clear Chat buttons to match "Get Started" - MORE SPECIFIC */
div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] button[data-testid="baseButton-send_btn"],
div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] button[data-testid="baseButton-clear_btn"] {
    background-color: #fff !important; /* White background */
    color: #000 !important; /* Black text */
    border: 1.5px solid #1e40af !important; /* Blue border */
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.75rem 1.5rem !important;
    transition: all 0.3s ease !important;
    box-shadow: none !important; /* Remove any default shadow */
}

/* Hover effect for both buttons - MORE SPECIFIC */
div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] button[data-testid="baseButton-send_btn"]:hover,
div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] button[data-testid="baseButton-clear_btn"]:hover {
    background-color: #f8f9fa !important; /* Very light grey/off-white on hover */
    color: #1e40af !important; /* Blue text on hover */
    border-color: #1e40af !important; /* Ensure border stays blue */
    box-shadow: 0 4px 8px rgba(30, 64, 175, 0.08) !important; /* Subtle blue-tinted shadow */
}

    /* Import Lato font from Google Fonts */
    .thinking-animation {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 8px;
        margin: 4px 0;
        width: fit-content;
    }
    
    .thinking-circle {
        width: 24px;
        height: 24px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-top: 2px solid #ffffff;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* Hide default spinner */
    .stSpinner {
        display: none !important;
    }

    /* Custom styling for st.info messages to be light blue */
    div.stAlert {
        background-color: #EEF2FF !important; /* Light blue background */
        color: #1e40af !important; /* Main blue text */
        border: 1px solid #C3DAFE !important; /* Softer blue border */
        border-left-width: 0.5rem !important; /* Keep a distinct left border */
        border-left-color: #1e40af !important; /* Main blue for left border */
        border-radius: 0.375rem !important; 
    }

    /* Ensure the icon in st.info also adapts */
    div.stAlert div[data-testid="stMarkdownContainer"] svg {
        fill: #1e40af !important; /* Change icon color to blue */
    }

    /* Ensure text within st.info is also blue */
    div.stAlert div[data-testid="stMarkdownContainer"] p {
        color: #1e40af !important; /* Main blue text for paragraphs */
    }

    /* Custom styling for the Generate Optimal Roster button */
    [data-testid="stButton"] button {
        background-color: #1e40af !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.75rem 1.5rem !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="stButton"] button:hover {
        background-color: #1a368b !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(30, 64, 175, 0.2) !important;
    }

    /* Custom styling for Streamlit tabs in Data Management */
    /* Target the container holding the tabs */
    div[data-testid="stVerticalBlock"] > div > div > div > div:nth-child(2) > div:nth-child(1) > div[data-testid="stTabs"] {
        /* Add styles for the tab container if needed */
    }

    /* Style for the individual tab buttons */
    div[data-testid="stVerticalBlock"] > div > div > div > div:nth-child(2) > div:nth-child(1) > div[data-testid="stTabs"] button {
        color: #B0B0B0 !important; /* Default tab text color - light grey for dark mode */
        background-color: transparent !important;
        border-bottom: 2px solid transparent !important;
        transition: color 0.2s ease, border-bottom-color 0.2s ease;
    }

    /* Style for the active tab button */
    div[data-testid="stVerticalBlock"] > div > div > div > div:nth-child(2) > div:nth-child(1) > div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #1e40af !important; /* Blue-800 for active tab text */
        border-bottom: 2px solid #1e40af !important; /* Blue-800 underline for active tab */
        font-weight: 600 !important;
    }

    /* Style for tab button hover */
    div[data-testid="stVerticalBlock"] > div > div > div > div:nth-child(2) > div:nth-child(1) > div[data-testid="stTabs"] button:not([aria-selected="true"]):hover {
        color: #1e40af !important; /* Blue-800 text on hover for inactive tabs */
    }

</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Make the Streamlit progress bar blue */
.stProgress > div > div > div > div {
    background-color: #1e40af !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    /* Custom blue button style for staff form */
    div[data-testid="stForm"] button[kind="primaryFormSubmit"] {
        background-color: #1e40af !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 1.5rem !important;
        font-size: 1em !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover {
        background-color: #1a368b !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(30, 64, 175, 0.2) !important;
    }
    
    /* Style for cancel button */
    div[data-testid="stForm"] button[kind="secondaryFormSubmit"] {
        background-color: #fff !important;
        color: #1e40af !important;
        border: 1.5px solid #1e40af !important;
        border-radius: 8px !important;
        padding: 0.75rem 1.5rem !important;
        font-size: 1em !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover {
        background-color: #f8f9fa !important;
        color: #1e40af !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(30, 64, 175, 0.08) !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
<style>
body {
    font-family: 'Lato', sans-serif !important;
    background-color: var(--background);
    color: var(--text-primary);
    line-height: 1.5;
}
* {
    font-family: 'Lato', sans-serif !important;
}

/* Add styles for the Data Management tabs here */
div[data-testid="stTabs"] button {
    color: #B0B0B0 !important; /* Default tab text color */
    background-color: transparent !important;
    border-bottom: 2px solid transparent !important;
    transition: color 0.2s ease, border-bottom-color 0.2s ease;
}

div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #1e40af !important; /* Changed to White */
    border-bottom: none !important;
    font-weight: 600 !important;
}

div[data-testid="stTabs"] button:not([aria-selected="true"]):hover {
    color: #1a368b !important; /* Blue-800 text on hover */
}

/* Attempt to remove the red line below tabs */
div[data-testid="stTabs"] > div:first-child {
    border-bottom: none !important;
    background-color: transparent !important;
}

/* Add styles for the Data Management section */
.data-management-section {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 2rem;
    margin-top: 2rem;
}

.data-status-container {
    margin-top: 1.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid rgba(255,255,255,0.1);
}

.data-status-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #FFFFFF;
    margin-bottom: 1rem;
}

.data-stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
}

.data-stat-item {
    background: rgba(30,64,175,0.2);
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
    border: 1px solid rgba(255, 255, 255, 0.2);
}

.data-stat-item .stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #FFFFFF !important; /* Changed to White */
    margin-bottom: 0.4rem;
}

.data-stat-item .stat-label {
    font-size: 0.85rem;
    color: #B0B0B0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Keep existing button styles */

</style>

</style>
""", unsafe_allow_html=True)

# Add this CSS styling section after the existing staff card styles
st.markdown("""
<style>
/* Modern icon button styles for staff cards */
div[data-testid="stButton"] button {
    background: rgba(255, 255, 255, 0.1) !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 8px !important;
    min-width: 44px !important;
    height: 44px !important;
    padding: 0 16px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 1.1em !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
    margin-left: 8px !important;
    position: relative !important;
    overflow: hidden !important;
}

/* Container for the buttons */
div[data-testid="stHorizontalBlock"] {
    display: flex !important;
    justify-content: flex-end !important;
    gap: 8px !important;
    margin-top: 0.5rem !important;
    padding-right: 0.5rem !important;
}

/* Edit button specific styles */
div[data-testid="stButton"] button[data-testid="baseButton-edit"] {
    background: linear-gradient(135deg, #1e40af 0%, #4b5563 100%) !important;
    border: none !important;
    color: #FFFFFF !important;
}

/* Delete button specific styles */
div[data-testid="stButton"] button[data-testid="baseButton-delete"] {
    background: linear-gradient(135deg, #1e40af 0%, #4b5563 100%) !important;
    border: none !important;
    color: #FFFFFF !important;
    opacity: 0.9 !important;
}

/* Hover effects */
div[data-testid="stButton"] button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(30, 64, 175, 0.2) !important;
    filter: brightness(1.1) !important;
    opacity: 1 !important;
}

/* Active state */
div[data-testid="stButton"] button:active {
    transform: translateY(0) !important;
    box-shadow: 0 2px 4px rgba(30, 64, 175, 0.15) !important;
    background: linear-gradient(135deg, #1e40af 0%, #374151 100%) !important;
}

/* Add tooltip effect */
div[data-testid="stButton"] button::after {
    content: attr(data-tooltip) !important;
    position: absolute !important;
    bottom: -30px !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    background: rgba(0, 0, 0, 0.8) !important;
    color: white !important;
    padding: 4px 8px !important;
    border-radius: 4px !important;
    font-size: 0.8em !important;
    white-space: nowrap !important;
    opacity: 0 !important;
    transition: opacity 0.3s ease !important;
    pointer-events: none !important;
}

div[data-testid="stButton"] button:hover::after {
    opacity: 1 !important;
}

/* Add ripple effect */
div[data-testid="stButton"] button::before {
    content: '' !important;
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    width: 0 !important;
    height: 0 !important;
    background: rgba(255, 255, 255, 0.2) !important;
    border-radius: 50% !important;
    transform: translate(-50%, -50%) !important;
    transition: width 0.3s ease, height 0.3s ease !important;
}

div[data-testid="stButton"] button:active::before {
    width: 100% !important;
    height: 100% !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Remove red border on input focus */
.stTextArea textarea:focus,
.stTextInput input:focus,
.stSelectbox select:focus,
.stMultiSelect [data-baseweb="select"]:focus-within {
    border-color:rgba(255, 0, 0, 0.66) !important;
    box-shadow: 0 0 0 1pxrgba(255, 0, 0, 0.72) !important;
}

/* Remove red border from all Streamlit inputs */
.stTextArea textarea,
.stTextInput input,
.stSelectbox select,
.stMultiSelect [data-baseweb="select"] {
    border-color: rgba(255,255,255,0.1) !important;
}

/* Remove red border from Streamlit components */
div[data-testid="stTextInput"] > div > div > input,
div[data-testid="stTextArea"] > div > div > textarea,
div[data-testid="stSelectbox"] > div > div > div,
div[data-testid="stMultiSelect"] > div > div > div {
    border-color: rgba(255,255,255,0.1) !important;
}

/* Focus state for Streamlit components */
div[data-testid="stTextInput"] > div > div > input:focus,
div[data-testid="stTextArea"] > div > div > textarea:focus,
div[data-testid="stSelectbox"] > div > div > div:focus-within,
div[data-testid="stMultiSelect"] > div > div > div:focus-within {
    border-color:rgba(255, 0, 0, 0.66) !important;
    box-shadow: 0 0 0 1pxrgba(255, 0, 0, 0.72) !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Ensure the main container of the chat text area is blue */
div[data-testid="stTextarea"] {
    border: 1px solid #1e40af !important; /* Blue border for the container */
    border-radius: 8px !important; /* Match the desired radius */
    box-shadow: none !important; /* Remove any default box shadow */
}

/* Ensure the border stays blue and add glow on focus-within */
div[data-testid="stTextarea"]:focus-within {
    border-color: #1e40af !important; /* Blue border on focus */
    box-shadow: 0 0 0 0.2rem rgba(30,64,175,0.25) !important; /* Subtle blue glow on focus */
}

/* Remove any potentially conflicting red borders on the textarea element itself */
.stTextArea textarea {
    border: none !important;
    box-shadow: none !important;
}

/* Ensure focus styles on the textarea itself don't add red */
.stTextArea textarea:focus {
    border: none !important;
    box-shadow: none !important;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Existing styles ... */

/* Roster Generation Page Styles */
.roster-header {
    font-size: 1.5rem;
    font-weight: 600;
    color: #ffffff;
    margin: 2rem 0 1rem 0;
    padding: 0.5rem 0;
    border-bottom: 2px solid #1e40af;
}

.metrics-container {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin: 2rem 0;
}

.metric-card {
    background: linear-gradient(to bottom right, rgba(30,64,175,0.1), rgba(0,0,0,0)) !important;
    border: 1.5px solid #1e3a8a !important;
    text-align: center;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px rgba(0,0,0,0.2);
    background: linear-gradient(to bottom right, rgba(30,64,175,0.2), rgba(0,0,0,0.1)) !important;
}

.metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 0.5rem;
}

.metric-label {
    font-size: 1rem;
    color: #e2e8f0;
}

/* Form styles */
div[data-testid="stForm"] {
    background: linear-gradient(to bottom right, rgba(30,64,175,0.05), rgba(0,0,0,0));
    border: 1px solid #1e3a8a;
    border-radius: 12px;
    padding: 2rem;
    margin: 1rem 0;
}

/* Number input styles */
div[data-testid="stNumberInput"] input {
    background-color: rgba(30,64,175,0.1) !important;
    border: 1px solid #1e3a8a !important;
    color: #ffffff !important;
}

/* Button styles */
div[data-testid="stForm"] button {
    background: linear-gradient(to bottom right, rgba(30,64,175,0.2), rgba(0,0,0,0.1)) !important;
    border: 1.5px solid #1e3a8a !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    padding: 0.75rem 1.5rem !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
}

div[data-testid="stForm"] button:hover {
    background: linear-gradient(to bottom right, rgba(30,64,175,0.3), rgba(0,0,0,0.2)) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 8px rgba(30,64,175,0.2) !important;
}

/* Export button styles */
div[data-testid="stButton"] button {
    background: linear-gradient(to bottom right, rgba(30,64,175,0.1), rgba(0,0,0,0)) !important;
    border: 1.5px solid #1e3a8a !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    padding: 0.75rem 1.5rem !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
}

div[data-testid="stButton"] button:hover {
    background: linear-gradient(to bottom right, rgba(30,64,175,0.2), rgba(0,0,0,0.1)) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 8px rgba(30,64,175,0.2) !important;
}

/* Dataframe styles */
div[data-testid="stDataFrame"] {
    background: linear-gradient(to bottom right, rgba(30,64,175,0.05), rgba(0,0,0,0));
    border: 1px solid #1e3a8a;
    border-radius: 12px;
    padding: 1rem;
    margin: 1rem 0;
}

/* Download button styles */
div[data-testid="stDownloadButton"] button {
    background: linear-gradient(to bottom right, rgba(30,64,175,0.1), rgba(0,0,0,0)) !important;
    border: 1.5px solid #1e3a8a !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    padding: 0.75rem 1.5rem !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
}

div[data-testid="stDownloadButton"] button:hover {
    background: linear-gradient(to bottom right, rgba(30,64,175,0.2), rgba(0,0,0,0.1)) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 8px rgba(30,64,175,0.2) !important;
}
</style>
""", unsafe_allow_html=True)