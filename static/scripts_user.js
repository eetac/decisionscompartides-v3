let files = [];
let uploadedFiles = new Set();

document.addEventListener('DOMContentLoaded', (event) => {
    const questionInput = document.getElementById('questionInput');

    questionInput.addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            askQuestion();
        }
    });
});

function askQuestion() {
    const question = document.getElementById('questionInput').value;
    const chatBox = document.getElementById('chatBox');
    const questionDiv = document.createElement('div');
    questionDiv.className = 'message question';
    questionDiv.innerText = question;
    chatBox.appendChild(questionDiv);

    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message loading';
    loadingDiv.innerText = 'Carregant';
    chatBox.appendChild(loadingDiv);

    let loadingDots = 0;
    const loadingInterval = setInterval(() => {
        loadingDots = (loadingDots + 1) % 4;
        loadingDiv.innerText = 'Carregant' + '.'.repeat(loadingDots);
    }, 500);

    fetch('/ask', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question: question })
    })
    .then(response => response.json())
    .then(data => {
        clearInterval(loadingInterval);

        if (chatBox.contains(loadingDiv)) {
            chatBox.removeChild(loadingDiv);
        }

        if (data.error) {
            console.error('Error:', data.error);
        } else {
            console.log('Respuesta del servidor:', data.answer);

            if (!data.answer || data.answer.trim() === '') {
                console.error('La respuesta está vacía.');
                return;
            }

            const answerDiv = document.createElement('div');
            answerDiv.className = 'message answer';

            const formattedAnswer = formatAnswerWithLink(answerDiv, data.answer);
            //answerDiv.innerHTML = formattedAnswer;
            chatBox.appendChild(answerDiv);
            scrollToBottom();
        }
    })
    .catch(error => {
        clearInterval(loadingInterval);
        if (chatBox.contains(loadingDiv)) {
            chatBox.removeChild(loadingDiv);
        }        
        console.error('Error:', error);
    });

    document.getElementById('questionInput').value = '';
    scrollToBottom();
}

function formatAnswerWithLink(answerDiv, inputText) {
    const regex = /^(.*?)<JAVASCRIPT>(.*?)<\/JAVASCRIPT>(.*?)$/s;

    const match = inputText.match(regex);
    let before = '';
    let inside = '';
    let after = '';

    if (match) {
        before = match[1].trim(); // Contenido antes de <JAVASCRIPT>
        inside = match[2].trim(); // Contenido entre <JAVASCRIPT> y </JAVASCRIPT>
        after = match[3].trim();  // Contenido después de </JAVASCRIPT>

        console.log("Antes:", before);
        console.log("Dentro:", inside);
        console.log("Después:", after);
    } else {
        console.warn("No se encontró la estructura esperada. Mostrando respuesta completa.");
        const fallbackPElement = document.createElement("p");

        // Eliminar comillas del inicio y el final si están presentes
        const sanitizedText = inputText.replace(/^"(.*)"$/, '$1');
        fallbackPElement.textContent = sanitizedText;

        answerDiv.appendChild(fallbackPElement);
        return answerDiv;
    }

    // Agregar texto antes
    if (before) {
        const beforePElement = document.createElement("p");
        beforePElement.textContent = before;
        answerDiv.appendChild(beforePElement);
    }

    // Parsear la sección <JAVASCRIPT>
    let sources;
    try {
        sources = JSON.parse(inside); // Manejar el JSON de manera segura
        console.log("Fuentes parseadas:", sources);
    } catch (error) {
        console.error("Error al parsear la sección <JAVASCRIPT>:", error);
        return answerDiv;
    }

    // Agregar los enlaces de las fuentes
    if (sources && sources.length > 0) {
        sources.forEach((source) => {
            const linkElement = document.createElement("a");
            linkElement.textContent = `${source.source} - Página: ${source.page}`;
            linkElement.href = `/download/${encodeURIComponent(source.source)}#page=${source.page}`;
            linkElement.target = "_blank";
            linkElement.style.color = "blue";
            answerDiv.appendChild(linkElement);

            const lineBreak = document.createElement("br");
            answerDiv.appendChild(lineBreak);
        });
    } else {
        console.warn("No se encontraron fuentes en la sección <JAVASCRIPT>.");
    }

    // Agregar texto después
    if (after) {
        const afterPElement = document.createElement("p");
        afterPElement.textContent = after;
        answerDiv.appendChild(afterPElement);
    }

    return answerDiv;
}



function scrollToBottom() {
    const chatBox = document.getElementById('chatBox');
    chatBox.scrollTop = chatBox.scrollHeight;
}
