import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image

# Initialize session state
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

def toggle_poll():
    current_params = st.experimental_get_query_params()
    current_params['poll_active'] = ['true' if current_params.get('poll_active', ['false'])[0] == 'false' else 'false']
    st.experimental_set_query_params(**current_params)
    if current_params['poll_active'][0] == 'true':
        st.session_state.responses = []

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

    st.write("Responses:")
    for idx, response in enumerate(st.session_state.responses, 1):
        st.write(f"{idx}. {response}")

def poll_page():
    st.title("User Poll")
    
    current_params = st.experimental_get_query_params()
    poll_active = current_params.get('poll_active', ['false'])[0] == 'true'
    
    st.write(f"Poll status: {'Active' if poll_active else 'Closed'}")

    question = "What's your favorite color?"
    options = ["Red", "Blue", "Green", "Yellow"]
    answer = st.radio(question, options)
    
    if st.button("Submit", disabled=not poll_active):
        if poll_active:
            st.session_state.responses.append(answer)
            st.success("Thank you for your response!")
        else:
            st.error("Sorry, the poll is currently closed.")

    if not poll_active:
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
