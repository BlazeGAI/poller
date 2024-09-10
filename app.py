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
SUPABASE_URL = "https://czivxiadenrdpxebnqpu.supabase.co"  # Replace with your actual Supabase URL
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN6aXZ4aWFkZW5yZHB4ZWJucXB1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjU1NjgxOTQsImV4cCI6MjA0MTE0NDE5NH0.i_xLmpxQlUfHGq_Hs9DzvaQPWciGD_FZuxAEo0caAvM"  # Replace with your actual Supabase Key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def extract_file_info(answer):
    if isinstance(answer, dict) and 'filename' in answer and 'url' in answer:
        url = answer['url'].rstrip('?')  # Remove trailing question mark
        return answer['filename'], url
    elif isinstance(answer, list):
        return ', '.join(answer), ''  # Join list items with comma and space
    return str(answer), ''  # Convert to string for all other types

def admin_registration():
    st.title("Admin Registration")
    
    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    email = st.text_input("Tiffin University Email")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Register"):
        if not first_name or not last_name or not email or not password or not confirm_password:
            st.error("All fields are required.")
            return

        if not email.endswith("@tiffin.edu"):
            st.error("Please use a valid Tiffin University email address.")
            return

        if password != confirm_password:
            st.error("Passwords do not match.")
            return

        try:
            # Attempt to create a new user in Supabase
            user = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "first_name": first_name,
                        "last_name": last_name
                    }
                }
            })
            st.success("Registration successful! Please log in with your new credentials.")
            return True  # Indicate successful registration
        except Exception as e:
            st.error(f"Registration failed: {str(e)}")
            return False  # Indicate failed registration

    return False  # No registration attempt made
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

