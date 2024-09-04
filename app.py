import streamlit as st
import qrcode
from io import BytesIO

# Function to generate QR code
def generate_qr(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img

# Admin page
def admin_page():
    st.title("Admin Page")
    if st.button("Start Poll"):
        st.session_state.poll_active = True
        st.session_state.responses = []
    
    if st.session_state.get('poll_active', False):
        qr = generate_qr("https://your-streamlit-app-url/poll")
        st.image(qr)
        
        st.write("Responses:")
        for response in st.session_state.responses:
            st.write(response)
        
        if st.button("Close Poll"):
            st.session_state.poll_active = False

# User poll page
def poll_page():
    st.title("User Poll")
    if st.session_state.get('poll_active', False):
        answer = st.radio("What's your favorite color?", ["Red", "Blue", "Green", "Yellow"])
        if st.button("Submit"):
            st.session_state.responses.append(answer)
            st.success("Response submitted!")
    else:
        st.write("Poll Closed")

# Main app logic
def main():
    page = st.sidebar.selectbox("Select Page", ["Admin", "Poll"])
    
    if page == "Admin":
        admin_page()
    else:
        poll_page()

if __name__ == "__main__":
    main()
