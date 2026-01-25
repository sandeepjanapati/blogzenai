# 🤖 BLOGZENAI

**BLOGZENAI** is an AI-powered multi-agent system designed for automated content research, SEO optimization, and high-quality writing. Built with Python and containerized with Docker, it leverages a specialized agent architecture to streamline the blog creation workflow.

---

## 🏗 Project Structure

- **`/agents`**: The core "brains" of the system.
  - `research_agent.py`: Scrapes and gathers data.
  - `seo_agent.py`: Optimizes content for search engines.
  - `writing_agent.py`: Handles creative copy and drafting.
  - `understanding_agent.py`: Processes context and user intent.
- **`/utils`**: Shared services like `database.py` and `api_clients.py`.
- **`/public`**: Static frontend assets (HTML/JS/CSS).
- **`api.py` & `main.py`**: Entry points for the backend service.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9+
- Docker (for containerized deployment)
- Google Cloud Project (`bolgzenai`)

### 2. Local Setup
Clone the repository and set up your environment:

bash
git clone https://github.com/sandeepjanapati/blogzenai.git
cd blogzenai
python -m venv venv
source venv/Scripts/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt


### 3. Environment Variables
Create a `.env` file in the root directory and add your credentials:
text
OPENAI_API_KEY=your_api_key
FIREBASE_CONFIG=your_config
DATABASE_URL=your_db_url


### 4. Running the App
bash
python main.py


---

## ☁️ Deployment

This project is configured for **Google Cloud Build**. To trigger a manual build:

bash
gcloud builds submit --config cloudbuild.yaml .


The image will be pushed to: `gcr.io/bolgzenai/blogzenai-api:latest`

---

## 🛠 Tech Stack
- **Language:** Python
- **Infrastructure:** Docker, Google Cloud Platform (GCP)
- **Frontend:** Vanilla JS, CSS, HTML
- **CI/CD:** Google Cloud Build