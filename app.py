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

# Improved Neo4j Query for Unique Chunks
def query_neo4j(user_query):
    with get_neo4j_connection().session() as session:
        query = """
        MATCH (c:Chunk)
        WHERE toLower(c.text) CONTAINS toLower($user_query)
        OPTIONAL MATCH (c)-[r]->(related)
        OPTIONAL MATCH (c)-[:SOURCE]->(doc:Document)
        RETURN DISTINCT c.text AS chunk, type(r) AS relationship, related.text AS related_chunk, doc.name AS source
        LIMIT 5
        """
        result = session.run(query, {"user_query": user_query})
        return [record.values() for record in result]

# Generate Chatbot Response
def generate_chat_response(user_query):
    graph_data = query_neo4j(user_query)

    # If no relevant data is found
    if not graph_data:
        return "No specific details were found in the policy. Please try rephrasing your question.", []

    # Extracting chunks for Gemini
    policy_info = "\n".join([f"- {chunk[:300]}..." if len(chunk) > 300 else f"- {chunk}" for chunk, _, _, _ in graph_data if chunk])

    # Prepare detailed information for "Show Details"
    detailed_info = [
        f"""
        <div style="font-size:14px; padding:10px; border-bottom: 1px solid #ddd;">
        <b>Chunk:</b> {chunk[:300]}...<br>
        <b>Relationship:</b> {relationship if relationship else "N/A"} → {related_chunk if related_chunk else "N/A"}<br>
        <b>Source Document:</b> {source if source else "Unknown"}
        </div>
        """
        for chunk, relationship, related_chunk, source in graph_data
    ]

    # Gemini AI Prompt for Direct Answer
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
                st.markdown(detail, unsafe_allow_html=True)
