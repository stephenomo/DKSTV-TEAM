# app.py
"""Simple Streamlit app with basic authentication - No roles"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Import from modules
from config import EXPECTED_PER_MEMBER
from auth import (
    setup_authentication, 
    register_user_ui, 
    load_users_from_db,
    get_user_count,
    get_all_users,
    get_user_role  # ✅ Add this import
)
from database import init_db, get_all_contributions, add_contribution, delete_entry, import_contributions_from_excel, export_contributions_to_excel

# ==================== PAGE CONFIG ====================
st.set_page_config(page_title="💰 DKSV TEAM", layout="wide")

# ==================== SIDEBAR: AUTHENTICATION ====================
st.sidebar.title("🔐 Authentication")

auth_mode = st.sidebar.radio("Select Action", ["🔑 Login", "🆕 Register"])

# Show registration form
if auth_mode == "🆕 Register":
    register_user_ui()
    st.stop()

# ==================== LOGIN ====================
# Setup authentication (store in session state)
if 'authenticator' not in st.session_state:
    st.session_state.authenticator, st.session_state.users = setup_authentication()

authenticator = st.session_state.authenticator

# Show login form
authenticator.login(location="sidebar")

# Get authentication status
authentication_status = st.session_state.get("authentication_status")
username = st.session_state.get("username")
name = st.session_state.get("name")

# ==================== MAIN APP ====================
st.title("💰 DKSV TEAM")
init_db()

# Handle authentication
if authentication_status is False:
    st.error("❌ Incorrect username or password")
    st.stop()

elif authentication_status is None:
    st.warning("🔐 Please log in or register to continue")
    st.stop()

elif authentication_status:
    # User is logged in!
    authenticator.logout("Logout", "sidebar")
    
    # ✅ Get user role directly from database using the dedicated function
    user_role = get_user_role(username)
    
    # 🔍 DEBUG INFO - Remove after fixing
    st.sidebar.write("---")
    st.sidebar.write("🔍 **DEBUG INFO:**")
    st.sidebar.write(f"Username: `{username}`")
    st.sidebar.write(f"Role from DB: `{user_role}`")
    st.sidebar.write(f"Role type: `{type(user_role)}`")
    
    # Check database directly
    import sqlite3
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, role FROM users")
    all_roles = cursor.fetchall()
    conn.close()
    st.sidebar.write("All users in DB:")
    for u, r in all_roles:
        st.sidebar.write(f"  - {u}: {r}")
    st.sidebar.write("---")
    
    # ✅ Fallback to viewer if role not found (should never happen, but safety first)
    if user_role is None:
        user_role = "viewer"
    
    st.sidebar.success(f"✅ Logged in as **{name}**")
    st.sidebar.info(f"🔑 Role: **{user_role.upper()}**")
    
    # Get all contributions
    df = get_all_contributions()
    
    # ==================== ADMIN CONTROLS ====================
    if user_role == "admin":
        st.sidebar.write("---")
        st.sidebar.subheader("🛠️ Admin Controls")
        st.sidebar.caption("Only you can add/delete contributions")
        
        # Excel Import/Export
        st.sidebar.write("---")
        st.sidebar.subheader("📁 Excel Import/Export")
        
        # Export to Excel
        if st.sidebar.button("📥 Download All Data (Excel)", use_container_width=True):
            try:
                excel_data = export_contributions_to_excel()
                st.sidebar.download_button(
                    label="💾 Download Excel File",
                    data=excel_data,
                    file_name=f"contributions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.sidebar.error(f"❌ Export failed: {e}")
        
        # Import from Excel
        st.sidebar.write("**Upload Excel File:**")
        uploaded_file = st.sidebar.file_uploader(
            "Choose Excel file",
            type=['xlsx', 'xls'],
            help="Excel must have columns: member, amount, month"
        )
        
        if uploaded_file is not None:
            if st.sidebar.button("📤 Import from Excel", use_container_width=True):
                success_count, errors = import_contributions_from_excel(uploaded_file)
                
                if success_count > 0:
                    st.sidebar.success(f"✅ Imported {success_count} contributions!")
                    if errors:
                        st.sidebar.warning(f"⚠️ {len(errors)} errors occurred")
                        with st.sidebar.expander("View errors"):
                            for error in errors:
                                st.write(f"- {error}")
                    st.rerun()
                else:
                    st.sidebar.error("❌ Import failed")
                    for error in errors:
                        st.sidebar.error(error)
        
        st.sidebar.write("---")
        
        # Add contribution for anyone
        st.sidebar.subheader("➕ Add Single Contribution")
        with st.sidebar.form("add_contribution_form"):
            member_name = st.text_input("Member Name*")
            amount = st.number_input("Amount*", min_value=0.0, format="%.2f")
            month = st.text_input("Month* (e.g., January 2025)")
            submit = st.form_submit_button("➕ Add Contribution")
            
            if submit:
                if not member_name or not month or amount <= 0:
                    st.error("Please fill all fields correctly")
                else:
                    add_contribution(member_name, amount, month)
                    st.success(f"✅ Added ${amount:.2f} for {member_name}")
                    st.rerun()
        
        # Delete any contribution
        st.sidebar.write("---")
        st.sidebar.subheader("🗑️ Delete Any Entry")
        
        if not df.empty:
            # Show all entries
            df_display = df.copy()
            df_display['display'] = df_display.apply(
                lambda row: f"ID:{row['id']} | {row['member']} | {row['month']} | ${row['amount']:.2f}", 
                axis=1
            )
            
            selected_display = st.sidebar.selectbox(
                "Choose entry to delete:",
                options=df_display['display'].tolist(),
                key="admin_delete_select"
            )
            
            if selected_display:
                selected_row = df_display[df_display['display'] == selected_display].iloc[0]
                st.sidebar.warning(
                    f"**Will delete:**\n\n"
                    f"👤 Member: {selected_row['member']}\n\n"
                    f"📅 Month: {selected_row['month']}\n\n"
                    f"💰 Amount: ${selected_row['amount']:.2f}"
                )
                
                if st.sidebar.button("❌ Delete Entry", key="admin_delete_btn", type="primary"):
                    entry_id = selected_row['id']
                    
                    # 🔍 DEBUG - Remove after fixing
                    st.sidebar.write(f"DEBUG: Attempting to delete ID: {entry_id}")
                    st.sidebar.write(f"DEBUG: ID type: {type(entry_id)}")
                    
                    result = delete_entry(entry_id)
                    
                    st.sidebar.write(f"DEBUG: Delete result: {result}")
                    
                    if result:
                        st.sidebar.success(f"✅ Deleted entry ID: {entry_id}")
                        st.rerun()
                    else:
                        st.sidebar.error(f"❌ Failed to delete entry ID: {entry_id}")
        else:
            st.sidebar.info("No entries to delete")
    
    else:
        # VIEWER - Read only
        st.sidebar.write("---")
        st.sidebar.info("📖 **Viewer Mode**\n\nYou can view all data but cannot add or delete contributions.")
        st.sidebar.caption("Contact the admin to make changes.")
    
    # ==================== DASHBOARD ====================
    st.write("### 📊 All Contributions")
    
    if df.empty:
        st.info("No contributions yet. Add your first contribution!")
    else:
        # Summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Collected", f"${df['amount'].sum():,.2f}")
        with col2:
            st.metric("Total Contributors", df["member"].nunique())
        with col3:
            st.metric("Total Entries", len(df))
        
        st.write("---")
        
        # Main data view
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            st.write("#### Recent Contributions")
            st.dataframe(df.sort_values("date", ascending=False), use_container_width=True)
        
        with col_right:
            st.write("#### By Member")
            by_member = df.groupby("member", as_index=False)["amount"].sum()
            by_member = by_member.sort_values("amount", ascending=False)
            st.dataframe(by_member, use_container_width=True)
            
            st.write("---")
            st.write(f"**Expected per member:** ${EXPECTED_PER_MEMBER:.2f}")
            
            # Show who's below expected
            defaulters = by_member[by_member["amount"] < EXPECTED_PER_MEMBER]
            if defaulters.empty:
                st.success("✅ Everyone met expectations!")
            else:
                st.warning("⚠️ Below expected amount:")
                for _, row in defaulters.iterrows():
                    remaining = EXPECTED_PER_MEMBER - row["amount"]
                    st.write(f"- {row['member']}: ${remaining:.2f} short")
        
        # ==================== CHARTS ====================
        st.write("---")
        st.write("### 📈 Visualizations")
        
        tab1, tab2 = st.tabs(["📊 By Member", "📅 Over Time"])
        
        with tab1:
            fig1 = px.bar(
                by_member, 
                x="member", 
                y="amount", 
                title="Total Contributed per Member",
                color="amount",
                color_continuous_scale="Blues"
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with tab2:
            df_time = df.copy()
            df_time["date_parsed"] = pd.to_datetime(df_time["date"], errors="coerce")
            df_time = df_time.sort_values("date_parsed")
            
            if not df_time["date_parsed"].isna().all():
                df_daily = df_time.groupby(
                    df_time["date_parsed"].dt.date
                )["amount"].sum().reset_index(name="daily_total")
                
                fig2 = px.line(
                    df_daily, 
                    x="date_parsed", 
                    y="daily_total", 
                    title="Contributions Over Time",
                    markers=True
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No date information available for timeline view")