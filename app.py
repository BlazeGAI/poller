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

# Supabase credentials
SUPABASE_URL = "https://czivxiadenrdpxebnqpu.supabase.co"  # Replace with your actual Supabase URL
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN6aXZ4aWFkZW5yZHB4ZWJucXB1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjU1NjgxOTQsImV4cCI6MjA0MTE0NDE5NH0.i_xLmpxQlUfHGq_Hs9DzvaQPWciGD_FZuxAEo0caAvM"  # Replace with your actual Supabase Key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    st.title("Admin Page")
    
    # Add a small logo to the upper-right corner using HTML/CSS
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
    
    st.image("https://tuonlineresources.com/apps/poller/images/logo-icon.png", width=50)  # Small logo in upper-right corner
    
    # Input field to enter a custom Poll ID
    custom_poll_id = st.text_input("Enter Custom Poll ID", key="custom_poll_id_input")
    
    if custom_poll_id:
        st.session_state.poll_id = custom_poll_id
    elif 'poll_id' not in st.session_state:
        st.session_state.poll_id = generate_poll_id()

    poll_id = st.session_state.poll_id
    
    st.write("Your Poll ID is:")
    st.code(poll_id)
    st.write("(Use this ID to view results or share with other admins)")

    # Check if poll exists in Supabase
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

        # Save poll status to Supabase
        if poll_data.data:
            supabase.table("polls").update({"active": poll_active}).eq("id", poll_id).execute()
        else:
            supabase.table("polls").insert({"id": poll_id, "questions": questions, "active": poll_active}).execute()
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

    st.write("Current Questions:")
    for i, question in enumerate(questions, 1):
        st.write(f"{i}. {question}")

    # Download Responses as Excel functionality
    if st.button("Download Responses as Excel", key="download_responses"):
        responses_data = supabase.table("responses").select("*").eq("poll_id", poll_id).execute()
        responses = responses_data.data
        
        if not responses:
            st.warning("No responses available for this poll.")
        else:
            headers = ["id", "name", "email"] + [f"q_{i+1}" for i in range(len(questions))]
            data = []
            for response in responses:
                row = [response["id"], response["name"], response["email"]] + response["responses"]
                data.append(row)
            
            df = pd.DataFrame(data, columns=headers)
            st.write(df)
            
            # Ensure the Excel file can be downloaded correctly
            excel_file = BytesIO()
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Responses')
            excel_file.seek(0)  # Reset the stream position to the beginning
            
            st.download_button(
                label="Download Excel file",
                data=excel_file,
                file_name="responses.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    # New button for downloading all uploaded files
    if st.button("Download All Uploaded Files"):
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
 
def poll_page():
    st.title("User Poll")

    query_params = st.experimental_get_query_params()
    poll_id = query_params.get('poll_id', [None])[0]

    if not poll_id:
        poll_id = st.text_input("Enter Poll ID")
        if not poll_id:
            st.error("Invalid poll ID. Please use the provided QR code or URL to access the poll.")
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
                    # Generate a unique file name
                    file_extension = os.path.splitext(uploaded_file.name)[1]
                    unique_filename = f"{poll_id}_{i}_{int(time.time())}{file_extension}"
                    
                    st.write(f"File selected: {uploaded_file.name}")
                    
                    # Store file information without uploading
                    answer = {
                        "file": uploaded_file,
                        "filename": unique_filename,
                        "original_filename": uploaded_file.name,
                        "content_type": uploaded_file.type,
                        "uploaded": False
                    }
                    
                    # Get the storage client (but don't upload yet)
                    storage_client = supabase.storage
                    bucket = storage_client.from_('poll_files')
                    
                    # Store the bucket information for later use
                    answer["bucket"] = bucket
                else:
                    answer = None
            else:
                st.error(f"Unknown question type: {q_type}")
                continue

            # Ensure only serializable data is appended
            user_responses.append(answer)

    if st.button("Submit"):
        if not name or not email:
            st.error("Please enter your name and email.")
            return
    
        try:
            # Process file uploads
            for i, response in enumerate(user_responses):
                if isinstance(response, dict) and 'file' in response and not response['uploaded']:
                    uploaded_file = response['file']
                    file_bytes = uploaded_file.read()
                    bucket = response['bucket']
                    
                    # Upload the file
                    res = bucket.upload(file=file_bytes, path=response['filename'], file_options={"content-type": response['content_type']})
                    
                    # Check the response and update user_responses
                    # (Add your response checking logic here)
    
            # Insert the poll responses into the database
            # (Add your database insertion logic here)
    
            st.success("Thank you for your responses!")
        except Exception as e:
            st.error(f"Error submitting responses: {str(e)}")

def results_page():
    st.title("Poll Results")
    
    default_poll_id = st.session_state.get('poll_id', "")
    poll_id = st.text_input("Enter Poll ID", value=default_poll_id)
    
    if poll_id:
        all_questions = supabase.table("polls").select("questions").eq("id", poll_id).execute()
        all_responses = supabase.table("responses").select("*").eq("poll_id", poll_id).execute()
        
        questions = all_questions.data[0]["questions"] if all_questions.data else []
        responses = all_responses.data

        if not questions:
            st.warning("No questions available for this poll.")
        elif not responses:
            st.write("No responses yet for this poll.")
        else:
            for i, question in enumerate(questions):
                st.write(f"\nQuestion {i+1}: {question}")
                options = ["Yes", "No", "Maybe"]
                counts = {option: sum(1 for r in responses if r["responses"][i] == option) for option in options}
                
                st.write("Response Counts:")
                for option, count in counts.items():
                    st.write(f"{option}: {count}")
                
                st.bar_chart(counts)

            st.write(f"\nTotal Responses: {len(responses)}")

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
                    
                    # Download the file from Supabase
                    storage_client = supabase.storage
                    bucket = storage_client.from_('poll_files')
                    file_data = bucket.download(file_url.split('/')[-1])
                    
                    # Add file to zip
                    zipf.writestr(file_name, file_data)
    
    return zip_filename

# Main app
def main():
    query_params = st.experimental_get_query_params()
    
    # Add logo and description to the sidebar
    st.sidebar.image("https://tuonlineresources.com/apps/poller/images/logo-256.png", use_column_width=True)  # Add the logo
    st.sidebar.markdown("Poller+")  # Add the app name
    st.sidebar.markdown("Polling and information gathering for Tiffin University research. Private and secure.")  # Add app description
    
    if 'page' in query_params and query_params['page'][0] == 'poll':
        poll_page()
    else:
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Select a page", ["Admin", "Poll", "Results"], key="page_radio")

        if page == "Admin":
            admin_page()
        elif page == "Poll":
            poll_page()
        elif page == "Results":
            results_page()

if __name__ == "__main__":
    main()
