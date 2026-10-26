let currentCV_HTML = "";
let currentLetter_HTML = "";
let activeTab = "cv";

async function uploadCV() {
  const fileInput = document.getElementById("cv_file");
  const file = fileInput.files[0];
  if (!file) return;
  const uploadStatus = document.getElementById("upload-status");
  uploadStatus.textContent = "Extracting text...";
  const formData = new FormData();
  formData.append("file", file);
  try {
    const response = await fetch("/extract", { method: "POST", body: formData });
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    document.getElementById("experience").value = data.text;
    uploadStatus.textContent = "✅ CV extracted successfully!";
    setTimeout(() => { uploadStatus.textContent = ""; }, 3000);
  } catch (e) {
    uploadStatus.style.color = "#ef4444";
    uploadStatus.textContent = "Error: " + e.message;
  }
}

async function generateCV() {
  const exp = document.getElementById("experience").value;
  const jd = document.getElementById("job_description").value;
  const title = document.getElementById("job_title").value;
  
  const btn = document.getElementById("generateBtn");
  const btnText = document.getElementById("btn-text");
  const spinner = document.getElementById("btn-spinner");
  const status = document.getElementById("status");
  const cvPreview = document.getElementById("cv-preview");
  const letterPreview = document.getElementById("letter-preview");
  const downloadBtn = document.getElementById("downloadBtn");
  const sendOptions = document.getElementById("send-options-container");
  
  if (!exp || !jd || !title) { 
    alert("Please provide your experience, target job title, and job description."); 
    return; 
  }
  
  btn.disabled = true;
  btnText.textContent = "Analyzing & Optimizing...";
  spinner.style.display = "block";
  downloadBtn.style.display = "none";
  sendOptions.style.display = "none";
  document.getElementById("send-status").textContent = "";
  status.textContent = "This takes 15-30 seconds...";
  cvPreview.innerHTML = "<div class='empty-state'>Writing your ATS CV...</div>";
  letterPreview.innerHTML = "<div class='empty-state'>Writing your Motivational Letter...</div>";
  
  const formData = new FormData();
  formData.append("experience", exp);
  formData.append("job_description", jd);
  formData.append("job_title", title);
  
  try {
    const response = await fetch("/generate", { method: "POST", body: formData });
    const data = await response.json();
    
    if (data.error) throw new Error(data.error);
    
    // Save the HTML to our variables
    currentCV_HTML = data.cv_html;
    currentLetter_HTML = data.letter_html;
    
    // Inject into the UI
    cvPreview.innerHTML = currentCV_HTML;
    letterPreview.innerHTML = currentLetter_HTML;
    
    status.textContent = "";
    
    // Switch to CV tab by default
    switchTab("cv");
    
    downloadBtn.style.display = "flex";
    sendOptions.style.display = "block";
  } catch (e) {
    status.textContent = "Error: " + e.message;
    cvPreview.innerHTML = "<div class='empty-state'>Generation failed.</div>";
    letterPreview.innerHTML = "<div class='empty-state'>Generation failed.</div>";
  } finally {
    btn.disabled = false;
    btnText.textContent = "Optimize CV & Letter";
    spinner.style.display = "none";
  }
}

function switchTab(tab) {
  activeTab = tab;
  const cvPreview = document.getElementById("cv-preview");
  const letterPreview = document.getElementById("letter-preview");
  const tabCV = document.getElementById("tab-cv");
  const tabLetter = document.getElementById("tab-letter");
  
  if (tab === "cv") {
    cvPreview.style.display = "block";
    letterPreview.style.display = "none";
    tabCV.classList.add("active");
    tabLetter.classList.remove("active");
  } else {
    cvPreview.style.display = "none";
    letterPreview.style.display = "block";
    tabCV.classList.remove("active");
    tabLetter.classList.add("active");
  }
}

function getActiveHTML() {
  return activeTab === "cv" ? currentCV_HTML : currentLetter_HTML;
}

async function downloadPDF() {
  const htmlContent = getActiveHTML();
  const downloadBtn = document.getElementById("downloadBtn");
  
  if (!htmlContent) { alert("Please generate first."); return; }
  
  downloadBtn.textContent = "Generating PDF...";
  downloadBtn.disabled = true;
  
  const formData = new FormData();
  formData.append("html_content", htmlContent);
  
  try {
    const response = await fetch("/download", { method: "POST", body: formData });
    if (!response.ok) throw new Error("Failed to create PDF");
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = activeTab === "cv" ? "ATS_Optimized_CV.pdf" : "Motivational_Letter.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (e) {
    alert("Error downloading PDF: " + e.message);
  } finally {
    downloadBtn.textContent = "⬇️ Download as PDF";
    downloadBtn.disabled = false;
  }
}

async function sendEmail() {
  const email = document.getElementById("email_input").value;
  const htmlContent = getActiveHTML();
  const status = document.getElementById("send-status");
  
  if (!email) { alert("Enter a valid email address."); return; }
  if (!htmlContent) { alert("Please generate first."); return; }
  
  status.textContent = "Sending Email...";
  status.style.color = "var(--email-color)";
  
  const formData = new FormData();
  formData.append("html_content", htmlContent);
  formData.append("recipient_email", email);
  
  const res = await fetch("/send-email", { method: "POST", body: formData });
  const data = await res.json();
  
  if (data.error) {
    status.textContent = "Error: " + data.error;
    status.style.color = "#ef4444";
  } else {
    status.textContent = data.message;
    status.style.color = "#10b981";
  }
}

async function sendWhatsApp() {
  const phone = document.getElementById("phone_input").value;
  const htmlContent = getActiveHTML();
  const status = document.getElementById("send-status");
  
  if (!phone) { alert("Enter a phone number with country code."); return; }
  if (!htmlContent) { alert("Please generate first."); return; }
  
  status.textContent = "Sending WhatsApp...";
  status.style.color = "var(--wa-color)";
  
  const formData = new FormData();
  formData.append("html_content", htmlContent);
  formData.append("phone_number", phone);
  
  const res = await fetch("/send-whatsapp", { method: "POST", body: formData });
  const data = await res.json();
  
  if (data.error) {
    status.textContent = "Error: " + data.error;
    status.style.color = "#ef4444";
  } else {
    status.textContent = data.message;
    status.style.color = "#10b981";
  }
}