from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
import pandas as pd
import json
import traceback
from datetime import datetime
from io import StringIO
import time
import base64
import re
import ast
import astroid
from typing import List, Dict

load_dotenv()
app = Flask(__name__)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.2,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)


@app.route("/generate_test_cases", methods=["POST"])
def generate_test_cases():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        prompt = data.get("prompt")
        url = data.get("url")

        if not prompt or not url:
            return jsonify({"error": "Both prompt and url are required"}), 400

        # ENHANCED DOM EXTRACTION - Much more comprehensive
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            page.wait_for_load_state("networkidle")

            # Extract comprehensive page information
            page_info = page.evaluate(
                """
                () => {
                    const info = {
                        title: document.title,
                        url: window.location.href,
                        meta: {
                            description: document.querySelector('meta[name="description"]')?.content || '',
                            keywords: document.querySelector('meta[name="keywords"]')?.content || '',
                            viewport: document.querySelector('meta[name="viewport"]')?.content || ''
                        },
                        forms: [],
                        inputs: [],
                        buttons: [],
                        links: [],
                        navigation: [],
                        content_sections: [],
                        validation_rules: {},
                        page_structure: {
                            has_header: !!document.querySelector('header, .header, #header'),
                            has_footer: !!document.querySelector('footer, .footer, #footer'),
                            has_sidebar: !!document.querySelector('aside, .sidebar, #sidebar'),
                            has_modal: !!document.querySelector('.modal, [role="dialog"]'),
                            has_carousel: !!document.querySelector('.carousel, .slider, .swiper'),
                            has_tabs: !!document.querySelector('.tab, .tabs, [role="tab"]'),
                            has_dropdown: !!document.querySelector('.dropdown, select'),
                            has_pagination: !!document.querySelector('.pagination, .pager'),
                            has_search: !!document.querySelector('input[type="search"], [placeholder*="search"], #search')
                        },
                        interactive_elements: []
                    };
                    
                    // Enhanced form analysis
                    document.querySelectorAll('form').forEach((form, i) => {
                        const formData = {
                            index: i,
                            action: form.action || '',
                            method: form.method || 'GET',
                            id: form.id || '',
                            className: form.className || '',
                            name: form.name || '',
                            autocomplete: form.autocomplete || '',
                            novalidate: form.noValidate || false,
                            enctype: form.enctype || '',
                            target: form.target || '',
                            inputs_count: form.querySelectorAll('input, textarea, select').length,
                            submit_buttons: form.querySelectorAll('input[type="submit"], button[type="submit"]').length,
                            required_fields: form.querySelectorAll('[required]').length,
                            hidden_fields: form.querySelectorAll('input[type="hidden"]').length,
                            validation_attributes: []
                        };
                        
                        // Check for HTML5 validation attributes
                        form.querySelectorAll('input').forEach(input => {
                            if (input.pattern) formData.validation_attributes.push('pattern');
                            if (input.min || input.max) formData.validation_attributes.push('minmax');
                            if (input.minLength || input.maxLength) formData.validation_attributes.push('length');
                            if (input.step) formData.validation_attributes.push('step');
                        });
                        
                        info.forms.push(formData);
                    });
                    
                    // Enhanced input analysis
                    document.querySelectorAll('input, textarea, select').forEach((input, i) => {
                        const inputData = {
                            type: input.type || input.tagName.toLowerCase(),
                            name: input.name || '',
                            id: input.id || '',
                            className: input.className || '',
                            placeholder: input.placeholder || '',
                            value: input.value || '',
                            defaultValue: input.defaultValue || '',
                            required: input.required || false,
                            disabled: input.disabled || false,
                            readonly: input.readOnly || false,
                            pattern: input.pattern || '',
                            min: input.min || '',
                            max: input.max || '',
                            minLength: input.minLength || -1,
                            maxLength: input.maxLength || -1,
                            step: input.step || '',
                            autocomplete: input.autocomplete || '',
                            autofocus: input.autofocus || false,
                            multiple: input.multiple || false,
                            size: input.size || -1,
                            validation_message: input.validationMessage || '',
                            associated_label: '',
                            parent_form: input.closest('form')?.id || 'no-form',
                            tabindex: input.tabIndex || -1,
                            data_attributes: {}
                        };
                        
                        // Collect data attributes
                        Object.keys(input.dataset || {}).forEach(key => {
                            inputData.data_attributes[key] = input.dataset[key];
                        });
                        
                        // Find associated label
                        const label = input.id ? document.querySelector(`label[for="${input.id}"]`) : 
                                     input.closest('label') || 
                                     input.parentElement?.querySelector('label');
                        if (label) {
                            inputData.associated_label = label.textContent.trim();
                        }
                        
                        // For select elements, get all options
                        if (input.tagName.toLowerCase() === 'select') {
                            inputData.options = Array.from(input.options).map(opt => ({
                                value: opt.value,
                                text: opt.textContent.trim(),
                                selected: opt.selected,
                                disabled: opt.disabled
                            }));
                        }
                        
                        info.inputs.push(inputData);
                    });
                    
                    // Enhanced button analysis
                    document.querySelectorAll('button, input[type="submit"], input[type="button"], input[type="reset"]').forEach((btn, i) => {
                        info.buttons.push({
                            type: btn.type || 'button',
                            text: btn.textContent?.trim() || btn.value || '',
                            id: btn.id || '',
                            className: btn.className || '',
                            disabled: btn.disabled || false,
                            form_association: btn.form?.id || 'no-form',
                            onclick: btn.onclick ? 'has-onclick' : 'no-onclick'
                        });
                    });
                    
                    // Navigation analysis
                    document.querySelectorAll('nav a, .nav a, .navbar a, .menu a').forEach((link, i) => {
                        if (i < 20) { // Limit navigation links
                            info.navigation.push({
                                text: link.textContent?.trim() || '',
                                href: link.href || '',
                                target: link.target || '',
                                active: link.classList.contains('active') || link.classList.contains('current')
                            });
                        }
                    });
                    
                    // All links analysis
                    document.querySelectorAll('a[href]').forEach((link, i) => {
                        if (i < 30) { // Increased limit for comprehensive testing
                            info.links.push({
                                text: link.textContent?.trim() || '',
                                href: link.href || '',
                                target: link.target || '',
                                download: link.download || '',
                                is_external: link.hostname !== window.location.hostname,
                                is_anchor: link.href.includes('#'),
                                is_email: link.href.startsWith('mailto:'),
                                is_phone: link.href.startsWith('tel:')
                            });
                        }
                    });
                    
                    // Content sections for comprehensive testing
                    ['main', 'section', 'article', '.content', '.main-content'].forEach(selector => {
                        document.querySelectorAll(selector).forEach((section, i) => {
                            info.content_sections.push({
                                selector: selector,
                                id: section.id || '',
                                className: section.className || '',
                                text_length: section.textContent?.length || 0,
                                has_images: section.querySelectorAll('img').length,
                                has_videos: section.querySelectorAll('video').length,
                                has_forms: section.querySelectorAll('form').length
                            });
                        });
                    });
                    
                    return info;
                }
            """
            )
            browser.close()

        # Build a concise, highly-structured prompt that passes the URL, DOM and the raw user prompt directly to the LLM.
        dom_context = json.dumps(
            {
                "url": url,
                "title": page_info["title"],
                "inputs": page_info["inputs"],
                "buttons": page_info["buttons"],
                "forms": page_info["forms"],
            },
            indent=2,
        )

        ai_prompt = f"""You are an expert QA engineer tasked with creating comprehensive test cases for a web application.

WEBSITE INFORMATION:
URL: {url}
Title: {page_info['title']}

DOM ELEMENTS FOUND:
- Input fields: {len(page_info['inputs'])}
- Buttons: {len(page_info['buttons'])}
- Forms: {len(page_info['forms'])}

USER REQUIREMENTS:
{prompt}

INSTRUCTIONS:
1. Parse the user's requirements carefully - extract any specific test data they provide
2. Generate exactly 30 high-value test cases (to avoid response truncation)
3. Use only literal string values (no JavaScript expressions)
4. For long strings, use actual characters like "aaaaaaa" not "a".repeat(7)

Generate test cases in this JSON format:
[
  {{
    "description": "Brief test description",
    "steps": ["Step 1", "Step 2", "Step 3"],
    "test_data": {{"field_name": "value", "another_field": "value"}},
    "expected_result": "Expected outcome",
    "test_type": "positive|negative|boundary|ui_ux|security",
    "priority": "high|medium|low"
  }}
]

IMPORTANT: Return ONLY the JSON array, no other text.
Focus on these test categories:
1. Authentication (5 tests): valid login, invalid credentials, empty fields
2. Security (5 tests): SQL injection, XSS, CSRF
3. Input validation (5 tests): special chars, length limits, unicode
4. UI/UX (5 tests): field focus, tab navigation, button states  
5. Edge cases (5 tests): concurrent logins, session timeout, network issues
6. Performance (5 tests): rapid submissions, slow network, multiple tabs
"""

        response = llm.invoke(ai_prompt)
        test_cases_text = response.content.strip()

        # Robust JSON extraction with multiple fallback strategies
        def extract_and_parse_json(text):
            """Extract JSON from LLM response with multiple strategies"""
            # Strategy 1: Try parsing as-is
            try:
                return json.loads(text)
            except:
                pass

            # Strategy 2: Remove markdown code blocks
            cleaned = text
            if "```json" in cleaned:
                cleaned = re.sub(r"```json\s*", "", cleaned)
                cleaned = re.sub(r"```", "", cleaned)
            elif "```" in cleaned:
                cleaned = re.sub(r"```\s*", "", cleaned)

            # Strategy 3: Fix JavaScript expressions in JSON
            def replace_repeat(match):
                char = match.group(1)
                count = int(match.group(2))
                # Limit repeated characters to prevent memory issues
                count = min(count, 1000)
                return f'"{char * count}"'

            # Fix patterns like "a".repeat(1001)
            cleaned = re.sub(r'"([^"]+)"\.repeat\((\d+)\)', replace_repeat, cleaned)

            # Strategy 4: Handle truncated JSON by closing it properly
            if cleaned.count("[") > cleaned.count("]"):
                # Find the last complete object
                last_complete = cleaned.rfind("},")
                if last_complete != -1:
                    cleaned = cleaned[: last_complete + 1] + "]"
                else:
                    # If no complete object, try to close the current one
                    cleaned = cleaned.rstrip()
                    if not cleaned.endswith("}"):
                        # Add a dummy closing for the incomplete object
                        if '"expected_result":' in cleaned:
                            cleaned += '"Truncated due to length limit"}'
                        else:
                            cleaned += "}"
                    cleaned += "]"

            # Strategy 5: Extract array portion
            array_match = re.search(r"\[\s*\{.*\}\s*\]", cleaned, re.DOTALL)
            if array_match:
                try:
                    return json.loads(array_match.group())
                except:
                    pass

            # Strategy 6: Find first [ and last valid }
            start = cleaned.find("[")
            if start != -1:
                # Find the last complete object
                end = cleaned.rfind("}")
                if end > start:
                    try:
                        json_str = cleaned[start : end + 1]
                        # Ensure it ends with ]
                        if not json_str.rstrip().endswith("]"):
                            json_str = json_str.rstrip() + "]"
                        # Fix JavaScript expressions before parsing
                        json_str = re.sub(
                            r'"([^"]+)"\.repeat\((\d+)\)', replace_repeat, json_str
                        )
                        # Fix common issues
                        json_str = re.sub(
                            r",\s*}", "}", json_str
                        )  # Remove trailing commas
                        json_str = re.sub(
                            r",\s*]", "]", json_str
                        )  # Remove trailing commas
                        return json.loads(json_str)
                    except:
                        pass

            raise ValueError("Could not extract valid JSON from LLM response")

        try:
            test_cases = extract_and_parse_json(test_cases_text)

            # Validate it's a list
            if not isinstance(test_cases, list):
                raise ValueError("LLM response is not a JSON array")

        except Exception as e:
            # Return error with raw response for debugging
            return (
                jsonify(
                    {
                        "error": f"Failed to parse AI response: {str(e)}",
                        "raw_response": test_cases_text,
                    }
                ),
                500,
            )

        # Enhanced validation and structure
        for i, test_case in enumerate(test_cases):
            required_fields = ["description", "steps", "expected_result", "test_type"]
            for field in required_fields:
                if field not in test_case:
                    test_case[field] = f"Generated {field} for test {i+1}"

            # Add missing optional fields
            if "category" not in test_case:
                test_case["category"] = "functional"
            if "priority" not in test_case:
                test_case["priority"] = "medium"
            if "automation_feasible" not in test_case:
                test_case["automation_feasible"] = True
            if "test_data" not in test_case:
                test_case["test_data"] = {}

        return jsonify(
            {
                "test_cases": test_cases,
                "page_analysis": {
                    "total_elements_analyzed": len(page_info["inputs"])
                    + len(page_info["buttons"])
                    + len(page_info["links"]),
                    "forms_count": len(page_info["forms"]),
                    "interactive_elements": len(page_info["buttons"]),
                    "page_complexity": (
                        "high"
                        if len(page_info["inputs"]) > 10
                        else "medium" if len(page_info["inputs"]) > 5 else "low"
                    ),
                },
            }
        )

    except Exception as e:
        return jsonify({"error": f"Error generating test cases: {str(e)}"}), 500
    





