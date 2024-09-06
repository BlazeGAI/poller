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

# File paths
RESPONSES_FILE = "responses.json"
QUESTIONS_FILE = "questions.json"
POLL_STATUS_FILE = "poll_status.json"

# Helper functions
def load_data(filename):
    for _ in range(5):  # Try up to 5 times
        try:
            if os.path.exists(filename):
                with open(filename, "r") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            return {}  # Return an empty dict if file doesn't exist
        except json.JSONDecodeError:
            time.sleep(0.1)  # Wait a bit before trying again
    return {}  # If still fails after 5 attempts, return empty dict

def save_data(data, filename):
    for _ in range(5):  # Try up to 5 times
        try:
            with open(filename, "w") as f:
                json.dump(data, f)
            return
        except:
            time.sleep(0.1)  # Wait a bit before trying again
    st.error("Failed to save data. Please try again.")

def generate_qr(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img

def get_qr_image_bytes(url):
    qr_img = generate_qr(url)
    buf = BytesIO()
    qr_img.save(buf, format="PNG")
    return buf.getvalue()

def generate_poll_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Page functions
def admin_page():
    st.title("Admin Page")
    
    # Input field to enter an existing poll ID
    existing_poll_id = st.text_input("Enter Poll ID to Load Existing Poll")
    
    if existing_poll_id:
        st.session_state.poll_id = existing_poll_id
    elif 'poll_id' not in st.session_state:
        st.session_state.poll_id = generate_poll_id()

    poll_id = st.session_state.poll_id
    
    st.write("Your Poll ID is:")
    st.code(poll_id)
    st.write("(Use this ID to view results or share with other admins)")

    poll_status = load_data(POLL_STATUS_FILE)
    poll_active = poll_status.get(poll_id, False)

    poll_active = st.checkbox("Poll Active", value=poll_active, key=f"poll_active_{poll_id}")

    if poll_active:
        st.success("Poll is active!")
    else:
        st.warning("Poll is inactive.")

    poll_status[poll_id] = poll_active
    save_data(poll_status, POLL_STATUS_FILE)

    base_url = "https://poller.streamlit.app"  # Replace with your actual base URL
    poll_url = f"{base_url}/?page=poll&poll_id={poll_id}"
    qr_bytes = get_qr_image_bytes(poll_url)
    st.image(qr_bytes, caption="Scan this QR code to access the poll")
    st.write(f"Poll URL: {poll_url}")

    uploaded_file = st.file_uploader("Upload questions file", type="txt")
    if uploaded_file is not None:
        questions = [line.decode("utf-8").strip() for line in uploaded_file.readlines() if line.strip()]
        all_questions = load_data(QUESTIONS_FILE)
        all_questions[poll_id] = questions
        save_data(all_questions, QUESTIONS_FILE)
        st.success("Questions uploaded successfully!")

    st.write("Current Questions:")
    questions = load_data(QUESTIONS_FILE).get(poll_id, [])
    for i, question in enumerate(questions, 1):
        st.write(f"{i}. {question}")

    if st.button("Download Responses as Excel"):
        all_responses = load_data(RESPONSES_FILE)
        responses = all_responses.get(poll_id, [])
        
        if not responses:
            st.warning("No responses available for this poll.")
        else:
            # Create DataFrame with appropriate headers
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

    poll_status = load_data(POLL_STATUS_FILE)
    if not poll_status.get(poll_id, False):
        st.error("This poll is not active.")
        return

    all_questions = load_data(QUESTIONS_FILE)
    all_responses = load_data(RESPONSES_FILE)
    
    questions = all_questions.get(poll_id, [])

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

            new_responses = all_responses if isinstance(all_responses, dict) else {}
            if poll_id not in new_responses:
                new_responses[poll_id] = []
            response_id = len(new_responses[poll_id]) + 1
            new_responses[poll_id].append({"id": response_id, "name": name, "email": email, "responses": user_responses})
            save_data(new_responses, RESPONSES_FILE)
            st.success("Thank you for your responses!")

def results_page():
    st.title("Poll Results")
    
    default_poll_id = st.session_state.get('poll_id', "")
    poll_id = st.text_input("Enter Poll ID", value=default_poll_id)
    
    if poll_id:
        all_questions = load_data(QUESTIONS_FILE)
        all_responses = load_data(RESPONSES_FILE)
        
        questions = all_questions.get(poll_id, [])
        responses = all_responses.get(poll_id, [])

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
