// Establish connection with Flask-SocketIO backend
const socket = io();

// Initialize speech recognition
const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.lang = "en-US";
recognition.continuous = true; // Keep listening
recognition.interimResults = false;
recognitionStarted = false; // Ensure variable exists

recognition.start();
recognitionStarted = true; // Set to true when recognition starts

let isListening = false; // Track if wake word is detected

recognition.onresult = function(event) {
    let transcript = event.results[event.results.length - 1][0].transcript.trim();
    console.log("🗣 User said:", transcript);
    
    if (transcript.toLowerCase().includes("reporter")) {
        isListening = true; // Activate processing
        console.log("🎤 Wake word detected: Hey Reporter");
    } else if (isListening) {
        isListening = false; // Stop listening for new input
        sendSpeechToBackend(transcript);
    }
};

recognition.onerror = function(event) {
    console.error("❌ Speech recognition error:", event.error);
};


// Fix: Prevent recognition from restarting incorrectly
recognition.onend = function() {
    console.log("🛑 Speech recognition stopped.");
    if (!recognitionStarted) {
        console.log("🎙 Restarting speech recognition...");
        recognition.start();
        recognitionStarted = true;
    }
};

// Send recognized speech to backend
function sendSpeechToBackend(text) {
    console.log("📡 Sending speech to backend:", text);

    fetch("/process_speech", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
    })
    .then(response => response.json())
    .then(data => {
        console.log("🤖 Response from Flask:", data.reply);
        speakText(data.reply);
    })
    .catch(error => console.error("❌ Error:", error));
}

let isTTSActivated = false;

function activateTTS() {
    if (isTTSActivated) return;

    console.log("🛠 Activating TTS...");
    
    let silentSpeech = new SpeechSynthesisUtterance(".");
    silentSpeech.volume = 0.1;  // Set low volume instead of 0
    silentSpeech.rate = 1;
    silentSpeech.lang = "en-IN"; // Use Indian English

    silentSpeech.onend = () => {
        console.log("✅ TTS Activated!");
        isTTSActivated = true;
        speakText("Welcome to Virtual News Reporter! Please say 'reporter' to start.");
    };

    window.speechSynthesis.speak(silentSpeech);
}

// 🔹 Ensure TTS activates on user interaction
document.addEventListener("click", activateTTS, { once: true });
document.addEventListener("keydown", activateTTS, { once: true });
document.addEventListener("touchstart", activateTTS, { once: true });

// Fix: Ensure speech works after activation
function speakText(text) {
    if (!isTTSActivated) {
        console.warn("⚠ TTS is not activated yet! Waiting...");
        return;
    }

    if (!text || text.trim() === "") {
        console.warn("⚠ No text provided for speech output.");
        return;
    }

    let speech = new SpeechSynthesisUtterance(text);
    speech.lang = "en-US";
    speech.rate = 1;
    speech.volume = 2;

    // 🔊 Select a different voice  
    let voices = window.speechSynthesis.getVoices();
    let selectedVoice = voices.find(voice => voice.name.includes("Google हिन्दी")); // Example: Change this  
    if (selectedVoice) {
        speech.voice = selectedVoice;
    } else {
        console.warn("⚠ Custom voice not found. Using default.");
    }

    console.log("🔊 Speaking with voice:", speech.voice.name);
    console.log("🔊 Speaking response...");
    recognition.stop(); // Stop recognition while speaking
    recognitionStarted = false;


    // Reset TTS before speaking to prevent Chrome blocking
    window.speechSynthesis.cancel();

    setTimeout(() => {
        window.speechSynthesis.speak(speech);
    }, 100); // Delay ensures Chrome processes request

    speech.onend = () => {
        console.log("✅ Speech finished, resuming recognition...");
        setTimeout(() => {
            recognition.start();
            recognitionStarted = true;
        }, 5000);
    };
}

window.onload = () => {
    console.log("🔄 Page loaded, trying to activate TTS...");
    setTimeout(activateTTS, 1500); // Small delay for smooth activation
};


// 📌 Open & Close Settings Modal
function openSettings() {
    document.getElementById("settingsModal").style.display = "flex";
}

function closeSettings() {
    document.getElementById("settingsModal").style.display = "none";
}

window.onclick = function(event) {
    let modal = document.getElementById("settingsModal");
    if (event.target == modal) {
        modal.style.display = "none";
    }
};

// 🔐 Logout Functionality
function confirmLogout() {
    if (confirm("Are you sure you want to log out?")) {
        logout();
    }
}

function logout() {
    fetch('/logout', { method: 'GET', credentials: 'include' }) 
    .then(() => {
        alert("You have been logged out!");
        window.location.href = "/login"; 
    })
    .catch(error => console.error("Logout failed:", error));
}

// 🌐 Fetch selected news domain from backend
document.addEventListener("DOMContentLoaded", function() {
    fetch('/get_news_domain', { credentials: "include" })
    .then(response => response.json())
    .then(data => {
        if (!data || !data.domain) {
            console.error("Invalid response from server.");
            return;
        }

        let selectElement = document.querySelector("#domain");
        let fetchedDomain = data.domain.toLowerCase();

        for (let option of selectElement.options) {
            if (option.value.toLowerCase() === fetchedDomain) {
                option.selected = true;
                console.log("Set selected domain:", option.value);
                break;
            }
        }
    })
    .catch(error => console.error("Error fetching domain:", error));
});

// 🔄 Update news domain and discussion setting
function updateDomain() {
    let selectElement = document.querySelector("#domain");
    let discussionToggle = document.querySelector("#discussionToggle");

    if (!selectElement || !discussionToggle) { 
        console.error("Dropdown or toggle element not found!"); 
        return;
    }

    let selectedDomain = selectElement.value;
    let discussionEnabled = discussionToggle.checked ? 1 : 0; 

    console.log("Updating domain to:", selectedDomain);
    console.log("Discussion Enabled:", discussionEnabled);

    fetch('/update_news_domain', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain: selectedDomain })
    })
    .then(response => response.json())
    .then(data => console.log("News domain update successful:", data))
    .catch(error => console.error("News domain update failed:", error));

    fetch('/update_discussion_setting', { 
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ discussion_enabled: discussionEnabled })
    })
    .then(response => response.json())
    .then(data => console.log("Discussion setting update successful:", data))
    .catch(error => console.error("Discussion setting update failed:", error));
}

// 🚀 Fetch domain on load (Authentication Check)
fetch('/get_news_domain', { credentials: "include" })
.then(response => {
    if (response.status === 401) {
        console.error("User is not authenticated!");
        return Promise.reject("Unauthorized");
    }
    return response.json();
})
.then(data => {
    if (!data || !data.domain) {
        console.error("Invalid response from server.");
        return;
    }

    let selectElement = document.querySelector("select");
    let fetchedDomain = data.domain.toLowerCase();

    for (let option of selectElement.options) {
        if (option.value.toLowerCase() === fetchedDomain) {
            option.selected = true;
            console.log("Set selected domain:", option.value);
            break;
        }
    }

     // Update Discussion Mode Toggle
     let discussionToggle = document.getElementById("discussion-toggle");
     discussionToggle.checked = data.discussion_mode;
     console.log("Set discussion mode:", data.discussion_mode);
})
.catch(error => console.error("Error fetching domain:", error));

// ⌨ Close settings modal on Escape key press
document.addEventListener("keydown", function(event) {
    if (event.key === "Escape") {
        closeSettings();
    }
});
