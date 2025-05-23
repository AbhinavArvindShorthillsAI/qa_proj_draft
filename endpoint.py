# from flask import Flask, request, jsonify
# from playwright.sync_api import sync_playwright
# from langchain_google_genai import ChatGoogleGenerativeAI
# import os
# from dotenv import load_dotenv
# import pandas as pd
# import json
# import tempfile
# import traceback

# load_dotenv()

# app = Flask(__name__)

# llm = ChatGoogleGenerativeAI(
#     model="gemini-2.0-flash",
#     temperature=0.2,
#     google_api_key=os.getenv("API_KEY")
# )

# @app.route('/generate_test', methods=['POST'])
# def generate_test():
#     url = request.form.get('url')
#     test_file = request.files['test_case_file']

#     # Read raw content
#     file_content = test_file.read().decode('utf-8')

#     # Parse based on file type
#     if test_file.mimetype == 'text/csv':
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmpfile:
#             tmpfile.write(file_content.encode())
#             tmpfile_path = tmpfile.name
#         test_cases = pd.read_csv(tmpfile_path).to_dict(orient='records')
#     elif test_file.mimetype == 'application/json':
#         test_cases = json.loads(file_content)
#     else:  # plain text or other
#         test_cases = [line.strip() for line in file_content.splitlines() if line.strip()]

#     # Get DOM
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=True)
#         page = browser.new_page()
#         page.goto(url)
#         html_dom = page.content()
#         browser.close()

#     # Prompt Gemini
#     prompt = f"""
# You're an expert QA automation engineer.

# Generate a Python Playwright test script based on the given context.
# Return ONLY raw Python code. Do NOT wrap it in markdown or code blocks.

# URL: {url}
# Test Data: {test_cases[:2]}
# HTML DOM (first 4000 chars): {html_dom[:4000]}

# Script should:
# 1. Navigate to the URL
# 2. Fill inputs using test data
# 3. Click buttons
# 4. Assert expected outcomes

# Make sure the selectors match the DOM provided.


# Example structure:
# from playwright.sync_api import sync_playwright

# with sync_playwright() as p:
#     browser = p.chromium.launch(headless=True)
#     page = browser.new_page()
#     ...
#     browser.close()
# """

#     response = llm.invoke(prompt)
#     test_script = response.content.strip()
#     return jsonify({"test_script": test_script})


# @app.route('/run_test', methods=['POST'])
# def run_test():
#     test_script = request.json.get('test_script')

#     try:
#         exec_namespace = {}
#         exec(test_script, exec_namespace)
#         result = "✅ Test passed!"
#         insight = "The test ran successfully without any exceptions."
#     except Exception as e:
#         result = "❌ Test failed"
#         insight = f"Error during test execution: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"

#     return jsonify({
#         "result": result,
#         "insight": insight
#     })


# if __name__ == "__main__":
#     app.run(debug=True)


from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
import pandas as pd
import json
import tempfile
from datetime import datetime
from io import StringIO
import traceback

load_dotenv()
app = Flask(__name__)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.2,
    google_api_key=os.getenv("API_KEY")
)

@app.route('/generate_test', methods=['POST'])
def generate_test():
    url = request.form.get('url')
    test_file = request.files['test_case_file']
    file_content = test_file.read().decode('utf-8')

    if test_file.mimetype == 'text/csv':
        test_cases = pd.read_csv(StringIO(file_content)).to_dict(orient='records')
    elif test_file.mimetype == 'application/json':
        test_cases = json.loads(file_content)
    else:
        test_cases = [line.strip() for line in file_content.splitlines() if line.strip()]

    # Get DOM
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        html_dom = page.content()
        browser.close()

    # Strict prompt that enforces logging
    prompt = f"""
You are a senior QA automation engineer. Write a Python Playwright test script using the following constraints:

- DOM (truncated): {html_dom[:4000]}
- URL: {url}
- Test Case Data: {test_cases[:2]}

INSTRUCTIONS:
1. Start the script with: `log_entries = []`
2. For every action (e.g., go to page, click, fill, assert), append to `log_entries`:
   log_entries.append({{"timestamp": "<timestamp>", "action": "What happened", "result": "OK/Failed"}})
3. Do NOT wrap code in markdown (no ```).
4. Script should run standalone with Playwright in headless mode.
5. Use selectors from the DOM.

Return only the raw Python code.
"""

    response = llm.invoke(prompt)
    test_script = response.content.strip()

    # Remove markdown code formatting if present
    if test_script.startswith("```"):
        test_script = test_script.strip("`").replace("python", "").strip()

    return jsonify({"test_script": test_script})


@app.route('/run_test', methods=['POST'])
def run_test():
    test_script = request.json.get('test_script')
    exec_namespace = {"log_entries": []}
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        exec(test_script, exec_namespace)
        result = "✅ Test passed!"
        insight = "Test completed without any exception."
    except Exception as e:
        result = "❌ Test failed"
        insight = f"Error during test execution: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        exec_namespace["log_entries"].append({
            "timestamp": timestamp,
            "action": "Test execution failed",
            "result": str(e)
        })

    # Fallback log if script forgot to log
    if not exec_namespace.get("log_entries"):
        exec_namespace["log_entries"] = [{
            "timestamp": timestamp,
            "action": "Test completed",
            "result": "✅ But no log was generated by the script"
        }]

    log_df = pd.DataFrame(exec_namespace["log_entries"])
    log_csv = log_df.to_csv(index=False)

    return jsonify({
        "result": result,
        "insight": insight,
        "log_csv": log_csv
    })


if __name__ == "__main__":
    app.run(debug=True)


