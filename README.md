# UI/UX Testing Agent

An intelligent, AI-powered testing automation framework that combines natural language processing with browser automation to perform comprehensive UI/UX and branding validation on websites.

## 🚀 Overview

The UI/UX Testing Agent is a sophisticated testing system that uses a multi-agent architecture to automatically generate, execute, and analyze UI/UX tests based on natural language requirements. It leverages OpenAI's GPT-4 for intelligent test scenario generation and Playwright for browser automation.

## 🏗️ Architecture

The system uses **LangGraph** to orchestrate a workflow of specialized AI agents:

```
User Input → UIA → TSPA → BUVA → PMEA → RAA → RCA → Final Report
```

### Agent Workflow

1. **User Interaction Agent (UIA)** - Extracts structured requirements from natural language input
2. **Test Scenario Planning Agent (TSPA)** - Creates detailed test scenarios based on requirements
3. **Branding UX Validation Agent (BUVA)** - Enriches scenarios with branding and UX validation checks
4. **Playwright Execution Agent (PMEA)** - Executes tests using browser automation
5. **Result Analysis Agent (RAA)** - Analyzes test results and generates summaries
6. **Reporting Communication Agent (RCA)** - Creates comprehensive human-readable reports

## 🔧 Features

- **Natural Language Test Generation**: Describe your testing needs in plain English
- **Automated Browser Testing**: Powered by Playwright for reliable web automation
- **Interactive Authentication**: Browser window pops up for manual login (handles 2FA, CAPTCHA, etc.)
- **Branding Validation**: Checks visual identity elements like logos, colors, and fonts
- **UX Assessment**: Evaluates layout, spacing, responsiveness, and accessibility
- **Screenshot Capture**: Automatic visual evidence collection during testing
- **Comprehensive Reporting**: Detailed pass/fail reports with actionable insights
- **RESTful API**: Easy integration with existing workflows

## 📦 Installation

### Prerequisites

- Python 3.8+
- Node.js (for Playwright browser installation)
- OpenAI API key

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
   OPENAI_API_KEY=your_openai_api_key_here
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

**With Interactive Authentication (for internal websites)**:
```json
{
  "input": "Test the dashboard navigation and verify branding consistency",
  "website": "https://internal-portal.company.com/dashboard",
  "auth_config": {
    "type": "interactive",
    "timeout": 180
  }
}
```

**Response**:
```json
{
  "final_report": "UI/UX and Branding Test Report\nWebsite: https://example.com\n...",
  "analysed_results": {
    "summary": {
      "total_scenarios": 3,
      "passed": 2,
      "failed": 1,
      "overall_result": "Fail"
    },
    "details": [...]
  }
}
```

### Example Usage

```python
import requests

response = requests.post('http://localhost:8000/run', json={
    "input": "Test the checkout process and verify the payment button styling matches brand guidelines",
    "website": "https://mystore.com"
})

print(response.json()['final_report'])
```

## 🔐 Interactive Authentication

For internal websites that require authentication, use the simplified interactive authentication approach:

### How it works:
1. 🌐 **Browser Opens**: Main browser window opens and navigates to your website
2. 🔄 **SSO Redirects**: Automatically follows all SSO redirects (e.g., Okta, Azure AD, etc.)
3. 👤 **User Logs In**: Complete authentication manually (2FA, CAPTCHA, SSO, etc.)
4. ✅ **Click Complete**: Click the green "Authentication Mode" indicator when done
5. 🤖 **Testing Begins**: System continues with testing using the authenticated session

### Benefits:
- ✅ **Session Preservation**: Authentication happens in main browser context
- ✅ **SSO Compatible**: Handles complex SSO redirects seamlessly
- ✅ **No Cookie Transfer**: No need to transfer cookies between contexts
- ✅ **Universal Compatibility**: Works with any authentication system
- ✅ **Secure**: No credentials stored or transmitted

### Example Usage:
```python
import requests

# Test an internal website with interactive auth
response = requests.post('http://localhost:8000/run', json={
    "input": "Test the admin panel navigation and branding compliance",
    "website": "https://admin.company.com",
    "auth_config": {
        "type": "interactive",
        "timeout": 300  # 5 minutes (optional)
    }
})

print(response.json()['final_report'])
```



## 🤖 Agent Details

### User Interaction Agent
- **Purpose**: Parses natural language requirements into structured data
- **Input**: User's testing requirements in plain text
- **Output**: Structured JSON with components, branding guidelines, and UX considerations

