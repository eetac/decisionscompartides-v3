import json
import weaviate
import os
from pypdf import PdfReader
import openai
import weaviate
from flask import current_app
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery
from weaviate.classes.config import Property, DataType, Configure
from openai import OpenAI
from opik.integrations.openai import track_openai
from opik import track

OPENAI_APIKEY = os.getenv("OPENAI_API_KEY")
URL_CLUSTER = os.getenv("URL_CLUSTER")
clientOpenAi = OpenAI(api_key= OPENAI_APIKEY)
client = track_openai(openai_client=clientOpenAi, project_name="Decisions Compartides")

# Cargar texto desde PDF
def cargar_texto_desde_pdf(pdf_path):
    try:
        current_app.logger.info(f"Inicio de carga del PDF: {pdf_path}")
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)
            num_pages = len(reader.pages)
            current_app.logger.info(f"El PDF tiene {num_pages} páginas.")
            
            documents = []
            for page_num, page in enumerate(reader.pages, start=1):
                current_app.logger.debug(f"Leyendo la página {page_num}")
                text = page.extract_text()
                if text.strip():  # Ignorar páginas vacías
                    current_app.logger.debug(f"Página {page_num} contiene texto.")
                    documents.append({"content": text, "metadata": {"page_number": page_num, "filename": os.path.basename(pdf_path)}})
                else:
                    current_app.logger.warning(f"La página {page_num} está vacía y será ignorada.")

        current_app.logger.info(f"Finalización de la carga del PDF: {pdf_path}")
        return documents
    except Exception as e:
        current_app.logger.info(f"Error al cargar el PDF: {e}")
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

# Inicializar Weaviate y almacenar embeddings DOCKER
def initialize_weaviate(pdf_path):
    current_app.logger.info("Inicializando conexión con Weaviate.")
    documentos_pdf = cargar_texto_desde_pdf(pdf_path)

    if documentos_pdf:
        current_app.logger.info("Conectando al cliente Weaviate.")
        client = weaviate.Client(
            url=URL_CLUSTER,  # Cambiado para conectarse al contenedor Docker
            # url="http://localhost:8080",  # Cambiado para conectarse al contenedor Docker
            additional_headers={
                "X-Openai-Api-Key": OPENAI_APIKEY
            }
        )

        # Verificar si Weaviate está listo
        if not client.is_ready():
            current_app.logger.error("Weaviate no está listo. Verifica que el contenedor Docker esté corriendo.")
            raise ConnectionError("Weaviate no está listo. Verifica que el contenedor Docker esté corriendo.")
        
        current_app.logger.info("Weaviate está listo para recibir datos.")

        # Crear la colección Rag1 si no existe
        try:
            current_app.logger.info("Intentando crear la colección Rag1.")
            client.schema.create_class({
                "class": "Rag1",
                "description": "Colección de documentos fragmentados para preguntas y respuestas",
                "vectorizer": "text2vec-openai",
                "properties": [
                    {"name": "content", "dataType": ["text"]},
                    {"name": "metadata", "dataType": ["text"]}
                ]
            })
            current_app.logger.info("Colección Rag1 creada exitosamente.")
        except Exception as e:
            current_app.logger.warning(f"No se pudo crear la colección Rag1: {e}")

        # Subir documentos a la colección
        current_app.logger.info("Iniciando la carga de documentos al esquema Rag1.")
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
                    current_app.logger.debug(f"Fragmento insertado correctamente.")
                except Exception as e:
                    current_app.logger.error(f"Error al insertar el fragmento: {e}")

        current_app.logger.info("Finalización de la carga de documentos.")

# Realizar búsqueda vectorial en Weaviate
@track(project_name="Decisions Compartides")
def buscar_en_weaviate(pregunta, k=5):
    current_app.logger.info("Iniciando búsqueda en Weaviate.")
    current_app.logger.debug("Conectando al cliente Weaviate.")
    # Conectar al contenedor Docker de Weaviate
    client = weaviate.Client(
        # url="http://localhost:8080",
        url=URL_CLUSTER,
        additional_headers={
            "X-Openai-Api-Key": OPENAI_APIKEY
        }
    )
    current_app.logger.info(f"Realizando consulta en Weaviate con la pregunta: '{pregunta}' y límite de {k} resultados.")

    # Realizar la consulta `near_text`
    try:
        response = client.query.get(
            "Rag1",
            ["content", "metadata"]
        ).with_near_text({
            "concepts": [pregunta]  # Consulta basada en texto
        }).with_limit(k).do()
    except Exception as e:
        current_app.logger.error(f"Error al realizar la búsqueda en Weaviate: {e}")
        raise ValueError(f"Error al realizar la búsqueda en Weaviate: {e}")

    # Procesar resultados
    current_app.logger.info("Procesando resultados de la consulta.")
    if "data" not in response or "Get" not in response["data"] or "Rag1" not in response["data"]["Get"]:
        current_app.logger.warning("No se encontraron resultados en Weaviate.")
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
        current_app.logger.debug(f"Documentos procesados: {contextos}")

    current_app.logger.info(f"Consulta finalizada")
    return contextos