def parse_manual_test_cases(text, url):
    """Parse manual test cases and convert to structured format using AI"""
    ai_prompt = f"""You are parsing manual test cases for the website: {url}

USER PROVIDED TEST CASES:
{text}

Convert these test cases into a structured JSON format. Extract any test data mentioned (like usernames, passwords, form values).
If test data is not explicitly mentioned, leave the test_data object empty.

Return ONLY a JSON array in this format:
[
  {{
    "description": "Brief test description",
    "steps": ["Step 1", "Step 2", "Step 3"],
    "test_data": {{"field_name": "value"}},
    "expected_result": "Expected outcome",
    "test_type": "positive|negative|boundary|ui_ux|security",
    "priority": "high|medium|low"
  }}
]
"""

    try:
        response = llm.invoke(ai_prompt)
        test_cases_text = response.content.strip()

        # Extract JSON
        if "```json" in test_cases_text:
            start = test_cases_text.find("```json") + 7
            end = test_cases_text.rfind("```")
            if end > start:
                test_cases_text = test_cases_text[start:end].strip()

        test_cases = json.loads(test_cases_text)
        return test_cases
    except:
        # Fallback: treat each line as a simple test case
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        test_cases = []
        for i, line in enumerate(lines):
            test_cases.append({
                "description": line,
                "steps": [line],
                "test_data": {},
                "expected_result": "Action completes successfully",
                "test_type": "positive",
                "priority": "medium",
            })
        return test_cases


