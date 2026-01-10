document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const uploadZone = document.getElementById('uploadZone');
    const processBtn = document.getElementById('processBtn');
    const resultsArea = document.getElementById('resultsArea');
    const splitHeightInput = document.getElementById('splitHeight');
    const gapHeightInput = document.getElementById('gapHeight');

    let selectedFiles = [];

    // Drag & Drop Handling
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    uploadZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            selectedFiles = Array.from(files).filter(file => file.type.startsWith('image/'));
            if (selectedFiles.length > 0) {
                processBtn.disabled = false;
                processBtn.textContent = `Process ${selectedFiles.length} Image${selectedFiles.length > 1 ? 's' : ''}`;
                // Optional: Show preview of selected files names?
            } else {
                alert('Please select valid image files.');
            }
        }
    }

    processBtn.addEventListener('click', async () => {
        const splitHeight = parseInt(splitHeightInput.value, 10);
        const gapHeight = parseInt(gapHeightInput.value, 10) || 0;

        if (!splitHeight || splitHeight <= 0) {
            alert('Please enter a valid split height.');
            return;
        }

        processBtn.disabled = true;
        processBtn.textContent = 'Processing...';
        resultsArea.innerHTML = ''; // Clear previous results

        for (const file of selectedFiles) {
            await processImage(file, splitHeight, gapHeight);
        }

        processBtn.disabled = false;
        processBtn.textContent = 'Process Images';
    });

    async function processImage(file, splitHeight, gap) {
        // Create a result card
        const card = document.createElement('div');
        card.className = 'result-card';
        card.innerHTML = `
            <div class="result-header">
                <h3>${file.name}</h3>
                <span class="stat-badge">Processing...</span>
            </div>
        `;
        resultsArea.appendChild(card);

        try {
            const imgBitmap = await createImageBitmap(file);
            const width = imgBitmap.width;
            const height = imgBitmap.height;

            const zip = new JSZip();
            const folder = zip.folder(file.name.replace(/\.[^/.]+$/, ""));

            let currentY = 0;
            let partIndex = 1;
            const chunks = [];

            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = width;

            while (currentY < height) {
                // Determine height of this chunk
                let chunkHeight = splitHeight;

                // If this chunk goes beyond image, clip it
                if (currentY + chunkHeight > height) {
                    chunkHeight = height - currentY;
                }

                // If chunkHeight is 0 or less (shouldn't happen with logic, but safety), break
                if (chunkHeight <= 0) break;

                // Resize canvas for this chunk
                canvas.height = chunkHeight;

                // Draw
                ctx.drawImage(imgBitmap, 0, currentY, width, chunkHeight, 0, 0, width, chunkHeight);

                // Convert to blob
                const blob = await new Promise(resolve => canvas.toBlob(resolve, file.type || 'image/png'));

                // Add to zip
                const ext = file.name.split('.').pop() || 'png';
                const partName = `${file.name.replace(/\.[^/.]+$/, "")}_${String(partIndex).padStart(2, '0')}.${ext}`;
                folder.file(partName, blob);

                chunks.push(partName);

                // Move Y
                currentY += splitHeight + gap;
                partIndex++;
            }

            // Generate Zip
            const content = await zip.generateAsync({ type: "blob" });

            // Update Card
            card.innerHTML = `
                <div class="result-header">
                    <h3>${file.name}</h3>
                    <span class="stat-badge">${chunks.length} Parts Created</span>
                </div>
                <button class="download-btn">Download ZIP</button>
            `;

            card.querySelector('.download-btn').addEventListener('click', () => {
                saveAs(content, `${file.name.replace(/\.[^/.]+$/, "")}_split.zip`);
            });

        } catch (err) {
            console.error(err);
            card.innerHTML = `
                <div class="result-header">
                    <h3>${file.name}</h3>
                    <span class="stat-badge" style="background: rgba(239, 68, 68, 0.1); color: #ef4444;">Error</span>
                </div>
                <p style="color: var(--text-secondary); font-size: 0.9rem;">Failed to process image.</p>
            `;
        }
    }
});
