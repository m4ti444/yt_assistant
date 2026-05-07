document.addEventListener('DOMContentLoaded', () => {
    const parseBtn = document.getElementById('parse-btn');
    const scriptInput = document.getElementById('script-input');
    const resultsPanel = document.getElementById('results-panel');
    const promptsList = document.getElementById('prompts-list');
    const phrasesList = document.getElementById('phrases-list');
    const copyNextBtn = document.getElementById('copy-next-btn');
    const generateAllBtn = document.getElementById('generate-all-btn');
    const downloadZipBtn = document.getElementById('download-zip-btn');
    const engineRadios = document.getElementsByName('engine');
    const fishOptions = document.querySelector('.fish-options');

    let currentData = null;
    let nextPromptIndex = 0;

    // Toggle Fish Audio options
    engineRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.value === 'fish') {
                fishOptions.style.display = 'block';
            } else {
                fishOptions.style.display = 'none';
            }
        });
    });

    parseBtn.addEventListener('click', async () => {
        const script = scriptInput.value.trim();
        if (!script) return alert('Por favor pega un guion primero');

        try {
            const response = await fetch('/parse', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ script })
            });
            const data = await response.json();

            if (data.error) throw new Error(data.error);

            currentData = data;
            renderPrompts(data.prompts);
            renderPhrases(data.phrases);
            resultsPanel.style.display = 'block';
            nextPromptIndex = 0;
            copyNextBtn.disabled = data.prompts.length === 0;
            generateAllBtn.disabled = data.phrases.length === 0;
            downloadZipBtn.disabled = true;

            // Scroll to results
            resultsPanel.scrollIntoView({ behavior: 'smooth' });
        } catch (err) {
            alert('Error: ' + err.message);
        }
    });

    function renderPrompts(prompts) {
        promptsList.innerHTML = '';
        prompts.forEach((p, index) => {
            const div = document.createElement('div');
            div.className = 'item-card prompt-card';
            div.id = `prompt-card-${index}`;
            div.innerHTML = `
                <div class="item-header">
                    <span class="badge">Prompt ${p.id}</span>
                    <button class="btn secondary" onclick="copyPrompt(${index})">Copiar</button>
                </div>
                <div class="item-text">${p.text}</div>
            `;
            promptsList.appendChild(div);
        });
    }

    function renderPhrases(phrases) {
        phrasesList.innerHTML = '';
        phrases.forEach((p, index) => {
            const div = document.createElement('div');
            div.className = 'item-card phrase-card';
            div.id = `phrase-card-${p.id}`;
            div.innerHTML = `
                <div class="item-header">
                    <span class="badge">Frase ${p.id}</span>
                    <span id="phrase-status-${p.id}" class="status-text">Pendiente</span>
                </div>
                <div class="item-text">${p.text}</div>
                <audio id="audio-${p.id}" controls style="display: none; width: 100%; margin-top: 10px;"></audio>
            `;
            phrasesList.appendChild(div);
        });
    }

    window.copyPrompt = async (index) => {
        if (!currentData || !currentData.prompts[index]) return;

        try {
            await navigator.clipboard.writeText(currentData.prompts[index].text);

            // Highlight card
            document.querySelectorAll('.prompt-card').forEach(c => c.classList.remove('copied'));
            const card = document.getElementById(`prompt-card-${index}`);
            card.classList.add('copied');

            document.getElementById('copy-status').textContent = `Prompt ${currentData.prompts[index].id} copiado!`;
            setTimeout(() => document.getElementById('copy-status').textContent = '', 2000);

            nextPromptIndex = index + 1;
            if (nextPromptIndex >= currentData.prompts.length) {
                copyNextBtn.textContent = 'Todos copiados!';
                copyNextBtn.disabled = true;
            } else {
                copyNextBtn.textContent = `Copiar Prompt ${currentData.prompts[nextPromptIndex].id}`;
            }
        } catch (err) {
            console.error('Failed to copy', err);
        }
    };

    copyNextBtn.addEventListener('click', () => {
        if (nextPromptIndex < currentData.prompts.length) {
            copyPrompt(nextPromptIndex);
        }
    });

    generateAllBtn.addEventListener('click', async () => {
        if (!currentData || !currentData.phrases.length) return;

        const engine = document.querySelector('input[name="engine"]:checked').value;
        const modelId = document.getElementById('fish-model-id').value.trim();

        generateAllBtn.disabled = true;

        if (engine === 'fish') {
            // Usa el Robot Automático (Playwright)
            alert("¡Iniciando Robot Automático! Se abrirá una ventana del navegador. Si es tu primera vez, por favor inicia sesión rápidamente. El robot se encargará del resto.");

            // Marcar todos como generando
            currentData.phrases.forEach(phrase => {
                const card = document.getElementById(`phrase-card-${phrase.id}`);
                const statusLabel = document.getElementById(`phrase-status-${phrase.id}`);
                card.classList.add('generating');
                statusLabel.textContent = 'En cola (Robot)...';
            });

            try {
                const response = await fetch('/generate-batch-fish', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        phrases: currentData.phrases
                    })
                });

                const data = await response.json();

                if (data.error) throw new Error(data.error);

                // Marcar todos como listos
                currentData.phrases.forEach(phrase => {
                    const card = document.getElementById(`phrase-card-${phrase.id}`);
                    const statusLabel = document.getElementById(`phrase-status-${phrase.id}`);
                    card.classList.remove('generating');
                    card.classList.add('done');
                    statusLabel.textContent = '✅ Listo';

                    const audioPlayer = document.getElementById(`audio-${phrase.id}`);
                    audioPlayer.src = `/outputs/${phrase.id}.mp3?t=${new Date().getTime()}`;
                    audioPlayer.style.display = 'block';
                });

            } catch (err) {
                currentData.phrases.forEach(phrase => {
                    const card = document.getElementById(`phrase-card-${phrase.id}`);
                    card.classList.remove('generating');
                });
                alert('Error en el robot: ' + err.message);
            }

        } else {
            // Edge TTS (Generación individual)
            for (const phrase of currentData.phrases) {
                const card = document.getElementById(`phrase-card-${phrase.id}`);
                const statusLabel = document.getElementById(`phrase-status-${phrase.id}`);

                card.classList.add('generating');
                statusLabel.textContent = 'Generando...';

                try {
                    const response = await fetch('/generate-audio', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            id: phrase.id,
                            text: phrase.text,
                            engine: engine,
                            model_id: modelId || null
                        })
                    });

                    const data = await response.json();
                    card.classList.remove('generating');

                    if (data.error) throw new Error(data.error);

                    card.classList.add('done');
                    statusLabel.textContent = '✅ Listo';

                    // Show audio player
                    const audioPlayer = document.getElementById(`audio-${phrase.id}`);
                    audioPlayer.src = `/outputs/${phrase.id}.mp3?t=${new Date().getTime()}`;
                    audioPlayer.style.display = 'block';

                } catch (err) {
                    card.classList.remove('generating');
                    statusLabel.textContent = '❌ Error';
                    statusLabel.style.color = '#ef4444';
                    console.error(`Error generating phrase ${phrase.id}:`, err);
                }
            }
        }

        generateAllBtn.disabled = false;
        downloadZipBtn.disabled = false;
        generateAllBtn.textContent = 'Regenerar Todos';
    });

    // IMAGE AUTOMATION
    const generateImagesBtn = document.getElementById('generate-images-btn');
    if (generateImagesBtn) {
        generateImagesBtn.addEventListener('click', async () => {
            if (!currentData || !currentData.prompts.length) return;

            generateImagesBtn.disabled = true;
            const refImageInput = document.getElementById('ref-image');

            alert("¡Iniciando Robot de Imágenes (Google Flow)! Se abrirá una ventana de navegador. Si no estás logueado en Google, tendrás 5 minutos para hacerlo.");

            // Marcar todos como generando
            currentData.prompts.forEach((prompt, index) => {
                const card = document.getElementById(`prompt-card-${index}`);
                if (card) card.style.opacity = '0.5';
            });

            try {
                const formData = new FormData();
                formData.append('prompts', JSON.stringify(currentData.prompts));
                if (refImageInput.files.length > 0) {
                    formData.append('ref_image', refImageInput.files[0]);
                }

                const response = await fetch('/generate-batch-images', {
                    method: 'POST',
                    body: formData // No setear Content-Type, fetch lo hace automático con FormData
                });

                const data = await response.json();

                if (data.error) throw new Error(data.error);

                // Marcar todos como listos
                currentData.prompts.forEach((prompt, index) => {
                    const card = document.getElementById(`prompt-card-${index}`);
                    if (card) {
                        card.style.opacity = '1';
                        card.style.borderLeft = '4px solid #10b981';
                    }
                });

                alert("¡Imágenes generadas y guardadas en outputs/ con éxito!");

            } catch (err) {
                currentData.prompts.forEach((prompt, index) => {
                    const card = document.getElementById(`prompt-card-${index}`);
                    if (card) card.style.opacity = '1';
                });
                alert('Error en el robot de imágenes: ' + err.message);
            }

            generateImagesBtn.disabled = false;
        });
    }

    downloadZipBtn.addEventListener('click', () => {
        window.location.href = '/download-zip';
    });
});