def enhance_csv_test_cases(df, url):
    """Enhance CSV test cases to ensure proper structure"""
    test_cases = []

    for _, row in df.iterrows():
        test_case = {}

        # Map common column names
        if "description" in df.columns:
            test_case["description"] = str(row.get("description", ""))
        elif "test_case" in df.columns:
            test_case["description"] = str(row.get("test_case", ""))
        elif "name" in df.columns:
            test_case["description"] = str(row.get("name", ""))
        else:
            test_case["description"] = f"Test Case {len(test_cases) + 1}"

        # Handle steps
        if "steps" in df.columns:
            steps_str = str(row.get("steps", ""))
            # Try to parse as JSON array first
            try:
                test_case["steps"] = json.loads(steps_str)
            except:
                # Split by common delimiters
                if ";" in steps_str:
                    test_case["steps"] = [s.strip() for s in steps_str.split(";")]
                elif "|" in steps_str:
                    test_case["steps"] = [s.strip() for s in steps_str.split("|")]
                else:
                    test_case["steps"] = [steps_str]
        else:
            test_case["steps"] = [test_case["description"]]

        # Extract test data
        test_case["test_data"] = {}

        # Common test data columns
        data_columns = [
            "username", "password", "email", "phone", "data", "input", "value"
        ]

        for col in data_columns:
            if col in df.columns and pd.notna(row.get(col)):
                test_case["test_data"][col] = str(row.get(col))

        # Try to parse test_data column if it exists
        if "test_data" in df.columns:
            try:
                parsed_data = json.loads(str(row.get("test_data", "{}")))
                if isinstance(parsed_data, dict):
                    test_case["test_data"].update(parsed_data)
            except:
                pass

        # Expected result
        if "expected_result" in df.columns:
            test_case["expected_result"] = str(row.get("expected_result", "Success"))
        elif "expected" in df.columns:
            test_case["expected_result"] = str(row.get("expected", "Success"))
        else:
            test_case["expected_result"] = "Action completes successfully"

        # Test type
        if "test_type" in df.columns:
            test_case["test_type"] = str(row.get("test_type", "positive"))
        elif "type" in df.columns:
            test_case["test_type"] = str(row.get("type", "positive"))
        else:
            # Infer from description
            desc_lower = test_case["description"].lower()
            if any(word in desc_lower for word in ["invalid", "error", "fail", "wrong"]):
                test_case["test_type"] = "negative"
            else:
                test_case["test_type"] = "positive"

        # Priority
        if "priority" in df.columns:
            test_case["priority"] = str(row.get("priority", "medium"))
        else:
            test_case["priority"] = "medium"

        test_cases.append(test_case)

    return test_cases


