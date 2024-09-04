import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image
import json
import os
import time
import random
import string

# File paths
RESPONSES_FILE = "responses.json"
QUESTIONS_FILE = "questions.json"

# Helper functions
def load_data(filename):
    for _ in range(5):  # Try up to 5 times
        try:
            if os.path.exists(filename):
                with open(filename, "r") as f:
                    return json.load(f)
            return {}
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
    
    if 'poll_id' not in st.session_state:
        st.session_state.poll_id = generate_poll_id()

    poll_id = st.session_state.poll_id
    
    st.write("Your Poll ID is:")
    st.code(poll_id)
    st.write("(Use this ID to view results or share with other admins)")

    poll_active = st.checkbox("Poll Active", value=False)

    if poll_active:
        st.success("Poll is active!")
    else:
        st.warning("Poll is inactive.")

    qr_bytes = get_qr_image_bytes(f"https://poller.streamlit.app/?page=poll&poll_id={poll_id}&poll_active={str(poll_active).lower()}")
    st.image(qr_bytes, caption="Scan this QR code to access the poll")

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

def poll_page():
    st.title("User Poll")
    
    query_params = st.experimental_get_query_params()
    poll_id = query_params.get('poll_id', [None])[0]
    poll_active = query_params.get('poll_active', ['false'])[0] == 'true'
    
    if not poll_id:
        st.error("Invalid poll ID. Please use the provided QR code to access the poll.")
        return

    st.write(f"Poll status: {'Active' if poll_active else 'Closed'}")

    questions = load_data(QUESTIONS_FILE).get(poll_id, [])
    all_responses = load_data(RESPONSES_FILE)

    if not questions:
        st.warning("No questions available for this poll.")
    else:
        user_responses = []
        for i, question in enumerate(questions):
            answer = st.radio(question, ["Yes", "No", "Maybe"])
            user_responses.append(answer)

        if st.button("Submit", disabled=not poll_active):
            if poll_active:
                if poll_id not in all_responses:
                    all_responses[poll_id] = []
                all_responses[poll_id].append(user_responses)
                save_data(all_responses, RESPONSES_FILE)
                st.success("Thank you for your responses!")
            else:
                st.error("Sorry, the poll is currently closed.")

    if not poll_active:
        st.info("The poll is currently closed. You can view the questions, but you cannot submit responses until the poll is reopened.")

def results_page():
    st.title("Poll Results")
    
    default_poll_id = st.session_state.get('poll_id', "")
    poll_id = st.text_input("Enter Poll ID", value=default_poll_id)
    
    if poll_id:
        questions = load_data(QUESTIONS_FILE).get(poll_id, [])
        responses = load_data(RESPONSES_FILE).get(poll_id, [])

        if not questions:
            st.warning("No questions available for this poll.")
        elif not responses:
            st.write("No responses yet for this poll.")
        else:
            for i, question in enumerate(questions):
                st.write(f"\nQuestion {i+1}: {question}")
                options = ["Yes", "No", "Maybe"]
                counts = {option: [r[i] for r in responses].count(option) for option in options}
                
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
