import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image

# Use cache_data to share poll status across sessions
@st.cache_data(experimental_allow_widgets=True)
def get_poll_status():
    return {"active": False, "responses": []}

def set_poll_status(status):
    get_poll_status.clear()
    st.cache_data(experimental_allow_widgets=True)(lambda: status)()

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
    
    poll_status = get_poll_status()

    if not poll_status["active"]:
        if st.button("Start Poll"):
            poll_status["active"] = True
            poll_status["responses"] = []
            set_poll_status(poll_status)
    else:
        if st.button("Close Poll"):
            poll_status["active"] = False
            set_poll_status(poll_status)

    if poll_status["active"]:
        qr_bytes = get_qr_image_bytes("https://poller.streamlit.app/?page=poll")
        st.image(qr_bytes, caption="Scan this QR code to access the poll")

        st.write("Responses:")
        for idx, response in enumerate(poll_status["responses"], 1):
            st.write(f"{idx}. {response}")

def poll_page():
    st.title("User Poll")
    
    poll_status = get_poll_status()
    
    if poll_status["active"]:
        question = "What's your favorite color?"
        options = ["Red", "Blue", "Green", "Yellow"]
        answer = st.radio(question, options)
        
        if st.button("Submit"):
            poll_status["responses"].append(answer)
            set_poll_status(poll_status)
            st.success("Thank you for your response!")
    else:
        st.write("The poll is currently closed. Please check back later.")

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
