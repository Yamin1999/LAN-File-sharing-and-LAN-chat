/* file download */
async function downloadFile(filename) {
  try {
    const response = await fetch(`/download/${filename}`);

    if (response.ok) {
      // If file exists, proceed with download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } else if (response.status === 404) {
      // If file doesn't exist, redirect to home page
      window.location.href = "/";
    }
  } catch (error) {
    console.error("Error downloading file:", error);
    // Redirect to home in case of an error
    window.location.href = "/";
  }
}

/* file deletion */
let fileToDelete = "";

function confirmDelete(filename) {
  fileToDelete = filename;
  const modal = document.getElementById("deleteModal");
  modal.style.display = "flex";
}

/* dom operations */
function closeModal_delete() {
  const deleteModal = document.getElementById("deleteModal");
  deleteModal.style.display = "none";
}

function confirmClearAll() {
  const modal = document.getElementById("clearAllModal");
  modal.style.display = "flex";
}

function closeClearAllModal() {
  const modal = document.getElementById("clearAllModal");
  modal.style.display = "none";
}

function clearAllFiles() {
  document.getElementById("clearAllForm").submit();
}

/* file deletion */
async function deleteFile() {
  try {
    const response = await fetch(`/delete/${fileToDelete}`, {
      method: "POST",
    });

    if (response.ok) {
      window.location.reload();
    } else {
      alert("Error deleting file");
    }
  } catch (error) {
    console.error("Error:", error);
    alert("Error deleting file");
  }
  closeModal_delete();
}

/* on click event */
// Close modals when clicking outside
window.onclick = function (event) {
  const deleteModal = document.getElementById("deleteModal");
  const clearAllModal = document.getElementById("clearAllModal");
  
  // Check if click is on the modal background
  if (event.target == deleteModal) {
    deleteModal.style.display = "none";
  }
  if (event.target == clearAllModal) {
    clearAllModal.style.display = "none";
  }
};
/* drag and drop */
document.addEventListener("DOMContentLoaded", function () {
  const uploadContainer = document.getElementById("upload-container");
  const fileInput = document.getElementById("fileInput");
  const uploadList = document.getElementById("upload-list");

  ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    uploadContainer.addEventListener(eventName, preventDefaults, false);
    document.body.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ["dragenter", "dragover"].forEach((eventName) => {
    uploadContainer.addEventListener(eventName, () => {
      uploadContainer.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    uploadContainer.addEventListener(eventName, () => {
      uploadContainer.classList.remove("dragover");
    });
  });

  uploadContainer.addEventListener("drop", handleDrop);
  uploadContainer.addEventListener("click", () => {
    fileInput.click();
  });

  fileInput.addEventListener("change", function (e) {
    handleFiles(Array.from(this.files));
  });
});

async function handleDrop(e) {
  const files = Array.from(e.dataTransfer.files);
  handleFiles(files);
}

/* file upload */
async function handleFiles(files) {
  const MAX_FILE_SIZE = 1024 * 1024 * 1024; // 1GB in bytes - match this with your server config
  const uploadContainer = document.getElementById("upload-container");

  for (const file of files) {
    if (file.size > MAX_FILE_SIZE) {
      uploadContainer.classList.remove("uploading");
      uploadContainer.classList.add("upload-error");
      uploadContainer.innerHTML = `
                <div class="upload-icon">⚠️</div>
                File too large! Maximum size is ${formatFileSize(MAX_FILE_SIZE)}
            `;
      setTimeout(() => {
        uploadContainer.classList.remove("upload-error");
        uploadContainer.innerHTML = `
                    <div class="upload-icon">📤</div>
                    Drag & Drop files here or click to upload<br>
                    <small>Maximum file size: ${formatFileSize(
                      MAX_FILE_SIZE
                    )}</small>
                `;
      }, 3000);
      return;
    }

    uploadContainer.classList.add("uploading");
    uploadContainer.innerHTML = `
            <div class="upload-icon">⏳</div>
            Uploading ${file.name}<br>
            <small>${formatFileSize(file.size)}</small>
        `;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/upload", {
        method: "POST",
        body: formData,
      });

      //console.log(response);

      if (response.ok) {
        uploadContainer.innerHTML = `
                    <div class="upload-icon">🎉</div>
                    Upload successful!
                `;
        setTimeout(() => window.location.reload(), 1000);
      } else {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.error("Error:", error);
      uploadContainer.classList.remove("uploading");
      uploadContainer.classList.add("upload-error");
      uploadContainer.innerHTML = `
                <div class="upload-icon">❌</div>
                Upload failed: ${error.message}
            `;
    }
  }
}

/* file size formatting */
function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";

  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