@app.route("/generate_test_script", methods=["POST"])
def generate_test_script():
    try:
        url = request.form.get("url")
        test_file = request.files.get("test_case_file")
        show_browser = (
            request.form.get("show_browser", "False").lower() == "true"
        )  # Get browser visibility preference
        browser_size_str = request.form.get("browser_size", "Small (800x600)")  # Get browser size

        if not url or not test_file:
            return jsonify({"error": "URL and test case file are required"}), 400

        # Parse browser_size_str to determine width and height
        window_width, window_height = 800, 600  # Default to Small
        if "Medium (1024x768)" in browser_size_str:
            window_width, window_height = 1024, 768
        elif "Large (1280x720)" in browser_size_str:
            window_width, window_height = 1280, 720
        
        # Set window position based on size for better screen placement
        if "Small" in browser_size_str:
            window_position = "1200,100"  # Side by side with other windows
        elif "Medium" in browser_size_str:
            window_position = "900,100"
        else:  # Large
            window_position = "600,100"

        file_content = test_file.read().decode("utf-8")

        # Parse test cases based on file type
        try:
            if test_file.mimetype == "text/csv":
                df = pd.read_csv(StringIO(file_content))
                test_cases = enhance_csv_test_cases(df, url)
            elif test_file.mimetype == "application/json":
                test_cases = json.loads(file_content)
                # Ensure proper structure
                if not isinstance(test_cases, list):
                    test_cases = [test_cases]
            else:
                # For text files, use AI to parse
                test_cases = parse_manual_test_cases(file_content, url)
        except Exception as e:
            return jsonify({"error": f"Failed to parse test case file: {str(e)}"}), 400

        # Initial DOM extraction for baseline
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            page.wait_for_load_state("networkidle")

            initial_dom = page.evaluate(
                """
                () => {
                    return {
                        title: document.title,
                        url: window.location.href,
                        body_text: document.body.innerText.substring(0, 1000)
                    };
                }
            """
            )
            browser.close()

        # Convert to Python-compatible JSON
        test_cases_json = (
            json.dumps(test_cases, indent=2)
            .replace("false", "False")
            .replace("true", "True")
            .replace("null", "None")
        )

        # Generate DYNAMIC, STATE-AWARE test script
        test_script = """from playwright.sync_api import sync_playwright
import time
import base64
import json
import re

test_case_logs = []
current_test_case = None
screenshot_counter = 0
SHOW_BROWSER = """ + str(show_browser) + """  # Browser visibility setting
WINDOW_WIDTH = """ + str(window_width) + """  # Dynamic window width
WINDOW_HEIGHT = """ + str(window_height) + """  # Dynamic window height
WINDOW_POSITION = \"""" + window_position + """\"  # Dynamic window position

# Global state tracking
current_page_state = {
    "url": "",
    "title": "",
    "logged_in": False,
    "current_section": "login",
    "available_elements": {},
    "navigation_options": []
}

def start_test_case(name, desc):
    global current_test_case
    current_test_case = {
        "test_case": name,
        "description": desc,
        "status": "Running",
        "start_time": time.time(),
        "actions": [],
        "screenshots": [],
        "result": "In Progress"
    }
    test_case_logs.append(current_test_case)

def log_action(action, result):
    if current_test_case:
        current_test_case["actions"].append({"action": action, "result": result, "timestamp": time.time()})

def capture_screenshot(page, description):
    global screenshot_counter
    if current_test_case:
        try:
            screenshot_counter += 1
            screenshot_bytes = page.screenshot(full_page=True)
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            screenshot_data = {
                "description": description,
                "timestamp": time.time(),
                "data": f"data:image/png;base64,{screenshot_base64}",
                "counter": screenshot_counter
            }
            
            current_test_case["screenshots"].append(screenshot_data)
            log_action(f"📸 Screenshot: {description}", "✅ Captured")
            return True
        except Exception as e:
            log_action(f"📸 Screenshot: {description}", f"❌ Failed: {str(e)}")
            return False

def complete_test_case(result):
    if current_test_case:
        current_test_case["status"] = "Completed"
        current_test_case["result"] = result
        current_test_case["end_time"] = time.time()

def analyze_current_page(page):
    \"\"\"Dynamically analyze the current page state and available elements\"\"\"
    global current_page_state
    
    try:
        page_analysis = page.evaluate('''
            () => {
                const analysis = {
                    url: window.location.href,
                    title: document.title,
                    inputs: [],
                    buttons: [],
                    links: [],
                    forms: [],
                    navigation: [],
                    popups: [],
                    page_indicators: {
                        has_login_form: false,
                        has_dashboard: false,
                        has_navigation_menu: false,
                        has_logout_button: false,
                        has_popup: false,
                        has_form: false
                    },
                    text_content: document.body.innerText.toLowerCase()
                };
                
                // Analyze inputs with comprehensive selectors
                document.querySelectorAll('input, textarea, select').forEach((element, index) => {
                    const selectors = [];
                    if (element.id) selectors.push(`#${element.id}`);
                    if (element.name) selectors.push(`[name="${element.name}"]`);
                    if (element.className) selectors.push(`.${element.className.split(' ')[0]}`);
                    if (element.type) selectors.push(`input[type="${element.type}"]`);
                    if (element.placeholder) selectors.push(`[placeholder="${element.placeholder}"]`);
                    selectors.push(`${element.tagName.toLowerCase()}:nth-of-type(${index + 1})`);
                    
                    // Find associated label
                    let label = '';
                    if (element.id) {
                        const labelEl = document.querySelector(`label[for="${element.id}"]`);
                        if (labelEl) label = labelEl.textContent.trim();
                    }
                    if (!label) {
                        const parentLabel = element.closest('label');
                        if (parentLabel) label = parentLabel.textContent.trim();
                    }
                    if (!label) {
                        const prevLabel = element.previousElementSibling;
                        if (prevLabel && prevLabel.tagName === 'LABEL') {
                            label = prevLabel.textContent.trim();
                        }
                    }
                    
                    analysis.inputs.push({
                        selectors: selectors,
                        type: element.type || element.tagName.toLowerCase(),
                        name: element.name || '',
                        id: element.id || '',
                        placeholder: element.placeholder || '',
                        label: label,
                        value: element.value || '',
                        required: element.required || false,
                        visible: element.offsetParent !== null
                    });
                });
                
                // Analyze buttons and clickable elements
                document.querySelectorAll('button, input[type="submit"], input[type="button"], [role="button"], .btn, a[href]').forEach((element, index) => {
                    const selectors = [];
                    if (element.id) selectors.push(`#${element.id}`);
                    if (element.className) selectors.push(`.${element.className.split(' ')[0]}`);
                    if (element.type) selectors.push(`${element.tagName.toLowerCase()}[type="${element.type}"]`);
                    if (element.textContent) selectors.push(`text="${element.textContent.trim()}"`);
                    selectors.push(`${element.tagName.toLowerCase()}:nth-of-type(${index + 1})`);
                    
                    const text = element.textContent?.trim() || element.value || element.alt || '';
                    const isVisible = element.offsetParent !== null;
                    
                    analysis.buttons.push({
                        selectors: selectors,
                        text: text,
                        type: element.type || element.tagName.toLowerCase(),
                        href: element.href || '',
                        visible: isVisible,
                        clickable: true
                    });
                });
                
                // Detect page state indicators
                const bodyText = analysis.text_content;
                analysis.page_indicators.has_login_form = document.querySelector('input[type="password"]') !== null;
                analysis.page_indicators.has_dashboard = bodyText.includes('dashboard') || bodyText.includes('welcome') || bodyText.includes('home');
                analysis.page_indicators.has_navigation_menu = document.querySelector('nav, .nav, .navbar, .menu') !== null;
                analysis.page_indicators.has_logout_button = bodyText.includes('logout') || bodyText.includes('sign out');
                analysis.page_indicators.has_popup = document.querySelector('.modal, .popup, [role="dialog"]') !== null;
                analysis.page_indicators.has_form = document.querySelector('form') !== null;
                
                // Find navigation options
                document.querySelectorAll('nav a, .nav a, .navbar a, .menu a, .sidebar a').forEach(link => {
                    if (link.textContent.trim() && link.href) {
                        analysis.navigation.push({
                            text: link.textContent.trim(),
                            href: link.href,
                            selectors: [
                                link.id ? `#${link.id}` : null,
                                link.className ? `.${link.className.split(' ')[0]}` : null,
                                `text="${link.textContent.trim()}"`
                            ].filter(Boolean)
                        });
                    }
                });
                
                // Detect popups
                document.querySelectorAll('.modal, .popup, [role="dialog"], .overlay').forEach(popup => {
                    if (popup.offsetParent !== null) {
                        analysis.popups.push({
                            text: popup.textContent.trim().substring(0, 100),
                            selectors: [
                                popup.id ? `#${popup.id}` : null,
                                popup.className ? `.${popup.className.split(' ')[0]}` : null
                            ].filter(Boolean)
                        });
                    }
                });
                
                return analysis;
            }
        ''')
        
        # Update global state
        current_page_state.update({
            "url": page_analysis["url"],
            "title": page_analysis["title"],
            "available_elements": page_analysis,
            "logged_in": not page_analysis["page_indicators"]["has_login_form"] and page_analysis["page_indicators"]["has_dashboard"],
            "current_section": determine_current_section(page_analysis)
        })
        
        log_action("🔍 Page Analysis", f"✅ Found {len(page_analysis['inputs'])} inputs, {len(page_analysis['buttons'])} buttons")
        return page_analysis
        
    except Exception as e:
        log_action("🔍 Page Analysis", f"❌ Failed: {str(e)}")
        return None

def determine_current_section(page_analysis):
    \"\"\"Determine what section/page we're currently on\"\"\"
    indicators = page_analysis["page_indicators"]
    text = page_analysis["text_content"]
    
    if indicators["has_login_form"] and not indicators["has_dashboard"]:
        return "login"
    elif indicators["has_dashboard"] or "dashboard" in text:
        return "dashboard"
    elif "probound" in text.lower() or "information" in text.lower():
        return "probound_info"
    elif indicators["has_form"] and not indicators["has_login_form"]:
        return "form_page"
    else:
        return "unknown"

def smart_fill_field(page, field_identifier, value, context=""):
    \"\"\"Intelligently fill fields using current page analysis\"\"\"
    page_analysis = analyze_current_page(page)
    if not page_analysis:
        return False
    
    field_identifier_lower = field_identifier.lower()
    
    # Find matching input fields
    for input_field in page_analysis["inputs"]:
        if not input_field["visible"]:
            continue
            
        # Multiple matching strategies
        matches = [
            field_identifier_lower in input_field["name"].lower(),
            field_identifier_lower in input_field["id"].lower(),
            field_identifier_lower in input_field["label"].lower(),
            field_identifier_lower in input_field["placeholder"].lower(),
            field_identifier_lower in input_field["type"].lower()
        ]
        
        if any(matches):
            # Try each selector until one works
            for selector in input_field["selectors"]:
                try:
                    if page.locator(selector).count() > 0:
                        element = page.locator(selector).first
                        
                        # Highlight if browser is visible
                        if SHOW_BROWSER:
                            element.evaluate('''
                                element => {
                                    element.style.border = '3px solid #10B981';
                                    element.style.boxShadow = '0 0 10px #10B981';
                                    setTimeout(() => {
                                        element.style.border = '';
                                        element.style.boxShadow = '';
                                    }, 2000);
                                }
                            ''')
                        
                        # Clear and fill
                        element.clear()
                        element.fill(str(value))
                        
                        field_display_name = field_identifier or input_field["label"] or 'field'
                        log_action(f"📝 Fill {field_display_name}", f"✅ {value}")
                        time.sleep(0.5)
                        return True
                        
                except Exception as e:
                    continue
    
    log_action(f"📝 Fill {field_identifier}", f"❌ Field not found")
    return False

def smart_click_element(page, element_identifier, context=""):
    \"\"\"Intelligently click elements using current page analysis\"\"\"
    page_analysis = analyze_current_page(page)
    if not page_analysis:
        return False
    
    element_identifier_lower = element_identifier.lower()
    
    # Find matching clickable elements
    for button in page_analysis["buttons"]:
        if not button["visible"]:
            continue
            
        # Multiple matching strategies
        matches = [
            element_identifier_lower in button["text"].lower(),
            element_identifier_lower in button["type"].lower(),
            any(element_identifier_lower in selector.lower() for selector in button["selectors"])
        ]
        
        if any(matches):
            # Try each selector until one works
            for selector in button["selectors"]:
                try:
                    if selector.startswith('text='):
                        # Use text selector
                        text_content = selector[5:]  # Remove 'text=' prefix
                        text_locator = f'text="{text_content}"'
                        if page.locator(text_locator).count() > 0:
                            element = page.locator(text_locator).first
                        else:
                            continue
                    else:
                        if page.locator(selector).count() > 0:
                            element = page.locator(selector).first
                        else:
                            continue
                    
                    # Highlight if browser is visible
                    if SHOW_BROWSER:
                        element.evaluate('''
                            element => {
                                element.style.border = '3px solid #EF4444';
                                element.style.boxShadow = '0 0 10px #EF4444';
                                setTimeout(() => {
                                    element.style.border = '';
                                    element.style.boxShadow = '';
                                }, 2000);
                            }
                        ''')
                    
                    # Click the element
                    element.click()
                    log_action(f"🖱️ Click {element_identifier}", "✅ Success")
                    time.sleep(1)  # Wait for action to complete
                    return True
                    
                except Exception as e:
                    continue
    
    log_action(f"🖱️ Click {element_identifier}", f"❌ Element not found")
    return False

def handle_popups(page):
    \"\"\"Handle any popups that appear\"\"\"
    page_analysis = analyze_current_page(page)
    if not page_analysis:
        return False
    
    if page_analysis["popups"]:
        for popup in page_analysis["popups"]:
            popup_text = popup["text"].lower()
            
            # Handle "New chat" popup specifically
            if "new chat" in popup_text:
                log_action("🔔 Popup detected", "New chat popup found")
                # Try to click on the popup or its close/accept button
                if smart_click_element(page, "new chat"):
                    return True
                # Try common popup buttons
                for button_text in ["ok", "accept", "continue", "yes"]:
                    if smart_click_element(page, button_text):
                        return True
            
            # Handle other popups
            log_action("🔔 Popup detected", f"Popup: {popup_text[:50]}")
            
        return True
    return False

def navigate_to_section(page, section_name):
    \"\"\"Navigate to a specific section of the application\"\"\"
    page_analysis = analyze_current_page(page)
    if not page_analysis:
        return False
    
    section_lower = section_name.lower()
    
    # Look for navigation links
    for nav_item in page_analysis["navigation"]:
        nav_text = nav_item["text"].lower()
        if section_lower in nav_text or any(word in nav_text for word in section_lower.split()):
            # Try to click the navigation item
            for selector in nav_item["selectors"]:
                try:
                    if selector.startswith('text='):
                        text_content = selector[5:]
                        text_locator = f'text="{text_content}"'
                        if page.locator(text_locator).count() > 0:
                            page.locator(text_locator).first.click()
                            log_action(f"🧭 Navigate to {section_name}", "✅ Success")
                            time.sleep(2)
                            return True
                    else:
                        if page.locator(selector).count() > 0:
                            page.locator(selector).first.click()
                            log_action(f"🧭 Navigate to {section_name}", "✅ Success")
                            time.sleep(2)
                            return True
                except:
                    continue
    
    log_action(f"🧭 Navigate to {section_name}", f"❌ Navigation not found")
    return False

def execute_intelligent_test_step(page, step, test_data):
    \"\"\"Execute a single test step with intelligence and context awareness\"\"\"
    step_lower = step.lower()
    
    # Show step banner if browser is visible
    if SHOW_BROWSER:
        # Escape the step content for JavaScript
        step_escaped = step.replace('"', '\\\\"').replace("'", "\\\\'")
        banner_script = '''
            () => {
                const banner = document.createElement('div');
                banner.innerHTML = '🤖 Executing: ''' + step_escaped + '''';
                banner.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; background: #3B82F6; color: white; padding: 10px; text-align: center; z-index: 9999; font-family: Arial; font-size: 14px;';
                document.body.appendChild(banner);
                setTimeout(() => banner.remove(), 3000);
            }
        '''
        page.evaluate(banner_script)
    
    # Handle different types of steps
    if "enter" in step_lower or "fill" in step_lower or "type" in step_lower:
        # Extract field and value from step
        if "username" in step_lower:
            username = test_data.get("username", "Admin")
            return smart_fill_field(page, "username", username)
        elif "password" in step_lower:
            password = test_data.get("password", "admin123")
            return smart_fill_field(page, "password", password)
        else:
            # Try to extract field name and value from test_data
            for field_name, field_value in test_data.items():
                if field_name.lower() in step_lower:
                    return smart_fill_field(page, field_name, field_value)
    
    elif "click" in step_lower or "press" in step_lower:
        # Extract what to click
        if "submit" in step_lower:
            return smart_click_element(page, "submit")
        elif "login" in step_lower:
            return smart_click_element(page, "login")
        elif "logout" in step_lower:
            return smart_click_element(page, "logout")
        elif "next" in step_lower:
            return smart_click_element(page, "next")
        elif "confirm" in step_lower:
            return smart_click_element(page, "confirm")
        elif "new chat" in step_lower:
            return smart_click_element(page, "new chat")
        else:
            # Try to extract button text from step
            words = step_lower.split()
            for i, word in enumerate(words):
                if word in ["click", "press"] and i + 1 < len(words):
                    button_text = words[i + 1]
                    return smart_click_element(page, button_text)
    
    elif "navigate" in step_lower:
        # Extract navigation target
        if "probound" in step_lower:
            return navigate_to_section(page, "probound information")
        else:
            # Try to extract section name
            words = step_lower.split()
            for i, word in enumerate(words):
                if word == "to" and i + 1 < len(words):
                    section = " ".join(words[i + 1:])
                    return navigate_to_section(page, section)
    
    elif "check" in step_lower or "verify" in step_lower:
        # Verification steps
        if "login" in step_lower:
            page_analysis = analyze_current_page(page)
            if page_analysis and current_page_state["logged_in"]:
                log_action("✅ Login verification", "User is logged in")
                return True
            else:
                log_action("❌ Login verification", "User is not logged in")
                return False
        elif "popup" in step_lower:
            return handle_popups(page)
    
    elif "handle" in step_lower and "popup" in step_lower:
        return handle_popups(page)
    
    # Default: try to interpret the step as a general action
    log_action("🤔 Interpreting step", step)
    return True

def fill_form_intelligently(page, context=""):
    \"\"\"Fill any form on the current page with available test data or reasonable defaults\"\"\"
    page_analysis = analyze_current_page(page)
    if not page_analysis:
        return False
    
    filled_count = 0
    
    for input_field in page_analysis["inputs"]:
        if not input_field["visible"] or input_field["type"] in ["hidden", "submit", "button"]:
            continue
        
        # Determine what to fill based on field characteristics
        field_name = input_field["name"].lower()
        field_label = input_field["label"].lower()
        field_placeholder = input_field["placeholder"].lower()
        field_type = input_field["type"].lower()
        
        value_to_fill = None
        
        # Smart value assignment
        if field_type == "email" or "email" in field_name or "email" in field_label:
            value_to_fill = "test@example.com"
        elif field_type == "tel" or "phone" in field_name or "phone" in field_label:
            value_to_fill = "+1234567890"
        elif "name" in field_name or "name" in field_label:
            if "first" in field_name or "first" in field_label:
                value_to_fill = "John"
            elif "last" in field_name or "last" in field_label:
                value_to_fill = "Doe"
            else:
                value_to_fill = "John Doe"
        elif "address" in field_name or "address" in field_label:
            value_to_fill = "123 Main Street"
        elif "city" in field_name or "city" in field_label:
            value_to_fill = "New York"
        elif "zip" in field_name or "postal" in field_name:
            value_to_fill = "10001"
        elif field_type == "number" or "age" in field_name:
            value_to_fill = "25"
        elif field_type == "date":
            value_to_fill = "2024-01-01"
        elif field_type == "text" and not value_to_fill:
            value_to_fill = "Test Data"
        
        # Fill the field if we have a value
        if value_to_fill:
            for selector in input_field["selectors"]:
                try:
                    if page.locator(selector).count() > 0:
                        page.locator(selector).first.fill(str(value_to_fill))
                        filled_count += 1
                        field_display_name = field_name or field_label or 'field'
                        log_action(f"📝 Auto-fill {field_display_name}", f"✅ {value_to_fill}")
                        break
                except:
                    continue
    
    # Handle checkboxes
    checkboxes = [inp for inp in page_analysis["inputs"] if inp["type"] == "checkbox" and inp["visible"]]
    for checkbox in checkboxes[:3]:  # Check first 3 checkboxes
        for selector in checkbox["selectors"]:
            try:
                if page.locator(selector).count() > 0:
                    page.locator(selector).first.check()
                    filled_count += 1
                    log_action("☑️ Auto-check checkbox", "✅ Checked")
                    break
            except:
                continue
    
    log_action(f"📝 Form auto-fill", f"✅ Filled {filled_count} fields")
    return filled_count > 0

with sync_playwright() as p:
    # Launch browser based on visibility preference
    if SHOW_BROWSER:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=300,  # Slow down for better visibility
            args=[
                f'--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}',
                f'--window-position={WINDOW_POSITION}',
                '--no-first-run',
                '--no-default-browser-check'
            ]
        )
    else:
        browser = p.chromium.launch(headless=True)
    
    # Create a SINGLE context that persists across all test cases
    context = browser.new_context(
        viewport={"width": WINDOW_WIDTH, "height": WINDOW_HEIGHT} if SHOW_BROWSER else None,
    )
    page = context.new_page()
    page.set_default_timeout(15000)
    
    try:
        original_url = \"""" + url + """\"
        
        # Initial navigation
        page.goto(original_url)
        page.wait_for_load_state("networkidle")
        analyze_current_page(page)
        capture_screenshot(page, "Initial page load")
        
        test_cases = """ + test_cases_json + """
        
        for i, test_case in enumerate(test_cases):
            start_test_case(f"Test Case {i+1}", str(test_case.get('description', test_case)))
            
            try:
                # Get test data and steps
                test_data = test_case.get('test_data', {})
                steps = test_case.get('steps', [])
                expected_result = test_case.get('expected_result', '')
                test_type = test_case.get('test_type', 'positive')
                
                # Capture screenshot at start of test case
                capture_screenshot(page, f"Test Case {i+1} - Start ({current_page_state['current_section']})")
                
                # Execute each step intelligently
                all_steps_successful = True
                
                for step_index, step in enumerate(steps):
                    log_action(f"🎯 Step {step_index + 1}", f"{step}")
                    
                    # Execute the step
                    step_success = execute_intelligent_test_step(page, step, test_data)
                    
                    if not step_success:
                        all_steps_successful = False
                        log_action(f"⚠️ Step {step_index + 1} failed", "Continuing with next step")
                    
                    # Handle popups after each step
                    handle_popups(page)
                    
                    # Wait for page to stabilize
                    time.sleep(1)
                    
                    # Re-analyze page state after each step
                    analyze_current_page(page)
                    
                    # Capture screenshot after significant steps
                    if step_index % 2 == 0 or "click" in step.lower():
                        capture_screenshot(page, f"Test Case {i+1} - After step {step_index + 1}")
                
                # Special handling for form filling steps
                if any("form" in step.lower() or "fill" in step.lower() for step in steps):
                    fill_form_intelligently(page, f"Test Case {i+1}")
                
                # Final screenshot and validation
                capture_screenshot(page, f"Test Case {i+1} - Final result")
                
                # Determine test result based on execution success and page state
                if all_steps_successful:
                    if test_type == "positive":
                        complete_test_case("✅ PASSED")
                    else:
                        # For negative tests, check if we're still in error state
                        if current_page_state["current_section"] == "login":
                            complete_test_case("✅ PASSED (Correctly failed)")
                        else:
                            complete_test_case("❌ FAILED (Should have failed)")
                else:
                    complete_test_case("⚠️ PARTIAL (Some steps failed)")
                
            except Exception as e:
                capture_screenshot(page, f"Test Case {i+1} - Error occurred")
                log_action("💥 Test case error", f"❌ {str(e)}")
                complete_test_case("❌ FAILED")
                
                # Don't break the entire test suite, continue with next test case
                continue
                
    except Exception as e:
        log_action("💥 Critical error", f"❌ {str(e)}")
        if current_test_case:
            complete_test_case("❌ FAILED")
    finally:
        # Close the single context and browser
        context.close()
        browser.close()
"""

        return jsonify({"test_script": test_script})

    except Exception as e:
        return jsonify({"error": f"Error generating test script: {str(e)}"}), 500


