import json
import asyncio
from playwright.async_api import async_playwright
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def analyze_page_with_llm(page_content, scenario, website_url):
    """Use LLM to analyze page content against specific branding and UX checks"""
    
    # Extract relevant page information
    page_info = {
        "url": website_url,
        "title": page_content.get("title", ""),
        "visible_text": page_content.get("text", "")[:3000],  # Limit text to avoid token limits
        "page_structure": page_content.get("structure", ""),
        "elements": page_content.get("elements", [])
    }
    
    branding_checks = scenario.get("branding_checks", [])
    ux_checks = scenario.get("ux_checks", [])
    
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
    
    Respond with a JSON object:
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
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert UI/UX tester with deep knowledge of web design principles, branding guidelines, and user experience best practices."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        raw_output = response.choices[0].message.content
        if raw_output is None:
            raise ValueError("OpenAI API returned None content")
        
        analysis = json.loads(raw_output.strip())
        return analysis
        
    except Exception as e:
        print(f"❌ Error in LLM analysis: {str(e)}")
        return {
            "overall_result": "Fail",
            "branding_results": [],
            "ux_results": [],
            "error": str(e)
        }

async def extract_page_content(page):
    """Extract comprehensive page content for LLM analysis"""
    try:
        # Get page title
        title = await page.title()
        
        # Get visible text content
        visible_text = await page.evaluate("""
            () => {
                // Remove script and style elements
                const scripts = document.querySelectorAll('script, style');
                scripts.forEach(el => el.remove());
                
                // Get visible text
                return document.body.innerText || document.body.textContent;
            }
        """)
        
        # Get page structure information
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
        
        # Get key elements for branding analysis
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
        
        return {
            "title": title,
            "text": visible_text,
            "structure": structure,
            "elements": elements
        }
        
    except Exception as e:
        print(f"❌ Error extracting page content: {str(e)}")
        return {
            "title": "",
            "text": "",
            "structure": {},
            "elements": []
        }

async def execute_scenario(scenario, website):
    results = {
        "scenario_id": scenario["scenario_id"],
        "description": scenario["description"],
        "result": "Pass",
        "details": [],
        "screenshot_path": None
    }

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to website
            await page.goto(website)
            
            # Wait for page to load
            await page.wait_for_load_state('networkidle')
            
            # Extract comprehensive page content
            page_content = await extract_page_content(page)
            
            # Take screenshot
            screenshot_path = f'screenshots/{scenario["scenario_id"]}.png'
            await page.screenshot(path=screenshot_path)
            results["screenshot_path"] = screenshot_path
            
            # Use LLM to analyze page content against checks
            analysis = await analyze_page_with_llm(page_content, scenario, website)
            
            # Process branding results
            for branding_result in analysis.get("branding_results", []):
                status = "✅" if branding_result["result"] == "Pass" else "❌"
                results["details"].append(f"{status} Branding: {branding_result['check']} - {branding_result['details']}")
                if branding_result["result"] == "Fail":
                    results["result"] = "Fail"
            
            # Process UX results
            for ux_result in analysis.get("ux_results", []):
                status = "✅" if ux_result["result"] == "Pass" else "❌"
                results["details"].append(f"{status} UX: {ux_result['check']} - {ux_result['details']}")
                if ux_result["result"] == "Fail":
                    results["result"] = "Fail"
            
            # Set overall result based on LLM analysis
            if analysis.get("overall_result") == "Fail":
                results["result"] = "Fail"
            
            # Handle LLM errors
            if "error" in analysis:
                results["result"] = "Fail"
                results["details"].append(f"❌ LLM Analysis Error: {analysis['error']}")
            
            await browser.close()

    except Exception as e:
        results["result"] = "Fail"
        results["details"].append(f"❌ Execution Error: {str(e)}")

    return results

async def playwright_execution_agent(state: dict) -> dict:
    website = state["website"]
    enriched_scenarios = state["enriched_scenarios"]

    results = []
    for scenario in enriched_scenarios:
        result = await execute_scenario(scenario, website)
        results.append(result)

    return {"execution_results": results}
