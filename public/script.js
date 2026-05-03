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
    const isLocalHost = ['localhost', '127.0.0.1'].includes(window.location.hostname);
    const API_URL = isLocalHost
        ? `${window.location.protocol}//${window.location.hostname}:8000`
        : 'https://blogzenai-api-474557573729.asia-south1.run.app';
    const converter = new showdown.Converter({
        simplifiedAutoLink: true,
        strikethrough: true,
        tables: true
    });

    const ALLOWED_TAGS = new Set([
        'a', 'blockquote', 'br', 'code', 'del', 'em', 'h1', 'h2', 'h3',
        'h4', 'h5', 'h6', 'hr', 'li', 'ol', 'p', 'pre', 'strong',
        'table', 'tbody', 'td', 'th', 'thead', 'tr', 'ul'
    ]);
    const ALLOWED_ATTRS = {
        a: new Set(['href', 'title', 'target', 'rel'])
    };
    const DROP_CONTENT_TAGS = new Set([
        'button', 'embed', 'form', 'iframe', 'input', 'link', 'math',
        'meta', 'object', 'script', 'select', 'style', 'svg', 'textarea'
    ]);
    const ALLOWED_PROTOCOLS = new Set(['http:', 'https:', 'mailto:']);

    // --- DOM Elements ---
    const body = document.body;
    const loginBtn = document.getElementById('login-btn');
    const creatorProfile = document.getElementById('creator-profile');
    const form = document.getElementById('blog-form');
    const topicInput = document.getElementById('topic');
    const newBlogBtn = document.getElementById('new-blog-btn');
    const welcomeView = document.getElementById('welcome-view');
    const generationView = document.getElementById('generation-view');
    const blogOutput = document.getElementById('blog-output');
    const historyList = document.getElementById('history-list');
    const generateBtn = document.getElementById('generate-btn');
    const sendIcon = document.querySelector('.send-icon');
    const loader = document.querySelector('.loader');
    const menuToggle = document.getElementById('menu-toggle');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const mobileToneSelect = document.getElementById('tone-mobile');
    const desktopToneSelect = document.getElementById('tone-desktop');
    const statusBanner = document.getElementById('status-banner');

    // --- UI State ---
    const openSidebar = () => body.classList.add('sidebar-open');
    const closeSidebar = () => body.classList.remove('sidebar-open');
    const showWelcomeView = () => {
        welcomeView.style.display = 'flex';
        generationView.style.display = 'none';
    };
    const showGenerationView = () => {
        welcomeView.style.display = 'none';
        generationView.style.display = 'block';
    };
    const clearStatus = () => {
        statusBanner.hidden = true;
        statusBanner.textContent = '';
        statusBanner.className = 'status-banner';
        statusBanner.removeAttribute('role');
    };
    const showStatus = (message, type = 'error') => {
        statusBanner.hidden = false;
        statusBanner.textContent = message;
        statusBanner.className = `status-banner ${type}`;
        statusBanner.setAttribute('role', type === 'error' ? 'alert' : 'status');
    };
    const setLoadingState = (isLoading) => {
        generateBtn.disabled = isLoading;
        topicInput.disabled = isLoading;
        mobileToneSelect.disabled = isLoading;
        desktopToneSelect.disabled = isLoading;
        sendIcon.style.display = isLoading ? 'none' : 'block';
        loader.style.display = isLoading ? 'block' : 'none';
    };
    const createContentLoader = () => {
        const loadingSpinner = document.createElement('div');
        loadingSpinner.className = 'loader content-loader';
        return loadingSpinner;
    };
    const renderLoadingState = () => {
        showGenerationView();
        blogOutput.replaceChildren(createContentLoader());
    };
    const renderHistoryPlaceholder = (message) => {
        const placeholder = document.createElement('li');
        placeholder.className = 'placeholder';
        placeholder.textContent = message;
        historyList.replaceChildren(placeholder);
    };

    const sanitizeHtml = (unsafeHtml) => {
        const template = document.createElement('template');
        template.innerHTML = unsafeHtml;

        const sanitizeNode = (node) => {
            const children = Array.from(node.childNodes);
            children.forEach((child) => {
                if (child.nodeType === Node.COMMENT_NODE) {
                    child.remove();
                    return;
                }

                if (child.nodeType !== Node.ELEMENT_NODE) {
                    return;
                }

                const tagName = child.tagName.toLowerCase();
                if (DROP_CONTENT_TAGS.has(tagName)) {
                    child.remove();
                    return;
                }

                if (!ALLOWED_TAGS.has(tagName)) {
                    const fragment = document.createDocumentFragment();
                    while (child.firstChild) {
                        fragment.appendChild(child.firstChild);
                    }
                    child.replaceWith(fragment);
                    sanitizeNode(node);
                    return;
                }

                Array.from(child.attributes).forEach((attribute) => {
                    const attrName = attribute.name.toLowerCase();
                    const allowedAttrs = ALLOWED_ATTRS[tagName];
                    const isAllowedAttr = allowedAttrs && allowedAttrs.has(attrName);

                    if (attrName.startsWith('on') || !isAllowedAttr) {
                        child.removeAttribute(attribute.name);
                        return;
                    }

                    if (tagName === 'a' && attrName === 'href') {
                        try {
                            const url = new URL(attribute.value, window.location.origin);
                            if (!ALLOWED_PROTOCOLS.has(url.protocol)) {
                                child.removeAttribute('href');
                            }
                        } catch (error) {
                            child.removeAttribute('href');
                        }
                    }
                });

                if (tagName === 'a' && child.getAttribute('href')) {
                    child.setAttribute('target', '_blank');
                    child.setAttribute('rel', 'noopener noreferrer');
                }

                sanitizeNode(child);
            });
        };

        sanitizeNode(template.content);
        return template.innerHTML;
    };

    const renderMarkdown = (markdownContent) => {
        showGenerationView();
        const html = converter.makeHtml(markdownContent || '');
        blogOutput.innerHTML = sanitizeHtml(html);
    };

    const parseApiError = async (response) => {
        let payload = {};

        try {
            payload = await response.json();
        } catch (error) {
            payload = {};
        }

        const detail = payload.detail;
        let message = response.status >= 500
            ? 'Something went wrong on the server. Please try again.'
            : 'Request failed.';

        if (Array.isArray(detail) && detail.length > 0) {
            message = detail[0].msg || message;
        } else if (typeof detail === 'string' && detail.trim()) {
            message = detail;
        }

        return {
            code: payload.code || `HTTP_${response.status}`,
            message,
            status: response.status
        };
    };

    const getAuthErrorMessage = (error, fallbackMessage) => {
        if (!error || !error.code) {
            return fallbackMessage;
        }

        if (error.code === 'auth/popup-closed-by-user') {
            return 'Sign-in was canceled.';
        }

        if (error.code === 'auth/popup-blocked') {
            return 'The sign-in popup was blocked. Please allow popups and try again.';
        }

        return fallbackMessage;
    };

    const getErrorMessage = (error, fallbackMessage) => {
        if (!error) {
            return fallbackMessage;
        }

        if (error.code && String(error.code).startsWith('auth/')) {
            return getAuthErrorMessage(error, fallbackMessage);
        }

        if (typeof error.message === 'string' && error.message.trim()) {
            return error.message;
        }

        return fallbackMessage;
    };

    const apiRequest = async (path, options = {}) => {
        const response = await fetch(`${API_URL}${path}`, {
            credentials: 'include',
            ...options,
            headers: {
                ...(options.headers || {})
            }
        });

        if (!response.ok) {
            throw await parseApiError(response);
        }

        return response.json();
    };

    const signInWithGoogle = async () => {
        const provider = new firebase.auth.GoogleAuthProvider();
        const result = await auth.signInWithPopup(provider);
        return result.user;
    };

    const loadHistory = async () => {
        const currentUser = auth.currentUser;
        if (!currentUser) {
            renderHistoryPlaceholder('Sign in to see history.');
            return;
        }

        try {
            const token = await currentUser.getIdToken();
            const history = await apiRequest('/history', {
                headers: {
                    Authorization: `Bearer ${token}`
                }
            });

            if (!Array.isArray(history) || history.length === 0) {
                renderHistoryPlaceholder('No history yet.');
                return;
            }

            historyList.replaceChildren();
            history.forEach((item) => {
                const listItem = document.createElement('li');
                listItem.textContent = item.topic;
                listItem.dataset.id = item.id;
                listItem.addEventListener('click', () => viewHistoryItem(item.id));
                historyList.appendChild(listItem);
            });
        } catch (error) {
            console.error('Error loading history:', error);
            renderHistoryPlaceholder('Could not load history.');
            showStatus(getErrorMessage(error, 'Could not load your history right now.'), 'error');
        }
    };

    const viewHistoryItem = async (id) => {
        const currentUser = auth.currentUser;
        if (!currentUser) {
            showStatus('Please sign in to view your history.', 'error');
            return;
        }

        clearStatus();
        closeSidebar();
        renderLoadingState();

        try {
            const token = await currentUser.getIdToken();
            const item = await apiRequest(`/history/${id}`, {
                headers: {
                    Authorization: `Bearer ${token}`
                }
            });
            renderMarkdown(item.generated_output);
        } catch (error) {
            console.error('Error viewing history item:', error);
            showStatus(getErrorMessage(error, 'Could not retrieve this history item.'), 'error');
            showWelcomeView();
        }
    };

    const generateAuthenticatedBlog = async (topic, tone, currentUser = auth.currentUser) => {
        let user = currentUser;
        if (!user) {
            user = await signInWithGoogle();
        }

        const token = await user.getIdToken();
        return apiRequest('/generate-blog', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({ topic, tone })
        });
    };

    const generateAnonymousBlog = (topic, tone) => apiRequest('/generate-blog-free', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ topic, tone })
    });

    // --- Authentication & History ---
    auth.onAuthStateChanged(async (user) => {
        if (user) {
            loginBtn.style.display = 'none';
            creatorProfile.style.display = 'flex';
            await loadHistory();
        } else {
            loginBtn.style.display = 'block';
            creatorProfile.style.display = 'none';
            renderHistoryPlaceholder('Sign in to see history.');
        }
    });

    loginBtn.addEventListener('click', async () => {
        clearStatus();
        try {
            await signInWithGoogle();
        } catch (error) {
            console.error('Sign-in error:', error);
            showStatus(getAuthErrorMessage(error, 'Sign-in failed. Please try again.'), 'error');
        }
    });

    // --- Generation ---
    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        clearStatus();
        const topic = topicInput.value.trim();
        const tone = window.innerWidth <= 768 ? mobileToneSelect.value : desktopToneSelect.value;

        renderLoadingState();
        setLoadingState(true);

        try {
            let data;

            if (auth.currentUser) {
                data = await generateAuthenticatedBlog(topic, tone, auth.currentUser);
            } else {
                try {
                    data = await generateAnonymousBlog(topic, tone);
                } catch (error) {
                    if (error.code === 'FREE_TRY_USED') {
                        showStatus('Your anonymous free generation has been used. Sign in to continue.', 'info');
                        const user = await signInWithGoogle();
                        clearStatus();
                        data = await generateAuthenticatedBlog(topic, tone, user);
                    } else {
                        throw error;
                    }
                }
            }

            renderMarkdown(data.blog_content_markdown);
            if (auth.currentUser) {
                await loadHistory();
            }
        } catch (error) {
            console.error('Generation failed:', error);
            showStatus(getErrorMessage(error, 'Generation failed. Please try again.'), 'error');
            showWelcomeView();
        } finally {
            setLoadingState(false);
        }
    });

    // --- Init & Event Listeners ---
    menuToggle.addEventListener('click', openSidebar);
    sidebarOverlay.addEventListener('click', closeSidebar);
    newBlogBtn.addEventListener('click', () => {
        clearStatus();
        showWelcomeView();
        closeSidebar();
    });
    mobileToneSelect.addEventListener('change', () => {
        desktopToneSelect.value = mobileToneSelect.value;
    });
    desktopToneSelect.addEventListener('change', () => {
        mobileToneSelect.value = desktopToneSelect.value;
    });

    // --- About Modal Logic ---
    const aboutBtn = document.getElementById('about-btn');
    const aboutModal = document.getElementById('about-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');

    const openModal = () => {
        aboutModal.style.display = 'flex';
    };
    const closeModal = () => {
        aboutModal.style.display = 'none';
    };

    aboutBtn.addEventListener('click', openModal);
    closeModalBtn.addEventListener('click', closeModal);
    aboutModal.addEventListener('click', (event) => {
        if (event.target === aboutModal) {
            closeModal();
        }
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && aboutModal.style.display === 'flex') {
            closeModal();
        }
    });

    showWelcomeView();
});