historial_conversacion = []


###
###        - For a single page: (Source: "{{filename}}", Page: "{{page_number}}")
###        - For a range of consecutive pages: (multi-source: "{{filename}}", Page: "{{start_page}}-{{end_page}}")
###        - For non-consecutive pages, separate each source reference as follows:

###

def generar_respuesta_llm(pregunta, contextos):
    try:
        current_app.logger.info("Iniciando la generación de respuesta para la pregunta.")
        current_app.logger.debug(f"Pregunta: {pregunta}")
        current_app.logger.debug(f"Contextos proporcionados: {len(contextos)}")
        
        # Formatear el contexto
        contexto_formateado = "\n".join([
            f"{ctx['content']} (Source: \"{ctx['filename']}\", Page: {ctx['page_number']})"
            for ctx in contextos
        ])
        
        current_app.logger.info("Contexto formateado correctamente.")
        current_app.logger.debug(f"Contexto formateado:\n{contexto_formateado}")
        
        # Formatear el historial
        historial_texto = "\n".join([f"Usuario: {q}\nAsistente: {a}" for q, a in historial_conversacion])
        
        current_app.logger.debug(f"Historial de conversación:\n{historial_texto}")
        
        # Crear el prompt
        prompt = f"""
        You are an assistant for question-answering tasks.
        Use the following pieces of recovered context to answer the question and chat history. 
        Please do not use information from your database or the internet to respond; 
        limit yourself to responding only from the recovered pieces of context.

        Always follow this format. PLEASE DO NOT DISOBEY THIS FORMAT.
        If the answer involves information from specific documents, include the document name 
        and page number(s) in the following format:
        <JAVASCRIPT>
        [
                {{ "source": "filename_1",
                   "page": "page_number_1"
                }},
                   {{ "source": "filename_2", 
                   "page": "page_number_2"
                   }}
        ]
        </JAVASCRIPT>
        PLEASE DO NOT DISOBEY THIS FORMAT.

        If there are multiple pieces of context from different sources, include each source 
        as a separate reference in the answer.

        If the context or the chat history does not provide an answer, state "Lamentablement, no he pogut trobar una resposta a la teva pregunta a partir de la informació disponible als documents. Si pots proporcionar més detalls o reformular la pregunta, estaré encantat d’ajudar-te!"
        Si es un saludo, responde amablemente seguido de un "Amb que et puc ajudar?" en catalán
        Si es una despedida, responde amablemente con un "Encantat d'ajudar-te a resoldre els teus dubtes!" en catalán
        
        Chat History:
        {historial_texto}

        Question: {pregunta}
        Context: {contexto_formateado}

        Answer:
        """
        
        current_app.logger.info("Prompt generado correctamente.")
        current_app.logger.debug(f"Prompt:\n{prompt}")

        
        # Generar la respuesta
        respuesta = clientOpenAi.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un asistente inteligente."},
                {"role": "user", "content": prompt},
            ],
            temperature= 0.2,
        )
        
        current_app.logger.info("Respuesta generada exitosamente.")
        current_app.logger.debug(f"Respuesta:\n{respuesta.choices[0].message.content}")
        
        return respuesta.choices[0].message.content
    
    except Exception as e:
        current_app.logger.error("Error al generar la respuesta.", exc_info=True)
        raise e

# RAG completo con memoria
def obtener_respuesta_rag(pregunta):
    try:
        # Buscar en Weaviate
        current_app.logger.info(f"Recibiendo pregunta: '{pregunta}'")
        current_app.logger.info("Iniciando búsqueda de contextos en Weaviate.")
        contextos = buscar_en_weaviate(pregunta)

        if not contextos:
            current_app.logger.warning("No se encontró información relevante en los documentos.")
            return "No se encontró información relevante en los documentos."

        # Generar respuesta con LLM
        current_app.logger.info("Generando respuesta con el modelo de lenguaje (LLM).")
        respuesta = generar_respuesta_llm(pregunta, contextos)
        current_app.logger.debug(f"Respuesta generada: {respuesta}")

        # Actualizar historial global
        current_app.logger.info("Actualizando el historial de la conversación.")
        historial_conversacion.append((pregunta, respuesta))

        current_app.logger.info("Proceso completado correctamente.")
        return respuesta
    except Exception as e:
        current_app.logger.error(f"Error al obtener respuesta RAG: {e}")
        return "Ocurrió un error al procesar la pregunta."
