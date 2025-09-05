# UI/UX Testing Agent

### Agent Workflow

1. **User Interaction Agent (UIA)** - Extracts structured requirements from natural language input
2. **Test Scenario Planning Agent (TSPA)** - Creates detailed test scenarios based on requirements
3. **Branding UX Validation Agent (BUVA)** - Enriches scenarios with branding and UX validation checks
4. **Playwright Execution Agent (PMEA)** - Executes tests using browser automation
5. **Result Analysis Agent (RAA)** - Analyzes test results and generates summaries
6. **Reporting Communication Agent (RCA)** - Creates comprehensive human-readable reports

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

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers**:
   ```bash
   playwright install
   ```

4. **Set up environment variables**:
   Create a `.env` file in the root directory:
   ```env
   AZURE_OPENAI_API_KEY=your key
   AZURE_OPENAI_ENDPOINT
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
uvicorn api:api --reload --port 8000
```

The API will be available at `http://localhost:8000`

### API Endpoint

**POST** `/run`

**Request Body**:
```json
{
  "input": "Test the homepage navigation menu and check if the logo is properly displayed",
  "website": "https://example.com"
}
```
