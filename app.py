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

# Supabase credentials
SUPABASE_URL = "https://czivxiadenrdpxebnqpu.supabase.co"  # Replace with your Supabase URL
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN6aXZ4aWFkZW5yZHB4ZWJucXB1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjU1NjgxOTQsImV4cCI6MjA0MTE0NDE5NH0.i_xLmpxQlUfHGq_Hs9DzvaQPWciGD_FZuxAEo0caAvM"  # Replace with your Supabase Key
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
    
    # Input field to enter a custom Poll ID
    custom_poll_id = st.text_input("Enter Custom Poll ID")
    
    if custom_poll_id:
        st.session_state.poll_id = custom_poll_id
    elif 'poll_id' not in st.session_state:
        st.session_state.poll_id = generate_poll_id()

    poll_id = st.session_state.poll_id
    
    st.write("Your Poll ID is:")
    st.code(poll_id)
    st.write("(Use this ID to view results or share with other admins)")
    
    # Check if poll exists in Supabase
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

    base_url = "https://poller.streamlit.app"  # Replace with your actual base URL
    poll_url = f"{base_url}/?page=poll&poll_id={poll_id}"
    qr_bytes = get_qr_image_bytes(poll_url)
    st.image(qr_bytes, caption="Scan this QR code to access the poll")
    st.write(f"Poll URL: {poll_url}")

    uploaded_file = st.file_uploader("Upload questions file", type="txt")
    if uploaded_file is not None:
        questions = [line.decode("utf-8").strip() for line in uploaded_file.readlines() if line.strip()]
        supabase.table("polls").update({"questions": questions}).eq("id", poll_id).execute()
        st.success("Questions uploaded successfully!")

    st.write("Current Questions:")
    for i, question in enumerate(questions, 1):
        st.write(f"{i}. {question}")

    if st.button("Download Responses as Excel"):
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
            
            excel_file = BytesIO()
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Responses')
            
            st.download_button(
                label="Download Excel file",
                data=excel_file.getvalue(),
                file_name="responses.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

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
        for i, question in enumerate(questions):
            q_type, q_text = question.split(":", 1)
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
                answer = st.file_uploader(q_text, key=f"q_{i}")
            else:
                st.error(f"Unknown question type: {q_type}")
                continue
            user_responses.append(answer)

        if st.button("Submit"):
            if not name or not email:
                st.error("Please enter your name and email.")
                return

            supabase.table("responses").insert({
                "poll_id": poll_id,
                "name": name,
                "email": email,
                "responses": user_responses
            }).execute()
            st.success("Thank you for your responses!")

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

# Main app
def main():
    query_params = st.experimental_get_query_params()
    if 'page' in query_params and query_params['page'][0] == 'poll':
        poll_page()
    else:
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Select a page", ["Admin", "Poll", "Results"])

        if page == "Admin":
            admin_page()
        elif page == "Poll":
            poll_page()
        elif page == "Results":
            results_page()

if __name__ == "__main__":
    main()
