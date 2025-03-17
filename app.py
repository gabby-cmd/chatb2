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

# Query Neo4j for chunks, relationships, and source document
def query_neo4j(user_query):
    with get_neo4j_connection().session() as session:
        query = f"""
        MATCH (c:Chunk)-[r]->(related), (c)-[:SOURCE]->(doc:Document)
        WHERE toLower(c.text) CONTAINS toLower('{user_query}')
        RETURN c.text AS chunk, type(r) AS relationship, related.text AS related_chunk, doc.name AS source
        LIMIT 5
        """
        result = session.run(query)
        return [record.values() for record in result]

# Generate Direct Chatbot Response
def generate_chat_response(user_query):
    graph_data = query_neo4j(user_query)

    # If no relevant data is found
    if not graph_data:
        return "No specific details were found in the policy. Please try rephrasing your question.", []

    # Extracting chunks for Gemini
    policy_info = "\n".join([f"- {chunk}" for chunk, _, _, _ in graph_data])

    # Prepare detailed information
    detailed_info = [
        f"Chunk: {chunk}\nRelationship: {relationship} → {related_chunk}\nSource Document: {source}\n---"
        for chunk, relationship, related_chunk, source in graph_data
    ]

    # Gemini AI Prompt for a Short Answer
    prompt = f"""
    You are a chatbot that provides concise answers based on policy documents.
    Below is the relevant information from the database:

    {policy_info}

    Question: {user_query}
    Provide a clear and professional response in 2-3 sentences.
    """

    # Call Gemini API
    try:
        response = model.generate_content(prompt)
        return response.text.strip() if response else "No relevant information was found.", detailed_info
    except Exception as e:
        return f"An error occurred while retrieving data: {str(e)}", []

# Streamlit UI
st.title("Bank Policy Chatbot")
st.write("Ask a question related to bank policies.")

user_input = st.text_input("Enter your question:")

if user_input:
    response, detailed_info = generate_chat_response(user_input)
    st.markdown(f"**Chatbot Response:**\n\n{response}")

    # Show details button
    if detailed_info:
        if st.button("Show Details"):
            for detail in detailed_info:
                st.markdown(detail)
