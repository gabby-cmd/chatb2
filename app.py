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

# Query Neo4j
def query_neo4j(query):
    with get_neo4j_connection().session() as session:
        result = session.run(query)
        return [record.values() for record in result]

# Generate Chatbot Response
def generate_chat_response(user_query):
    # Fetch relevant data from Neo4j
    neo4j_query = f"""
    MATCH (n) WHERE toLower(n.name) CONTAINS toLower('{user_query}')
    RETURN n.name, n.description LIMIT 5
    """
    graph_data = query_neo4j(neo4j_query)

    context = "Here is some relevant data from our Neo4j database:\n"
    context += "\n".join([f"- {name}: {desc}" for name, desc in graph_data])

    # Send Query to Gemini
    try:
        response = model.generate_content(f"{context}\nUser query: {user_query}")
        return response.text if response else "Sorry, I couldn't find a good answer."
    except Exception as e:
        return f"Error with Gemini API: {str(e)}"

# Streamlit UI
st.title("Neo4j-Powered Chatbot (Gemini 1.5 Flash)")
st.write("Ask me anything related to the graph database!")

user_input = st.text_input("Your question:")

if user_input:
    response = generate_chat_response(user_input)
    st.markdown(f"**Chatbot Response:**\n\n{response}")
