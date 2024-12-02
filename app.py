import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from flask_cors import CORS



load_dotenv()

app = Flask(__name__)
CORS(app)

google_api_key = os.getenv("GOOGLE_API_KEY")

CHROMA_PERSIST_DIR = "chroma_db"

KNOWLEDGE_BASE_FILE = "KnowledgeBase.pdf"

@app.route('/view_default_file')
def view_default_file():
    return send_from_directory(os.getcwd(), KNOWLEDGE_BASE_FILE)

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0, max_tokens=None, timeout=None)


system_prompt = (
    "You are an assistant for question-answering tasks. "
    "Use the following pieces of retrieved context to answer "
    "the question. If you don't know the answer, say that you "
    "don't know. Use three sentences maximum and keep the "
    "answer concise. Don't add your own knowledge base and answer using a single line, "
    "and if the question is out of context, tell that you can't answer this question."
    "\n\n"
    "{context}"
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

def process_pdf(file_path):
   
    loader = PyPDFLoader(file_path)
    data = loader.load()


    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
    docs = text_splitter.split_documents(data)

   
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")


    if os.path.exists(CHROMA_PERSIST_DIR):
        vectorstore = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embeddings
        )

        vectorstore.add_documents(docs)
    else:
       
        vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )


    vectorstore.persist()

    return vectorstore

@app.route('/uploading')
def up():
    return render_template('upload.html')

@app.route('/')
def index():
    return render_template('homepage.html')

@app.route('/gpt')
def voicebot():
    return render_template('gpt.html')

@app.route('/ask', methods=['POST'])
def ask():
    query = request.json.get("query")
    
    if query:

        vectorstore = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        )
        
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 10})

        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)

        response = rag_chain.invoke({"input": query})
        answer = response["answer"] if "answer" in response else "Sorry, I don't have the answer to that."

        return jsonify({"answer": answer})
    
    return jsonify({"answer": "Invalid query."}), 400


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'use_default_file' in request.form and request.form['use_default_file'] == 'true':
            file_path = os.path.join(os.getcwd(), KNOWLEDGE_BASE_FILE)
            process_pdf(file_path)
            return redirect(url_for('chatbot')) 

        if 'file' not in request.files:
            return jsonify({"error": "No file part."}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No selected file."}), 400
        
      
        file_path = os.path.join(os.getcwd(), file.filename)
        file.save(file_path)
        
   
        process_pdf(file_path)
        
        return redirect(url_for('voicebot'))  
    
    return render_template('upload.html')



if __name__ == '__main__':
    app.run(debug=True)