@app.route("/run_test", methods=["POST"])
def run_test():
    test_script = request.json.get("test_script")

    exec_namespace = {
        "test_case_logs": [],
        "__builtins__": __builtins__,
        "sync_playwright": sync_playwright,
        "time": time,
        "datetime": datetime,
        "base64": base64,
    }

    try:
        exec(test_script, exec_namespace)

        test_case_logs = exec_namespace.get("test_case_logs", [])
        log_entries = []
        all_screenshots = []

        if test_case_logs:
            for test_case in test_case_logs:
                log_entries.append(
                    {
                        "timestamp": datetime.fromtimestamp(
                            test_case.get("start_time", time.time())
                        ).isoformat(),
                        "action": f"🧪 {test_case['test_case']}: {test_case['description']}",
                        "result": test_case.get("result", "Unknown"),
                        "test_case": test_case["test_case"],
                        "type": "test_case_header",
                    }
                )

                for action in test_case.get("actions", []):
                    log_entries.append(
                        {
                            "timestamp": datetime.fromtimestamp(
                                action["timestamp"]
                            ).isoformat(),
                            "action": f"  └─ {action['action']}",
                            "result": action["result"],
                            "test_case": test_case["test_case"],
                            "type": "action",
                        }
                    )

                # Add screenshots to the response
                for screenshot in test_case.get("screenshots", []):
                    all_screenshots.append(
                        {
                            "test_case": test_case["test_case"],
                            "description": screenshot["description"],
                            "timestamp": datetime.fromtimestamp(
                                screenshot["timestamp"]
                            ).isoformat(),
                            "data": screenshot["data"],
                            "counter": screenshot["counter"],
                        }
                    )

            passed_tests = sum(
                1 for tc in test_case_logs if "PASSED" in tc.get("result", "")
            )
            failed_tests = sum(
                1 for tc in test_case_logs if "FAILED" in tc.get("result", "")
            )
            total_tests = len(test_case_logs)

            if failed_tests == 0:
                result = f"✅ All {total_tests} test cases passed!"
            else:
                result = f"⚠️ {passed_tests}/{total_tests} test cases passed, {failed_tests} failed"

            insight = f"Executed {total_tests} test cases. {passed_tests} passed, {failed_tests} failed. Captured {len(all_screenshots)} screenshots."
        else:
            result = "❌ No test cases executed"
            insight = "No test execution logs found"
            log_entries = []
            all_screenshots = []

    except Exception as e:
        result = "❌ Test execution failed"
        insight = f"Error: {str(e)}"
        log_entries = [
            {
                "timestamp": datetime.now().isoformat(),
                "action": "Test execution failed",
                "result": f"❌ {str(e)}",
                "test_case": "System",
                "type": "error",
            }
        ]
        all_screenshots = []

    return jsonify(
        {
            "result": result,
            "insight": insight,
            "log_entries": log_entries,
            "screenshots": all_screenshots,
        }
    )


