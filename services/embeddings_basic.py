import json
import weaviate
import os
from pypdf import PdfReader
import openai
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery
from weaviate.classes.config import Property, DataType, Configure
from openai import OpenAI
from opik.integrations.openai import track_openai
from opik import track

OPENAI_APIKEY = os.getenv("OPENAI_API_KEY")
clientOpenAi = OpenAI(api_key= OPENAI_APIKEY)
client = track_openai(openai_client=clientOpenAi, project_name="Decisions Compartides")

# Configurar OpenAI
# openai.api_key = os.getenv("OPENAI_API_KEY")

# Cargar texto desde PDF
def cargar_texto_desde_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)
            num_pages = len(reader.pages)
            print(f"El PDF tiene {num_pages} páginas.")
            
            documents = []
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text()
                if text.strip():  # Ignorar páginas vacías
                    documents.append({"content": text, "metadata": {"page_number": page_num, "filename": os.path.basename(pdf_path)}})
        return documents
    except Exception as e:
        print(f"Error al cargar el PDF: {e}")
        return []

# Dividir texto en fragmentos más pequeños
def dividir_texto(text, chunk_size=2000, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

# Inicializar Weaviate y almacenar embeddings WEAVIATE CLOUD
# def initialize_weaviate(pdf_path):
#     documentos_pdf = cargar_texto_desde_pdf(pdf_path)

#     if documentos_pdf:
#         URL = os.getenv('URL_CLUSTER')
#         APIKEY = os.getenv('WEAVIATE_API_KEY')

#         client = weaviate.connect_to_weaviate_cloud(
#             cluster_url=URL,
#             auth_credentials=Auth.api_key(APIKEY),
#             headers={
#         "X-Openai-Api-Key": OPENAI_APIKEY
#     }
#         )
        
#         # Crear la colección Rag1 si no existe
#         try:
#             client.collections.create(
#                 name="Rag1",
#                 description="Colección de documentos fragmentados para preguntas y respuestas",
#                 properties=[
#                     Property(name="content", data_type=DataType.TEXT),
#                     Property(name="metadata", data_type=DataType.TEXT)
#                 ],
#                 vectorizer_config=Configure.Vectorizer.text2vec_openai(),
#             )
#             print("Colección Rag1 creada exitosamente.")
#         except Exception as e:
#             print(f"Error o la colección Rag1 ya existe: {e}")

#         # Obtener la colección creada
#         try:
#             rag1_collection = client.collections.get("Rag1")
#         except Exception as e:
#             print(f"Error al obtener la colección Rag1: {e}")
#             client.close()
#             raise

#         # Subir documentos a la colección
#         for doc in documentos_pdf:
#             chunks = dividir_texto(doc["content"])
#             for chunk in chunks:
#                 try:
#                     metadata = {
#                         "page_number": doc["metadata"]["page_number"],
#                         "filename": doc["metadata"]["filename"]
#                     }
#                     new_uuid = rag1_collection.data.insert(
#                         properties={
#                             "content": chunk,
#                             "metadata": json.dumps(metadata)  # Asegúrate de serializar como JSON
#                         },
#                     )
#                     print(f"Fragmento insertado con UUID: {new_uuid}")
#                 except Exception as e:
#                     print(f"Error al insertar el fragmento: {e}")

# Inicializar Weaviate y almacenar embeddings DOCKER
def initialize_weaviate(pdf_path):
    documentos_pdf = cargar_texto_desde_pdf(pdf_path)

    if documentos_pdf:
        client = weaviate.Client(
            url="http://localhost:8080",  # Cambiado para conectarse al contenedor Docker
            additional_headers={
                "X-Openai-Api-Key": OPENAI_APIKEY
            }
        )

        # Verificar si Weaviate está listo
        if not client.is_ready():
            raise ConnectionError("Weaviate no está listo. Verifica que el contenedor Docker esté corriendo.")

        # Crear la colección Rag1 si no existe
        try:
            client.schema.create_class({
                "class": "Rag1",
                "description": "Colección de documentos fragmentados para preguntas y respuestas",
                "vectorizer": "text2vec-openai",
                "properties": [
                    {"name": "content", "dataType": ["text"]},
                    {"name": "metadata", "dataType": ["text"]}
                ]
            })
            print("Colección Rag1 creada exitosamente.")
        except Exception as e:
            print(f"Error o la colección Rag1 ya existe: {e}")

        # Subir documentos a la colección
        for doc in documentos_pdf:
            chunks = dividir_texto(doc["content"])
            for chunk in chunks:
                try:
                    metadata = {
                        "page_number": doc["metadata"]["page_number"],
                        "filename": doc["metadata"]["filename"]
                    }
                    client.data_object.create(
                        data_object={
                            "content": chunk,
                            "metadata": json.dumps(metadata)
                        },
                        class_name="Rag1"
                    )
                    print(f"Fragmento insertado.")
                except Exception as e:
                    print(f"Error al insertar el fragmento: {e}")

# Realizar búsqueda vectorial en Weaviate usando WEAVIATE CLOUD
# def buscar_en_weaviate(pregunta, k=5):
#     URL = os.getenv('URL_CLUSTER')
#     APIKEY = os.getenv('WEAVIATE_API_KEY')

#     # Connect to Weaviate Cloud
#     client = weaviate.connect_to_weaviate_cloud(
#         cluster_url=URL,
#         auth_credentials=Auth.api_key(APIKEY),
#         headers={
#         "X-Openai-Api-Key": OPENAI_APIKEY
#     },
#     )


#     # Generar el embedding de la pregunta utilizando OpenAI
#     embedding = clientOpenAi.embeddings.create(
#         input=pregunta,
#         model="text-embedding-ada-002"
#     ).data[0].embedding  # Accede al embedding generado

#     # Obtener la colección de documentos
#     document_collection = client.collections.get("Rag1")

#     # Realizar la consulta vectorial
#     try:
#         response = document_collection.query.near_text(
#             # near_vector=embedding,
#             query=pregunta,
#             # limit=k,
#             return_metadata=MetadataQuery(distance=True)  # Retornar la distancia en los resultados
#         )
#     except Exception as e:
#         client.close()
#         raise ValueError(f"Error al realizar la búsqueda en Weaviate: {e}")

#     client.close()

#     # Procesar resultados
#     if not response.objects:
#         return []

#     # Extraer contenidos relevantes con metadatos
#     contextos = []
#     for obj in response.objects:
#         # Verifica que las propiedades existan
#         if obj.properties:
#             metadata = obj.properties.get("metadata", "{}")  # Asegúrate de que sea una cadena válida
#             try:
#                 metadata_dict = json.loads(metadata)  # Deserializa el campo metadata
#             except json.JSONDecodeError:
#                 metadata_dict = {}  # Si falla la deserialización, usa un diccionario vacío

#             contextos.append({
#                 "content": obj.properties.get("content", ""),
#                 "page_number": metadata_dict.get("page_number", "Unknown"),
#                 "filename": metadata_dict.get("filename", "Unknown"),
#                 "distance": obj.metadata.distance  # Opcional: Para verificar relevancia
#             })

#     return contextos

# Realizar búsqueda vectorial en Weaviate
@track(project_name="Decisions Compartides")
def buscar_en_weaviate(pregunta, k=5):
    # Conectar al contenedor Docker de Weaviate
    client = weaviate.Client(
        url="http://localhost:8080",
        additional_headers={
            "X-Openai-Api-Key": OPENAI_APIKEY
        }
    )

    # Realizar la consulta `near_text`
    try:
        response = client.query.get(
            "Rag1",
            ["content", "metadata"]
        ).with_near_text({
            "concepts": [pregunta]  # Consulta basada en texto
        }).with_limit(k).do()
    except Exception as e:
        raise ValueError(f"Error al realizar la búsqueda en Weaviate: {e}")

    # Procesar resultados
    if "data" not in response or "Get" not in response["data"] or "Rag1" not in response["data"]["Get"]:
        return []

    documentos = response["data"]["Get"]["Rag1"]
    contextos = []
    for doc in documentos:
        metadata = json.loads(doc["metadata"]) if "metadata" in doc else {}
        contextos.append({
            "content": doc.get("content", ""),
            "page_number": metadata.get("page_number", "Unknown"),
            "filename": metadata.get("filename", "Unknown"),
        })

    return contextos

historial_conversacion = []

def generar_respuesta_llm(pregunta, contextos):
    # Formatear el contexto
    contexto_formateado = "\n".join([
        f"{ctx['content']} (Source: \"{ctx['filename']}\", Page: {ctx['page_number']})"
        for ctx in contextos
    ])
    
    # Formatear el historial
    historial_texto = "\n".join([f"Usuario: {q}\nAsistente: {a}" for q, a in historial_conversacion])
    
    # Crear el prompt
    prompt = f"""
    You are an assistant for question-answering tasks.
    Use the following pieces of recovered context to answer the question and chat history. 
    Please do not use information from your database or the internet to respond; 
    limit yourself to responding only from the recovered pieces of context.

    Always follow this format. PLEASE DO NOT DISOBEY THIS FORMAT.
    If the answer involves information from specific documents, include the document name 
    and page number(s) in the following format:
    - For a single page: (Source: "{{filename}}", Page: "{{page_number}}")
    - For a range of consecutive pages: (Source: "{{filename}}", Page: "{{start_page}}-{{end_page}}")
    - For non-consecutive pages, separate each source reference as follows:
      (Source: "{{filename}}", Page: "{{page_number_1}}")
      (Source: "{{filename}}", Page: "{{page_number_2}}")

    If there are multiple pieces of context from different sources, include each source 
    as a separate reference in the answer.

    If the context does not provide an answer, state "I don't know based on the provided context."

    Chat History:
    {historial_texto}

    Question: {pregunta}
    Context: {contexto_formateado}

    Answer:
    """
    
    # Generar la respuesta
    respuesta = clientOpenAi.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Eres un asistente inteligente."},
            {"role": "user", "content": prompt},
        ]
    )
    
    return respuesta.choices[0].message.content

