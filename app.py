import streamlit as st
import qrcode
from io import BytesIO
import pandas as pd

# Function to generate a QR code
def generate_qr_code(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    buf = BytesIO()
    img.save(buf)
    return buf

# Set up Streamlit app
st.title("Live Polling App")

# Simulate a poll link (replace with actual deployment link)
poll_link = "http://localhost:8501"

# Generate and display QR code for poll link
st.header("Scan this QR code to participate in the poll")
qr_image = generate_qr_code(poll_link)
st.image(qr_image.getvalue(), use_column_width=True)

# Questions for the poll
questions = [
    "What is your favorite color?",
    "Do you like coffee or tea?"
]

# Admin control
if 'responses' not in st.session_state:
    st.session_state['responses'] = []

if st.button("Start Poll"):
    st.session_state['poll_started'] = True

if 'poll_started' in st.session_state and st.session_state['poll_started']:
    question_number = len(st.session_state['responses']) + 1

    if question_number <= len(questions):
        question = questions[question_number - 1]
        st.write(f"**Question {question_number}:** {question}")

        # Input for response
        response = st.text_input("Your Answer:")
        if st.button("Submit Answer"):
            st.session_state['responses'].append(response)
            st.experimental_rerun()
    else:
        st.write("Thank you for participating! The poll is now closed.")

# Display live responses for admin
st.sidebar.header("Admin Panel")
st.sidebar.write("Live Responses")
st.sidebar.table(pd.DataFrame(st.session_state['responses'], columns=["Responses"]))

# Close poll button
if st.sidebar.button("Close Poll"):
    st.session_state['poll_started'] = False
    st.sidebar.write("Poll Closed")
    st.write("The poll has been closed. Thank you for participating!")
