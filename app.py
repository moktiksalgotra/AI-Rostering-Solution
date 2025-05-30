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

# Load environment variables
load_dotenv()

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
    initial_sidebar_state="expanded"
)

# Modern UI CSS styling
st.markdown("""
    <style>
        /* Import Lato font from Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700;900&display=swap');
        
        /* Base Theme */
        :root {
            --primary: #6366F1;
            --primary-light: #818CF8; 
            --primary-dark: #4F46E5;
            --secondary: #10B981;
            --accent: #F59E0B;
            --background: #F9FAFB;
            --card: #FFFFFF;
            --text-primary: #1F2937;
            --text-secondary: #4B5563;
            --text-tertiary: #9CA3AF;
            --border: #E5E7EB;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            --radius-sm: 0.25rem;
            --radius-md: 0.5rem;
            --radius-lg: 1rem;
        }
        
        /* Base Styles */
        body {
            font-family: 'Lato', sans-serif !important;
            background-color: var(--background);
            color: var(--text-primary);
            line-height: 1.5;
        }
        
        /* Apply Lato font to all elements */
        * {
            font-family: 'Lato', sans-serif !important;
        }
        
        .main {
            padding: 1.5rem;
            max-width: 1280px;
            margin: 0 auto;
        }
        
        .block-container {
            padding: 0;
            max-width: 100%;
        }
        
        /* Card Component */
        .card {
            background: var(--card);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-md);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid var(--border);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }
        
        /* Dashboard Grid Layout */
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        /* Sidebar Styling */
        .sidebar .sidebar-content {
            /* background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%); */
            background-color: #D10000; /* Red background */
            color: #FFFFFF; /* White text */
            padding: 1.5rem 1rem; /* Adjusted padding */
            height: 100vh;
            border-right: 1px solid #E0E0E0; /* Subtle border to separate from main content */
        }
        
        /* Sidebar Header */
        .sidebar .sidebar-content h1, .sidebar-main-title /* Target both potential h1 elements */
         {
            color: #000000 !important; /* Black text */
            font-weight: 700 !important;
            text-align: left !important; /* Align to left for a cleaner look */
            margin-bottom: 0.25rem !important; /* Reduced margin */
            padding-bottom: 0 !important;
            font-size: 1.6rem !important; /* Slightly adjusted size */
            border-bottom: none !important; /* Ensure no border */
        }

        /* Styling for the subtitle in the sidebar */
        .sidebar .sidebar-content p[style*="intelligent scheduling partner"] /* More specific selector for subtitle */
        {
            text-align: left !important; /* Align to left */
            color: #FFFFFF !important; /* White text */
            margin-top: 0rem !important;
            margin-bottom: 1.75rem !important; /* Increased bottom margin for separation */
            font-size: 0.85rem !important; /* Slightly smaller */
        }
        
        .sidebar .sidebar-content h1::after, .sidebar-main-title::after /* Also target the h1 in markdown */
        {
            display: none !important; /* Forcefully hide the ::after pseudo-element for sidebar h1 */
        }
        
        /* Override for sidebar h1 - remove the blue line */
        .sidebar h1:after {
            display: none !important;
            content: none !important;
            background: none !important;
        }
        
        /* Remove blue line from sidebar navigation radio buttons */
        .sidebar [data-testid="stRadio"] {
            border: none !important;
        }
        
        .sidebar [data-testid="stRadio"] label {
            border: none !important;
        }
        
        .sidebar [data-testid="stRadio"] label:after {
            display: none !important;
            content: none !important;
            background: none !important;
            border: none !important;
        }
        
        /* Remove any blue line from the sidebar navigation section */
        .sidebar .stRadio::after,
        .sidebar .stRadio::before,
        .sidebar .stRadio div::after,
        .sidebar .stRadio div::before {
            display: none !important;
            content: none !important;
            background: none !important;
            border: none !important;
        }
        
        /* Sidebar Controls */
        .sidebar .sidebar-content .stTextInput input,
        .sidebar .sidebar-content .stSelectbox div[data-baseweb="select"] > div,
        .sidebar .sidebar-content .stMultiSelect div[data-baseweb="select"] > div,
        .sidebar .sidebar-content .stDateInput div[data-baseweb="input"] > div,
        .sidebar .sidebar-content .stNumberInput input {
            border: none;
            border-radius: var(--radius-md);
            background: rgba(255,255,255,0.2); /* Slightly lighter background for contrast */
            color: #FFFFFF; /* White text */
            border: 1px solid rgba(255,255,255,0.3); /* Light border */
            transition: all 0.2s ease;
        }
        
        .sidebar .sidebar-content .stTextInput input:focus,
        .sidebar .sidebar-content .stSelectbox div[data-baseweb="select"] > div:focus-within,
        .sidebar .sidebar-content .stMultiSelect div[data-baseweb="select"] > div:focus-within,
        .sidebar .sidebar-content .stDateInput div[data-baseweb="input"] > div:focus-within,
        .sidebar .sidebar-content .stNumberInput input:focus {
            background: rgba(255,255,255,0.25);
            box-shadow: 0 0 0 2px rgba(255,255,255,0.4); /* Light glow */
            border-color: rgba(255,255,255,0.5); /* Brighter border on focus */
        }
        
        .sidebar .sidebar-content label {
            color: #FFFFFF; /* White text */
            font-weight: 500;
            font-size: 0.875rem;
        }
        
        /* Sidebar Button */
        .sidebar .sidebar-content .stButton > button {
            background: var(--accent);
            color: white;
            border: none;
            border-radius: var(--radius-md);
            padding: 0.625rem 1.25rem;
            font-weight: 600;
            width: 100%;
            transition: all 0.2s ease;
            margin-top: 1rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .sidebar .sidebar-content .stButton > button:hover {
            background: #E68A00;
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0,0,0,0.15);
        }
        
        .sidebar .sidebar-content .stButton > button:active {
            transform: translateY(0);
        }
        
        /* Main Content Header */
        h1, h2, h3, h4, h5, h6 {
            color: var(--text-primary);
            font-weight: 700;
            margin-bottom: 1rem;
        }
        
        h1 {
            font-size: 2rem;
            position: relative;
            padding-bottom: 0.75rem;
        }
        
        h1:after {
            display: none !important;
            content: none !important;
            background: none !important;
        }
        
        h2 {
            font-size: 1.5rem;
            color: var(--text-primary);
        }
        
        h3 {
            font-size: 1.25rem;
            color: var(--text-secondary);
        }
        
        /* Tabs */
        div[data-baseweb="tabs"] {
            background-color: var(--card);
            border-radius: var(--radius-lg);
            padding: 0.5rem;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border);
            margin-bottom: 1.5rem;
        }
        
        div[data-baseweb="tabs"] button[role="tab"] {
            background-color: transparent;
            color: var(--text-secondary);
            border-radius: var(--radius-md);
            padding: 0.625rem 1rem;
            font-weight: 500;
            transition: all 0.15s ease;
            margin: 0 0.25rem;
            border: none;
        }
        
        div[data-baseweb="tabs"] button[role="tab"]:hover {
            background-color: rgba(99, 102, 241, 0.05);
            color: var(--primary);
        }
        
        div[data-baseweb="tabs"] button[role="tab"][aria-selected="true"] {
            background-color: var(--primary);
            color: white;
            font-weight: 600;
        }
        
        div[data-baseweb="tab-list"] {
            border-bottom: none;
        }
        
        div[data-baseweb="tab-highlight"] {
            display: none;
        }
        
        /* Data Tables */
        .dataframe {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
            margin-bottom: 1.5rem;
            border-radius: var(--radius-md);
            overflow: hidden;
            box-shadow: var(--shadow-sm);
        }
        
        .dataframe thead tr {
            background-color: var(--primary);
            color: white;
            text-align: left;
            font-weight: 600;
        }
        
        .dataframe th, .dataframe td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
        }
        
        .dataframe tbody tr {
            transition: background-color 0.15s ease;
        }
        
        .dataframe tbody tr:nth-of-type(odd) {
            background-color: rgba(99, 102, 241, 0.05);
        }
        
        .dataframe tbody tr:hover {
            background-color: rgba(99, 102, 241, 0.1);
        }
        
        /* Calendar View */
        .calendar-view {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 0.5rem;
            margin-bottom: 2rem;
        }
        
        .calendar-day {
            background-color: #FFFFFF; /* White background */
            border: 1px solid #E0E0E0; /* Light grey border */
            border-radius: 8px; /* Slightly less rounded */
            padding: 15px; /* Consistent padding */
            margin: 5px; /* Reduced margin */
            box-shadow: 0 1px 5px rgba(0,0,0,0.05); /* Softer shadow */
            transition: box-shadow 0.2s ease, border-color 0.2s ease, transform 0.2s ease; /* Add transform to transition */
        }
        
        .calendar-day:hover {
            box-shadow: 0 4px 10px rgba(0,0,0,0.1); /* Slightly more pronounced hover shadow */
            border-color: #D10000; /* Red border on hover */
            transform: translateY(-3px); /* Subtle upward animation */
        }
        
        .calendar-day-header {
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: var(--text-primary);
            padding-bottom: 0.25rem;
            border-bottom: 1px solid var(--border);
        }
        
        .calendar-day.today {
            border: 1px solid #E0E0E0; /* Light grey border */
            background-color: rgba(99, 102, 241, 0.05);
        }
        
        .no-staff {
            color: var(--text-tertiary);
            font-style: italic;
        }
        
        /* Buttons */
        .stButton > button {
            background-color: var(--primary);
            color: white;
            border: none;
            border-radius: var(--radius-md);
            padding: 0.625rem 1.25rem;
            font-weight: 600;
            transition: all 0.2s ease;
            height: auto;
        }
        
        .stButton > button:hover {
            background-color: var(--primary-dark);
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }
        
        .stButton > button:active {
            transform: translateY(0);
        }
        
        /* Secondary Button */
        .secondary-button > button {
            background-color: white;
            color: var(--primary);
            border: 1px solid var(--primary);
        }
        
        .secondary-button > button:hover {
            background-color: rgba(99, 102, 241, 0.05);
            color: var(--primary-dark);
            border-color: var(--primary-dark);
        }
        
        /* Badge/Tag Component */
        .badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            font-size: 0.75rem;
            font-weight: 600;
            border-radius: 9999px;
            margin-right: 0.5rem;
        }
        
        .badge-primary {
            background-color: rgba(99, 102, 241, 0.1);
            color: var(--primary);
        }
        
        .badge-success {
            background-color: rgba(16, 185, 129, 0.1);
            color: var(--secondary);
        }
        
        .badge-warning {
            background-color: rgba(245, 158, 11, 0.1);
            color: var(--accent);
        }
        
        /* Metrics/KPI Cards */
        .metric-card {
            text-align: center;
            padding: 1.5rem;
            border-radius: var(--radius-lg);
            background: white;
            box-shadow: var(--shadow-md);
            border: 1px solid var(--border);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .metric-card:hover {
            transform: translateY(-3px);
            box-shadow: var(--shadow-lg);
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 0.5rem;
            line-height: 1;
        }
        
        .metric-label {
            font-size: 0.875rem;
            color: var(--text-secondary);
            margin-bottom: 0.25rem;
        }
        
        .metric-change {
            font-size: 0.75rem;
            font-weight: 500;
            padding: 0.125rem 0.5rem;
            border-radius: 9999px;
            display: inline-block;
        }
        
        .metric-change.positive {
            background-color: rgba(16, 185, 129, 0.1);
            color: var(--secondary);
        }
        
        .metric-change.negative {
            background-color: rgba(239, 68, 68, 0.1);
            color: #EF4444;
        }
        
        /* Mobile Responsiveness */
        @media screen and (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
            
            .calendar-view {
                grid-template-columns: repeat(1, 1fr);
            }
            
            .main {
                padding: 1rem;
            }
        }
        
        div[data-baseweb="tab-panel"] {
            padding: 1rem 0.5rem;
        }

        /* Input Fields (General) */
        .stTextInput input, .stNumberInput input, .stDateInput input,
        .stSelectbox div[data-baseweb="select"] > div, .stMultiselect div[data-baseweb="select"] > div,
        .stTextArea textarea {
            border-radius: 5px;
            border: 1px solid #ced4da; /* Standard border color */
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }
        .stTextInput input:focus, .stNumberInput input:focus, .stDateInput input:focus,
        .stSelectbox div[data-baseweb="select"] > div:focus-within,
        .stMultiselect div[data-baseweb="select"] > div:focus-within,
        .stTextArea textarea:focus {
            border-color: #D10000 !important; /* Red on focus */
            box-shadow: 0 0 0 0.2rem rgba(209, 0, 0, 0.25) !important; /* Red focus ring */
        }


        /* Staff Form - Modern and user-friendly */
        .staff-form {
            background: linear-gradient(135deg, #f8faff 0%, #f0f7ff 100%);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.05), 0 5px 15px rgba(0,0,0,0.03);
            margin: 25px 0;
            border: 1px solid rgba(222, 226, 230, 0.7);
            position: relative;
            overflow: hidden;
        }
        .staff-form::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            height: 4px;
            width: 100%;
            background: none; /* Removed blue gradient */
        }
        /* Improved form inputs */
        .staff-form .stTextInput input, 
        .staff-form .stSelectbox div[data-baseweb="select"] > div,
        .staff-form .stMultiselect div[data-baseweb="select"] > div {
            border-radius: 8px;
            padding: 10px 15px;
            border: 2px solid #e0e7ff;
            background-color: rgba(255, 255, 255, 0.8);
            transition: all 0.2s ease;
            box-shadow: 0 2px 5px rgba(0,0,0,0.02);
        }
        .staff-form .stTextInput input:focus,
        .staff-form .stSelectbox div[data-baseweb="select"] > div:focus-within,
        .staff-form .stMultiselect div[data-baseweb="select"] > div:focus-within {
            border-color: #3a86ff;
            background-color: white;
            box-shadow: 0 0 0 3px rgba(58, 134, 255, 0.15);
            transform: translateY(-1px);
        }
        .staff-form .stTextInput label,
        .staff-form .stSelectbox label,
        .staff-form .stMultiselect label {
            font-weight: 600;
            color: #0a2540;
            font-size: 1em;
            margin-bottom: 5px;
            letter-spacing: 0.3px;
        }
        .staff-table {
            margin: 20px 0;
        }
        .staff-table .stContainer { /* Each staff item container */
            background-color: #ffffff;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 15px;
            border: 1px solid #e9ecef;
        }
        .staff-actions {
            display: flex;
            gap: 10px;
            align-items: center; /* Align buttons vertically */
        }
        .staff-actions .stButton button {
            width: auto; /* Override full width for action buttons */
            padding: 0.4em 0.8em;
            height: auto;
            font-size: 0.9em;
        }
        .edit-button, .stButton button:contains("✏️ Edit") { /* Target by text if specific class isn't rendered */
            background-color: #28a745; /* Red */
        }
        .edit-button:hover, .stButton button:contains("✏️ Edit"):hover {
            background-color: #218838; /* Red */
        }
        .delete-button, .stButton button:contains("🗑️ Delete") { /* Target by text */
            background-color: #dc3545; /* Red */
        }
        .delete-button:hover, .stButton button:contains("🗑️ Delete"):hover {
            background-color: #c82333; /* Red */
        }

        /* Roster Table styling */
        .roster-table .stDataFrame {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            border: 1px solid #e9ecef;
        }
        .roster-stats {
            display: flex;
            gap: 25px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        .stat-card {
            background: linear-gradient(135deg, #ffffff 0%, #f9fbff 100%);
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.06), 0 3px 10px rgba(0,0,0,0.03);
            flex: 1;
            min-width: 220px;
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
            border: 1px solid rgba(222, 226, 230, 0.7);
        }
        .stat-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 6px;
            height: 100%;
            background: none; /* Removed blue gradient */
            border-radius: 12px 0 0 12px;
        }
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.08), 0 5px 15px rgba(0,0,0,0.05);
        }
        .stat-title {
            color: #5a677d;
            font-size: 1em;
            margin-bottom: 12px;
            font-weight: 600;
            letter-spacing: 0.3px;
            padding-left: 8px;
        }
        .stat-value {
            color: #0a2540;
            font-size: 2em;
            font-weight: 800;
            letter-spacing: 0.5px;
            padding-left: 8px;
            text-shadow: 0 2px 3px rgba(0,0,0,0.05);
        }

        /* Calendar View Styling - Modern and elegant */
        .calendar-day {
            background: linear-gradient(135deg, #ffffff 0%, #fcfcff 100%); /* Subtle gradient */
            border: none;
            border-radius: 12px;
            padding: 20px;
            margin: 8px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.05), 0 3px 6px rgba(0,0,0,0.02);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        .calendar-day:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.08), 0 5px 15px rgba(0,0,0,0.04);
        }
        .day-header {
            font-weight: 700;
            color: #0a2540; /* Dark navy */
            border-bottom: none;
            padding-bottom: 12px;
            margin-bottom: 15px;
            text-align: center;
            position: relative;
        }
        .day-header::after {
            content: "";
            position: absolute;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 50px;
            height: 3px;
            background: none; /* Removed blue gradient */
            border-radius: 3px;
        }
        .weekday {
            color: #0a2540;
            font-size: 1.3em;
            margin-bottom: 5px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .date {
            color: #5a677d;
            font-size: 0.95em;
        }
        .shift-block {
            margin: 15px 0;
            padding: 15px;
            border-radius: 10px;
            transition: all 0.25s ease;
            box-shadow: 0 3px 10px rgba(0,0,0,0.04);
            border: none;
        }
        .shift-block:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.08);
        }
        .shift-morning {
            background: linear-gradient(135deg, #fffbea 0%, #fff8e1 100%);
            border-left: 5px solid #FF9E00; /* Rich amber */
        }
        .shift-evening {
            background: linear-gradient(135deg, #e8f4ff 0%, #e3f2fd 100%);
            border-left: none; /* Removed blue border */
        }
        .shift-night {
            background: linear-gradient(135deg, #f3eeff 0%, #ede7f6 100%);
            border-left: 5px solid #8B5CF6; /* Rich purple */
        }
        .shift-title {
            font-weight: 700;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #0a2540;
            font-size: 1.05em;
            letter-spacing: 0.3px;
        }
        .shift-time {
            font-size: 0.85em;
            color: #5a677d;
            font-weight: 600;
            background-color: rgba(255, 255, 255, 0.5);
            padding: 3px 8px;
            border-radius: 12px;
        }
        .staff-list {
            margin-top: 8px;
            font-size: 0.92em;
            line-height: 1.6;
            color: #333;
        }
        .staff-list span {
            transition: all 0.2s ease;
        }
        .staff-list span:hover {
            color: #3a86ff;
            font-weight: 600;
        }
        .no-staff {
            color: #888;
            font-style: italic;
            background-color: rgba(0, 0, 0, 0.03);
            padding: 5px 10px;
            border-radius: 5px;
            display: inline-block;
        }
        .today { /* Highlight for current day in calendar */
            border: none;
            box-shadow: 0 0 0 2px #FF9E00, 0 10px 25px rgba(255, 158, 0, 0.2);
            position: relative;
        }
        .today::before {
            content: "Today";
            position: absolute;
            top: -10px;
            right: 10px;
            background: linear-gradient(90deg, #FF9E00 0%, #FF7A00 100%);
            color: white;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: 600;
            box-shadow: 0 3px 8px rgba(255, 158, 0, 0.3);
        }

        /* Staff Schedule (in Staff View) */
        .staff-schedule {
            margin: 20px 0;
        }
        .schedule-day {
            padding: 12px 15px;
            border-left: none; /* Removed blue border */
            margin-bottom: 15px;
            background-color: white;
            border-radius: 6px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.07);
        }
        .schedule-date {
            font-weight: bold;
            color: #000000; /* Changed to black */
            margin-bottom: 5px;
            font-size: 1.05em;
        }
        .schedule-shift {
            color: #000000; /* Changed to black */
            font-size: 0.95em;
        }
        .stats-container { /* For staff schedule stats */
            background-color: #f8f9fa; /* Changed to light grey */
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
            border: 1px solid #e0e0e0; /* Changed to light grey border */
        }
        .stats-header {
            color: #333333; /* Changed to dark grey/black */
            font-weight: bold;
            margin-bottom: 15px;
            font-size: 1.1em;
        }
        .stats-item {
            margin: 10px 0;
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #cccccc; /* Changed to grey separator */
        }
        .stats-item:last-child {
            border-bottom: none;
        }
        .stats-label {
            color: #555555; /* Changed to grey */
        }
        .stats-value {
            font-weight: bold;
            color: #D10000; /* Changed to red */
        }

        /* Leave Management Styling */
        .leave-container {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            margin: 15px 0;
            border: 1px solid #e9ecef;
        }
        .leave-form {
            background-color: #f8f9fa; /* Light grey for form background */
            padding: 25px;
            border-radius: 8px;
            margin: 20px 0;
            border: 1px solid #e0e0e0;
        }
        .leave-calendar {
            margin: 20px 0;
        }
        .leave-status-approved {
            color: #28a745; /* Green */
            font-weight: bold;
        }
        .leave-status-pending {
            color: #ffc107; /* Yellow */
            font-weight: bold;
        }
        .leave-status-rejected {
            color: #dc3545; /* Red */
            font-weight: bold;
        }
        .leave-type-tag {
            padding: 5px 10px;
            border-radius: 15px; /* Pill shape */
            font-size: 0.85em;
            margin-right: 8px;
            font-weight: 500;
            color: white; /* Default white text */
        }
        .annual-leave {
            background-color: #17a2b8; /* Teal */
        }
        .sick-leave {
            background-color: #fd7e14; /* Orange */
        }
        .personal-leave {
            background-color: #6f42c1; /* Purple */
        }

        /* Chat UI Styling */
        .chat-container {
            background-color: #f9f9f9; /* Light grey, slightly different from page bg */
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            margin-bottom: 20px;
            border: 1px solid #e0e0e0;
        }
        .chat-message {
            display: flex;
            align-items: flex-start;
            margin-bottom: 15px;
            clear: both;
        }
        .chat-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            margin-right: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            color: white;
        }
        .assistant-avatar {
            background-color: #0074D9; /* Bright Blue */
        }
        .user-avatar {
            background-color: #FF851B; /* Orange */
            margin-left: 12px; /* For user messages aligned right */
            margin-right: 0;
        }
        .user-bubble {
            background-color: #0074D9; /* Bright Blue */
            color: white;
            padding: 10px 15px; /* Adjusted padding */
            border-radius: 18px 18px 5px 18px; /* Adjusted for a slightly softer look */
            margin: 5px 0;
            max-width: 80%;
            float: right;
            clear: both;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .assistant-bubble {
            background: #e9ecef; /* Light grey for assistant */
            color: #212529; /* Dark text */
            padding: 10px 15px; /* Adjusted padding */
            border-radius: 18px 18px 18px 5px; /* Adjusted for a slightly softer look */
            margin: 5px 0;
            max-width: 80%;
            float: left;
            clear: both;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .message-content-container { /* New container for bubble and time */
            display: flex;
            flex-direction: column;
        }
        .user-message .message-content-container {
            align-items: flex-end; /* Align time to the right for user */
        }
        .assistant-message .message-content-container {
            align-items: flex-start; /* Align time to the left for assistant */
        }
        .message-time {
            font-size: 11px; /* Smaller time */
            color: #777;
            margin-top: 5px;
            display: block; /* Ensure it's on its own line if needed */
        }

        .stTextArea textarea {
            border-radius: 10px !important;
            border: 1px solid #ced4da !important;
            padding: 12px 20px !important;
            font-size: 1em !important;
            min-height: 80px; /* Ensure decent height */
        }
        .stTextArea textarea:focus {
            border-color: #D10000 !important; /* Red on focus */
            box-shadow: 0 0 0 0.2rem rgba(209, 0, 0, 0.25) !important; /* Red focus ring */
        }

        /* Voice button specific styling */
        button[data-testid="baseButton-secondary"]:has(div:contains("🎙️")) {
            width: 48px !important; /* Slightly larger */
            height: 48px !important;
            padding: 0 !important;
            border-radius: 50% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            background-color: #e9ecef !important; /* Light grey */
            color: #0074D9; /* Bright Blue icon */
            font-size: 24px; /* Larger icon */
            transition: all 0.2s ease !important;
            border: 1px solid #ced4da !important;
            margin-top: auto !important; /* Align with bottom of text area */
            margin-bottom: auto !important; /* Align with bottom of text area */
        }
        button[data-testid="baseButton-secondary"]:has(div:contains("🎙️")):hover {
            background-color: #d4dcdf !important; /* Darker grey on hover */
            transform: scale(1.05);
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }

        /* Send and Clear Chat Buttons specific styling for chat tab */
        #tab-5-content .stButton>button, /* Assuming tab6 is index 5 for content ID */
        div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"]:has(button:contains("Send")) .stButton>button {
             /* More specific selector if needed */
            width: auto; /* Override full width for these specific buttons */
            padding: 0.6em 1.5em;
            font-size: 0.95em;
            height: auto;
        }
        #tab-5-content .stButton>button[kind="primary"],
        div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"]:has(button:contains("Send")) .stButton>button[kind="primary"] {
            background-color: #0074D9; /* Bright Blue for Send */
        }
        #tab-5-content .stButton>button[kind="primary"]:hover,
        div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"]:has(button:contains("Send")) .stButton>button[kind="primary"]:hover {
            background-color: #0056b3; /* Darker Blue */
        }
        #tab-5-content .stButton>button:not([kind="primary"]),
        div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"]:has(button:contains("Clear Chat")) .stButton>button {
            background-color: #6c757d; /* Grey for Clear Chat */
            color: white;
        }
        #tab-5-content .stButton>button:not([kind="primary"]):hover,
        div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"]:has(button:contains("Clear Chat")) .stButton>button:hover {
            background-color: #5a6268; /* Darker Grey */
        }

        /* Footer Styling */
        /* Old footer CSS is replaced by .custom-footer below */
        .custom-footer {
            background-color: #0a2540; /* Dark navy */
            color: #d0d8e0; /* Light grey/blue text */
            padding: 2.5rem 1.5rem; /* Increased padding */
            margin-top: 3rem;
            border-top: 4px solid #3a86ff; /* Accent color border */
        }
        .custom-footer .footer-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 1200px;
            margin: 0 auto;
            flex-wrap: wrap; /* For responsiveness */
        }
        .custom-footer .footer-logo-area {
            flex-basis: auto; /* Adjust as needed */
            text-align: left;
            margin-bottom: 1rem; /* For mobile */
        }
        .custom-footer .footer-logo-area span {
            font-weight: bold;
            font-size: 1.5em; /* Larger QuantAI name */
            color: #ffffff;
        }
        .custom-footer .footer-text {
            flex-grow: 1; /* Allows text to take available space */
            text-align: center;
            font-size: 0.9em;
            line-height: 1.6;
            margin: 0 1rem; /* Spacing around text on larger screens */
            margin-bottom: 1rem; /* For mobile */
        }
        .custom-footer .footer-powered-by {
            flex-basis: auto; /* Adjust as needed */
            text-align: right;
            font-size: 0.85em;
            font-style: italic;
            color: #a0b0c0; /* Subtler color */
            margin-bottom: 1rem; /* For mobile */
        }
        .custom-footer a {
            color: #8cb4ff; /* Lighter blue for links */
            text-decoration: none;
            font-weight: 500;
            transition: color 0.2s ease, text-decoration 0.2s ease;
        }
        .custom-footer a:hover {
            color: #ffffff;
            text-decoration: underline;
        }

        /* Responsive adjustments for footer */
        @media screen and (max-width: 768px) {
            .custom-footer .footer-content {
                flex-direction: column;
                text-align: center;
            }
            .custom-footer .footer-logo-area,
            .custom-footer .footer-text,
            .custom-footer .footer-powered-by {
                flex-basis: 100%;
                text-align: center;
                margin-bottom: 1.5rem; /* Increased bottom margin for mobile */
            }
            .custom-footer .footer-powered-by {
                margin-bottom: 0;
            }
            .custom-footer .footer-text {
                margin: 0 0 1.5rem 0;
            }
        }

        /* Staff Management Tab Enhancements - Modern card design */
        .staff-card {
            background: linear-gradient(135deg, #ffffff 0%, #f9fbff 100%); /* Subtle gradient background */
            padding: 25px; /* More generous padding */
            border-radius: 12px; /* More rounded */
            box-shadow: 0 10px 20px rgba(0,0,0,0.06), 0 2px 6px rgba(0,0,0,0.04); /* Layered shadow for depth */
            margin-bottom: 25px; /* Margin between cards */
            border: 1px solid rgba(222, 226, 230, 0.7); /* Softer border */
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        .staff-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            height: 100%;
            width: 6px;
            background: linear-gradient(180deg, #3a86ff 0%, #2667ff 100%); /* Left accent gradient */
            border-radius: 12px 0 0 12px;
        }
        .staff-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.1), 0 5px 15px rgba(0,0,0,0.05);
            border-color: rgba(58, 134, 255, 0.3);
        }
        .staff-card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }
        .staff-card-info {
             flex-grow: 1;
             padding-left: 10px; /* Space after the left accent line */
        }
        .staff-card-name {
            font-size: 1.4em;
            font-weight: 700;
            color: #0a2540; /* Dark navy */
            margin-bottom: 5px;
            letter-spacing: 0.3px;
        }
        .staff-card-role {
            font-size: 1em;
            color: #3a86ff; /* Bright blue */
            margin-bottom: 12px;
            font-style: italic;
            font-weight: 500;
        }
        .staff-card-skills {
            font-size: 0.9em;
            color: #5a677d;
            margin-bottom: 15px;
            padding-left: 10px;
        }
        .staff-card-skills .skill-tag-label {
            font-weight: 600;
            color: #0a2540;
            margin-bottom: 8px;
            display: block;
            letter-spacing: 0.3px;
        }
        .staff-card-skills .skill-tag {
            background: linear-gradient(90deg, #e8f1ff 0%, #d8e8ff 100%); /* Gradient background */
            color: #2667ff; /* Darker blue text */
            padding: 6px 12px;
            border-radius: 20px;
            margin-right: 8px;
            margin-bottom: 8px;
            display: inline-block;
            font-size: 0.85em;
            font-weight: 600;
            box-shadow: 0 2px 4px rgba(58, 134, 255, 0.15);
            transition: all 0.2s ease;
        }
        .staff-card-skills .skill-tag:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(58, 134, 255, 0.25);
            background: linear-gradient(90deg, #d8e8ff 0%, #c8deff 100%);
        }
        .staff-card-actions {
            display: flex; 
            justify-content: flex-end;
            align-items: center;
            margin-top: 15px;
            gap: 12px; /* Modern spacing between buttons */
        }
        .staff-card-actions .stButton button { 
            margin-left: 0; /* Use gap instead */
            padding: 0.5em 1em;
            font-size: 0.9em;
            min-width: 85px;
            height: auto;
            border-radius: 30px; /* Rounded pill buttons */
            box-shadow: 0 3px 8px rgba(0,0,0,0.1);
            transition: all 0.25s ease;
        }
        .staff-card-actions .stButton button:hover {
            transform: translateY(-2px) scale(1.03);
            box-shadow: 0 5px 12px rgba(0,0,0,0.15);
        }
        
        /* Edit/Delete buttons styled differently */
        .stButton button:contains("✏️ Edit") {
            background: linear-gradient(90deg, #2ecc71 0%, #27ae60 100%) !important; /* Green gradient */
            color: white !important;
        }
        .stButton button:contains("✏️ Edit"):hover {
            background: linear-gradient(90deg, #27ae60 0%, #219653 100%) !important; /* Darker green gradient */
        }
        .stButton button:contains("🗑️ Delete") {
            background: linear-gradient(90deg, #e74c3c 0%, #c0392b 100%) !important; /* Red gradient */
            color: white !important;
        }
        .stButton button:contains("🗑️ Delete"):hover {
            background: linear-gradient(90deg, #c0392b 0%, #a93226 100%) !important; /* Darker red gradient */
        }

        /* Filter styling - Modern and interactive */
        .filters-container {
            background: linear-gradient(135deg, #f8faff 0%, #eef5ff 100%); /* Subtle gradient */
            padding: 25px 30px;
            border-radius: 15px;
            margin-bottom: 35px;
            border: 1px solid rgba(222, 226, 230, 0.7);
            box-shadow: 0 10px 25px rgba(0,0,0,0.03), 0 5px 10px rgba(0,0,0,0.02);
            position: relative;
            overflow: hidden;
        }
        .filters-container::after {
            content: "🔍";
            position: absolute;
            top: 10px;
            right: 15px;
            font-size: 24px;
            opacity: 0.2;
            transform: rotate(-15deg);
        }
        .filters-container .stMultiSelect, .filters-container .stSelectbox {
             margin-bottom: 0 !important;
        }
        .filters-container .stMultiSelect div[data-baseweb="select"] > div,
        .filters-container .stSelectbox div[data-baseweb="select"] > div {
            border-radius: 8px;
            border: 1px solid #d1e0ff;
            transition: all 0.2s ease;
            background-color: rgba(255, 255, 255, 0.7);
        }
        .filters-container .stMultiSelect div[data-baseweb="select"] > div:focus-within,
        .filters-container .stSelectbox div[data-baseweb="select"] > div:focus-within {
            border-color: #3a86ff;
            box-shadow: 0 0 0 3px rgba(58, 134, 255, 0.2);
            background-color: white;
        }
        .filters-container > div[data-testid="stHorizontalBlock"] > div {
            padding-right: 15px;
        }
        .filters-container > div[data-testid="stHorizontalBlock"] > div:last-child {
            padding-right: 0;
        }

        .centered-header h2 {
            text-align: center;
            width: 100%; /* Ensure it takes full width for centering to be effective */
        }

        .main-title-container {
            background: #ffffff; /* White background */
            color: #000000; /* Black text */
            padding: 2.5rem 3rem;
            border-radius: 0;
            margin-bottom: 2.5rem;
            text-align: center;
        }
        /* Add subtle pattern overlay to title */
        .main-title-container::before {
            display: none; /* Ensure pattern is also removed */
        }
        .main-title-container h1 {
            color: #000000; /* Black title text */
            border-bottom: none;
            margin-bottom: 0.5rem;
            padding-bottom: 0;
            position: relative;
            font-size: 2.4rem;
            font-weight: 800;
            letter-spacing: 1px;
            text-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
        }
        .main-title-container h1::after {
            /* content: ""; */ /* Removed to hide the blue line under the main title */
            /* display: block; */
            /* width: 80px; */
            /* height: 4px; */
            /* background: linear-gradient(90deg, #3a86ff 0%, #38bdf8 100%); */
            /* margin: 15px auto 0; */
            /* border-radius: 2px; */
            display: none; /* Effectively removes the line */
        }

        /* Custom CSS for hero section */
        .hero {
            background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
            padding: 3rem 2rem 2rem 2rem;
            border-radius: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 24px rgba(30,60,114,0.15);
            color: white;
            text-align: center;
        }
        .hero-title {
            font-size: 2.8rem;
            font-weight: 800;
            margin-bottom: 1rem;
            letter-spacing: -1px;
        }
        .hero-subtitle {
            font-size: 1.3rem;
            font-weight: 400;
            margin-bottom: 2rem;
            color: #e0e6f7;
        }
        .hero-btn {
            background: #ff6b6b;
            color: white;
            padding: 0.8rem 2.2rem;
            border-radius: 2rem;
            font-size: 1.1rem;
            font-weight: 600;
            border: none;
            cursor: pointer;
            text-decoration: none;
            transition: background 0.2s;
        }
        .hero-btn:hover {
            background: #ff4757;
        }

        /* Staff Directory styling */
        .staff-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); /* Reduced minmax */
            gap: 15px; /* Reduced gap */
            margin-top: 20px;
        }
        .staff-card {
            background: linear-gradient(135deg, #ffffff 0%, #f9fbff 100%);
            border-radius: 8px; /* Reduced border-radius */
            padding: 12px; /* Reduced padding */
            box-shadow: 0 10px 20px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(222, 226, 230, 0.7);
        }
        .staff-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 4px; /* Reduced width */
            height: 100%;
            background: linear-gradient(180deg, #3a86ff 0%, #2667ff 100%);
            border-radius: 8px 0 0 8px; /* Matched border-radius */
        }
        .staff-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.1);
        }
        .staff-header {
            display: flex;
            align-items: center;
            margin-bottom: 8px; /* Reduced margin-bottom */
        }
        .staff-avatar {
            width: 40px; /* Reduced width */
            height: 40px; /* Reduced height */
            border-radius: 50%;
            background: linear-gradient(135deg, #3a86ff 0%, #2667ff 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 18px; /* Reduced font-size */
            font-weight: bold;
            margin-right: 10px; /* Reduced margin-right */
        }
        .staff-info {
            flex-grow: 1;
        }
        .staff-name {
            font-size: 1.1em; /* Reduced font-size */
            font-weight: 700;
            color: #0a2540;
            margin-bottom: 2px; /* Reduced margin-bottom */
        }
        .staff-role {
            font-size: 0.85em; /* Reduced font-size */
            color: #3a86ff;
            font-weight: 500;
            margin-bottom: 8px; /* Added margin-bottom */
        }
        .staff-skills {
            margin-top: 8px; /* Reduced margin-top */
        }
        .skill-tag {
            display: inline-block;
            padding: 3px 8px; /* Reduced padding */
            background: linear-gradient(90deg, #e8f1ff 0%, #d8e8ff 100%);
            color: #2667ff;
            border-radius: 20px;
            margin: 0 5px 5px 0; /* Reduced margin */
            font-size: 0.75em; /* Reduced font-size */
            font-weight: 600;
            transition: all 0.2s ease;
        }
        .skill-tag:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(58, 134, 255, 0.2);
        }
        .staff-actions {
            display: flex;
            justify-content: flex-end;
            margin-top: 15px;
            gap: 10px;
        }
        .action-button {
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 600;
            transition: all 0.2s ease;
            cursor: pointer;
            border: none;
        }
        .edit-button {
            background: linear-gradient(90deg, #2ecc71 0%, #27ae60 100%);
            color: white;
        }
        .delete-button {
            background: linear-gradient(90deg, #e74c3c 0%, #c0392b 100%);
            color: white;
        }
        .action-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .staff-stats {
            display: flex;
            justify-content: space-between;
            margin-top: 10px; /* Reduced margin-top */
            padding-top: 10px; /* Reduced padding-top */
            border-top: 1px solid rgba(222, 226, 230, 0.7);
        }
        .stat-item {
            text-align: center;
        }
        .stat-value {
            font-size: 1em; /* Reduced font-size */
            font-weight: 700;
            color: #0a2540;
        }
        .stat-label {
            font-size: 0.7em; /* Reduced font-size */
            color: #5a677d;
        }

        /* Styling for Streamlit Radio buttons used as sidebar navigation */
        .sidebar .stRadio > div[role="radiogroup"] {
            padding: 0.25rem 0; /* Add some vertical padding to the group */
        }

        .sidebar .stRadio > label[data-baseweb="radio"] { /* Target individual radio item labels */
            background-color: transparent; /* Make background transparent */
            padding: 0.6rem 0.75rem; /* Adjust padding for a better touch target and look */
            border-radius: 0.375rem; /* Apply border radius (6px) */
            margin-bottom: 0.3rem; /* Space between nav items */
            transition: background-color 0.2s ease, color 0.2s ease; /* Smooth transition for hover/active */
            display: flex; /* Use flex to align icon and text */
            align-items: center; /* Vertically align icon and text */
            border: 1px solid transparent; /* For a potential border on hover/active */
        }

        .sidebar .stRadio > label[data-baseweb="radio"]:hover {
            background-color: #E9ECEF; /* Light hover effect */
            color: #000000;
        }

        /* Style for the selected navigation item */
        .sidebar .stRadio input[type="radio"]:checked + div > div > label,
        .sidebar .stRadio > label[data-baseweb="radio"]:has(input[type="radio"]:checked)
        {
            background-color: var(--primary) !important; /* Use primary color for selected item */
            color: white !important; /* White text for selected item */
            font-weight: 600; /* Bold text for selected item */
            /* box-shadow: 0 2px 4px rgba(99, 102, 241, 0.2); */ /* Optional shadow */
        }

        /* Hide the actual radio button circle */
        .sidebar .stRadio input[type="radio"] {
            opacity: 0;
            width: 0;
            height: 0;
            position: absolute;
        }
        
        .sidebar .stRadio label div[data-testid="stMarkdownContainer"] p {
            color: inherit !important; /* Ensure text color inherits from parent label state (hover/active) */
            margin: 0 !important; /* Remove default paragraph margins */
            font-size: 0.95rem !important; /* Consistent font size */
        }
        
        /* Ensure selected item text remains white */
        .sidebar .stRadio input[type="radio"]:checked + div > div > label div[data-testid="stMarkdownContainer"] p,
        .sidebar .stRadio > label[data-baseweb="radio"]:has(input[type="radio"]:checked) div[data-testid="stMarkdownContainer"] p
        {
             color: white !important;
        }

        /* Remove blue line from sidebar navigation radio buttons - existing rules were too broad */
    </style>
    """, unsafe_allow_html=True)

