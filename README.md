# Antigravity Elite Finance - Beyond Simplistic

Elite Finance is a professional-grade home accounting application designed with a high-readability "Vintage Technicolor" aesthetic. It features dynamic category management, budgeting systems, and AI-driven financial insights powered by Gemini v2.5.

## 🚀 Key Features
- **Elite Dashboard**: Live budget tracking with color-coded progress bars.
- **Dynamic Settings**: Manage categories, subcategories, and budgets via a persistent JSON configuration.
- **Full History & Search**: Instant full-text search across all your Excel-stored movements.
- **AI Insights**: Gemini-powered financial advice based on your spending patterns.
- **High Readability**: Custom UI using Lexend typography for data clarity.

## 🛠️ Tech Stack
- **Backend**: Python (Flask)
- **Frontend**: HTML5, Vanilla CSS, Vanilla JavaScript, Chart.js
- **Intelligence**: Google Gemini v2.5
- **Storage**: Microsoft Excel (.xlsx) for movements, `taxonomy.json` for config.

## 📦 Setup
1. Clone the repository.
2. Create a `.venv` and install dependencies:
   ```bash
   pip install flask flask-cors python-dotenv google-generativeai openpyxl
   ```
3. Create a `.env` file with your credentials:
   ```env
   GEMINI_API_KEY=your_key_here
   EXCEL_PATH=path/to/your/finance.xlsx
   ```
4. Launch the server:
   ```bash
   python app.py
   ```
5. Open `index.html` in your browser.

---
*Created with ❤️ by Antigravity*
