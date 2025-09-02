import json
import asyncio
import base64
from playwright.async_api import async_playwright
from openai import AzureOpenAI

from dotenv import load_dotenv
import os
import sys
import re
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logging_config import (
    log_agent_start, log_agent_thinking, log_llm_prompt, 
    log_llm_response, log_agent_complete, log_agent_error,
    log_playwright_action, log_page_analysis
)

load_dotenv()
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

def extract_json_from_response(raw_response):
    """Extract JSON from LLM response that might be wrapped in markdown or contain extra text"""
    
    # First, try to parse as direct JSON
    try:
        return json.loads(raw_response.strip())
    except json.JSONDecodeError:
        pass
    
    # Look for JSON wrapped in markdown code blocks
    json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    match = re.search(json_pattern, raw_response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Look for JSON that starts with { and ends with }
    json_pattern = r'\{.*\}'
    match = re.search(json_pattern, raw_response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    
    # If all else fails, return an error structure
    return {
        "overall_result": "Fail",
        "branding_results": [],
        "ux_results": [],
        "error": f"Failed to parse JSON from response: {raw_response[:200]}..."
    }

async def handle_interactive_authentication(page, website_url, timeout_seconds=300):
    """Handle authentication interactively in the main browser context"""
    
    log_playwright_action(f"🔓 Starting INTERACTIVE authentication for {website_url}")
    log_playwright_action("🔐 Using main browser window for authentication to preserve session")
    
    try:
        # Navigate to the authentication website in the main context
        log_playwright_action(f"🌐 Navigating to authentication page: {website_url}")
        await page.goto(website_url)
        await page.wait_for_load_state('domcontentloaded')
        
        # Function to inject the authentication indicator
        async def inject_auth_indicator():
            try:
                await page.evaluate("""
                    () => {
                        // Remove existing indicator if present
                        const existing = document.getElementById('auth-indicator');
                        if (existing) {
                            existing.remove();
                        }
                        
                        // Add authentication indicator
                        const indicator = document.createElement('div');
                        indicator.id = 'auth-indicator';
                        indicator.style.cssText = `
                            position: fixed;
                            top: 10px;
                            right: 10px;
                            background: #4CAF50;
                            color: white;
                            padding: 12px 16px;
                            border-radius: 6px;
                            font-family: Arial, sans-serif;
                            font-size: 14px;
                            font-weight: bold;
                            z-index: 999999;
                            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                            cursor: pointer;
                        `;
                        indicator.innerHTML = `
                            🔐 Authentication Mode<br>
                            <small style="font-size: 11px; opacity: 0.9;">Click when authentication complete</small>
                        `;
                        document.body.appendChild(indicator);
                        
                        // Add click handler to signal completion
                        indicator.addEventListener('click', () => {
                            indicator.remove();
                            // Signal completion by changing page title
                            document.title = 'AUTH_COMPLETE_' + document.title;
                        });
                    }
                """)
            except Exception as e:
                log_playwright_action(f"⚠️ Failed to inject auth indicator: {str(e)}")
        
        # Inject initial indicator
        await inject_auth_indicator()
        
        # Set up navigation listener to re-inject indicator after redirects
        last_url = page.url
        
        async def check_for_navigation():
            nonlocal last_url
            current_url = page.url
            if current_url != last_url:
                log_playwright_action(f"🔄 Navigation detected: {last_url} → {current_url}")
                last_url = current_url
                # Wait for page to load then re-inject indicator
                try:
                    await page.wait_for_load_state('domcontentloaded', timeout=5000)
                    await inject_auth_indicator()
                    log_playwright_action("✅ Re-injected authentication indicator after navigation")
                except Exception as e:
                    log_playwright_action(f"⚠️ Failed to re-inject indicator: {str(e)}")
        
        log_playwright_action("⏳ Waiting for user to complete authentication...")
        log_playwright_action("📝 Instructions: Complete your login (including SSO redirects), then click the green authentication indicator")
        
        # Wait for user to complete authentication
        start_time = asyncio.get_event_loop().time()
        
        while True:
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - start_time
            remaining = timeout_seconds - elapsed
            
            if elapsed > timeout_seconds:
                log_agent_error("PMEA", f"Authentication timeout after {timeout_seconds} seconds")
                return False
            
            # Log progress every 30 seconds
            if int(elapsed) % 30 == 0 and elapsed > 0:
                log_playwright_action(f"⏳ Still waiting for authentication... {remaining:.0f}s remaining")
            
            # Check for navigation and re-inject indicator if needed
            await check_for_navigation()
            
            # Check if user clicked the authentication complete indicator
            try:
                title = await page.title()
                if title.startswith('AUTH_COMPLETE_'):
                    log_playwright_action("✅ User completed authentication successfully!")
                    
                    # Clean up the title
                    await page.evaluate("""
                        () => {
                            if (document.title.startsWith('AUTH_COMPLETE_')) {
                                document.title = document.title.replace('AUTH_COMPLETE_', '');
                            }
                        }
                    """)
                    break
            except Exception as e:
                log_playwright_action(f"⚠️ Error checking authentication status: {str(e)}")
                # Continue waiting despite error
            
            # Wait before checking again
            await asyncio.sleep(3)
        
        # Wait for page to settle after authentication
        log_playwright_action("⏱️  Waiting for page to settle after authentication")
        await page.wait_for_load_state('networkidle', timeout=10000)
        
        # Log current state
        current_url = page.url
        log_playwright_action(f"📍 Authentication completed. Current URL: {current_url}")
        
        # Check if we need to navigate back to the original target
        if website_url not in current_url:
            log_playwright_action(f"🎯 Navigating back to target website: {website_url}")
            try:
                await page.goto(website_url)
                await page.wait_for_load_state('networkidle', timeout=15000)
                log_playwright_action("✅ Successfully navigated to target website with authenticated session")
            except Exception as e:
                log_playwright_action(f"⚠️  Failed to navigate back to target: {str(e)}")
                log_playwright_action("🔄 Continuing with current page for testing")
        else:
            log_playwright_action("✅ Already on target website - ready for testing")
        
        return True
        
    except Exception as e:
        log_agent_error("PMEA", f"Interactive authentication failed: {str(e)}")
        return False

async def setup_interactive_authentication(page, auth_config):
    """Setup interactive authentication using main browser context"""
    website_url = auth_config.get("website_url", "")
    timeout = auth_config.get("timeout", 300)  # Default timeout to 5 minutes
    return await handle_interactive_authentication(page, website_url, timeout)

async def setup_standard_authentication(page, auth_config):
    """Setup standard authentication methods on the given page"""
    
    if not auth_config:
        log_playwright_action("No authentication required")
        return True
    
    auth_type = auth_config.get("type", "").lower()
    
    # Keep existing authentication methods for backward compatibility
    log_playwright_action(f"Setting up {auth_type} authentication")
    
    try:
        if auth_type == "basic":
            # Basic HTTP authentication
            username = auth_config.get("username")
            password = auth_config.get("password")
            if username and password:
                # Set basic auth header
                await page.set_extra_http_headers({
                    "Authorization": f"Basic {base64.b64encode(f'{username}:{password}'.encode()).decode()}"
                })
                log_playwright_action(f"Basic auth configured for user: {username}")
                return True
        
        elif auth_type == "cookie":
            # Cookie-based authentication
            cookies = auth_config.get("cookies", [])
            if cookies:
                await page.context.add_cookies(cookies)
                log_playwright_action(f"Added {len(cookies)} authentication cookies")
                return True
        
        elif auth_type == "token":
            # Token-based authentication (Bearer token)
            token = auth_config.get("token")
            if token:
                await page.set_extra_http_headers({
                    "Authorization": f"Bearer {token}"
                })
                log_playwright_action("Bearer token authentication configured")
                return True
        
        elif auth_type == "form":
            # Form-based login
            login_url = auth_config.get("login_url")
            username = auth_config.get("username")
            password = auth_config.get("password")
            username_selector = auth_config.get("username_selector", "input[name='username'], input[name='email'], #username, #email")
            password_selector = auth_config.get("password_selector", "input[name='password'], #password")
            submit_selector = auth_config.get("submit_selector", "button[type='submit'], input[type='submit'], button:has-text('login'), button:has-text('sign in')")
            
            if login_url and username and password:
                log_playwright_action(f"Navigating to login page: {login_url}")
                await page.goto(login_url)
                await page.wait_for_load_state('networkidle')
                
                log_playwright_action("Filling login form")
                await page.fill(username_selector, username)
                await page.fill(password_selector, password)
                
                log_playwright_action("Submitting login form")
                await page.click(submit_selector)
                await page.wait_for_load_state('networkidle')
                
                # Check if login was successful (you might need to customize this)
                current_url = page.url
                if current_url != login_url and "login" not in current_url.lower():
                    log_playwright_action("Form authentication successful")
                    return True
                else:
                    log_agent_error("PMEA", "Form authentication may have failed - still on login page")
                    return False
        
        elif auth_type == "header":
            # Custom header authentication
            headers = auth_config.get("headers", {})
            if headers:
                await page.set_extra_http_headers(headers)
                log_playwright_action(f"Custom headers configured: {list(headers.keys())}")
                return True
        
        log_agent_error("PMEA", f"Unsupported authentication type: {auth_type}")
        return False
        
    except Exception as e:
        log_agent_error("PMEA", f"Authentication setup failed: {str(e)}")
        return False

async def analyze_page_with_llm(page_content, scenario, website_url):
    """Use LLM to analyze page content against specific branding and UX checks"""
    
    log_agent_thinking("PMEA", f"Starting LLM analysis for scenario: {scenario.get('scenario_id', 'Unknown')}")
    
    # Extract relevant page information
    page_info = {
        "url": website_url,
        "title": page_content.get("title", ""),
        "visible_text": page_content.get("text", "")[:3000],  # Limit text to avoid token limits
        "page_structure": page_content.get("structure", ""),
        "elements": page_content.get("elements", [])
    }
    
    log_page_analysis("Content", f"Page title: {page_info['title']}")
    log_page_analysis("Content", f"Visible text length: {len(page_info['visible_text'])} chars")
    log_page_analysis("Content", f"Key elements found: {len(page_info['elements'])}")
    
    branding_checks = scenario.get("branding_checks", [])
    ux_checks = scenario.get("ux_checks", [])
    
    log_agent_thinking("PMEA", f"Analyzing {len(branding_checks)} branding checks and {len(ux_checks)} UX checks")
    
    prompt = f"""
    You are an expert UI/UX tester analyzing a web page. Based on the page content provided, evaluate each of the specific checks listed below.

    Page Information:
    - URL: {page_info['url']}
    - Title: {page_info['title']}
    - Visible Text: {page_info['visible_text']}
    - Page Structure: {page_info['page_structure']}
    - Key Elements: {page_info['elements']}

    Scenario: {scenario.get('description', '')}

    Branding Checks to Evaluate:
    {json.dumps(branding_checks, indent=2)}

    UX Checks to Evaluate:
    {json.dumps(ux_checks, indent=2)}

    For each check, provide a detailed analysis and determine if it passes or fails.
    
    IMPORTANT: Respond with ONLY a valid JSON object, no markdown formatting or extra text:
    
    {{
        "overall_result": "Pass" or "Fail",
        "branding_results": [
            {{
                "check": "check description",
                "result": "Pass" or "Fail",
                "details": "detailed explanation of what was found and why it passed/failed"
            }}
        ],
        "ux_results": [
            {{
                "check": "check description", 
                "result": "Pass" or "Fail",
                "details": "detailed explanation of what was found and why it passed/failed"
            }}
        ]
    }}
    """
    
    log_llm_prompt("PMEA", prompt)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert UI/UX tester with deep knowledge of web design principles, branding guidelines, and user experience best practices. Always respond with valid JSON only, no markdown formatting."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        raw_output = response.choices[0].message.content
        if raw_output is None:
            raise ValueError("OpenAI API returned None content")
        
        log_llm_response("PMEA", raw_output)
        log_agent_thinking("PMEA", "Parsing LLM response with enhanced JSON extraction")
        
        # Use enhanced JSON extraction
        analysis = extract_json_from_response(raw_output)
        
        # Log analysis results
        overall_result = analysis.get("overall_result", "Unknown")
        branding_results = analysis.get("branding_results", [])
        ux_results = analysis.get("ux_results", [])
        
        log_agent_thinking("PMEA", f"LLM analysis complete - Overall: {overall_result}")
        log_agent_thinking("PMEA", f"Branding results: {len(branding_results)} checks processed")
        log_agent_thinking("PMEA", f"UX results: {len(ux_results)} checks processed")
        
        for result in branding_results:
            status = result.get("result", "Unknown")
            check = result.get("check", "Unknown check")
            log_agent_thinking("PMEA", f"Branding check '{check}': {status}")
        
        for result in ux_results:
            status = result.get("result", "Unknown")
            check = result.get("check", "Unknown check")
            log_agent_thinking("PMEA", f"UX check '{check}': {status}")
        
        return analysis
        
    except Exception as e:
        error_msg = f"Error in LLM analysis: {str(e)}"
        log_agent_error("PMEA", error_msg)
        return {
            "overall_result": "Fail",
            "branding_results": [],
            "ux_results": [],
            "error": str(e)
        }

async def extract_page_content(page):
    """Extract comprehensive page content for LLM analysis"""
    log_playwright_action("Starting page content extraction")
    
    try:
        # Get page title
        log_playwright_action("Extracting page title")
        title = await page.title()
        log_page_analysis("Title", f"'{title}'")
        
        # Get visible text content
        log_playwright_action("Extracting visible text content")
        visible_text = await page.evaluate("""
            () => {
                // Remove script and style elements
                const scripts = document.querySelectorAll('script, style');
                scripts.forEach(el => el.remove());
                
                // Get visible text
                return document.body.innerText || document.body.textContent;
            }
        """)
        log_page_analysis("Text", f"Extracted {len(visible_text)} characters of visible text")
        
        # Get page structure information
        log_playwright_action("Analyzing page structure")
        structure = await page.evaluate("""
            () => {
                const structure = {
                    headings: [],
                    links: [],
                    images: [],
                    forms: [],
                    buttons: []
                };
                
                // Extract headings
                document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(h => {
                    structure.headings.push({
                        tag: h.tagName.toLowerCase(),
                        text: h.innerText.trim()
                    });
                });
                
                // Extract links
                document.querySelectorAll('a[href]').forEach(a => {
                    structure.links.push({
                        text: a.innerText.trim(),
                        href: a.href
                    });
                });
                
                // Extract images
                document.querySelectorAll('img').forEach(img => {
                    structure.images.push({
                        alt: img.alt,
                        src: img.src,
                        width: img.width,
                        height: img.height
                    });
                });
                
                // Extract forms
                document.querySelectorAll('form').forEach(form => {
                    const inputs = [];
                    form.querySelectorAll('input, textarea, select').forEach(input => {
                        inputs.push({
                            type: input.type,
                            name: input.name,
                            placeholder: input.placeholder
                        });
                    });
                    structure.forms.push({inputs});
                });
                
                // Extract buttons
                document.querySelectorAll('button, input[type="button"], input[type="submit"]').forEach(btn => {
                    structure.buttons.push({
                        text: btn.innerText || btn.value,
                        type: btn.type
                    });
                });
                
                return structure;
            }
        """)
        
        log_page_analysis("Structure", f"Found {len(structure['headings'])} headings, {len(structure['links'])} links, {len(structure['images'])} images, {len(structure['forms'])} forms, {len(structure['buttons'])} buttons")
        
        # Get key elements for branding analysis
        log_playwright_action("Identifying key branding elements")
        elements = await page.evaluate("""
            () => {
                const elements = [];
                
                // Look for logos
                document.querySelectorAll('img[alt*="logo" i], img[src*="logo" i], .logo, #logo').forEach(el => {
                    elements.push({
                        type: 'logo',
                        info: {
                            src: el.src || 'N/A',
                            alt: el.alt || 'N/A',
                            className: el.className
                        }
                    });
                });
                
                // Look for navigation
                document.querySelectorAll('nav, .nav, .navigation, .menu').forEach(el => {
                    elements.push({
                        type: 'navigation',
                        info: {
                            text: el.innerText.trim(),
                            className: el.className
                        }
                    });
                });
                
                // Look for headers/footers
                document.querySelectorAll('header, footer, .header, .footer').forEach(el => {
                    elements.push({
                        type: el.tagName.toLowerCase(),
                        info: {
                            text: el.innerText.trim().substring(0, 200),
                            className: el.className
                        }
                    });
                });
                
                return elements;
            }
        """)
        
        log_page_analysis("Elements", f"Found {len(elements)} key elements")
        for element in elements:
            log_page_analysis("Elements", f"  - {element['type']}: {element['info']}")
        
        return {
            "title": title,
            "text": visible_text,
            "structure": structure,
            "elements": elements
        }
        
    except Exception as e:
        error_msg = f"Error extracting page content: {str(e)}"
        log_agent_error("PMEA", error_msg)
        return {
            "title": "",
            "text": "",
            "structure": {},
            "elements": []
        }

async def execute_scenario_with_page(scenario, page, website):
    """Execute a scenario using a provided page (no browser management)"""
    scenario_id = scenario["scenario_id"]
    log_agent_thinking("PMEA", f"Executing scenario {scenario_id}: {scenario.get('description', 'No description')}")
    
    results = {
        "scenario_id": scenario_id,
        "description": scenario["description"],
        "result": "Pass",
        "details": [],
        "screenshot_path": None
    }
    
    try:
        # Extract comprehensive page content
        log_playwright_action("Extracting page content for analysis")
        page_content = await extract_page_content(page)
        
        # Take screenshot
        screenshot_path = f'screenshots/{scenario_id}.png'
        log_playwright_action(f"Taking screenshot: {screenshot_path}")
        await page.screenshot(path=screenshot_path)
        results["screenshot_path"] = screenshot_path
        
        # Use LLM to analyze page content against checks
        log_agent_thinking("PMEA", "Starting LLM-based page analysis")
        analysis = await analyze_page_with_llm(page_content, scenario, website)
        
        # Process branding results
        log_agent_thinking("PMEA", "Processing branding check results")
        for branding_result in analysis.get("branding_results", []):
            status = "✅" if branding_result["result"] == "Pass" else "❌"
            detail = f"{status} Branding: {branding_result['check']} - {branding_result['details']}"
            results["details"].append(detail)
            if branding_result["result"] == "Fail":
                results["result"] = "Fail"
                log_agent_thinking("PMEA", f"Branding check failed: {branding_result['check']}")
        
        # Process UX results
        log_agent_thinking("PMEA", "Processing UX check results")
        for ux_result in analysis.get("ux_results", []):
            status = "✅" if ux_result["result"] == "Pass" else "❌"
            detail = f"{status} UX: {ux_result['check']} - {ux_result['details']}"
            results["details"].append(detail)
            if ux_result["result"] == "Fail":
                results["result"] = "Fail"
                log_agent_thinking("PMEA", f"UX check failed: {ux_result['check']}")
        
        # Set overall result based on LLM analysis
        if analysis.get("overall_result") == "Fail":
            results["result"] = "Fail"
        
        # Handle LLM errors
        if "error" in analysis:
            results["result"] = "Fail"
            results["details"].append(f"❌ LLM Analysis Error: {analysis['error']}")
            log_agent_error("PMEA", f"LLM analysis error: {analysis['error']}")
        
        log_agent_thinking("PMEA", f"Scenario {scenario_id} completed with result: {results['result']}")
        
    except Exception as e:
        results["result"] = "Fail"
        error_detail = f"❌ Execution Error: {str(e)}"
        results["details"].append(error_detail)
        log_agent_error("PMEA", f"Execution error for scenario {scenario_id}: {str(e)}")
    
    return results

async def execute_scenario(scenario, website, auth_config=None):
    """Legacy function for backward compatibility - creates its own browser instance"""
    scenario_id = scenario["scenario_id"]
    log_agent_thinking("PMEA", f"Executing scenario {scenario_id}: {scenario.get('description', 'No description')}")
    
    results = {
        "scenario_id": scenario_id,
        "description": scenario["description"],
        "result": "Pass",
        "details": [],
        "screenshot_path": None
    }

    playwright_instance = None
    browser = None
    
    try:
        # Determine if we should use headless mode
        use_headless = True
        if auth_config and auth_config.get("type") == "interactive":
            use_headless = False
            log_playwright_action("🖥️  Launching browser in VISIBLE mode for interactive authentication")
        else:
            log_playwright_action("🔍 Launching browser in headless mode")
        
        # Launch playwright and browser manually (not with async context manager)
        playwright_instance = await async_playwright().start()
        browser = await playwright_instance.chromium.launch(headless=use_headless)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Handle authentication if provided
            if auth_config:
                auth_type = auth_config.get("type", "").lower()
                
                if auth_type == "interactive":
                    # For interactive auth, use main browser context to preserve session
                    auth_config["website_url"] = website
                    auth_success = await setup_interactive_authentication(page, auth_config)
                    if not auth_success:
                        results["result"] = "Fail"
                        results["details"].append("❌ Interactive authentication failed")
                        return results
                    
                    # Interactive auth handles navigation internally, page is ready for testing
                    log_playwright_action("✅ Interactive authentication complete - ready for testing")
                    
                else:
                    # For standard auth methods, set up on the main page
                    auth_success = await setup_standard_authentication(page, auth_config)
                    if not auth_success:
                        results["result"] = "Fail"
                        results["details"].append("❌ Authentication failed")
                        return results
                        
                    # Navigate to website after setting up auth
                    log_playwright_action(f"Navigating to {website}")
                    await page.goto(website)
                    await page.wait_for_load_state('networkidle')
            else:
                # No authentication - just navigate to website
                log_playwright_action(f"Navigating to {website}")
                await page.goto(website)
                
                # Wait for page to load
                log_playwright_action("Waiting for page to load completely")
                await page.wait_for_load_state('networkidle')
            
            # Use the new function to execute the scenario
            return await execute_scenario_with_page(scenario, page, website)
            
        except Exception as page_error:
            log_agent_error("PMEA", f"Error during page operations: {str(page_error)}")
            results["result"] = "Fail"
            results["details"].append(f"❌ Page Operation Error: {str(page_error)}")
            
    except Exception as e:
        results["result"] = "Fail"
        error_detail = f"❌ Execution Error: {str(e)}"
        results["details"].append(error_detail)
        log_agent_error("PMEA", f"Execution error for scenario {scenario_id}: {str(e)}")
    
    finally:
        # Always ensure browser and playwright are properly closed
        if browser:
            try:
                log_playwright_action("Closing browser")
                await browser.close()
            except Exception as e:
                log_playwright_action(f"Error closing browser: {str(e)}")
        
        if playwright_instance:
            try:
                await playwright_instance.stop()
            except Exception as e:
                log_playwright_action(f"Error stopping playwright: {str(e)}")

    return results

async def playwright_execution_agent(state: dict) -> dict:
    log_agent_start("PMEA", {
        "website": state["website"],
        "scenarios_count": len(state["enriched_scenarios"]),
        "scenario_ids": [s.get("scenario_id", "Unknown") for s in state["enriched_scenarios"]]
    })
    
    website = state["website"]
    enriched_scenarios = state["enriched_scenarios"]
    auth_config = state.get("auth_config")
    
    log_agent_thinking("PMEA", f"Starting execution of {len(enriched_scenarios)} scenarios on {website}")
    
    if auth_config:
        auth_type = auth_config.get('type', 'unknown')
        log_agent_thinking("PMEA", f"Authentication configured: {auth_type}")
        
        if auth_type == "interactive":
            log_agent_thinking("PMEA", "🖥️  Interactive authentication mode - browser will be visible for user login")

    # Create single browser instance for all scenarios
    playwright_instance = None
    browser = None
    context = None
    
    try:
        # Determine if we should use headless mode
        use_headless = True
        if auth_config and auth_config.get("type") == "interactive":
            use_headless = False
            log_playwright_action("🖥️  Launching browser in VISIBLE mode for interactive authentication")
        else:
            log_playwright_action("🔍 Launching browser in headless mode")
        
        # Launch browser once
        playwright_instance = await async_playwright().start()
        browser = await playwright_instance.chromium.launch(headless=use_headless)
        context = await browser.new_context()
        
        # Handle authentication once if required
        authenticated_page = None
        if auth_config:
            log_agent_thinking("PMEA", "🔐 Performing authentication once for all scenarios")
            auth_page = await context.new_page()
            
            auth_type = auth_config.get("type", "").lower()
            if auth_type == "interactive":
                # Interactive authentication
                auth_config["website_url"] = website
                auth_success = await setup_interactive_authentication(auth_page, auth_config)
                if not auth_success:
                    log_agent_error("PMEA", "❌ Interactive authentication failed")
                    return {"execution_results": []}
                authenticated_page = auth_page
                log_agent_thinking("PMEA", "✅ Interactive authentication completed successfully")
            else:
                # Standard authentication
                auth_success = await setup_standard_authentication(auth_page, auth_config)
                if not auth_success:
                    log_agent_error("PMEA", "❌ Authentication failed")
                    return {"execution_results": []}
                
                # Navigate to website after auth setup
                await auth_page.goto(website)
                await auth_page.wait_for_load_state('networkidle')
                authenticated_page = auth_page
                log_agent_thinking("PMEA", "✅ Standard authentication completed successfully")
        
        # Execute all scenarios using the authenticated context
        results = []
        for i, scenario in enumerate(enriched_scenarios):
            log_agent_thinking("PMEA", f"Processing scenario {i+1}/{len(enriched_scenarios)}: {scenario.get('scenario_id', 'Unknown')}")
            
            # Create new page for each scenario (reuses authenticated context)
            scenario_page = await context.new_page()
            
            # If we have authentication, copy cookies/session to new page
            if authenticated_page:
                # Navigate to website to inherit authentication
                log_playwright_action(f"🎯 Navigating to {website} with authenticated session")
                await scenario_page.goto(website)
                await scenario_page.wait_for_load_state('networkidle')
            else:
                # No authentication needed
                log_playwright_action(f"🌐 Navigating to {website}")
                await scenario_page.goto(website)
                await scenario_page.wait_for_load_state('networkidle')
            
            # Execute scenario with the authenticated page
            result = await execute_scenario_with_page(scenario, scenario_page, website)
            results.append(result)
            
            # Close scenario page to clean up
            await scenario_page.close()
        
        # Log summary
        passed = sum(1 for r in results if r["result"] == "Pass")
        failed = len(results) - passed
        
        log_agent_complete("PMEA", {
            "total_scenarios": len(results),
            "passed": passed,
            "failed": failed,
            "website": website
        })
        
        return {"execution_results": results}
        
    except Exception as e:
        log_agent_error("PMEA", f"Error in playwright execution agent: {str(e)}")
        return {"execution_results": []}
        
    finally:
        # Clean up browser resources
        if context:
            try:
                await context.close()
            except Exception as e:
                log_playwright_action(f"Error closing context: {str(e)}")
        
        if browser:
            try:
                log_playwright_action("Closing browser")
                await browser.close()
            except Exception as e:
                log_playwright_action(f"Error closing browser: {str(e)}")
        
        if playwright_instance:
            try:
                await playwright_instance.stop()
            except Exception as e:
                log_playwright_action(f"Error stopping playwright: {str(e)}")
