const API_BASE_URL = 'http://localhost:5000/api';
let currentResult = null;
let selectedFile = null;

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing...');
    
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadSection = document.getElementById('uploadSection');
    const processingSection = document.getElementById('processingSection');
    const resultsSection = document.getElementById('resultsSection');
    
    console.log('Elements found:', { 
        dropZone: !!dropZone, 
        fileInput: !!fileInput, 
        uploadSection: !!uploadSection, 
        processingSection: !!processingSection, 
        resultsSection: !!resultsSection 
    });
    
    if (!dropZone || !fileInput) {
        console.error('Critical elements not found!');
        return;
    }
    
    // Drop zone click event
    dropZone.addEventListener('click', function(e) {
        console.log('Drop zone clicked');
        e.preventDefault();
        fileInput.click();
    });
    
    // File input change event
    fileInput.addEventListener('change', function(e) {
        console.log('File selected:', e.target.files.length);
        if (e.target.files.length > 0) {
            selectedFile = e.target.files[0];
            processFile();
        }
    });
    
    // Drag and drop events
    dropZone.addEventListener('dragover', function(e) {
        console.log('Dragover event triggered');
        e.preventDefault();
        e.stopPropagation();
        dropZone.style.borderColor = '#0d6efd';
        dropZone.style.backgroundColor = 'rgba(13, 110, 253, 0.05)';
    });
    
    dropZone.addEventListener('dragleave', function(e) {
        console.log('Dragleave event triggered');
        e.preventDefault();
        e.stopPropagation();
        dropZone.style.borderColor = '#dee2e6';
        dropZone.style.backgroundColor = '#f8f9fa';
    });
    
    dropZone.addEventListener('drop', function(e) {
        console.log('Drop event triggered');
        e.preventDefault();
        e.stopPropagation();
        dropZone.style.borderColor = '#dee2e6';
        dropZone.style.backgroundColor = '#f8f9fa';
        
        const files = e.dataTransfer.files;
        console.log('Files dropped:', files.length, files);
        if (files.length > 0) {
            selectedFile = files[0];
            processFile();
        }
    });
    
    // Download buttons
    document.getElementById('downloadCsv').addEventListener('click', downloadCSV);
    document.getElementById('downloadLog').addEventListener('click', downloadLog);
    
    async function processFile() {
        const file = selectedFile || (fileInput.files && fileInput.files[0]);
        
        console.log('Processing file:', file);
        
        if (!file) {
            alert('Please select a file.');
            return;
        }
        
        if (!file.name.toLowerCase().endsWith('.csv')) {
            alert('Please select a CSV file.');
            return;
        }

        console.log('File validation passed, showing processing section');
        uploadSection.style.display = 'none';
        processingSection.style.display = 'block';

        try {
            const formData = new FormData();
            formData.append('file', file);
            
            // Add cleaning options
            const form = document.getElementById('uploadForm');
            for (let element of form.elements) {
                if (element.type === 'checkbox') {
                    formData.append(element.name, element.checked);
                } else if (element.type === 'select-one') {
                    formData.append(element.name, element.value);
                }
            }
            
            console.log('Sending request to:', `${API_BASE_URL}/upload`);

            const response = await fetch(`${API_BASE_URL}/upload`, {
                method: 'POST',
                body: formData
            });
            
            console.log('Response status:', response.status);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log('API response:', result);

            if (result.success) {
                currentResult = result;
                showResults(result);
            } else {
                throw new Error(result.error || 'Processing failed');
            }

        } catch (error) {
            console.error('Error:', error);
            alert(`Error: ${error.message}`);
            resetApp();
        }
    }

    function showResults(result) {
        processingSection.style.display = 'none';
        resultsSection.style.display = 'block';

        // Summary statistics
        const summaryHtml = `
            <p><strong>Original Rows:</strong> ${result.summary.original_shape[0]}</p>
            <p><strong>Cleaned Rows:</strong> ${result.summary.original_shape[0]}</p>
            <p><strong>Columns:</strong> ${result.summary.original_shape[1]}</p>
            <p><strong>Column Names:</strong> ${result.summary.columns.join(', ')}</p>
        `;
        document.getElementById('summaryStats').innerHTML = summaryHtml;

        // Issues found
        const totalMissing = Object.values(result.summary.missing_values).reduce((a, b) => a + b, 0);
        const issuesHtml = `
            <p><strong>Missing Values:</strong> ${totalMissing}</p>
            <p><strong>Operations Performed:</strong> ${result.summary.log.length}</p>
        `;
        document.getElementById('issuesFound').innerHTML = issuesHtml;

        // Preview table
        const tableHtml = generateTableHTML(result.preview);
        document.getElementById('previewTable').innerHTML = tableHtml;

        // Cleaning log
        const logHtml = result.summary.log.map(entry => 
            `<div><strong>${Object.keys(entry)[0]}:</strong> ${JSON.stringify(entry, null, 2)}</div>`
        ).join('<br>');
        document.getElementById('cleaningLog').innerHTML = logHtml;
    }

    function generateTableHTML(data) {
        if (!data || data.length === 0) return '<p>No data to display</p>';
        
        const headers = Object.keys(data[0]);
        const headerRow = '<thead><tr>' + headers.map(h => `<th>${h}</th>`).join('') + '</tr></thead>';
        const bodyRows = '<tbody>' + data.map(row => 
            '<tr>' + headers.map(h => `<td>${row[h] || ''}</td>`).join('') + '</tr>'
        ).join('') + '</tbody>';
        
        return headerRow + bodyRows;
    }

    async function downloadCSV() {
        if (!currentResult) return;
        const filename = currentResult.cleaned_filename.replace('cleaned_' + currentResult.file_id + '_', '');
        const url = `${API_BASE_URL}/download/csv/${currentResult.file_id}/${filename}`;
        window.open(url, '_blank');
    }

    async function downloadLog() {
        if (!currentResult) return;
        const filename = currentResult.log_filename.replace('log_' + currentResult.file_id + '_', '');
        const url = `${API_BASE_URL}/download/log/${currentResult.file_id}/${filename}`;
        window.open(url, '_blank');
    }

    function resetApp() {
        uploadSection.style.display = 'block';
        processingSection.style.display = 'none';
        resultsSection.style.display = 'none';
        fileInput.value = '';
        selectedFile = null;
        currentResult = null;
    }

    // Add back button functionality
    window.resetApp = resetApp;
    
    console.log('App initialized successfully!');
});
