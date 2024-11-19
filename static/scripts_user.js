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

            const formattedAnswer = formatAnswerWithLink(data.answer);
            answerDiv.innerHTML = formattedAnswer;
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

function formatAnswerWithLink(inputText) {
    const regex = /\(Source:\s*"([^"]+\.pdf)",\s*Page:\s*(\d+(-\d+)?)(\))/g;

    const formattedText = inputText.replace(regex, (match, pdfName, pageRange) => {
        const pageLink = pageRange.includes("-")
            ? pageRange.split("-")[0]
            : pageRange;

        return `<a href="/download/${encodeURIComponent(pdfName)}#page=${pageLink}" target="_blank" style="color: blue; text-decoration: underline;">(${pdfName}, página: ${pageRange})</a>`;
    });

    return formattedText;
}

function scrollToBottom() {
    const chatBox = document.getElementById('chatBox');
    chatBox.scrollTop = chatBox.scrollHeight;
}
