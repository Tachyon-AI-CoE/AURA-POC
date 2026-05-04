import streamlit as st
import uuid
import secrets
import asyncio
from agent_client import invoke_agent

st.title("Vertexai Client")
st.caption("Ask question to Vertexai agent")

# Initialize chat history and user details
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.user = f"User-{uuid.uuid4()}"
    st.session_state.sessionId = secrets.randbelow(9000) + 1000

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("How can I help you today?"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        with st.spinner(""):
            response = asyncio.run(invoke_agent(prompt))
            st.markdown(response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    if "__streamlitmagic__" not in locals():
        import streamlit.web.bootstrap

        streamlit.web.bootstrap.run(__file__, False, [], {})