# RAG completo con memoria
def obtener_respuesta_rag(pregunta):
    try:
        # Buscar en Weaviate
        contextos = buscar_en_weaviate(pregunta)

        if not contextos:
            return "No se encontró información relevante en los documentos."

        # Generar respuesta con LLM
        respuesta = generar_respuesta_llm(pregunta, contextos)

        # Actualizar historial global
        historial_conversacion.append((pregunta, respuesta))

        return respuesta
    except Exception as e:
        print(f"Error al obtener respuesta RAG: {e}")
        return "Ocurrió un error al procesar la pregunta."

# # Flujo principal
# if __name__ == "__main__":
#     # pregunta = "¿Qué menciona el documento sobre la dpa?"
#     # resultados = buscar_en_weaviate(pregunta, k=5)

#     # for resultado in resultados:
#     #     print(f"Contenido: {resultado['content']}")
#     #     print(f"Archivo: {resultado['filename']}, Página: {resultado['page_number']}")
#     #     print(f"Distancia: {resultado.get('distance')}")
#     #     print("-" * 50)
#         # Realizar consultas
#     while True:
#         pregunta = input("Usuario: ")
#         if pregunta.lower() in ["salir", "exit"]:
#             print("Terminando el asistente.")
#             break

#         # Obtener la respuesta del sistema RAG
#         respuesta = obtener_respuesta_rag(pregunta)

#         # Mostrar la respuesta
#         print(f"Asistente: {respuesta}")
#         print("-" * 50)
