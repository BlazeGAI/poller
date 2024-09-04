import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image
import json
import os

# Files to store responses and questions
RESPONSES_FILE = "responses.json"
QUESTIONS_FILE = "questions.json"

def load_data(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return []

def save_data(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f)

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

def toggle_poll():
    current_params = st.experimental_get_query_params()
    current_params['poll_active'] = ['true' if current_params.get('poll_active', ['false'])[0] == 'false' else 'false']
    st.experimental_set_query_params(**current_params)
    if current_params['poll_active'][0] == 'true':
        save_data([], RESPONSES_FILE)  # Clear responses when starting a new poll

def admin_page():
    st.title("Admin Page")
    
    current_params = st.experimental_get_query_params()
    poll_active = current_params.get('poll_active', ['false'])[0] == 'true'
    
    if poll_active:
        if st.button("Close Poll", on_click=toggle_poll):
            st.success("Poll closed!")
    else:
        if st.button("Start Poll", on_click=toggle_poll):
            st.success("Poll started!")

    st.write(f"Poll status: {'Active' if poll_active else 'Closed'}")

    qr_bytes = get_qr_image_bytes(f"https://poller.streamlit.app/?page=poll&poll_active={'true' if poll_active else 'false'}")
    st.image(qr_bytes, caption="Scan this QR code to access the poll")

    # File uploader for questions
    uploaded_file = st.file_uploader("Upload questions file", type="txt")
    if uploaded_file is not None:
        questions = [line.decode("utf-8").strip() for line in uploaded_file.readlines() if line.strip()]
        save_data(questions, QUESTIONS_FILE)
        st.success("Questions uploaded successfully!")

    # Display current questions
    st.write("Current Questions:")
    questions = load_data(QUESTIONS_FILE)
    for i, question in enumerate(questions, 1):
        st.write(f"{i}. {question}")

def poll_page():
    st.title("User Poll")
    
    current_params = st.experimental_get_query_params()
    poll_active = current_params.get('poll_active', ['false'])[0] == 'true'
    
    st.write(f"Poll status: {'Active' if poll_active else 'Closed'}")

    questions = load_data(QUESTIONS_FILE)
    responses = load_data(RESPONSES_FILE)

    if not questions:
        st.warning("No questions available. Please ask the admin to upload questions.")
    else:
        user_responses = []
        for i, question in enumerate(questions):
            answer = st.radio(question, ["Yes", "No", "Maybe"])
            user_responses.append(answer)

        if st.button("Submit", disabled=not poll_active):
            if poll_active:
                responses.append(user_responses)
                save_data(responses, RESPONSES_FILE)
                st.success("Thank you for your responses!")
            else:
                st.error("Sorry, the poll is currently closed.")

    if not poll_active:
        st.info("The poll is currently closed. You can view the questions, but you cannot submit responses until the poll is reopened.")

def results_page():
    st.title("Poll Results")
    
    questions = load_data(QUESTIONS_FILE)
    responses = load_data(RESPONSES_FILE)

    if not questions:
        st.warning("No questions available.")
    elif not responses:
        st.write("No responses yet.")
    else:
        for i, question in enumerate(questions):
            st.write(f"\nQuestion {i+1}: {question}")
            options = ["Yes", "No", "Maybe"]
            counts = {option: [r[i] for r in responses].count(option) for option in options}
            
            st.write("Response Counts:")
            for option, count in counts.items():
                st.write(f"{option}: {count}")
            
            # Create a bar chart
            st.bar_chart(counts)

        st.write(f"\nTotal Responses: {len(responses)}")

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
