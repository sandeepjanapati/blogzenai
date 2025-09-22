document.addEventListener('DOMContentLoaded', () => {

    const firebaseConfig = {
      apiKey: "AIzaSyAZTNe_2vLOP1Ommwb99Bj46h81phBVFj8",
      authDomain: "bolgzenai.firebaseapp.com",
      projectId: "bolgzenai",
      storageBucket: "bolgzenai.appspot.com", // Note: This might be different (e.g., bolgzenai.firebasestorage.app) check your console
      messagingSenderId: "474557573729",
      appId: "1:474557573729:web:409bea6f9b3e0979745820",
      measurementId: "G-5M6ZM3XJPW"
    };
    firebase.initializeApp(firebaseConfig);
    const auth = firebase.auth();

    // --- DOM Elements ---
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const authContainer = document.getElementById('auth-container');
    const userInfoDiv = document.getElementById('user-info');
    const userDisplay = document.getElementById('user-display');
    const form = document.getElementById('blog-form');


    // --- Handle User State Changes ---
    auth.onAuthStateChanged(user => {
        if (user) {
            // User is signed IN
            loginBtn.style.display = 'none';
            userInfoDiv.style.display = 'block';
            userDisplay.textContent = `Welcome, ${user.displayName}!`;
        } else {
            // User is signed OUT
            loginBtn.style.display = 'block';
            userInfoDiv.style.display = 'none';
        }
    });

    // --- Event Listeners ---
    loginBtn.addEventListener('click', () => {
        const provider = new firebase.auth.GoogleAuthProvider();
        auth.signInWithPopup(provider);
    });

    logoutBtn.addEventListener('click', () => {
        auth.signOut();
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        let currentUser = auth.currentUser;

        // ** THIS IS THE CORE LOGIC CHANGE **
        // If user is not logged in, trigger the login popup
        if (!currentUser) {
            try {
                const provider = new firebase.auth.GoogleAuthProvider();
                const result = await auth.signInWithPopup(provider);
                currentUser = result.user; // Now we have the user
            } catch (error) {
                console.error("Login failed:", error);
                alert("You must sign in to generate content.");
                return; // Stop if login fails or is cancelled
            }
        }

        // --- Proceed with generation since we now have a user ---
        const token = await currentUser.getIdToken();
        const topic = document.getElementById('topic').value;
        const tone = document.getElementById('tone').value;

        setLoadingState(true);

        try {
            const response = await fetch(`${API_URL}/generate-blog`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ topic, tone: tone || 'informative' })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'An unknown error occurred.');
            }

            const data = await response.json();
            displayContent(data.blog_content_markdown);
            loadHistory();
        } catch (error) {
            console.error('Error generating blog:', error);
            alert(`Generation Failed: ${error.message}`);
        } finally {
            setLoadingState(false);
        }
    });

    // IMPORTANT: Replace with your API URL
    // For local testing: 'http://127.0.0.1:8000'
    // For production: 'https://your-cloud-run-service-url'
    const API_URL = 'https://blogzenai-api-474557573729.asia-south1.run.app';

    const generateBtn = document.getElementById('generate-btn');
    const btnText = document.querySelector('.btn-text');
    const loader = document.querySelector('.loader');
    
    const resultsSection = document.getElementById('results-section');
    const blogOutput = document.getElementById('blog-output');
    const historyList = document.getElementById('history-list');

    // Initialize Showdown Markdown converter
    const converter = new showdown.Converter();

    const displayContent = (markdown) => {
        const htmlContent = converter.makeHtml(markdown);
        blogOutput.innerHTML = htmlContent;
        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    };

    const setLoadingState = (isLoading) => {
        if (isLoading) {
            generateBtn.disabled = true;
            btnText.style.display = 'none';
            loader.style.display = 'block';
        } else {
            generateBtn.disabled = false;
            btnText.style.display = 'block';
            loader.style.display = 'none';
        }
    };
    
    const loadHistory = async () => {
        try {
            const response = await fetch(`${API_URL}/history?limit=10`);
            if (!response.ok) throw new Error('Failed to fetch history');
            const history = await response.json();
            
            historyList.innerHTML = '';
            if (history.length === 0) {
                 historyList.innerHTML = '<li class="placeholder">No history yet.</li>';
                 return;
            }

            history.forEach(item => {
                const li = document.createElement('li');
                li.textContent = `📝 ${item.topic}`;
                li.dataset.id = item.id;
                li.title = `View post on "${item.topic}"`;
                li.addEventListener('click', () => viewHistoryItem(item.id));
                historyList.appendChild(li);
            });
        } catch (error) {
            console.error('Error loading history:', error);
            historyList.innerHTML = '<li class="placeholder">Could not load history.</li>';
        }
    };

    const viewHistoryItem = async (id) => {
        setLoadingState(true); // Show loader on button while fetching history
        try {
            const response = await fetch(`${API_URL}/history/${id}`);
            if (!response.ok) throw new Error('History item not found');
            const item = await response.json();
            displayContent(item.markdown_content);
        } catch (error) {
            console.error('Error viewing history item:', error);
            alert('Could not retrieve this history item.');
        } finally {
            setLoadingState(false);
        }
    };

    // Initial load
    loadHistory();
});