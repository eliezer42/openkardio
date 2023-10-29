document.addEventListener('DOMContentLoaded', () => {
    const diagnosisForm = document.getElementById('diagnosisForm');
    const examIdInput = diagnosisForm.querySelector('[name="examId"]');

    // Get the examId from the query parameter
    const urlParams = new URLSearchParams(window.location.search);
    const examId = urlParams.get('examId');

    if (!examId) {
        // Exam ID is not provided, show an error message or redirect
        window.location.href = 'no-exam-selected.html';
    } else {
      // Exam ID is provided, populate the hidden input field
      examIdInput.value = examId;

      const endpoint = `https://us-central1-openkardio-6586d.cloudfunctions.net/checkDiagnosisStatus?examId=${examId}`;

      fetch(endpoint)
        .then(response => response.json())
        .then(data => {
          if (data.isDiagnosed) {
            // Exam has been diagnosed
            window.location.href = 'already-diagnosed.html';
          } 
        })
        .catch(error => {
          console.error('Error:', error);
        });

      const subtitleElement = document.querySelector('.subtitle');
      subtitleElement.innerHTML = `ID del caso: <strong>${examId}</strong>`;
    }
    
    if (diagnosisForm) {
      diagnosisForm.addEventListener('submit', async (e) => {
        e.preventDefault();
  
        const diagnosisTextarea = diagnosisForm.querySelector('#diagnosis');
        const diagnosis = diagnosisTextarea.value;
  
        const submissionUrl = 'https://us-central1-openkardio-6586d.cloudfunctions.net/submitDiagnosis';
  
        try {
          const response = await fetch(submissionUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ examId: examId, diagnosis: diagnosis }) // Send diagnosis to the server
          });
  
          if (response.ok) {
            window.location.href = 'submission-success.html';
          } else {
            window.location.href = 'submission-failure.html';
            console.error(response)
          }
        } catch (error) {
          console.error('Error submitting diagnosis', error);
          window.location.href = 'submission-failure.html';
        }
      });
    }
  });
  