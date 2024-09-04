import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image

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
        qr = generate_qr("https://poller.streamlit.app/poll")
        
        # Convert PIL Image to bytes
        buf = BytesIO()
        qr.save(buf, format="PNG")
        byte_im = buf.getvalue()
        
        st.image(byte_im)
        
        st.write("Responses:")
        for response in st.session_state.responses:
            st.write(response)
        
        if st.button("Close Poll"):
            st.session_state.poll_active = False