# Initialize session state

# Initialize session state
if 'data_handler' not in st.session_state:
    st.session_state.data_handler = DataHandler()
if 'optimizer' not in st.session_state:
    st.session_state.optimizer = RosterOptimizer()
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()
if 'roster_df' not in st.session_state:
    st.session_state.roster_df = None
if 'editing_staff_id' not in st.session_state:
    st.session_state.editing_staff_id = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_page' not in st.session_state: # Added for new navigation
    st.session_state.current_page = "🏠 Home"
if 'trigger_rerun_for_delete' not in st.session_state: # New flag
    st.session_state.trigger_rerun_for_delete = False
if 'trigger_rerun_for_roster' not in st.session_state: # New flag
    st.session_state.trigger_rerun_for_roster = False
if 'trigger_rerun_for_add' not in st.session_state: # New flag for adding staff
    st.session_state.trigger_rerun_for_add = False

# Initialize chatbot with OpenRouter API key
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    st.error("OpenRouter API key not found. Please set the OPENROUTER_API_KEY environment variable.")
    st.stop()

from utils.chatbot import RosteringChatbot

# Force reinitialization of chatbot to ensure latest implementation
st.session_state.chatbot = RosteringChatbot(OPENROUTER_API_KEY, st.session_state.data_handler, st.session_state.optimizer)

