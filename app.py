import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image

# Use cache_data to share poll status across sessions
@st.cache_data(experimental_allow_widgets=True)
def get_poll_status():
    if 'poll_status' not in st.session_state:
        st.session_state.poll_status = {"active": False, "responses": []}
    return st.session_state.poll_status

def set_poll_status(status):
    st.session_state.poll_status = status
    get_poll_status.clear()

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
            set_poll_status(poll_status)
            st.success("Poll started!")
            st.experimental_rerun()
    else:
        if st.button("Close Poll"):
            poll_status["active"] = False
            set_poll_status(poll_status)
            st.success("Poll closed!")
            st.experimental_rerun()

    st.write(f"Poll status: {'Active' if poll_status['active'] else 'Closed'}")

    qr_bytes = get_qr_image_bytes("https://poller.streamlit.app/?page=poll")
    st.image(qr_bytes, caption="Scan this QR code to access the poll")

    st.write("Responses:")
    for idx, response in enumerate(poll_status["responses"], 1):
        st.write(f"{idx}. {response}")

def poll_page():
    st.title("User Poll")
    
    poll_status = get_poll_status()
    
    st.write(f"Poll status: {'Active' if poll_status['active'] else 'Closed'}")

    question = "What's your favorite color?"
    options = ["Red", "Blue", "Green", "Yellow"]
    answer = st.radio(question, options)
    
    if st.button("Submit", disabled=not poll_status["active"]):
        if poll_status["active"]:
            poll_status["responses"].append(answer)
            set_poll_status(poll_status)
            st.success("Thank you for your response!")
        else:
            st.error("Sorry, the poll is currently closed.")

    if not poll_status["active"]:
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
