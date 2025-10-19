document.addEventListener('DOMContentLoaded', () => {
    // --- Config and Init ---
    const firebaseConfig = {
        apiKey: "AIzaSyAZTNe_2vLOP1Ommwb99Bj46h81phBVFj8",
        authDomain: "bolgzenai.firebaseapp.com",
        projectId: "bolgzenai",
        storageBucket: "bolgzenai.firebasestorage.app",
        messagingSenderId: "474557573729",
        appId: "1:474557573729:web:409bea6f9b3e0979745820",
        measurementId: "G-5M6ZM3XJPW"
        };
    firebase.initializeApp(firebaseConfig);
    const auth = firebase.auth();
    const API_URL = 'https://blogzenai-api-474557573729.asia-south1.run.app';
    const converter = new showdown.Converter({ simplifiedAutoLink: true, strikethrough: true, tables: true });
    
    // --- DOM Elements ---
    const body = document.body, loginBtn = document.getElementById('login-btn'), creatorProfile = document.getElementById('creator-profile'), form = document.getElementById('blog-form'), newBlogBtn = document.getElementById('new-blog-btn'), welcomeView = document.getElementById('welcome-view'), generationView = document.getElementById('generation-view'), blogOutput = document.getElementById('blog-output'), historyList = document.getElementById('history-list'), generateBtn = document.getElementById('generate-btn'), sendIcon = document.querySelector('.send-icon'), loader = document.querySelector('.loader'), menuToggle = document.getElementById('menu-toggle'), sidebar = document.getElementById('sidebar'), sidebarOverlay = document.getElementById('sidebar-overlay'), mobileToneSelect = document.getElementById('tone-mobile'), desktopToneSelect = document.getElementById('tone-desktop');

    // --- UI State ---
    const openSidebar = () => body.classList.add('sidebar-open');
    const closeSidebar = () => body.classList.remove('sidebar-open');
    menuToggle.addEventListener('click', openSidebar);
    sidebarOverlay.addEventListener('click', closeSidebar);
    const showWelcomeView = () => { welcomeView.style.display = 'flex'; generationView.style.display = 'none'; };
    const showGenerationView = (markdownContent) => {
        welcomeView.style.display = 'none';
        generationView.style.display = 'block';
        blogOutput.innerHTML = markdownContent ? converter.makeHtml(markdownContent) : '';
    };
    const setLoadingState = (isLoading) => {
        generateBtn.disabled = isLoading;
        sendIcon.style.display = isLoading ? 'none' : 'block';
        loader.style.display = isLoading ? 'block' : 'none';
    };

    // --- Authentication & History ---
    auth.onAuthStateChanged(async user => {
        if (user) {
            loginBtn.style.display = 'none';
            creatorProfile.style.display = 'flex';
            await loadHistory();
        } else {
            loginBtn.style.display = 'block';
            creatorProfile.style.display = 'none';
            historyList.innerHTML = '<li class="placeholder">Sign in to see history.</li>';
        }
    });
    loginBtn.addEventListener('click', () => {
        const provider = new firebase.auth.GoogleAuthProvider();
        auth.signInWithPopup(provider).catch(error => console.error("Sign-in error", error));
    });
    const loadHistory = async () => {
        const currentUser = auth.currentUser;
        if (!currentUser) return;
        try {
            const token = await currentUser.getIdToken();
            const response = await fetch(`${API_URL}/history`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!response.ok) throw new Error('Failed to fetch history');
            const history = await response.json();
            historyList.innerHTML = '';
            if (history.length === 0) {
                 historyList.innerHTML = '<li class="placeholder">No history yet.</li>';
                 return;
            }
            history.forEach(item => {
                const li = document.createElement('li');
                li.textContent = item.topic;
                li.dataset.id = item.id;
                li.addEventListener('click', () => viewHistoryItem(item.id));
                historyList.appendChild(li);
            });
        } catch (error) {
            console.error('Error loading history:', error);
            historyList.innerHTML = '<li class="placeholder">Could not load history.</li>';
        }
    };
    const viewHistoryItem = async (id) => {
        const currentUser = auth.currentUser;
        if (!currentUser) { alert("Please sign in to view history."); return; }
        closeSidebar();
        showGenerationView('');
        blogOutput.innerHTML = '<div class="loader" style="margin: 4rem auto; border-top-color: var(--accent-color);"></div>';
        try {
            const token = await currentUser.getIdToken();
            const response = await fetch(`${API_URL}/history/${id}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!response.ok) throw new Error('History item not found or permission denied.');
            const item = await response.json();
            showGenerationView(item.generated_output);
        } catch (error) {
            console.error('Error viewing history item:', error);
            alert('Could not retrieve this history item.');
            showWelcomeView();
        }
    };

    // --- Generation ---
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const hasUsedFreeTry = localStorage.getItem('hasUsedFreeTry');
        const topic = document.getElementById('topic').value;
        const tone = window.innerWidth <= 768 ? mobileToneSelect.value : desktopToneSelect.value;
        showGenerationView(''); setLoadingState(true);
        if (hasUsedFreeTry) {
            let currentUser = auth.currentUser;
            if (!currentUser) {
                try {
                    const provider = new firebase.auth.GoogleAuthProvider();
                    const result = await auth.signInWithPopup(provider);
                    currentUser = result.user;
                } catch (error) {
                    alert("You must sign in to generate more content.");
                    setLoadingState(false); showWelcomeView(); return;
                }
            }
            try {
                const token = await currentUser.getIdToken();
                const response = await fetch(`${API_URL}/generate-blog`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }, body: JSON.stringify({ topic, tone }) });
                if (!response.ok) { const err = await response.json(); throw new Error(err.detail); }
                const data = await response.json();
                showGenerationView(data.blog_content_markdown); await loadHistory();
            } catch(error) {
                alert(`Generation Failed: ${error.message}`); showWelcomeView();
            } finally { setLoadingState(false); }
        } else {
            try {
                const response = await fetch(`${API_URL}/generate-blog-free`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ topic, tone }) });
                if (!response.ok) { const err = await response.json(); throw new Error(err.detail); }
                const data = await response.json();
                showGenerationView(data.blog_content_markdown); await loadHistory();
            } catch (error) {
                alert(`Generation Failed: ${error.message}`); showWelcomeView();
            } finally {
                localStorage.setItem('hasUsedFreeTry', 'true'); setLoadingState(false);
            }
        }
    });

    // --- Init & Event Listeners ---
    newBlogBtn.addEventListener('click', () => { showWelcomeView(); closeSidebar(); });
    mobileToneSelect.addEventListener('change', () => desktopToneSelect.value = mobileToneSelect.value);
    desktopToneSelect.addEventListener('change', () => mobileToneSelect.value = mobileToneSelect.value);

    // --- NEW: ABOUT MODAL LOGIC ---
    const aboutBtn = document.getElementById('about-btn');
    const aboutModal = document.getElementById('about-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');

    const openModal = () => aboutModal.style.display = 'flex';
    const closeModal = () => aboutModal.style.display = 'none';

    aboutBtn.addEventListener('click', openModal);
    closeModalBtn.addEventListener('click', closeModal);
    // Also close modal if user clicks on the dark overlay
    aboutModal.addEventListener('click', (e) => {
        if (e.target === aboutModal) {
            closeModal();
        }
    });
    // Also close modal if user presses the Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === "Escape" && aboutModal.style.display === 'flex') {
            closeModal();
        }
    });

    showWelcomeView();
});