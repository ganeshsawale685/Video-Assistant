# AI Video & Meeting Assistant

An AI-powered application that transcribes, summarizes, and enables intelligent conversations with YouTube videos and meeting recordings using **Generative AI and RAG**.

### Live Demo
[Try the App](https://aivideoassistant2005.streamlit.app/)

### Features
- YouTube video and audio transcription using Whisper
- AI-powered video and meeting summarization
- Chat with video content using RAG
- Semantic search with ChromaDB
- Multilingual translation support
- Interactive Streamlit interface

### Tech Stack
**Python | LangChain | Groq LLM | Whisper | ChromaDB | Hugging Face | Streamlit | FFmpeg**

### RAG Workflow
Video/Audio → Whisper → Text Chunks → Embeddings → ChromaDB → Retriever → Groq LLM → Answer

### Run Locally
```bash
git clone https://github.com/ganeshsawale685/Video-Assistant.git
cd Video-Assistant
uv venv --python 3.12
uv pip install -r requirements.txt
uv run streamlit run app.py
```

Add `GROQ_API_KEY` to your `.env` file and ensure FFmpeg is installed.

### Developer
**Ganesh Sawale**

[GitHub](https://github.com/ganeshsawale685) | [LinkedIn](https://www.linkedin.com/in/ganesh-sawale/)
