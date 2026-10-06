import streamlit as st


st.set_page_config(
    page_title="Test",
    page_icon="⚖️",
)

st.title("Streamlit Test")

st.write("Streamlit is running.")

query = st.chat_input("Type something...")

if query:
    st.write("QUERY RECEIVED")
    st.write(query)