# Sidebar Navigation
with st.sidebar:
    # AI Rostering Solution Title - Using st.markdown to allow for more control if needed
    st.markdown("<h1 class='sidebar-main-title'>Q-Roster</h1>", unsafe_allow_html=True)
    # Subtitle
    st.markdown("<p style='text-align: left; font-size: 0.85rem; color: #4B5563; margin-top: 0rem; margin-bottom: 1.75rem; font-style: italic;'>Your intelligent scheduling partner</p>", unsafe_allow_html=True)

    page_options = ["🏠 Home", "👥 Staff Management", "📅 Roster Generation", "📋 Leave Management", "💬 AI Assistant"]
    
    # Ensure current_page is valid, reset if not (e.g. due to old session state)
    if st.session_state.current_page not in page_options:
        st.session_state.current_page = "🏠 Home" # Default to "🏠 Home"

    # Store the originally selected page to compare after st.radio
    previous_page = st.session_state.current_page

    st.session_state.current_page = st.radio(
        "Navigation",
        options=page_options,
        index=page_options.index(st.session_state.current_page),
        label_visibility="collapsed"
    )
    
    # If page changed via radio button, rerun. This handles direct navigation clicks.
    if st.session_state.current_page != previous_page and st.session_state.get('navigation_radio_changed', False):
        st.session_state.navigation_radio_changed = False # Reset flag
        st.rerun()
    
    # A small trick to detect if the radio button itself caused the change
    # This is imperfect as other reruns might happen between radio click and this check.
    # A more robust way would involve callbacks if st.radio supported it directly for this purpose.
    # For now, we rely on the fact that st.radio writes to session state immediately.
    # We set a flag that this specific widget interaction happened.
    # Note: Streamlit's execution model means this key might be set, then another rerun happens
    # before the check above. This is a known challenge with widget interactions triggering reruns.
    # The key 'navigation_radio' is automatically created by Streamlit for the radio button.
    if f"on_change_for_navigation_radio" not in st.session_state: # Initialize a flag for on_change logic
        st.session_state.f_on_change_for_navigation_radio = False

    if st.session_state.get('navigation_radio') != previous_page:
         st.session_state.navigation_radio_changed = True


    st.markdown("<hr style='margin: 1.5rem 0 0.75rem 0; border-color: #D1D5DB; border-style: solid; border-width: 1px 0 0 0;'>", unsafe_allow_html=True) # Updated hr style
    # st.markdown("<p style='text-align: left; font-size: 0.75rem; color: #6B7280; padding-left: 0.1rem;'>Version 2.1</p>", unsafe_allow_html=True) # Adjusted version style and padding


