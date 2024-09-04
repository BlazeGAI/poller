import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image

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
    
    if 'poll_active' not in st.session_state:
        st.session_state.poll_active = False
    if 'responses' not in st.session_state:
        st.session_state.responses = []

    if not st.session_state.poll_active:
        if st.button("Start Poll"):
            st.session_state.poll_active = True
            st.session_state.responses = []
            st.experimental_rerun()
    else:
        if st.button("Close Poll"):
            st.session_state.poll_active = False
            st.experimental_rerun()

        qr_bytes = get_qr_image_bytes("https://poller.streamlit.app/poll")
        st.image(qr_bytes, caption="Scan this QR code to access the poll")

        st.write("Responses:")
        for idx, response in enumerate(st.session_state.responses, 1):
            st.write(f"{idx}. {response}")

def poll_page():
    st.title("User Poll")
    
    if st.session_state.get('poll_active', False):
        question = "What's your favorite color?"
        options = ["Red", "Blue", "Green", "Yellow"]
        answer = st.radio(question, options)
        
        if st.button("Submit"):
            st.session_state.responses.append(answer)
            st.success("Thank you for your response!")
    else:
        st.write("The poll is currently closed. Please check back later.")

def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select a page", ["Admin", "Poll"])

    if page == "Admin":
        admin_page()
    elif page == "Poll":
        poll_page()

if __name__ == "__main__":
    main()