# Page functions
def admin_page():
    st.markdown(
        """
        <style>
        [data-testid="stHeader"] {
            display: flex;
            justify-content: space-between;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.image("https://tuonlineresources.com/apps/poller/images/logo-icon.png", width=50)

    if 'user' not in st.session_state or not st.session_state.user:
        st.title("Admin Login")
        
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = "Login"
        
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", key="login_button"):
                try:
                    user = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = user
                    st.session_state.user_id = user.user.id  # Store user ID in session state
                    st.success("Login successful!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {str(e)}")
        
        with tab2:
            with st.form("registration_form"):
                first_name = st.text_input("First Name", key="reg_first_name")
                last_name = st.text_input("Last Name", key="reg_last_name")
                reg_email = st.text_input("Tiffin University Email", key="reg_email")
                reg_password = st.text_input("Password", type="password", key="reg_password")
                confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")
                
                submit_button = st.form_submit_button("Register")
                
                if submit_button:
                    if not first_name or not last_name or not reg_email or not reg_password or not confirm_password:
                        st.error("All fields are required.")
                    elif not reg_email.endswith("@tiffin.edu"):
                        st.error("Please use a valid Tiffin University email address.")
                    elif reg_password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            user = supabase.auth.sign_up({
                                "email": reg_email,
                                "password": reg_password,
                                "options": {
                                    "data": {
                                        "first_name": first_name,
                                        "last_name": last_name
                                    }
                                }
                            })
                            st.success("Registration successful! Please log in with your new credentials.")
                            st.session_state.active_tab = "Login"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Registration failed: {str(e)}")
    else:
        st.title("Admin Page")

        custom_poll_id = st.text_input("Enter Custom Poll ID", key="custom_poll_id_input")
        
        if custom_poll_id:
            st.session_state.current_poll_id = custom_poll_id
        elif 'current_poll_id' not in st.session_state:
            st.session_state.current_poll_id = generate_poll_id()

        poll_id = st.session_state.current_poll_id
        
        st.write("Your Poll ID is:")
        st.code(poll_id)
        st.write("(Use this ID to view results or share with other admins)")

        try:
            poll_data = supabase.table("polls").select("*").eq("id", poll_id).execute()
            poll_active = False
            questions = []
            if poll_data.data:
                poll_active = poll_data.data[0]["active"]
                questions = poll_data.data[0]["questions"]

            poll_active = st.checkbox("Poll Active", value=poll_active, key=f"poll_active_{poll_id}")

            if poll_active:
                st.success("Poll is active!")
            else:
                st.warning("Poll is inactive.")

            current_time = datetime.now().isoformat()
            if poll_data.data:
                supabase.table("polls").update({
                    "active": poll_active,
                    "updated_at": current_time
                }).eq("id", poll_id).execute()
            else:
                supabase.table("polls").insert({
                    "id": poll_id,
                    "questions": questions,
                    "active": poll_active,
                    "created_at": current_time,
                    "updated_at": current_time,
                    "created_by": st.session_state.user_id
                }).execute()
        except Exception as e:
            st.error(f"Error querying Supabase: {e}")

        base_url = "https://poller.streamlit.app"  # Replace with your actual base URL
        poll_url = f"{base_url}/?page=poll&poll_id={poll_id}"
        qr_bytes = get_qr_image_bytes(poll_url)
        st.image(qr_bytes, caption="Scan this QR code to access the poll")
        st.write(f"Poll URL: {poll_url}")

        uploaded_file = st.file_uploader("Upload questions file", type="txt", key="questions_uploader")
        if uploaded_file is not None:
            questions = [line.decode("utf-8").strip() for line in uploaded_file.readlines() if line.strip()]
            supabase.table("polls").update({"questions": questions}).eq("id", poll_id).execute()
            st.success("Questions uploaded successfully!")

        # Show current questions only if there are any
        if questions:
            st.write("Current Questions:")
            for i, question in enumerate(questions, 1):
                st.write(f"{i}. {question}")

        # Check if there are any responses
        responses_data = supabase.table("responses").select("*").eq("poll_id", poll_id).execute()
        responses = responses_data.data if responses_data else []

        if responses:
            # Show download responses button only if there are responses
            if st.button("Download Responses as Excel", key="download_responses"):
                headers = ["id", "name", "email"]
                data = []
                for response in responses:
                    row = [response["id"], response["name"], response["email"]]
                    for i, answer in enumerate(response["responses"]):
                        filename, url = extract_file_info(answer)
                        if url:  # If it's a file upload question
                            headers.extend([f"q_{i+1}_file_name", f"q_{i+1}_file_URL"])
                            row.extend([filename, url])
                        else:
                            headers.append(f"q_{i+1}")
                            row.append(filename)  # filename here is actually the original answer
                    data.append(row)
            
                df = pd.DataFrame(data, columns=headers)
                
                # Ensure the Excel file can be downloaded correctly
                excel_file = BytesIO()
                with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Responses')
                    worksheet = writer.sheets['Responses']
                    for column in worksheet.columns:
                        max_length = 0
                        column = [cell for cell in column]
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(cell.value)
                            except:
                                pass
                        adjusted_width = (max_length + 2)
                        worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
                excel_file.seek(0)  # Reset the stream position to the beginning
                
                st.download_button(
                    label="Download Excel file",
                    data=excel_file,
                    file_name="responses.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # Show download all uploads button only if there are file uploads
            if any(isinstance(answer, dict) and 'url' in answer for response in responses for answer in response['responses']):
                if st.button("Download All Uploaded Files", key="download_uploads"):
                    with st.spinner("Preparing zip file..."):
                        zip_filename = create_zip_of_uploaded_files(poll_id)
                    
                    # Read the zip file
                    with open(zip_filename, "rb") as f:
                        zip_contents = f.read()
                    
                    # Offer the zip file for download
                    st.download_button(
                        label="Download Zip File",
                        data=zip_contents,
                        file_name=zip_filename,
                        mime="application/zip"
                    )
                    
                    # Clean up: remove the temporary zip file
                    os.remove(zip_filename)

        # Debug information
        # Add a toggle for debug messages at the bottom of the page
        st.write("---")  # Add a separator line
        show_debug = st.toggle("Show Debug Messages", value=False)

        if show_debug:
            st.write("Debug Information:")
            st.write(f"Debug: Current Poll ID: {poll_id}")
            if 'responses' in locals():
                st.write(f"Debug: Number of responses: {len(responses)}")
            st.write("Debug: Attempting to retrieve responses")
            try:
                responses_data = supabase.table("responses").select("*").eq("poll_id", poll_id).execute()
                st.write("Debug: Raw Supabase response", responses_data)
                st.write("Debug: Responses data", responses_data.data)
                st.write(f"Debug: Number of responses: {len(responses_data.data)}")
            except Exception as e:
                st.error(f"Error retrieving responses: {str(e)}")
                st.write("Debug: Full error information", e)
                st.write("Debug: Error type", type(e).__name__)

def poll_page():
    st.title("User Poll")

    query_params = st.experimental_get_query_params()
    poll_id = query_params.get('poll_id', [None])[0]

    if not poll_id:
        if 'current_poll_id' in st.session_state:
            poll_id = st.session_state.current_poll_id
            st.write(f"Currently selected poll: {poll_id}")
        else:
            poll_id = st.text_input("Enter Poll ID")

    if not poll_id:
        st.error("Please enter a valid poll ID.")
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
        file_url = None  # Placeholder for the file URL
        for i, question in enumerate(questions):
            try:
                q_type, q_text = question.split(":", 1)
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
                answer = str(st.date_input(q_text, key=f"q_{i}"))  # Convert date to string
            elif q_type == "time":
                answer = str(st.time_input(q_text, key=f"q_{i}"))  # Convert time to string
            elif q_type == "file":
                uploaded_file = st.file_uploader(q_text, key=f"q_{i}")
                if uploaded_file is not None:
                    st.write(f"File selected: {uploaded_file.name}")
                    # Store only the necessary file information
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

            # Ensure only serializable data is appended
            user_responses.append(answer)

        if st.button("Submit"):
            st.write("Debug: Submit button clicked")
            if not name or not email:
                st.error("Please enter your name and email.")
                return
        
            try:
                st.write("Debug: Starting submission process")
                
                # Process file uploads
                for i, response in enumerate(user_responses):
                    if isinstance(response, dict) and 'uploaded' in response and not response['uploaded']:
                        st.write(f"Debug: Processing file upload for question {i+1}")
                        
                        # Get the file uploader object
                        file_uploader_key = f"q_{i}"
                        uploaded_file = st.session_state[file_uploader_key]
                        
                        # Generate a unique file name
                        file_extension = os.path.splitext(uploaded_file.name)[1]
                        unique_filename = f"{poll_id}_{i}_{int(time.time())}{file_extension}"
                        
                        try:
                            # Read file bytes
                            file_bytes = uploaded_file.read()
                            
                            # Upload the file
                            storage_client = supabase.storage
                            bucket = storage_client.from_('poll_files')
                            res = bucket.upload(file=file_bytes, path=unique_filename, file_options={"content-type": uploaded_file.type})
                            
                            if res:  # Supabase storage upload returns True on success
                                file_url = bucket.get_public_url(unique_filename)
                                user_responses[i] = {
                                    "filename": uploaded_file.name,
                                    "url": file_url,
                                    "content_type": uploaded_file.type,
                                    "size": uploaded_file.size,
                                    "uploaded": True  # Set to True after successful upload
                                }
                                st.success(f"File {uploaded_file.name} uploaded successfully.")
                            else:
                                raise Exception("Upload failed")
                        except Exception as e:
                            st.error(f"Error during file upload: {str(e)}")
                            user_responses[i] = {
                                "filename": uploaded_file.name,
                                "content_type": uploaded_file.type,
                                "size": uploaded_file.size,
                                "uploaded": False
                            }
        
                # Prepare response data
                response_data = {
                    "poll_id": poll_id,
                    "name": name,
                    "email": email,
                    "responses": user_responses
                }
                st.write("Debug: Response data prepared", response_data)
        
                # Insert the poll responses
                st.write("Debug: Attempting to insert data into Supabase")
                result = supabase.table("responses").insert(response_data).execute()
                st.write("Debug: Supabase insert result", result)
        
                st.success("Thank you for your responses!")
            except Exception as e:
                st.error(f"Error submitting responses: {str(e)}")
                st.write("Debug: Full error information", e)
                st.write("Debug: Error type", type(e).__name__)

def results_page():
    st.title("Poll Results")

    current_user_id = st.session_state.user_id
    all_polls = supabase.table("polls").select("id, questions").eq("created_by", current_user_id).execute()

    if not all_polls.data:
        st.warning("You haven't created any polls yet.")
        return

    poll_options = {poll['id']: f"Poll {poll['id']}" for poll in all_polls.data}

    selected_poll_id = st.selectbox(
        "Select a poll to view results",
        options=list(poll_options.keys()),
        format_func=lambda x: poll_options[x]
    )

    poll_data = supabase.table("polls").select("*").eq("id", selected_poll_id).execute()
    
    if not poll_data.data:
        st.warning("No poll found with this ID.")
        return

    poll = poll_data.data[0]
    questions = poll["questions"]

    if isinstance(questions, str):
        try:
            questions = json.loads(questions)
        except json.JSONDecodeError:
            questions = questions.split('\n')
    elif not isinstance(questions, list):
        st.warning("Invalid question format in the database.")
        return

    responses = supabase.table("responses").select("*").eq("poll_id", selected_poll_id).execute()

    if not responses.data:
        st.warning("No responses available for this poll.")
        return

    # Display total responses just under the title
    st.write(f"Total responses: {len(responses.data)}")

    selected_questions = st.multiselect(
        "Select questions to visualize",
        options=questions,
        default=questions[:1]
    )

    visual_type = st.selectbox(
        "Select visualization type",
        options=["Bar Chart", "Pie Chart", "Scatter Plot"]
    )

    for question in selected_questions:
        question_index = questions.index(question)
        answers = [response['responses'][question_index] for response in responses.data if question_index < len(response['responses'])]
        
        answer_counts = pd.Series(answers).value_counts()

        # Parse the question text
        question_parts = question.split(':', 1)
        if len(question_parts) > 1:
            question_text = question_parts[1].strip()
        else:
            question_text = question.strip()

        # Format the question text
        formatted_question = f"Results for: {question_text}"
        st.subheader(formatted_question)

        try:
            if visual_type == "Bar Chart":
                if len(answer_counts) == 0:
                    st.warning(f"No data available for the question: {question_text}")
                    continue
                fig = px.bar(x=answer_counts.index, y=answer_counts.values, labels={'x': 'Answer', 'y': 'Count'})
            elif visual_type == "Pie Chart":
                if len(answer_counts) == 0:
                    st.warning(f"No data available for the question: {question_text}")
                    continue
                fig = px.pie(values=answer_counts.values, names=answer_counts.index)
            elif visual_type == "Scatter Plot":
                if len(answer_counts) < 2:
                    st.warning(f"Scatter plot requires at least two different answers for the question: {question_text}")
                    continue
                fig = px.scatter(x=range(len(answer_counts)), y=answer_counts.values, text=answer_counts.index)
                fig.update_traces(textposition='top center')
            
            st.plotly_chart(fig)
        except Exception as e:
            st.error(f"Error creating {visual_type} for question: {question_text}. Please try a different visualization type.")
            st.error(f"Error details: {str(e)}")

    # Add a separator line
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
    query_params = st.experimental_get_query_params()
    
    # Add logo and description to the sidebar
    with st.sidebar:
        st.image("https://tuonlineresources.com/apps/poller/images/logo-256.png", use_column_width=True)
        st.markdown("Poller+")
        st.markdown("Polling and information gathering for Tiffin University research. Private and secure.")
        
        # Display current poll ID if available
        if 'current_poll_id' in st.session_state:
            st.write(f"Current Poll ID: {st.session_state.current_poll_id}")
        
        # Add logout button if user is logged in
        if 'user' in st.session_state and st.session_state.user:
            if st.button("Logout", key="sidebar_logout"):
                supabase.auth.sign_out()
                st.session_state.user = None
                if 'current_poll_id' in st.session_state:
                    del st.session_state.current_poll_id
                st.success("Logged out successfully!")
                st.rerun()
    
    if 'page' in query_params and query_params['page'][0] == 'poll':
        poll_page()
    else:
        page = st.sidebar.radio("Select a page", ["Admin", "Poll", "Results"], key="page_radio")

        if page == "Admin":
            admin_page()
        elif page == "Poll":
            poll_page()
        elif page == "Results":
            results_page()

if __name__ == "__main__":
    main()
