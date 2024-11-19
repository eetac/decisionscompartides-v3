import os
from typing import List, Optional, Tuple
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from services.embeddings_basic import initialize_weaviate
from services.embeddings_basic import obtener_respuesta_rag
from openai import OpenAI
import weaviate
import traceback

routes_bp = Blueprint('routes', __name__)

openai_api_key = os.getenv('OPENAI_API_KEY')
llm = OpenAI(api_key=openai_api_key)

@routes_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    files = request.files.getlist('file')
    if not files:
        return jsonify({"error": "No selected file"}), 400
    
    for file in files:
        if file.filename == '':
            return jsonify({"error": f"Empty filename in {file}"}), 400
        filename = secure_filename(file.filename)
        file_path = os.path.join('uploads', filename)
        file.save(file_path)

        try:
            initialize_weaviate(file_path)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    return jsonify({"message": "Files uploaded, processed, and embeddings stored in Weaviate"}), 200

# @routes_bp.route('/ask', methods=['POST'])
# def ask_question():
#     data = request.get_json()
#     question = data.get('question')
    
#     if not question:
#         return jsonify({"error": "No question provided"}), 400

#     try:
#         client = weaviate.connect_to_wcs(
#             cluster_url=os.getenv('URL_CLUSTER'),
#             auth_credentials=weaviate.auth.AuthApiKey(os.getenv('WEAVIATE_API_KEY'))
#         )
        
#         vs = WeaviateVectorStore(client=client, index_name="rag1", embedding=OpenAIEmbeddings(), text_key= "text")
#         retriever = vs.as_retriever()

#         response = obtener_respuesta_rag(question, retriever)

#         client.close()

#         return jsonify({"answer": response}), 200

#     except Exception as e:
#         traceback.print_exc()
#         return jsonify({"error": str(e)}), 500

@routes_bp.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get('question')
    
    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        response = obtener_respuesta_rag(question)
        return jsonify({"answer": response}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
@routes_bp.route('/delete', methods=['POST'])
def delete_file():
    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
    
    file_path = os.path.join('uploads', secure_filename(filename))
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"message": "File deleted"}), 200
    else:
        return jsonify({"error": "File not found"}), 404
    
@routes_bp.route('/exists', methods=['POST'])
def check_file_exists():
    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
    
    file_path = os.path.join('uploads', secure_filename(filename))
    if os.path.exists(file_path):
        return jsonify({"exists": True}), 200
    else:
        return jsonify({"exists": False}), 200

@routes_bp.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        safe_filename = secure_filename(filename)
        upload_folder = os.path.join(os.getcwd(), 'uploads')
        
        file_path = os.path.join(upload_folder, safe_filename)
        if os.path.exists(file_path):
            return send_from_directory(upload_folder, safe_filename)
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    

# @routes_bp.route('/evaluar_ragas', methods=['GET'])
# def evaluar_sistema_con_ragas():
#     try:
#         resultados = evaluar_rag_con_nota()
#         print(resultados)
#         return jsonify({"resultados": resultados}), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