@app.route("/validate_script", methods=["POST"])
def validate_script():
    """Validate the Python script for syntax and basic safety checks"""
    try:
        data = request.json
        if not data or "test_script" not in data:
            return jsonify({"error": "No script provided"}), 400

        script = data["test_script"]
        warnings: List[str] = []

        # Basic syntax check
        try:
            ast.parse(script)
        except SyntaxError as e:
            return jsonify(
                {"valid": False, "error": f"Syntax error at line {e.lineno}: {str(e)}"}
            )

        # Use astroid for more detailed analysis
        try:
            module = astroid.parse(script)

            # Check for potentially dangerous operations
            for node in module.nodes_of_class(
                (astroid.Delete, astroid.Import, astroid.ImportFrom)
            ):
                if isinstance(node, (astroid.Import, astroid.ImportFrom)):
                    # Check for suspicious imports
                    for name in node.names:
                        if name[0] in ["os", "sys", "subprocess", "shutil"]:
                            warnings.append(
                                f"Warning: Using system module '{name[0]}' - ensure it's necessary"
                            )
                elif isinstance(node, astroid.Delete):
                    warnings.append(
                        "Warning: Found delete operation - ensure it's intended"
                    )

            # Check for file operations
            for node in module.nodes_of_class(astroid.Call):
                if isinstance(node.func, astroid.Attribute):
                    if node.func.attrname in ["remove", "rmdir", "unlink", "delete"]:
                        warnings.append(
                            f"Warning: Found file deletion operation '{node.func.attrname}' - ensure it's intended"
                        )

        except Exception as e:
            warnings.append(f"Static analysis warning: {str(e)}")

        return jsonify({"valid": True, "warnings": warnings})

    except Exception as e:
        return jsonify({"valid": False, "error": str(e)})


