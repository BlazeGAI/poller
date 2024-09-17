import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image
import json
import os
import time
import random
import string
import pandas as pd
from supabase import create_client, Client
import zipfile
from datetime import datetime
import requests
import plotly.express as px
import plotly.graph_objects as go

# Supabase credentials
SUPABASE_URL = "https://czivxiadenrdpxebnqpu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN6aXZ4aWFkZW5yZHB4ZWJucXB1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjU1NjgxOTQsImV4cCI6MjA0MTE0NDE5NH0.i_xLmpxQlUfHGq_Hs9DzvaQPWciGD_FZuxAEo0caAvM"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'current_poll_id' not in st.session_state:
    st.session_state.current_poll_id = None
if 'current_poll_data' not in st.session_state:
    st.session_state.current_poll_data = None

# Helper functions
def get_qr_image_bytes(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def generate_poll_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def extract_file_info(answer):
    if isinstance(answer, dict) and 'filename' in answer and 'url' in answer:
        url = answer['url'].rstrip('?')
        return answer['filename'], url
    elif isinstance(answer, list):
        return ', '.join(answer), ''
    return str(answer), ''

def check_user_session():
    if st.session_state.user:
        try:
            user = supabase.auth.get_user()
            if user:
                return True
        except Exception:
            st.session_state.user = None
    return False

def register_user(email, password):
    try:
        user = supabase.auth.sign_up({"email": email, "password": password})
        st.success("Registration successful! Please log in.")
        return True
    except Exception as e:
        st.error(f"Registration failed: {str(e)}")
        print(f"Registration Error Details: {str(e)}")  # Debugging print
        return False

def login_user(email, password):
    try:
        user = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = user
        st.session_state.user_id = user.user.id
        st.success("Login successful!")
        st.experimental_rerun()  # This will rerun the app after a successful login
        return True
    except Exception as e:
        st.error(f"Login failed: {str(e)}")
        print(f"Login Error Details: {str(e)}")
        return False

def logout_user():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.session_state.current_poll_id = None
    st.session_state.current_poll_data = None
    st.session_state.clear()
    st.success("Logged out successfully!")

def create_new_poll():
    new_poll_id = generate_poll_id()
    new_poll_data = {
        "id": new_poll_id,
        "questions": [],
        "active": True,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "created_by": st.session_state.user_id
    }
    result = supabase.table("polls").insert(new_poll_data).execute()
    if result.data:
        st.session_state.current_poll_id = new_poll_id
        st.session_state.current_poll_data = new_poll_data
        st.success(f"New poll created with ID: {new_poll_id}")
    else:
        st.error("Failed to create new poll")

def load_current_poll():
    if st.session_state.current_poll_id:
        poll_data = supabase.table("polls").select("*").eq("id", st.session_state.current_poll_id).execute()
        if poll_data.data:
            st.session_state.current_poll_data = poll_data.data[0]
        else:
            st.error("Failed to load current poll data")

def admin_page():
    st.title("Admin Page")
    
    if st.button("New Poll"):
        create_new_poll()
    
    if st.session_state.current_poll_data:
        poll_data = st.session_state.current_poll_data
        st.write(f"Current Poll ID: {poll_data['id']}")
        
        poll_active = st.checkbox("Poll Active", value=poll_data["active"])
        if poll_active != poll_data["active"]:
            supabase.table("polls").update({"active": poll_active}).eq("id", poll_data["id"]).execute()
            poll_data["active"] = poll_active
            st.session_state.current_poll_data = poll_data

        uploaded_file = st.file_uploader("Upload questions file", type="txt")
        if uploaded_file is not None:
            questions = [line.decode("utf-8").strip() for line in uploaded_file.readlines() if line.strip()]
            supabase.table("polls").update({"questions": questions}).eq("id", poll_data["id"]).execute()
            poll_data["questions"] = questions
            st.session_state.current_poll_data = poll_data
            st.success("Questions uploaded successfully!")

        if poll_data["questions"]:
            st.write("Current Questions:")
            for i, question in enumerate(poll_data["questions"], 1):
                st.write(f"{i}. {question}")

        base_url = "https://poller.streamlit.app"
        poll_url = f"{base_url}/?page=poll&poll_id={poll_data['id']}"
        qr_bytes = get_qr_image_bytes(poll_url)
        st.image(qr_bytes, caption="Scan this QR code to access the poll")
        st.write(f"Poll URL: {poll_url}")

    else:
        st.warning("No active poll. Create a new poll to get started.")

def poll_page():
    st.title("User Poll")
    
    query_params = st.experimental_get_query_params()
    poll_id = query_params.get('poll_id', [None])[0] or st.session_state.current_poll_id

    if not poll_id:
        st.error("No poll ID provided.")
        return

    poll_data = supabase.table("polls").select("*").eq("id", poll_id).execute()
    if not poll_data.data or not poll_data.data[0]["active"]:
        st.error("This poll is not active or does not exist.")
        return

    questions = poll_data.data[0]["questions"]

    if not questions:
        st.warning("No questions available for this poll.")
    else:
        st.write(f"Poll ID: {poll_id}")
        name = st.text_input("Name")
        email = st.text_input("Email")

        user_responses = []
        for i, question in enumerate(questions):
            try:
                q_type, q_text = question.split(":", 1)
                q_type = q_type.strip().lower()
                q_text = q_text.strip()
            except ValueError:
                st.error(f"Invalid question format: {question}")
                continue

            if q_type == "text":
                answer = st.text_input(q_text, key=f"q_{i}")
            elif q_type == "textarea":
                answer = st.text_area(q_text, key=f"q_{i}")
            elif q_type == "select":
                options = q_text.split(":")[1].split(",")
                answer = st.selectbox(q_text.split(":")[0], options, key=f"q_{i}")
            elif q_type == "multiselect":
                options = q_text.split(":")[1].split(",")
                answer = st.multiselect(q_text.split(":")[0], options, key=f"q_{i}")
            elif q_type == "slider":
                min_val, max_val, step = map(int, q_text.split(":")[1].split(","))
                answer = st.slider(q_text.split(":")[0], min_val, max_val, step, key=f"q_{i}")
            elif q_type == "number":
                answer = st.number_input(q_text, key=f"q_{i}")
            elif q_type == "date":
                answer = st.date_input(q_text, key=f"q_{i}")
            elif q_type == "time":
                answer = st.time_input(q_text, key=f"q_{i}")
            elif q_type == "file":
                uploaded_file = st.file_uploader(q_text, key=f"q_{i}")
                if uploaded_file is not None:
                    answer = {
                        "filename": uploaded_file.name,
                        "content_type": uploaded_file.type,
                        "size": uploaded_file.size,
                        "uploaded": False
                    }
                else:
                    answer = None
            else:
                st.error(f"Unknown question type: {q_type}")
                continue

            user_responses.append(answer)

        if st.button("Submit Responses"):
            if not name or not email:
                st.error("Please enter your name and email.")
                return

            try:
                for i, response in enumerate(user_responses):
                    if isinstance(response, dict) and 'uploaded' in response and not response['uploaded']:
                        file_uploader_key = f"q_{i}"
                        uploaded_file = st.session_state[file_uploader_key]
                        file_extension = os.path.splitext(uploaded_file.name)[1]
                        unique_filename = f"{poll_id}_{i}_{int(time.time())}{file_extension}"
                        
                        file_bytes = uploaded_file.read()
                        storage_client = supabase.storage
                        bucket = storage_client.from_('poll_files')
                        res = bucket.upload(file=file_bytes, path=unique_filename, file_options={"content-type": uploaded_file.type})
                        
                        if res:
                            file_url = bucket.get_public_url(unique_filename)
                            user_responses[i] = {
                                "filename": uploaded_file.name,
                                "url": file_url,
                                "content_type": uploaded_file.type,
                                "size": uploaded_file.size,
                                "uploaded": True
                            }
                        else:
                            raise Exception("Upload failed")

                response_data = {
                    "poll_id": poll_id,
                    "name": name,
                    "email": email,
                    "responses": user_responses
                }

                result = supabase.table("responses").insert(response_data).execute()
                st.success("Thank you for your responses!")
            except Exception as e:
                st.error(f"Error submitting responses: {str(e)}")

def results_page():
    st.title("Poll Results")
    
    if not check_user_session():
        st.warning("Please log in to view poll results.")
        return

    current_user_id = st.session_state.user_id
    all_polls = supabase.table("polls").select("id, questions, active").eq("created_by", current_user_id).execute()

    if not all_polls.data:
        st.info("You haven't created any polls yet.")
        return

    poll_options = {poll['id']: f"Poll {poll['id']} ({'Active' if poll['active'] else 'Inactive'})" for poll in all_polls.data}
    selected_poll_id = st.selectbox("Select a poll to view results", options=list(poll_options.keys()), format_func=lambda x: poll_options[x])

    poll_data = supabase.table("polls").select("*").eq("id", selected_poll_id).execute()
    
    if not poll_data.data:
        st.warning("No poll found with this ID.")
        return

    poll = poll_data.data[0]
    questions = poll["questions"]

    if not poll['active']:
        st.warning("This poll is currently inactive. Activate the poll to collect responses.")

    responses = supabase.table("responses").select("*").eq("poll_id", selected_poll_id).execute()

    if not responses.data:
        st.info("This poll has not received any responses yet.")
        return

    st.write(f"Total responses: {len(responses.data)}")

    selected_questions = st.multiselect("Select questions to visualize", options=questions, default=questions[:1])
    visual_type = st.selectbox("Select visualization type", options=["Bar Chart", "Pie Chart", "Scatter Plot"])

    for question in selected_questions:
        question_parts = question.split(":", 1)
        if len(question_parts) > 1:
            q_text = question_parts[1].strip()
        else:
            q_text = question.strip()

        st.subheader(f"Results for: {q_text}")

        question_index = questions.index(question)
        answers = [response['responses'][question_index] for response in responses.data if question_index < len(response['responses'])]
        
        answer_counts = pd.Series(answers).value_counts()

        try:
            if visual_type == "Bar Chart":
                if len(answer_counts) == 0:
                    st.warning(f"No data available for the question: {q_text}")
                    continue
                fig = px.bar(x=answer_counts.index, y=answer_counts.values, labels={'x': 'Answer', 'y': 'Count'})
            elif visual_type == "Pie Chart":
                if len(answer_counts) == 0:
                    st.warning(f"No data available for the question: {q_text}")
                    continue
                fig = px.pie(values=answer_counts.values, names=answer_counts.index)
            elif visual_type == "Scatter Plot":
                if len(answer_counts) < 2:
                    st.warning(f"Scatter plot requires at least two different answers for the question: {q_text}")
                    continue
                fig = px.scatter(x=range(len(answer_counts)), y=answer_counts.values, text=answer_counts.index)
                fig.update_traces(textposition='top center')
            
            st.plotly_chart(fig)
        except Exception as e:
            st.error(f"Error creating {visual_type} for question: {q_text}. Please try a different visualization type.")
            st.error(f"Error details: {str(e)}")

    st.markdown("---")

    # Display metadata at the bottom of the page
    st.subheader("Poll Metadata")
    st.write(f"Poll ID: {selected_poll_id}")
    st.write(f"Poll created at: {poll.get('created_at', 'Not available')}")
    st.write(f"Last updated at: {poll.get('updated_at', 'Not available')}")
    st.write(f"Poll status: {'Active' if poll['active'] else 'Inactive'}")


def create_zip_of_uploaded_files(poll_id):
    # Get all responses for this poll
    responses = supabase.table("responses").select("*").eq("poll_id", poll_id).execute()
    
    # Create a temporary zip file
    zip_filename = f"{poll_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for response in responses.data:
            for i, answer in enumerate(response['responses']):
                if isinstance(answer, dict) and 'url' in answer:
                    file_url = answer['url']
                    original_filename = answer['filename']
                    file_name = f"{response['name']}_{i+1}_{original_filename}"
                    
                    # Download the file content using requests
                    file_response = requests.get(file_url)
                    if file_response.status_code == 200:
                        content_type = file_response.headers.get('content-type', '')
                        if 'text/html' in content_type:
                            st.warning(f"File {original_filename} appears to be HTML, not the expected file type.")
                            continue
                        
                        file_data = file_response.content
                        
                        # Add file to zip
                        zipf.writestr(file_name, file_data)
                    else:
                        st.warning(f"Failed to download file: {original_filename}. Status code: {file_response.status_code}")
    
    return zip_filename

# Main app
def main():
    st.sidebar.image("https://tuonlineresources.com/apps/poller/images/logo-256.png", use_column_width=True)
    st.sidebar.markdown("Poller+")
    st.sidebar.markdown("Polling and information gathering for Tiffin University research. Private and secure.")

    # Check if the user is already logged in
    if check_user_session():  # Check if session state contains the logged-in user
        load_current_poll()
        # Automatically switch to the Admin page if the user is logged in
        page = st.sidebar.selectbox("Select a page", ["Admin", "Poll", "Results"], index=0)
        if st.sidebar.button("Logout"):
            logout_user()
            st.experimental_rerun()  # Rerun the app after logout
    else:
        page = "Login"

    if page == "Login":
        st.title("Admin Login / Register")

        # Create Tabs for Login and Registration
        tab1, tab2 = st.tabs(["Login", "Register"])

        # Login Tab
        with tab1:
            st.header("Login")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                if login_user(email, password):
                    st.experimental_rerun()  # Rerun the app after login
                else:
                    st.error("Login failed. Please check your credentials or contact support.")

        # Register Tab
        with tab2:
            st.header("Register")
            reg_email = st.text_input("Register Email")
            reg_password = st.text_input("Register Password", type="password")
            if st.button("Register"):
                if register_user(reg_email, reg_password):
                    st.success("Registration successful! Please log in.")
                else:
                    st.error("Registration failed. Please try again or contact support.")

    elif page == "Admin":
        admin_page()
    elif page == "Poll":
        poll_page()
    elif page == "Results":
        results_page()

    if st.session_state.get('current_poll_id'):
        st.sidebar.write(f"Current Poll ID: {st.session_state.current_poll_id}")

# Improved login function with detailed error logging
def login_user(email, password):
    try:
        user = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = user
        st.session_state.user_id = user.user.id
        return True
    except Exception as e:
        st.error(f"Login failed: {str(e)}")  # More detailed error reporting
        print(f"Login Error Details: {str(e)}")  # Debugging print
        return False

# Registration function
def register_user(email, password):
    try:
        user = supabase.auth.sign_up({"email": email, "password": password})
        st.success("Registration successful! Please log in.")
        return True
    except Exception as e:
        st.error(f"Registration failed: {str(e)}")
        print(f"Registration Error Details: {str(e)}")  # Debugging print
        return False

if __name__ == "__main__":
    main()
