
import streamlit as st
import google.generativeai as genai
from neo4j import GraphDatabase

# Load API Key from Streamlit Secrets
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# Ensure API Key is Set
if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY is missing. Add it in Streamlit Secrets.")
    st.stop()

# Initialize Gemini API with "gemini-1.5-flash"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Neo4j Connection
def get_neo4j_connection():
    driver = GraphDatabase.driver(
        st.secrets["NEO4J_URI"],
        auth=(st.secrets["NEO4J_USER"], st.secrets["NEO4J_PASSWORD"])
    )
    return driver

# Improved Neo4j Query
def query_neo4j(user_query):
    with get_neo4j_connection().session() as session:
        query = f"""
        MATCH (n:Policy)
        WHERE toLower(n.title) CONTAINS toLower('{user_query}') OR 
              toLower(n.description) CONTAINS toLower('{user_query}') OR
              toLower(n.keywords) CONTAINS toLower('{user_query}')
        RETURN n.title, n.description, n.source LIMIT 5
        """
        result = session.run(query)
        return [record.values() for record in result]

# Generate Chatbot Response
def generate_chat_response(user_query):
    graph_data = query_neo4j(user_query)

    # If no relevant data is found
    if not graph_data:
        return "I couldn't find specific details in the policy. Can you rephrase or ask a different question?", []

    # Format policy information
    policy_info = "\n".join([f"**{title}**: {desc}" for title, desc, _ in graph_data])

    # Prepare detailed info for "Show Details"
    detailed_info = [
        f"🔹 **Policy:** {title}\n📌 **Description:** {desc}\n📄 **Source:** {source}\n---"
        for title, desc, source in graph_data
    ]

    # Gemini AI Prompt
    prompt = f"""
    You are a chatbot that answers questions directly based on banking policy documents. 
    Here is the relevant information retrieved from the database:

    {policy_info}

    Question: {user_query}
    Answer concisely and directly based on the provided data.
    """

    # Call Gemini API
    try:
        response = model.generate_content(prompt)
        return response.text.strip() if response else "Sorry, I couldn't find a good answer.", detailed_info
    except Exception as e:
        return f"Error with Gemini API: {str(e)}", []

# Streamlit UI
st.title("📜 Bank Policy Chatbot (Neo4j + Gemini)")
st.write("💡 Ask a question related to bank policies!")

user_input = st.text_input("🔍 Your question:")

if user_input:
    response, detailed_info = generate_chat_response(user_input)
    st.markdown(f"**🤖 Chatbot Response:**\n\n{response}")

    # Show details button
    if detailed_info:
        if st.button("📑 Show Details"):
            for detail in detailed_info:
                st.markdown(detail)