@app.route("/ai_script_help", methods=["POST"])
def ai_script_help():
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "No JSON data received"}), 400

        script = data.get("script")
        question = data.get("question")
        error = data.get("error")
        warnings = data.get("warnings", [])
        help_type = data.get("help_type", "general")

        if not script:
            return jsonify({"success": False, "error": "Script is required"}), 400

        # Construct the appropriate prompt based on help_type
        if help_type == "error":
            prompt = f"""
            As a QA automation expert, help fix this Python test script that has an error:
            
            SCRIPT WITH ERROR:
            {script}
            
            ERROR MESSAGE:
            {error}
            
            Please analyze the error and provide:
            1. A clear explanation of what's wrong (in simple terms)
            2. The complete fixed version of the script with the error corrected
            3. Best practices to avoid similar issues
            
            IMPORTANT: 
            - Ensure the fixed script is complete and properly formatted
            - Maintain the original functionality while fixing the syntax
            - Add comments to explain the fixes
            
            Return the response in this JSON format:
            {{
                "explanation": "Clear explanation of the error and how it was fixed",
                "fixed_script": "Complete fixed script with comments",
                "best_practices": [
                    "Specific practice to avoid this error",
                    "General best practice for script writing",
                    "Additional relevant tips"
                ]
            }}
            """
        elif help_type == "warning":
            prompt = f"""
            As a QA automation expert, review this Python test script that has warnings:
            
            SCRIPT:
            {script}
            
            WARNINGS:
            {json.dumps(warnings, indent=2)}
            
            Please provide:
            1. Analysis of each warning
            2. Suggestions to address them
            3. Best practices for safer test automation
            
            Return response as JSON with these keys:
            {{
                "analysis": "Warning analysis",
                "suggestions": ["Suggestion 1", "Suggestion 2"],
                "best_practices": ["Practice 1", "Practice 2"]
            }}
            """
        else:  # general help
            prompt = f"""
            As a QA automation expert, help with this Python test script question:
            
            SCRIPT:
            {script}
            
            QUESTION:
            {question}
            
            Please provide:
            1. A detailed answer to the question
            2. Any relevant suggestions for improvement
            3. Best practices related to the question
            
            Return response as JSON with these keys:
            {{
                "answer": "Detailed answer",
                "suggestions": ["Suggestion 1", "Suggestion 2"],
                "best_practices": ["Practice 1", "Practice 2"]
            }}
            """

        try:
            response = llm.invoke(prompt)

            # Try to parse as JSON first
            try:
                ai_response = json.loads(response.content)
                return jsonify({"success": True, "response": ai_response})
            except json.JSONDecodeError:
                # If not JSON, extract content between code blocks if present
                content = response.content
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.rfind("```")
                    if end > start:
                        content = content[start:end].strip()
                        try:
                            ai_response = json.loads(content)
                            return jsonify({"success": True, "response": ai_response})
                        except:
                            pass

                # If still not JSON, structure the response based on help_type
                if help_type == "error":
                    return jsonify(
                        {
                            "success": True,
                            "response": {
                                "explanation": "Error analysis from AI:",
                                "fixed_script": response.content,
                                "best_practices": [
                                    "Review the suggested fixes and validate the script"
                                ],
                            },
                        }
                    )
                elif help_type == "warning":
                    return jsonify(
                        {
                            "success": True,
                            "response": {
                                "analysis": "Warning analysis from AI:",
                                "suggestions": [response.content],
                                "best_practices": [
                                    "Review the suggestions and validate the script"
                                ],
                            },
                        }
                    )
                else:
                    return jsonify(
                        {
                            "success": True,
                            "response": {
                                "answer": response.content,
                                "suggestions": [],
                                "best_practices": [],
                            },
                        }
                    )

        except Exception as e:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"AI processing error: {str(e)}",
                        "details": traceback.format_exc(),
                    }
                ),
                500,
            )

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Request processing error: {str(e)}",
                    "details": traceback.format_exc(),
                }
            ),
            500,
        )


if __name__ == "__main__":
    app.run(debug=True, port=5001)  # Different port to avoid conflicts