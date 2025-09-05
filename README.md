# UI/UX Testing Agent

## Installation

### Prerequisites

- Python 3.8+
- Node.js (for Playwright browser installation)
- Azure AI API key

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd uiux-testing-agent
   ```
2. Setup virtual env and activate
 ```bash
   python -m venv venv
   venv\Scripts\Activate
   ```

##Once virtual env is activated: 

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**:
   ```bash
   playwright install
   pip install fastapi uvicorn playwright python-dotenv openai
   ```

5. **Set up environment variables**:
   Create a `.env` file in the root directory, can extract all this from :
   ```env
   AZURE_OPENAI_API_KEY=your key
   AZURE_OPENAI_ENDPOINT= 
   AZURE_OPENAI_DEPLOYMENT_NAME
   AZURE_OPENAI_API_VERSION
   ```

5. **Create screenshots directory**:
   ```bash
   mkdir screenshots
   ```

## 🚀 Usage

### Starting the API Server

```bash
uvicorn api:api --port 8000
```

The API will be available at `http://127.0.0.1:8000/docs`

### API Endpoint

**POST** `/run`

**Request Body**:
```json
{
  "input": "On the home page with H1 heading 'Loop', verify that the list with role tablist below the 'Search' button now has children exposing appropriate accessibility roles.",
  "website": "***",
  "auth_config": {
    "type": "mslogin",
    "username": "***",
    "password": "***"
  }
}

```