# Main Content Area - Old hero section is removed from here
# Old tabs are removed from here

# Conditional Page Display
if st.session_state.current_page == "🏠 Home":
    st.markdown("""
        <div class="main-title-container" style="padding: 2.5rem 2rem; margin-bottom: 2rem; text-align: center;">
            <h1 style=\"font-size: 2.8rem; letter-spacing: -0.5px; margin-bottom: 0.75rem; color: #000000;\">AI-Powered Rostering Solution</h1>
            <p style=\"font-size: 1.1rem; font-style: italic; color: #4B5563; font-weight: 400; margin-bottom: 1.5rem; max-width: 800px; margin-left: auto; margin-right: auto;\">
                Optimize your hospital's workforce with AI. Streamline staff scheduling, create efficient clinical rosters, manage leave, and gain insights for a productive environment.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    cols_hero_btn_container = st.columns([1, 1.5, 1]) # For centering the button
    with cols_hero_btn_container[1]:
        if st.button("Get Started", key="home_get_started_staff_btn", use_container_width=True):
            st.session_state.current_page = "👥 Staff Management"
            st.session_state.navigation_radio_changed = False # Prevent immediate re-rerun from radio check
            st.rerun()

    st.markdown("<hr style='margin-top: 2.5rem; margin-bottom: 2.5rem; border-top: 1px solid var(--border);'>", unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center; color: var(--text-primary); margin-bottom: 0.5rem;'>Discover Our Core Features</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: var(--text-secondary); margin-bottom: 2.5rem; max-width: 700px; margin-left: auto; margin-right: auto;'>Explore the powerful tools designed to simplify your rostering challenges, enhance fairness, and improve operational efficiency.</p>", unsafe_allow_html=True)

    feature_cols = st.columns(3)
    features = [
        {"icon": "👥", "title": "Smart Staff Management", "desc": "Easily add, edit, and organize staff profiles. Filter and search with advanced criteria to find the right personnel quickly."},
        {"icon": "📅", "title": "Optimal Roster Generation", "desc": "AI-driven rostering considers skills, preferences, fairness, and operational needs to create balanced schedules."},
        {"icon": "📋", "title": "Efficient Leave Tracking", "desc": "Manage leave requests and visualize team availability with an integrated calendar and approval workflow."}
    ]
    for i, feature in enumerate(features):
        with feature_cols[i]:
            st.markdown(f"""
            <div class="metric-card" style="height: 100%; background: var(--card); border: 1px solid var(--border); text-align: center; padding: 2.5rem; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="font-size: 3rem; margin-bottom: 1.5rem; color: var(--primary); text-align:center;">{feature["icon"]}</div>
                <h3 style="color: #000000; margin-bottom: 1.25rem; font-size: 1.3rem; text-align:center;">{feature["title"]}</h3>
                <p style="color: var(--text-secondary); font-size: 0.95rem; line-height: 1.6; text-align: left;">{feature["desc"]}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True) # Spacer

    feature_cols2 = st.columns(3)
    features2 = [
        {"icon": "💬", "title": "AI Assistant Support", "desc": "Interact with an AI chatbot for quick answers, data insights, task automation, and operational support via text or voice."},
        {"icon": "📊", "title": "Insightful Analytics", "desc": "Visualize roster metrics, staff utilization, and coverage statistics to make informed, data-driven decisions."},
        {"icon": "📱", "title": "Modern & Responsive UI", "desc": "Enjoy a user-friendly, intuitive interface designed for ease of use and accessibility on any device."}
    ]

    for i, feature in enumerate(features2):
        with feature_cols2[i]:
            st.markdown(f"""
            <div class="metric-card" style="height: 100%; background: var(--card); border: 1px solid var(--border); text-align: center; padding: 2.5rem; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="font-size: 3rem; margin-bottom: 1.5rem; color: var(--primary); text-align:center;">{feature["icon"]}</div>
                <h3 style="color: #000000; margin-bottom: 1.25rem; font-size: 1.3rem; text-align:center;">{feature["title"]}</h3>
                <p style="color: var(--text-secondary); font-size: 0.95rem; line-height: 1.6; text-align: left;">{feature["desc"]}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<hr style='margin-top: 2.5rem; margin-bottom: 2.5rem; border-top: 1px solid var(--border);'>", unsafe_allow_html=True)
    
    # Add custom CSS for white buttons with red borders and black text
    st.markdown("""
    <style>
    /* Custom styling for the workforce optimization buttons */
    [data-testid="stHorizontalBlock"] [data-testid="baseButton-secondary"],
    [data-testid="stHorizontalBlock"] [data-testid="baseButton-primary"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #D10000 !important;
        font-weight: 600 !important;
        padding: 0.75rem 1.5rem !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="stHorizontalBlock"] [data-testid="baseButton-secondary"]:hover,
    [data-testid="stHorizontalBlock"] [data-testid="baseButton-primary"]:hover {
        background-color: #f8f9fa !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(209, 0, 0, 0.2) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background-color: #D10000; padding: 3rem 2rem; margin-top: 2.5rem; margin-bottom: 2.5rem; text-align: center;">
        <h2 style="text-align: center; color: #ffffff; margin-bottom: 2rem;">Ready to Optimize Your Workforce?</h2>
    </div>
    """, unsafe_allow_html=True)
    
    quick_links_cols = st.columns([1,1,1])
    with quick_links_cols[0]:
        if st.button("👤 Manage Staff Directory", key="home_staff_dir_btn", use_container_width=True, type="secondary"):
            st.session_state.current_page = "👥 Staff Management"
            st.session_state.navigation_radio_changed = False
            st.rerun()
    with quick_links_cols[1]:
        if st.button("📆 Create Optimized Roster", key="home_gen_roster_btn", use_container_width=True, type="primary"):
            st.session_state.current_page = "📅 Roster Generation"
            st.session_state.navigation_radio_changed = False
            st.rerun()
    with quick_links_cols[2]:
        if st.button("💬 Chat with AI Assistant", key="home_ai_assist_btn", use_container_width=True, type="secondary"):
            st.session_state.current_page = "💬 AI Assistant"
            st.session_state.navigation_radio_changed = False
            st.rerun()

# Ensure the hero button styling is applied if it's a streamlit button
# We will use the .stButton styling and make it prominent if needed
# For now, we use the key "home_get_started_staff_btn" which will get default stButton styling or specific class if we target it.
# The class `hero-btn` might need to be adapted for st.button or use st.markdown for a custom button look.
# For simplicity, a standard streamlit button is used above.

elif st.session_state.current_page == "👥 Staff Management": # Staff Management Tab
    st.markdown("<h2 style='text-align: center; width: 100%; font-size: 2rem; color: var(--text-primary); font-weight: 700; margin-bottom: 0.5rem;'>👥 Smart Staff Management</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; max-width: 700px; margin-left: auto; margin-right: auto; font-size: 1rem; color: var(--text-secondary); font-style: italic; margin-bottom: 1.5rem;'>Easily add, edit, and organize staff profiles. Filter and search with advanced criteria to find the right personnel quickly.</p>", unsafe_allow_html=True)

    # === Move Staff Directory to Top ===
    st.header("Staff Directory")
    if st.session_state.data_handler.staff_data is not None and not st.session_state.data_handler.staff_data.empty:
        staff_df = st.session_state.data_handler.staff_data
        # Staff filters with modern design (keep only the filter bar, no extra divs)
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
            # Minimal table/row layout, no extra divs or boxes
            st.markdown("""
            <style>
            .staff-row-header, .staff-row {
                border-bottom: 1px solid #eee;
                padding: 0.3rem 0 0.3rem 0;
                margin: 0;
                background: none;
            }
            .staff-row-header {
                font-weight: bold;
                color: #000000;
                background: none;
            }
            .staff-row {
                background: none;
            }
            .staff-initials {
                background: #FFFFFF;
                color: #000000;
                border-radius: 50%;
                width: 34px;
                height: 34px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: 1em;
                margin-right: 0.3rem;
                border: 1px solid #000000;
            }
            .staff-skill-tag {
                display: inline-block;
                background: #FFF0F0;
                color: #D10000;
                padding: 2px 10px;
                border-radius: 12px;
                font-size: 0.85em;
                margin: 0 0.2rem 0.2rem 0;
                border: 1px solid #FFD6D6;
            }
            .icon-btn-staff {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 32px;
                height: 32px;
                border-radius: 50%;
                border: 2px solid #D10000;
                background: #fff;
                color: #D10000;
                font-size: 1.1em;
                font-weight: bold;
                margin-right: 0.2em;
                transition: background 0.2s, color 0.2s;
                cursor: pointer;
            }
            .icon-btn-staff.edit:hover {
                background: #D10000;
                color: #fff;
            }
            .icon-btn-staff.delete {
                color: #fff;
                background: #D10000;
                border: 2px solid #D10000;
            }
            .icon-btn-staff.delete:hover {
                background: #fff;
                color: #D10000;
            }
            </style>
            """, unsafe_allow_html=True)

            # Header row (no extra container)
            header_cols = st.columns([0.7, 2, 1.2, 2, 0.8, 1.2])
            with header_cols[0]:
                st.markdown('<div class="staff-row-header">Initials</div>', unsafe_allow_html=True)
            with header_cols[1]:
                st.markdown('<div class="staff-row-header">Name</div>', unsafe_allow_html=True)
            with header_cols[2]:
                st.markdown('<div class="staff-row-header">Role</div>', unsafe_allow_html=True)
            with header_cols[3]:
                st.markdown('<div class="staff-row-header">Skills</div>', unsafe_allow_html=True)
            with header_cols[4]:
                st.markdown('<div class="staff-row-header">Total Shifts</div>', unsafe_allow_html=True)
            with header_cols[5]:
                st.markdown('<div class="staff-row-header">Actions</div>', unsafe_allow_html=True)

            for index, staff in filtered_data.iterrows():
                staff_id = staff.get('id', index)
                initials = ''.join([name[0] for name in staff['name'].split()])
                skills_list = [skill.strip() for skill in staff['skills'].split(',') if skill.strip()]
                total_shifts = len(st.session_state.roster_df[st.session_state.roster_df['Staff'].str.contains(staff['name'], na=False)]) if st.session_state.roster_df is not None else 0

                row_cols = st.columns([0.7, 2, 1.2, 2, 0.8, 1.2])
                with row_cols[0]:
                    st.markdown(f'<div class="staff-row"><span class="staff-initials">{initials}</span></div>', unsafe_allow_html=True)
                with row_cols[1]:
                    st.markdown(f'<div class="staff-row">{staff["name"]}</div>', unsafe_allow_html=True)
                with row_cols[2]:
                    st.markdown(f'<div class="staff-row">{staff["role"]}</div>', unsafe_allow_html=True)
                with row_cols[3]:
                    st.markdown('<div class="staff-row">' + ''.join([f'<span class="staff-skill-tag">{skill}</span>' for skill in skills_list]) + '</div>', unsafe_allow_html=True)
                with row_cols[4]:
                    st.markdown(f'<div class="staff-row">{total_shifts}</div>', unsafe_allow_html=True)
                with row_cols[5]:
                    action_cols = st.columns([1, 1])
                    with action_cols[0]:
                        edit_btn = st.button("✏️", key=f"edit_{staff_id}", help="Edit", use_container_width=True)
                    with action_cols[1]:
                        delete_btn = st.button("🗑️", key=f"delete_{staff_id}", help="Delete", use_container_width=True)
                    st.markdown("""
                    <style>
                    button[data-testid^="baseButton-edit_"], button[data-testid^="baseButton-delete_"] {
                        border-radius: 50% !important;
                        width: 36px !important;
                        height: 36px !important;
                        min-width: 36px !important;
                        min-height: 36px !important;
                        padding: 0 !important;
                        font-size: 1.2em !important;
                        font-weight: bold !important;
                        display: flex !important;
                        align-items: center !important;
                        justify-content: center !important;
                        border: 2px solid #D10000 !important;
                        background: #fff !important;
                        color: #D10000 !important;
                        margin: 0 2px !important;
                        transition: background 0.2s, color 0.2s;
                    }
                    button[data-testid^="baseButton-edit_"]:hover {
                        background: #D10000 !important;
                        color: #fff !important;
                    }
                    button[data-testid^="baseButton-delete_"] {
                        background: #D10000 !important;
                        color: #fff !important;
                    }
                    button[data-testid^="baseButton-delete_"]:hover {
                        background: #fff !important;
                        color: #D10000 !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    if edit_btn:
                        st.session_state.editing_staff_id = staff_id
                        st.rerun()
                    if delete_btn:
                        if st.session_state.data_handler.delete_staff_member(staff_id):
                            st.session_state.data_handler.staff_data = st.session_state.data_handler.db.get_all_staff()
                            st.session_state.chatbot = RosteringChatbot(OPENROUTER_API_KEY, st.session_state.data_handler, st.session_state.optimizer)
                            st.success(f"✅ Staff member {staff['name']} deleted successfully!")
                            st.rerun()
                        else:
                            st.error(f"❌ Error deleting staff member {staff['name']}.")
    else:
        st.info("ℹ️ The staff directory is currently empty. Please add staff members or load data.")

    # Enhanced Add/Edit Staff Form (move above Data Management)
    form_bg = "background: #f9fafb; border: 1.5px solid #e5e7eb; border-radius: 12px; box-shadow: 0 2px 8px rgba(209,0,0,0.03); padding: 2.2rem 2.2rem 1.2rem 2.2rem; margin-bottom: 2rem;"
    
    st.markdown("<div style='font-size: 1.15rem; font-weight: 700; color: #000000; margin-bottom: 1.2rem;'>🆕 Add / Edit Staff Member</div>", unsafe_allow_html=True)
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
        st.markdown("&nbsp;")
        btn_col1, btn_col2, btn_col_spacer = st.columns([1,1,2])
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
    
    # Data Management Section
    st.markdown("<div style='font-size: 1.15rem; font-weight: 700; color: #000000; margin-bottom: 1.2rem;'>📊 Data Management</div>", unsafe_allow_html=True)

    # Data Management Tabs
    tab1, tab2 = st.tabs(["📤 Upload Staff Data", "📋 Use Sample Data"])
    
    with tab1:
        uploaded_file = st.file_uploader("Upload Staff Excel File", type=['xlsx'], label_visibility="collapsed")
        if uploaded_file is not None:
            try:
                staff_data = st.session_state.data_handler.load_staff_data(uploaded_file)
                st.success("✅ Staff data loaded successfully!")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    with tab2:
        st.markdown("<p style='font-size: 0.95rem; color: #555; margin-bottom: 1rem;'>Generate a sample dataset to explore the app's features.</p>", unsafe_allow_html=True)
        if st.button("Generate Sample Data", key="gen_sample_data_tab_btn", use_container_width=True):
            staff_data = st.session_state.data_handler.create_sample_staff_data()
            st.success("✅ Sample data generated and loaded!")
            st.rerun()

    # Data Status Section
    if st.session_state.data_handler.staff_data is not None:
        st.markdown("""
        <div style='margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e5e7eb;'>
            <div style='font-size: 1rem; font-weight: 600; color: #374151; margin-bottom: 0.8rem;'>Current Data Status</div>
            <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.8rem;'>
                <div style='background: #f3f4f6; padding: 0.8rem; border-radius: 6px;'>
                    <div style='font-size: 0.85rem; color: #6B7280;'>Total Staff</div>
                    <div style='font-size: 1.2rem; font-weight: 600; color: #111827;'>{}</div>
                </div>
                <div style='background: #f3f4f6; padding: 0.8rem; border-radius: 6px;'>
                    <div style='font-size: 0.85rem; color: #6B7280;'>Unique Roles</div>
                    <div style='font-size: 1.2rem; font-weight: 600; color: #111827;'>{}</div>
                </div>
                <div style='background: #f3f4f6; padding: 0.8rem; border-radius: 6px;'>
                    <div style='font-size: 0.85rem; color: #6B7280;'>Total Skills</div>
                    <div style='font-size: 1.2rem; font-weight: 600; color: #111827;'>{}</div>
                </div>
            </div>
        </div>
        """.format(
            len(st.session_state.data_handler.staff_data),
            len(st.session_state.data_handler.staff_data['role'].unique()),
            len(set([s.strip() for skills in st.session_state.data_handler.staff_data['skills'] for s in skills.split(',')]))
        ), unsafe_allow_html=True)
    
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
            <div style='background: #fff; border: 2px solid #D10000; border-radius: 12px; padding: 1.5rem 1.5rem 1.2rem 1.5rem; margin-bottom: 1rem;'>
                <div style='color: #6B7280; font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem;'>📋 Roster Parameters:</div>
                <ul style='color: #000; font-size: 1rem; margin-top: 0.5rem; margin-bottom: 0;'>
                    <li>Planning Period: {num_days} days</li>
                    <li>Shifts per Day: {shifts_per_day}</li>
                    <li>Min. Staff per Shift: {min_staff_per_shift}</li>
                    <li>Max. Shifts per Week: {max_shifts_per_week}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        with constraints_col2:
            st.markdown(f"""
            <div style='background: #fff; border: 2px solid #D10000; border-radius: 12px; padding: 1.5rem 1.5rem 1.2rem 1.5rem; margin-bottom: 1rem;'>
                <div style='color: #6B7280; font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem;'>👥 Staff Coverage:</div>
                <ul style='color: #000; font-size: 1rem; margin-top: 0.5rem; margin-bottom: 0;'>
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
                    with st.spinner("🔄 Generating optimal roster..."):
                        # Show progress
                        progress_bar = st.progress(0)
                        for i in range(100):
                            time.sleep(0.01)
                            progress_bar.progress(i + 1)
                        
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
                        
                        if success:
                            st.session_state.roster_df = roster_df
                            st.session_state.last_update = datetime.now()
                            st.markdown('<div style="background: #fff; color: #000; border: 2px solid #D10000; padding: 1.2rem 1.5rem; border-radius: 10px; margin-bottom: 1rem; font-size: 1.15rem; font-weight: 400; text-align: left;">✅ Roster generated successfully!</div>', unsafe_allow_html=True)
                            metrics = st.session_state.optimizer.calculate_roster_metrics(roster_df)
                            staff_on_leave = len([
                                leave for leave in approved_leaves
                                if leave['status'] == 'Approved'
                            ]) if approved_leaves else 0
                            st.markdown(f'''<div style="background: #fff; color: #000; border: 2px solid #D10000; padding: 1.2rem 1.5rem; border-radius: 10px; margin-bottom: 1.5rem; font-size: 1.08rem; font-weight: 400; text-align: left;">
    <span style="font-size: 1.15rem; font-weight: 600; color: #000;">📊 Roster Metrics:</span><br><br>
    Staff Utilization: <span style=\"color: #000; font-weight: 400;\">{metrics['staff_utilization']:.1f}%</span><br>
    Coverage: <span style=\"color: #000; font-weight: 400;\">{metrics['coverage']:.1f}%</span><br>
    Preference Satisfaction: <span style=\"color: #000; font-weight: 400;\">{metrics['preference_satisfaction']:.1f}%</span><br>
    Staff on Leave: <span style=\"color: #000; font-weight: 400;\">{staff_on_leave}</span>
    </div>''', unsafe_allow_html=True)
                        else:
                            error_message = getattr(st.session_state.optimizer, 'last_error', 'Unknown error occurred')
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
                        background-color: white;
                        padding: 15px 20px;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        flex: 1;
                        min-width: 200px;
                    }
                    .stat-title {
                        color: #333333; /* Dark grey/black text */
                        font-size: 0.9em;
                        margin-bottom: 5px;
                         font-weight: 600; /* Make title bold */
                    }
                    .stat-value {
                        color: #000000; /* Changed to Black color */
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

                    # Add shift distribution chart
                    # Removed Shift Distribution by Day chart as requested
                    # st.subheader("Shift Distribution by Day")
                    # shift_pivot = pd.crosstab(
                    #     index=[display_df['Weekday'], display_df['Date']], 
                    #     columns=display_df['Shift Time'],
                    #     values=display_df['Staff Count'],
                    #     aggfunc='sum'
                    # ).fillna(0)

                    # fig = go.Figure()
                    # shift_times = ["07:00-15:00", "15:00-23:00", "23:00-07:00"]
                    # colors = ["#FFD700", "#4169E1", "#483D8B"]

                    # for shift, color in zip(shift_times, colors):
                    #     if shift in shift_pivot.columns:
                    #         fig.add_trace(go.Bar(
                    #             name=f"{shift} Shift",
                    #             x=[f"{day}<br>{date}" for day, date in shift_pivot.index],
                    #             y=shift_pivot[shift],
                    #             marker_color=color
                    #         ))

                    # fig.update_layout(
                    #     barmode='group',
                    #     title="Staff Distribution Across Shifts",
                    #     xaxis_title="Day",
                    #     yaxis_title="Number of Staff",
                    #     height=400,
                    #     showlegend=True,
                    #     legend=dict(
                    #         orientation="h",
                    #         yanchor="bottom",
                    #         y=1.02,
                    #         xanchor="right",
                    #         x=1
                    #     )
                    # )

                    # st.plotly_chart(fig, use_container_width=True)
            
            elif view_type == "Calendar View":
                st.subheader("Calendar View")
                
                # Add week navigation
                current_week_start = datetime.strptime(min(st.session_state.roster_df['Date']), '%Y-%m-%d')
                week_dates = [(current_week_start + timedelta(days=x)).strftime('%Y-%m-%d') 
                            for x in range(7)]
                
                st.markdown(f"""
                <div style='text-align: center; margin-bottom: 20px; padding: 10px; background-color: #f8f9fa; border-radius: 5px;'>
                    <h3 style='margin: 0;'>Week of {format_date(week_dates[0])}</h3>
                </div>
                """, unsafe_allow_html=True)
                
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
                        background-color: #FFFFFF; /* White background */
                        border: 1px solid #E0E0E0; /* Light grey border */
                        border-radius: 8px; /* Slightly less rounded */
                        padding: 15px; /* Consistent padding */
                        margin: 5px; /* Reduced margin */
                        box-shadow: 0 1px 5px rgba(0,0,0,0.05); /* Softer shadow */
                        transition: box-shadow 0.2s ease, border-color 0.2s ease, transform 0.2s ease; /* Add transform to transition */
                    }
                    .calendar-day:hover {
                        box-shadow: 0 4px 10px rgba(0,0,0,0.1); /* Slightly more pronounced hover shadow */
                        border-color: #D10000; /* Red border on hover */
                        transform: translateY(-3px); /* Subtle upward animation */
                    }
                    .day-header {
                        font-weight: 700;
                        color: #333333; /* Dark grey/black text */
                        border-bottom: 1px solid #EEEEEE; /* Light grey separator line */
                        padding-bottom: 10px; /* Adjusted padding */
                        margin-bottom: 10px; /* Adjusted margin */
                        text-align: center;
                        position: relative;
                    }
                    .day-header::after {
                        content: none; /* Remove the accent line below header */
                    }
                    .weekday {
                        color: #000000; /* Changed to black */
                        font-size: 1.1em; /* Slightly smaller font */
                        margin-bottom: 2px; /* Reduced margin */
                        font-weight: 700;
                    }
                    .date {
                        color: #666666; /* Grey color for date */
                        font-size: 0.9em;
                    }
                    .shift-block {
                        margin: 8px 0; /* Reduced margin */
                        padding: 10px; /* Reduced padding */
                        border-radius: 5px; /* Slightly less rounded corners */
                        transition: all 0.2s ease;
                        background-color: #F9F9F9; /* Very light grey background for shifts */
                        border: 1px solid #EEEEEE; /* Light grey border for shifts */
                    }
                    .shift-block:hover {
                        transform: none; /* Remove hover transform */
                        box-shadow: 0 1px 4px rgba(0,0,0,0.08); /* Subtle hover shadow */
                        border-color: #D10000; /* Red border on hover */
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
                        color: #333333; /* Dark grey/black text */
                        font-size: 1em; /* Slightly smaller font */
                    }
                    .shift-time {
                        font-size: 0.8em; /* Smaller font size */
                        color: #666666; /* Grey color */
                    }
                    .staff-list {
                        margin-top: 5px; /* Adjusted margin */
                        font-size: 0.85em; /* Smaller font size */
                        line-height: 1.4; /* Adjusted line height */
                        color: #555555; /* Grey color */
                    }
                    .no-staff {
                        color: #888; /* Keep grey for no staff */
                        font-style: italic;
                    }
                    .calendar-day.today { /* Highlight for current day in calendar */
                        border: 1px solid #E0E0E0; /* Changed to light grey border */
                        box-shadow: none; /* Remove the shadow for today highlight */
                    }
                     .calendar-day.today:hover { /* Add hover effects for the 'Today' card */
                        border: 1px solid #D10000; /* Red border on hover */
                        box-shadow: 0 4px 10px rgba(0,0,0,0.1); /* Subtle shadow on hover */
                        transform: translateY(-3px); /* Subtle upward animation on hover */
                    }
                     .today::before { /* Style and position the 'Today' label */
                        content: "Today";
                        position: absolute;
                        top: 5px; /* Adjusted position from top */
                        right: 5px; /* Adjusted position from right */
                        background: #D10000; /* Solid red background */
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
                        background-color: #FFFFFF; /* White background */
                        padding: 15px 20px; /* Increased padding */
                        border: 1px solid #E0E0E0; /* Light grey border */
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
                        background-color: #D10000; /* Red color */
                    }
                    .schedule-day:hover {
                        transform: translateY(-3px); /* Subtle upward animation */
                        box-shadow: 0 4px 10px rgba(0,0,0,0.1); /* More pronounced shadow on hover */
                         border-color: #D10000; /* Red border on hover */
                    }

                    .schedule-date {
                        font-weight: bold;
                        color: #333333; /* Dark grey/black color */
                        margin-bottom: 5px;
                        font-size: 1.05em;
                        padding-left: 10px; /* Space for the accent line */
                    }
                    .schedule-shift {
                        color: #666666; /* Grey color */
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
                        background-color: #f8f9fa;
                        padding: 20px;
                        border-radius: 8px;
                        margin-top: 20px;
                    }
                    .stats-header {
                        color: #333333; /* Changed to dark grey/black */
                        font-weight: bold;
                        margin-bottom: 15px;
                    }
                    .stats-item {
                        margin: 10px 0;
                        display: flex;
                        justify-content: space-between;
                        padding: 5px 0;
                        border-bottom: 1px solid #cccccc; /* Changed to grey separator */
                    }
                    .stats-label {
                        color: #555555; /* Changed to grey */
                    }
                    .stats-value {
                        font-weight: bold;
                        color: #D10000; /* Changed to red */
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

elif st.session_state.current_page == "📋 Leave Management":
    st.markdown("""
    <h1 style='text-align: center; margin-bottom: 0.5rem;'>📋 Leave Management</h1>
    <p style='text-align: center; color: #4B5563; font-size: 1.05rem; font-style: italic; margin-bottom: 2rem;'>
        Manage leave requests, track staff absences, and keep your roster up to date.
    </p>
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
        color: #000000; /* Changed to black */
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
        background-color: #D10000 !important;
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
        background-color: #D10000;
        color: #FFFFFF;
    }
    
    .leave-status-pending {
        background-color: #F0F0F0;
        color: #666666;
        border: 1px solid #D0D0D0;
    }
    
    .leave-status-rejected {
        background-color: #333333;
        color: #FFFFFF;
    }
    
    /* Leave type tags */
    .leave-type-tag {
        background-color: #F0F0F0;
        color: #D10000;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
        border: 1px solid #D10000;
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
        background-color: #D10000 !important;
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
        background-color: #D10000 !important;
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
        
    if submit_leave:
        if staff_member and leave_type and start_date and end_date:
            duration = (end_date - start_date).days + 1
            success = st.session_state.data_handler.db.add_leave_request(
                staff_member, leave_type, str(start_date), str(end_date), duration, reason
            )
            if success:
                st.success("Leave request submitted!")
                st.session_state.leave_requests = st.session_state.data_handler.db.get_all_leave_requests()
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

elif st.session_state.current_page == "💬 AI Assistant": # AI Assistant Tab
    
    
    st.markdown("""
    <style>
        /* Style for Streamlit's text input when focused */
        .stTextArea textarea:focus {
            border-color: #D10000 !important;
            box-shadow: 0 0 0 1px #D10000 !important;
        }
        
        .ai-chat-page-container { /* Wrapper for the entire chat section on the page */
            padding: 0;
            margin-top: -0.5rem; /* Reduced margin to remove gap */
        }
        
        .ai-chat-header {
            background: linear-gradient(135deg, #D10000 0%, #B80000 100%); /* Gradient red header */
            color: white;
            padding: 0.6rem 1rem; /* Reduced padding */
            text-align: left;
            font-size: 1.1rem; /* Slightly smaller */
            font-weight: 600;
            border-bottom: 1px solid #A30000;
            display: flex;
            align-items: center;
        }
        .ai-chat-header-icon {
            font-size: 1.3rem; /* Slightly smaller */
            margin-right: 0.5rem; /* Reduced margin */
        }
        .ai-chat-history {
            flex-grow: 1;
            padding: 5px 10px 18px 10px; /* Reduced top padding */
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 1.1rem;
            background: #FFFFFF; /* Changed to white background */
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
            padding: 13px 18px;
            border-radius: 22px;
            font-size: 1.04em;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            margin-bottom: 2px;
            word-break: break-word;
            position: relative;
        }
        .ai-user-message {
            background: #D10000;
            color: #fff;
            border-bottom-right-radius: 8px;
            border-top-right-radius: 22px;
            border-top-left-radius: 22px;
            border-bottom-left-radius: 22px;
        }
        .ai-assistant-message {
            background: #fff;
            color: #222;
            border-bottom-left-radius: 8px;
            border-top-right-radius: 22px;
            border-top-left-radius: 22px;
            border-bottom-right-radius: 22px;
            border: 1px solid #ECECEC;
        }
        .ai-message-time {
            font-size: 0.78em;
            color: #B0B0B0;
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
            background: #fff;
            color: #D10000;
        }
        .ai-avatar.assistant {
            background: #E5E5EA;
            color: #6C47FF;
        }
        /* Option buttons (suggested replies) */
        .ai-option-buttons {
            display: flex;
            gap: 0.7rem;
            margin-top: 0.7rem;
        }
        .ai-option-btn {
            background: #fff;
            color: #6C47FF;
            border: 1.5px solid #6C47FF;
            border-radius: 999px;
            padding: 7px 18px;
            font-size: 1em;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.15s, color 0.15s;
        }
        .ai-option-btn.selected, .ai-option-btn:hover {
            background: #6C47FF;
            color: #fff;
        }
        
        /* Enhanced Welcome Message */
        .empty-chat-prompt-new {
            text-align: center;
            padding: 2.5rem 1.5rem; /* Increased padding */
            margin: auto;
            background-color: #FFFFFF; /* White background */
            border-radius: 12px;
            border: 1px solid #D10000; /* Red border */
            box-shadow: 0 8px 24px rgba(209, 0, 0, 0.08); /* Subtle red shadow */
            max-width: 70%; /* Adjusted width */
        }
        .empty-chat-prompt-new h3 {
            color: #D10000; /* Red heading */
            margin-bottom: 1rem; /* Space below heading */
            font-weight: 700;
            font-size: 1.6rem; /* Larger font size */
        }
        .empty-chat-prompt-new p {
            color: #333333; /* Darker grey for text for better contrast */
            margin: 0.5rem 0 0 0; /* Adjusted margin */
            font-size: 1.1rem; /* Slightly larger text */
            font-weight: 400; /* Regular weight for paragraph */
            line-height: 1.6;
        }
        /* Remove list styling as it's no longer needed */
        .empty-chat-prompt-new ul {
            display: none;
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
        st.markdown("""
        <style>
        .chat-row {
            display: flex;
            align-items: flex-end;
            margin-bottom: 0.7rem;
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
            margin: 0 0.5rem;
            background: #e9e9e9;
            box-shadow: 0 1px 4px rgba(0,0,0,0.07);
        }
        .chat-avatar-real.user {
            background: linear-gradient(135deg, #d10000 0%, #ff4b4b 100%);
            color: #fff;
        }
        .chat-avatar-real.assistant {
            background: #fff;
            color: #3a86ff;
            border: 1.5px solid #e0eaff;
        }
        .bubble {
            max-width: 70vw;
            padding: 0.7rem 1.1rem;
            border-radius: 18px;
            font-size: 1.08em;
            line-height: 1.6;
            word-break: break-word;
            position: relative;
            margin-bottom: 0.18rem;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
            transition: box-shadow 0.15s;
        }
        .chat-row.user .bubble {
            background: linear-gradient(90deg, #d10000 0%, #ff4b4b 100%);
            color: #fff;
            border-bottom-right-radius: 6px;
            border-bottom-left-radius: 18px;
            border-top-right-radius: 18px;
            border-top-left-radius: 18px;
            margin-right: 0.2rem;
        }
        .chat-row.assistant .bubble {
            background: #fff;
            color: #222;
            border-bottom-left-radius: 6px;
            border-bottom-right-radius: 18px;
            border-top-right-radius: 18px;
            border-top-left-radius: 18px;
            border: 1.5px solid #e0eaff;
            margin-left: 0.2rem;
        }
        .bubble:hover {
            box-shadow: 0 2px 8px rgba(209,0,0,0.13);
        }
        .bubble-tail {
            position: absolute;
            width: 0;
            height: 0;
        }
        .chat-row.user .bubble-tail {
            right: -10px;
            bottom: 0;
            border-top: 10px solid transparent;
            border-bottom: 0 solid transparent;
            border-left: 10px solid #ff4b4b;
        }
        .chat-row.assistant .bubble-tail {
            left: -10px;
            bottom: 0;
            border-top: 10px solid transparent;
            border-bottom: 0 solid transparent;
            border-right: 10px solid #fff;
        }
        .chat-timestamp {
            font-size: 0.78em;
            color: #b0b0b0;
            margin-top: 0.1rem;
            margin-bottom: 0.1rem;
            text-align: right;
            padding: 0 0.2rem;
        }
        .chat-row.user .chat-timestamp {
            text-align: left;
            margin-left: 0.5rem;
        }
        .chat-row.assistant .chat-timestamp {
            text-align: right;
            margin-right: 0.5rem;
        }
        </style>
        """, unsafe_allow_html=True)
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
        background: #D10000 !important;
        color: #fff !important;
        border: none !important;
    }
    .ai-chat-send-btn:hover {
        background: #B30000 !important;
        color: #fff !important;
    }
    .ai-chat-clear-btn {
        background: #fff !important;
        color: #D10000 !important;
        border: 2px solid #D10000 !important;
    }
    .ai-chat-clear-btn:hover {
        background: #f8f0f0 !important;
        color: #D10000 !important;
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
            height=44
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
                    <div class="thinking-dots">
                        <div class="thinking-dot"></div>
                        <div class="thinking-dot"></div>
                        <div class="thinking-dot"></div>
                    </div>
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
<div style="text-align: center; padding: 1.5rem 0; margin-top: 2rem; background-color: #ffffff; color: #000000; border-top: 1px solid #e0e0e0;">
    <p style="font-size: 1.2em; font-family: 'Lato', sans-serif; color: #000000;">Powered by QuantAI</p>
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
    background-color: #FFFFFF; /* White background */
    border: 1px solid #E0E0E0; /* Light grey border */
    border-radius: 12px;
    padding: 1.5rem; /* Ample padding */
    box-shadow: 0 4px 8px rgba(0,0,0,0.05);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    position: relative;
    overflow: hidden; /* For accent */
}

.new-staff-card::before { /* Red accent line on top */
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 5px;
    background-color: #D10000; /* Main red color */
}

.new-staff-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 16px rgba(0,0,0,0.1);
}

.new-staff-header {
            display: flex;
    align-items: center;
    margin-bottom: 1rem;
    padding-top: 0.5rem; /* Space below accent line */
}

.new-staff-avatar {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background-color: #D10000; /* Red background */
    color: #FFFFFF; /* White initials */
    display: flex;
    align-items: center;
            justify-content: center;
    font-size: 1.5em;
    font-weight: bold;
    margin-right: 1rem;
    border: 2px solid #FFFFFF; /* White border for avatar */
    box-shadow: 0 2px 4px rgba(209,0,0,0.3);
}

.new-staff-info {
    flex-grow: 1;
}

.new-staff-name {
    font-size: 1.3em;
    font-weight: bold;
    color: #333333;
    margin-bottom: 0.25rem;
}

.new-staff-role {
    font-size: 1em;
    color: #666666;
}

.new-staff-skills-section {
    margin: 1rem 0;
}

.skills-label {
    font-size: 0.9em;
    color: #666666;
    margin-bottom: 0.5rem;
}

.new-skill-tag {
    display: inline-block;
    background-color: #FFF0F0; /* Light red background */
    color: #D10000; /* Red text */
    padding: 0.4rem 0.8rem;
    border-radius: 15px;
    font-size: 0.85em;
    margin: 0 0.5rem 0.5rem 0;
    border: 1px solid #FFD6D6;
}

.new-staff-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #EEEEEE;
}

.stat-item {
    text-align: center;
}

.stat-value {
    font-size: 1.4em;
    font-weight: bold;
    color: #D10000; /* Red color for stats */
    margin-bottom: 0.25rem;
}

.stat-label {
    font-size: 0.8em;
    color: #666666;
}

.new-staff-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 1rem;
}

.new-staff-actions button {
    background-color: #D10000; /* Red background */
    color: #FFFFFF; /* White text */
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 5px;
    cursor: pointer;
    transition: background-color 0.2s ease;
}

.new-staff-actions button:hover {
    background-color: #B30000; /* Darker red on hover */
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
    color: #D10000;
    border: 2px solid #D10000;
    border-radius: 6px;
    padding: 0.6em 1.5em;
    font-size: 1em;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s, color 0.2s, box-shadow 0.2s;
    margin-right: 0.5rem;
}
.new-staff-edit-btn:hover {
    background: #D10000;
    color: #fff;
    box-shadow: 0 2px 8px rgba(209,0,0,0.08);
}
.new-staff-delete-btn {
    background: #D10000;
    color: #fff;
    border: 2px solid #D10000;
    border-radius: 6px;
    padding: 0.6em 1.5em;
    font-size: 1em;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s, color 0.2s, box-shadow 0.2s;
}
.new-staff-delete-btn:hover {
    background: #fff;
    color: #D10000;
    box-shadow: 0 2px 8px rgba(209,0,0,0.08);
}
.icon-btn {
    background: #fff;
    border: 2px solid #D10000;
    color: #D10000;
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
    background: #D10000;
    color: #fff;
    box-shadow: 0 2px 8px rgba(209,0,0,0.08);
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
        background-color: #D10000 !important;  /* Red */
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.7em 2em !important;
        transition: background 0.2s;
    }
    button[data-testid="baseButton-send_btn"]:hover {
        background-color: #B30000 !important;  /* Darker red */
        color: #fff !important;
    }

    /* Style for the Clear Chat button */
    button[data-testid="baseButton-clear_btn"] {
        background-color: #fff !important;
        color: #D10000 !important;
        border: 2px solid #D10000 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.7em 2em !important;
        transition: background 0.2s;
    }
    button[data-testid="baseButton-clear_btn"]:hover {
        background-color: #f8f0f0 !important;
        color: #D10000 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Style for Send and Clear Chat buttons to match "Get Started" */
button[data-testid="baseButton-send_btn"],
button[data-testid="baseButton-clear_btn"] {
    background-color: #fff !important;
    color: #000 !important;
    border: 1.5px solid #D10000 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.75rem 1.5rem !important;
    transition: all 0.3s ease !important;
    box-shadow: none !important;
}
button[data-testid="baseButton-send_btn"]:hover,
button[data-testid="baseButton-clear_btn"]:hover {
    background-color: #f8f9fa !important;
    color: #D10000 !important;
    box-shadow: 0 4px 8px rgba(209, 0, 0, 0.08) !important;
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
    border: 1.5px solid #D10000 !important; /* Red border */
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
    color: #D10000 !important; /* Red text on hover */
    border-color: #D10000 !important; /* Ensure border stays red */
    box-shadow: 0 4px 8px rgba(209, 0, 0, 0.08) !important; /* Subtle red-tinted shadow */
}

    /* Import Lato font from Google Fonts */
    .thinking-animation {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 12px 16px;
        background: #f8f9fa;
        border-radius: 12px;
        border: 1px solid #e9ecef;
        margin: 8px 0;
        width: fit-content;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    .thinking-dots {
        display: flex;
        gap: 4px;
    }
    
    .thinking-dot {
        width: 8px;
        height: 8px;
        background: #D10000;
        border-radius: 50%;
        animation: thinking 1.4s infinite ease-in-out;
    }
    
    .thinking-dot:nth-child(1) { animation-delay: 0s; }
    .thinking-dot:nth-child(2) { animation-delay: 0.2s; }
    .thinking-dot:nth-child(3) { animation-delay: 0.4s; }
    
    @keyframes thinking {
        0%, 80%, 100% { transform: scale(0.6); opacity: 0.6; }
        40% { transform: scale(1); opacity: 1; }
    }
    
    /* Hide default spinner */
    .stSpinner {
        display: none !important;
    }

    /* Custom styling for st.info messages to be light red */
    div.stAlert {
        background-color: #FFEEEE !important; /* Light red background */
        color: #D10000 !important; /* Main red text */
        border: 1px solid #F8C8C8 !important; /* Softer red border */
        border-left-width: 0.5rem !important; /* Keep a distinct left border */
        border-left-color: #D10000 !important; /* Main red for left border */
        border-radius: 0.375rem !important; 
    }

    /* Ensure the icon in st.info also adapts */
    div.stAlert div[data-testid="stMarkdownContainer"] svg {
        fill: #D10000 !important; /* Change icon color to red */
    }

    /* Ensure text within st.info is also red */
    div.stAlert div[data-testid="stMarkdownContainer"] p {
        color: #D10000 !important; /* Main red text for paragraphs */
    }

    /* Custom styling for the Generate Optimal Roster button */
    [data-testid="stButton"] button {
        background-color: #D10000 !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.75rem 1.5rem !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="stButton"] button:hover {
        background-color: #B00000 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(209, 0, 0, 0.2) !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Make the Streamlit progress bar red */
.stProgress > div > div > div > div {
    background-color: #D10000 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    /* Custom red button style for staff form */
    div[data-testid="stForm"] button[kind="primaryFormSubmit"] {
        background-color: #D10000 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 1.5rem !important;
        font-size: 1em !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover {
        background-color: #B00000 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(209, 0, 0, 0.2) !important;
    }
    
    /* Style for cancel button */
    div[data-testid="stForm"] button[kind="secondaryFormSubmit"] {
        background-color: #fff !important;
        color: #D10000 !important;
        border: 1.5px solid #D10000 !important;
        border-radius: 8px !important;
        padding: 0.75rem 1.5rem !important;
        font-size: 1em !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover {
        background-color: #f8f9fa !important;
        color: #D10000 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(209, 0, 0, 0.08) !important;
    }
    </style>
    """, unsafe_allow_html=True)