// Verify background image loading
const bgImage = new Image();
bgImage.src = "{{ url_for('static', filename='images/bdcom.jpg') }}";
bgImage.onerror = function () {
  console.error("Error loading background image");
  // Fallback to a solid color if image fails to load
  document.body.style.backgroundColor = "#f0f2f5";
};

function openPopup() {
  const popup = document.getElementById('noticePopup');
  popup.style.display = 'flex';
  document.body.style.overflow = 'hidden';
}

function closePopup() {
  const popup = document.getElementById('noticePopup');
  popup.style.display = 'none';
  document.body.style.overflow = 'auto';
}

function closePopupOnOverlay(event) {
  if (event.target === event.currentTarget) {
    closePopup();
  }
}


let selectedFile = null;
const socket = io();
const messageList = document.getElementById('messageList');
const messageForm = document.getElementById('messageForm');
const messageInput = document.getElementById('messageInput');
const imageInput = document.getElementById('imageInput');
const imagePreview = document.getElementById('imagePreview');
const previewContainer = document.getElementById('previewContainer');
const modal = document.getElementById('imageModal');
const modalImage = document.getElementById('modalImage');

// Add new scroll function
function scrollToBottom(smooth = true) {
  // Wait for DOM to update
  setTimeout(() => {
    messageList.scrollTo({
      top: messageList.scrollHeight,
      behavior: smooth ? 'smooth' : 'auto'
    });
  }, 0);
}

function toggleChat() {
  const chatPopup = document.getElementById('chatPopup');
  chatPopup.classList.toggle('active');
  if (chatPopup.classList.contains('active')) {
    scrollToBottom(false); // Instant scroll when opening chat
  }
}

function formatTime(timestamp) {
  const date = new Date(timestamp);
  const utcOffset = 6; // UTC+6
  const localTime = new Date(date.getTime() + utcOffset * 60 * 60 * 1000);
  return localTime.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
}

function createMessageElement(data) {
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message';

  const header = document.createElement('div');
  header.className = 'message-header';
  header.innerHTML = `
    <strong>${data.sender}</strong>
    <span class="message-time">${formatTime(data.timestamp)}</span>
  `;

  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';

  if (data.message_type === 'image') {
    contentDiv.innerHTML = data.message;
    const imgElement = contentDiv.querySelector('img');
    if (imgElement) {
      imgElement.onload = () => scrollToBottom(); // Scroll after image loads
      imgElement.onclick = () => showImage(imgElement.src);
    }
  } else {
    contentDiv.innerHTML = data.message;
  }

  messageDiv.appendChild(header);
  messageDiv.appendChild(contentDiv);
  return messageDiv;
}

function showPreview(file) {
  if (file) {
    const reader = new FileReader();
    reader.onload = function(e) {
      imagePreview.querySelector('img').src = e.target.result;
      previewContainer.style.display = 'block';
      scrollToBottom(); // Scroll after preview shows
    };
    reader.readAsDataURL(file);
  }
}

function removePreview() {
  previewContainer.style.display = 'none';
  imagePreview.querySelector('img').src = '';
  imageInput.value = '';
  selectedFile = null;
}

function showImage(src) {
  modalImage.src = src;
  modal.classList.add('active');
}

function closeModal() {
  modal.classList.remove('active');
}

// Event Listeners
imageInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (file && file.type.startsWith('image/')) {
    selectedFile = file;
    showPreview(file);
  }
});

modal.addEventListener('click', (e) => {
  if (e.target === modal) {
    closeModal();
  }
});

messageForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = messageInput.value.trim();

  if (selectedFile) {
    const reader = new FileReader();
    reader.onload = function(e) {
      const imageData = new Uint8Array(e.target.result);
      socket.emit('image_upload', {
        filename: selectedFile.name,
        image: imageData,
        message: message
      });
      removePreview();
      messageInput.value = '';
    };
    reader.readAsArrayBuffer(selectedFile);
  } else if (message) {
    socket.emit('chat_message', { message });
    messageInput.value = '';
  }
});

socket.on('connect', () => {
  console.log('Connected to chat');
});

socket.on('chat_history', (messages) => {
  messageList.innerHTML = '';
  messages.forEach(msg => {
    const messageElement = createMessageElement(msg);
    messageList.appendChild(messageElement);
  });
  scrollToBottom(false); // Instant scroll for initial load
});

socket.on('new_message', (data) => {
  const messageElement = createMessageElement(data);
  messageList.appendChild(messageElement);
  
  // If chat is not already active, toggle it open
  const chatPopup = document.getElementById('chatPopup');
  if (!chatPopup.classList.contains('active')) {
    toggleChat();
  }
  
  scrollToBottom(); // Smooth scroll for new messages
});

socket.on('user_list', (users) => {
  console.log('Active users:', users);
});