### Test Scenario Planning Agent  
- **Purpose**: Creates detailed test scenarios from structured requirements
- **Input**: Structured requirements from UIA
- **Output**: Array of test scenarios with steps and expected results

### Branding UX Validation Agent
- **Purpose**: Enriches test scenarios with specific validation checks
- **Input**: Basic test scenarios
- **Output**: Enhanced scenarios with branding and UX validation criteria

### Playwright Execution Agent
- **Purpose**: Executes tests using browser automation
- **Input**: Enriched test scenarios and target website
- **Output**: Test execution results with screenshots
- **Features**: 
  - Headless browser testing
  - Screenshot capture
  - Error handling and reporting

### Result Analysis Agent
- **Purpose**: Analyzes test execution results
- **Input**: Raw test execution results
- **Output**: Structured analysis with pass/fail summary

### Reporting Communication Agent
- **Purpose**: Generates human-readable test reports
- **Input**: Analyzed results
- **Output**: Formatted report with timestamps and detailed findings

## 📊 Example Test Scenarios

The system can generate tests for:

- **Navigation Testing**: Menu functionality, breadcrumbs, search
- **Visual Validation**: Logo placement, color schemes, typography
- **Form Testing**: Input validation, submission flows, error handling
- **Responsive Design**: Mobile compatibility, layout adaptations
- **Accessibility**: Contrast ratios, keyboard navigation, screen reader compatibility
- **Performance**: Load times, rendering issues
- **Brand Consistency**: Visual identity elements, messaging tone

## 🔍 Sample Report Output

```
UI/UX and Branding Test Report
Website: https://example.com
Generated on: 2024-01-15 14:30:25

Overall Result: Pass
Total Scenarios: 3
✅ Passed: 3
❌ Failed: 0

Detailed Results:
--------------------------------

Scenario ID: SC001
Description: Verify homepage logo placement and size
Result: ✅ Pass
Screenshot: screenshots/SC001.png

Scenario ID: SC002
Description: Check navigation menu visibility and functionality
Result: ✅ Pass
Screenshot: screenshots/SC002.png
```

## 🛠️ Development

### Project Structure
```
uiux-testing-agent/
├── agents/                          # AI agent implementations
│   ├── user_interaction_agent.py
│   ├── test_scenario_planning_agent.py
│   ├── branding_ux_validation_agent.py
│   ├── playwright_execution_agent.py
│   ├── result_analysis_agent.py
│   └── reporting_communication_agent.py
├── screenshots/                     # Generated test screenshots
├── api.py                          # FastAPI server
├── main.py                         # LangGraph workflow definition
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

### Key Technologies
- **LangGraph**: Agent orchestration and workflow management
- **OpenAI GPT-4**: Natural language processing and intelligent analysis
- **Playwright**: Browser automation and testing
- **FastAPI**: REST API framework
- **Pydantic**: Data validation and serialization

### Adding New Agents

1. Create a new agent file in the `agents/` directory
2. Implement the agent function following the existing pattern
3. Add the agent to the workflow in `main.py`
4. Update the `AgentState` TypedDict if needed

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 access | Yes |

## 📝 Configuration

The system uses several configurable parameters:

- **OpenAI Model**: Currently set to `gpt-4` (can be changed in agent files)
- **Browser**: Chromium (configurable in playwright_execution_agent.py)
- **Screenshots**: Saved to `screenshots/` directory
- **Temperature**: AI creativity level (0.2-0.3 for consistent results)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🐛 Troubleshooting

### Common Issues

1. **OpenAI API Key Error**: Ensure your API key is set in the `.env` file
2. **Playwright Installation**: Run `playwright install` if browsers are missing
3. **Screenshots Directory**: Create the `screenshots/` directory manually if it doesn't exist
4. **Port Conflicts**: Change the port in the uvicorn command if 8000 is in use

### Debug Mode

To run with debug output:
```bash
uvicorn api:api --reload --port 8000 --log-level debug
```

## 🚧 Roadmap

- [ ] Support for additional browsers (Firefox, Safari)
- [ ] Integration with CI/CD pipelines
- [ ] Advanced accessibility testing
- [ ] Performance metrics collection
- [ ] Visual regression testing
- [ ] Multi-language support
- [ ] Custom reporting formats (PDF, HTML)

---

**Built with ❤️ for automated UI/UX testing** 