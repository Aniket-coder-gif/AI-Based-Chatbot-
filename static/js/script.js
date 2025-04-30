document.addEventListener('DOMContentLoaded', function() {
    // Chat elements
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const chatStatus = document.getElementById('chat-status');
    const avatarContainer = document.getElementById('avatar-container');
    const appContainer = document.getElementById('app-container');
    const closeButton = document.getElementById('close-button');
    
    // New UI elements
    const themeToggle = document.getElementById('theme-toggle');
    const chatButton = document.getElementById('chat-button');
    const heroChatButton = document.getElementById('hero-chat-button');
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    
    // Storage status tracking
    let usingFallbackStorage = false;
    
    // Initialize - chat should be hidden, avatar visible
    appContainer.classList.remove('active');
    
    // Track if history has been loaded
    let historyLoaded = false;
    
    // Check system status
    async function checkStatus() {
        try {
            const response = await fetch('/api/status');
            if (response.ok) {
                const data = await response.json();
                console.log('System status:', data);
                
                // Check MongoDB status
                if (data.mongodb && data.mongodb.includes('fallback')) {
                    usingFallbackStorage = true;
                    console.log('Using fallback file storage');
                }
                
                // Check Gemini API status
                if (data.gemini_api !== 'online') {
                    console.warn('Gemini API issue:', data.gemini_api);
                    // Could show a warning in the UI if needed
                }
            }
        } catch (error) {
            console.error('Error checking system status:', error);
        }
    }
    
    // Run status check on load
    checkStatus();
    
    // Theme toggle functionality
    themeToggle.addEventListener('click', function() {
        document.body.classList.toggle('dark-theme');
        const isDarkTheme = document.body.classList.contains('dark-theme');
        themeToggle.innerHTML = isDarkTheme ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
    });
    
    // Mobile menu toggle
    mobileMenuToggle.addEventListener('click', function() {
        const mainNav = document.querySelector('.main-nav');
        const headerActions = document.querySelector('.header-actions');
        
        mainNav.classList.toggle('active');
        headerActions.classList.toggle('active');
        mobileMenuToggle.classList.toggle('active');
        
        const isActive = mobileMenuToggle.classList.contains('active');
        mobileMenuToggle.innerHTML = isActive ? '<i class="fas fa-times"></i>' : '<i class="fas fa-bars"></i>';
    });
    
    // Load chat history from the database
    async function loadChatHistory() {
        if (historyLoaded) return;
        
        try {
            chatMessages.innerHTML = ''; // Clear existing messages
            showTypingIndicator();
            
            const response = await fetch('/api/history');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            hideTypingIndicator();
            
            if (data.history && data.history.length > 0) {
                data.history.forEach(msg => {
                    const isUser = msg.role === 'user';
                    displaySavedMessage(msg.content, isUser, new Date(msg.timestamp));
                });
                historyLoaded = true;
                scrollToBottom();
            } else if (!document.querySelector('.bot-message')) {
                // Add default welcome message if no history and no welcome message
                const welcomeMsg = "Hello! I'm your AI assistant. How can I help you today?";
                displaySavedMessage(welcomeMsg, false, new Date());
            }
        } catch (error) {
            hideTypingIndicator();
            console.error('Error loading chat history:', error);
            if (!document.querySelector('.bot-message')) {
                const errorMsg = usingFallbackStorage 
                    ? "I'm currently using backup storage. Your chat history may be limited. How can I help you today?"
                    : "Sorry, couldn't load chat history. How can I help you today?";
                displaySavedMessage(errorMsg, false, new Date());
            }
        }
    }
    
    // Clear chat history
    async function clearChatHistory() {
        try {
            showTypingIndicator();
            
            const response = await fetch('/api/clear-history', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            hideTypingIndicator();
            
            if (data.success) {
                chatMessages.innerHTML = ''; // Clear UI
                historyLoaded = false;
                
                // Add welcome message
                const welcomeMsg = "Chat history cleared. How can I help you today?";
                displaySavedMessage(welcomeMsg, false, new Date());
                scrollToBottom();
            }
        } catch (error) {
            hideTypingIndicator();
            console.error('Error clearing chat history:', error);
            addMessage(usingFallbackStorage 
                ? "Could not clear chat history. I'm currently using backup storage." 
                : "Error clearing chat history. Please try again.", false);
        }
    }
    
    // Add clear history button to chat header
    function addClearHistoryButton() {
        const appHeader = document.querySelector('.app-header');
        if (!appHeader) return;
        
        const clearHistoryBtn = document.createElement('button');
        clearHistoryBtn.id = 'clear-history-btn';
        clearHistoryBtn.className = 'clear-history-btn';
        clearHistoryBtn.innerHTML = '<i class="fas fa-trash-alt"></i>';
        clearHistoryBtn.title = 'Clear Chat History';
        
        clearHistoryBtn.addEventListener('click', clearChatHistory);
        
        appHeader.appendChild(clearHistoryBtn);
    }
    
    // Call this function once to add the button
    addClearHistoryButton();
    
    // Chat toggle functionality - multiple entry points
    function toggleChat() {
        appContainer.classList.add('active');
        userInput.focus();
        
        // Load chat history if not already loaded
        loadChatHistory();
        
        scrollToBottom();
        
        // Add bounce animation
        avatarContainer.classList.add('bounce');
        setTimeout(() => {
            avatarContainer.classList.remove('bounce');
        }, 1000);
    }
    
    // Avatar click to open chat
    avatarContainer.addEventListener('click', toggleChat);
    
    // Hero section chat button
    if (heroChatButton) {
        heroChatButton.addEventListener('click', toggleChat);
    }
    
    // Close button functionality
    closeButton.addEventListener('click', function(e) {
        e.stopPropagation();
        appContainer.classList.remove('active');
    });
    
    // Close chat when clicking outside
    document.addEventListener('click', function(e) {
        if (appContainer.classList.contains('active')) {
            if (!appContainer.contains(e.target) && 
                !avatarContainer.contains(e.target) && 
                (heroChatButton && !heroChatButton.contains(e.target))) {
                appContainer.classList.remove('active');
            }
        }
    });
    
    // Animation for avatar on page load
    setTimeout(() => {
        avatarContainer.classList.add('active');
    }, 500);

    // Scroll to bottom of chat
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTypingIndicator() {
        chatStatus.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';
    }

    function hideTypingIndicator() {
        chatStatus.innerHTML = '';
    }

    function getTimeString(timestamp) {
        const date = timestamp || new Date();
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    // Display saved message from history (doesn't save to DB again)
    function displaySavedMessage(content, isUser, timestamp) {
        if (!content) return; // Skip empty messages
        
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'bot-message');
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.classList.add('message-bubble');
        
        if (!isUser) {
            const iconSpan = document.createElement('i');
            iconSpan.classList.add('fas', 'fa-robot', 'bot-icon');
            bubbleDiv.appendChild(iconSpan);
        }
        
        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');
        contentDiv.textContent = content;
        
        const timeSpan = document.createElement('span');
        timeSpan.classList.add('message-time');
        timeSpan.textContent = getTimeString(timestamp);
        
        bubbleDiv.appendChild(contentDiv);
        bubbleDiv.appendChild(timeSpan);
        messageDiv.appendChild(bubbleDiv);
        chatMessages.appendChild(messageDiv);
    }

    function addMessage(content, isUser) {
        if (!content) return; // Skip empty messages
        
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'bot-message');
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.classList.add('message-bubble');
        
        if (!isUser) {
            const iconSpan = document.createElement('i');
            iconSpan.classList.add('fas', 'fa-robot', 'bot-icon');
            bubbleDiv.appendChild(iconSpan);
        }
        
        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');
        contentDiv.textContent = content;
        
        const timeSpan = document.createElement('span');
        timeSpan.classList.add('message-time');
        timeSpan.textContent = getTimeString();
        
        bubbleDiv.appendChild(contentDiv);
        bubbleDiv.appendChild(timeSpan);
        messageDiv.appendChild(bubbleDiv);
        chatMessages.appendChild(messageDiv);
        
        scrollToBottom();
    }

    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        // Add user message to chat
        addMessage(message, true);
        userInput.value = '';
        userInput.focus();
        
        // Show typing indicator
        showTypingIndicator();
        
        // Add a slight delay before showing typing indicator (simulates real typing)
        const typingDelay = Math.min(1000, message.length * 50);
        
        // Make avatar pulse more noticeably during processing
        avatarContainer.classList.add('processing');

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            // Ensure typing indicator shows for at least a short time
            setTimeout(() => {
                // Hide typing indicator
                hideTypingIndicator();
                avatarContainer.classList.remove('processing');
                
                // Process response
                if (response.ok) {
                    response.json().then(data => {
                        if (data.error) {
                            addMessage("Error: " + data.error, false);
                        } else {
                            addMessage(data.response, false);
                        }
                    });
                } else {
                    const fallbackMsg = usingFallbackStorage 
                        ? "I'm having trouble connecting to my main system. I'm using backup storage, but some features may be limited."
                        : "Error: Server returned status " + response.status;
                    addMessage(fallbackMsg, false);
                }
            }, typingDelay);
        } catch (error) {
            setTimeout(() => {
                hideTypingIndicator();
                avatarContainer.classList.remove('processing');
                const errorMsg = usingFallbackStorage
                    ? "I'm currently in offline mode with limited capabilities. Please try again later."
                    : "Error connecting to the chatbot. Please try again.";
                addMessage(errorMsg, false);
                console.error('Error:', error);
            }, 1000);
        }
    }

    sendButton.addEventListener('click', sendMessage);
    
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Add input focus styles
    userInput.addEventListener('focus', function() {
        document.querySelector('.chat-input').classList.add('focused');
    });
    
    userInput.addEventListener('blur', function() {
        document.querySelector('.chat-input').classList.remove('focused');
    });
    
    // Add animation to initial message
    setTimeout(() => {
        const botMessage = document.querySelector('.bot-message');
        if (botMessage) botMessage.classList.add('animate');
    }, 300);
    
    // Handle ESC key to close chat
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && appContainer.classList.contains('active')) {
            appContainer.classList.remove('active');
        }
    });
    
    // Add smooth scrolling for nav links
    document.querySelectorAll('.main-nav a').forEach(link => {
        link.addEventListener('click', function(e) {
            // Allow default action for the About link
        if (this.getAttribute('href') === '/about') {
            return; // Do nothing, let the link work as intended
        }
            e.preventDefault(); // Prevent default for other links
            
            // Add active class to clicked link and remove from siblings
            document.querySelectorAll('.main-nav a').forEach(navLink => {
                navLink.classList.remove('active');
            });
            this.classList.add('active');
            
            // For a real website, you would add scroll to section here
            // const targetId = this.getAttribute('href').substring(1);
            // const targetSection = document.getElementById(targetId);
            // window.scrollTo({
            //     top: targetSection.offsetTop - 80,
            //     behavior: 'smooth'
            // });
        });
    });
});