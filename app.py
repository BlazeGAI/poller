import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image

# Use session state to store poll status
if 'poll_active' not in st.session_state:
    st.session_state.poll_active = False
if 'responses' not in st.session_state:
    st.session_state.responses = []

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

def admin_page():
    st.title("Admin Page")
    
    if not st.session_state.poll_active:
        if st.button("Start Poll"):
            st.session_state.poll_active = True
            st.session_state.responses = []
            st.success("Poll started!")
            st.experimental_rerun()
    else:
        if st.button("Close Poll"):
            st.session_state.poll_active = False
            st.success("Poll closed!")
            st.experimental_rerun()

    st.write(f"Poll status: {'Active' if st.session_state.poll_active else 'Closed'}")

    qr_bytes = get_qr_image_bytes("https://poller.streamlit.app/?page=poll")
    st.image(qr_bytes, caption="Scan this QR code to access the poll")

    st.write("Responses:")
    for idx, response in enumerate(st.session_state.responses, 1):
        st.write(f"{idx}. {response}")

def poll_page():
    st.title("User Poll")
    
    st.write(f"Poll status: {'Active' if st.session_state.poll_active else 'Closed'}")

    question = "What's your favorite color?"
    options = ["Red", "Blue", "Green", "Yellow"]
    answer = st.radio(question, options)
    
    if st.button("Submit", disabled=not st.session_state.poll_active):
        if st.session_state.poll_active:
            st.session_state.responses.append(answer)
            st.success("Thank you for your response!")
        else:
            st.error("Sorry, the poll is currently closed.")

    if not st.session_state.poll_active:
        st.info("The poll is currently closed. You can view the question, but you cannot submit a response until the poll is reopened.")

def main():
    query_params = st.experimental_get_query_params()
    if 'page' in query_params and query_params['page'][0] == 'poll':
        poll_page()
    else:
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Select a page", ["Admin", "Poll"])

        if page == "Admin":
            admin_page()
        elif page == "Poll":
            poll_page()

if __name__ == "__main__":
    main()
