import streamlit as st
import requests
import pandas as pd
import json
from io import StringIO
import streamlit.components.v1 as components


st.set_page_config(page_title="🧪 AI-Powered QA Tool (Enhanced)", layout="wide")
st.title("🧪 AI-Powered Automated Testing Tool (Enhanced)")

# Sidebar instructions
with st.sidebar:
    st.header("Instructions")
    st.markdown(
        """
    1. Enter the Website URL
    2. Choose how you want to provide test cases:
       - Upload CSV/JSON/TXT
       - Type manually
       - Let AI generate based on prompt
    3. Generate and run test script
    4. View & download results
    """
    )

    st.markdown("---")
    st.info(
        "💡 **Enhanced Features:**\n- Better parsing of manual test cases\n- Smart test data extraction\n- Improved CSV handling\n- Test steps execution"
    )

# Use port 5001 for enhanced backend
BACKEND_URL = "http://localhost:5001"

# Step 1: Input URL
url = st.text_input("🌐 Enter Website URL:", "")

if not url:
    st.warning("Please enter a URL to proceed.")
else:
    test_case_input_method = st.radio(
        "Choose how to provide test cases:",
        (
            "Upload Test Case File",
            "Manual Test Case Input",
            "Let AI Generate Test Cases",
        ),
    )

    uploaded_file = None
    manual_test_cases = ""
    ai_prompt = ""

    if test_case_input_method == "Upload Test Case File":
        uploaded_file = st.file_uploader(
            "📁 Upload Test Case File (CSV/JSON/TXT)", type=["csv", "json", "txt"]
        )

        # Show file preview and format guide
        with st.expander("📖 File Format Guide"):
            st.markdown(
                """
            **CSV Format:**
            ```
            description,steps,test_data,expected_result,test_type
            "Login with valid credentials","Enter username;Enter password;Click login","{""username"":""john"",""password"":""pass123""}","User logged in successfully","positive"
            ```
            
            **JSON Format:**
            ```json
            [
              {
                "description": "Login with valid credentials",
                "steps": ["Enter username", "Enter password", "Click login"],
                "test_data": {"username": "john", "password": "pass123"},
                "expected_result": "User logged in successfully",
                "test_type": "positive"
              }
            ]
            ```
            
            **TXT Format:**
            ```
            Test: Login with valid credentials
            Username: john
            Password: pass123
            Expected: Success
            ```
            """
            )

    elif test_case_input_method == "Manual Test Case Input":
        st.info("💡 **Tip:** Our AI will help structure your test cases!")
        manual_test_cases = st.text_area(
            "📝 Enter your test cases:",
            placeholder="""Example formats:

Simple format:
Login with username "john" and password "pass123"
Try login with empty fields
Test SQL injection in login form

Detailed format:
Test: Login with valid credentials
Steps: 
1. Enter username "john"
2. Enter password "pass123"
3. Click login button
Expected: User should be logged in

Or any other format - our AI will understand!""",
            height=300,
        )
    else:
        ai_prompt = st.text_area("🧠 Describe what you want to test:")

    # Add browser visibility toggle here
    st.markdown("---")
    st.subheader("⚙️ Test Execution Settings")
    show_browser = st.checkbox(
        "👁️ Show browser during test execution",
        value=False,
        help="Enable this to see the browser window during test execution. Useful for debugging and demonstrations.",
    )
    
    browser_size_options = ["Small (800x600)", "Medium (1024x768)", "Large (1280x720)"]
    if show_browser:
        browser_size = st.selectbox(
            "🖥️ Browser window size",
            browser_size_options,
            index=0, # Default to Small
            help="Select the desired browser window size for visible tests."
        )
        st.info(
            f"🖥️ Browser window will be visible during test execution with size: {browser_size.split(' (')[0]}."
        )
    else:
        # Default to small if browser is not shown, though it won't be used by Playwright in headless.
        # This ensures browser_size is always defined.
        browser_size = browser_size_options[0] 
        st.info("🚀 Tests will run in headless mode (faster, no visible browser).")

    # Step 2: Generate Test Cases (if AI selected)
    if (
        test_case_input_method == "Let AI Generate Test Cases"
        and ai_prompt
        and st.button("🧠 Generate Test Cases")
    ):
        with st.spinner("Generating test cases with AI..."):
            res = requests.post(
                f"{BACKEND_URL}/generate_test_cases",
                json={"prompt": ai_prompt, "url": url},
            )
            if res.status_code == 200:
                test_cases = res.json()["test_cases"]
                st.session_state["ai_generated_test_cases"] = test_cases
                st.success("✅ Test cases generated successfully!")

                # Display generated test cases in a nice format
                st.subheader("📋 Generated Test Cases:")
                for i, test_case in enumerate(test_cases, 1):
                    with st.expander(
                        f"Test Case {i}: {test_case.get('description', 'Unnamed Test')}"
                    ):
                        st.write("**Steps:**")
                        for step in test_case.get("steps", []):
                            st.write(f"• {step}")

                        if test_case.get("test_data"):
                            st.write("**Test Data:**")
                            st.json(test_case.get("test_data"))

                        st.write(
                            f"**Expected Result:** {test_case.get('expected_result', 'Not specified')}"
                        )
                        st.write(
                            f"**Type:** {test_case.get('test_type', 'Not specified')}"
                        )
                        st.write(
                            f"**Priority:** {test_case.get('priority', 'Not specified')}"
                        )

                # Option to download test cases as JSON
                test_cases_json = json.dumps(test_cases, indent=2)
                st.download_button(
                    "⬇️ Download Test Cases (JSON)",
                    test_cases_json,
                    "generated_test_cases.json",
                    "application/json",
                )
            else:
                # Better error handling for generate test cases
                try:
                    error_data = res.json()
                    st.error(f"Error: {error_data.get('error', 'Unknown error')}")
                    if "raw_response" in error_data:
                        with st.expander("Raw AI Response"):
                            st.code(error_data["raw_response"], language="text")
                except requests.exceptions.JSONDecodeError:
                    st.error(f"Backend Error (Status {res.status_code})")
                    st.error(
                        "The backend returned a non-JSON response. This usually means there's a server error."
                    )
                    with st.expander("Raw Response"):
                        st.code(res.text, language="text")
                except Exception as e:
                    st.error(f"Failed to parse error response: {str(e)}")
                    with st.expander("Raw Response"):
                        st.code(res.text, language="text")

    # Step 3: Generate Test Script
    # Check if we have test cases ready (from any method)
    can_generate_script = False

    if test_case_input_method == "Upload Test Case File" and uploaded_file:
        can_generate_script = True
    elif (
        test_case_input_method == "Manual Test Case Input" and manual_test_cases.strip()
    ):
        can_generate_script = True
    elif (
        test_case_input_method == "Let AI Generate Test Cases"
        and "ai_generated_test_cases" in st.session_state
    ):
        can_generate_script = True

    # Modify the Generate Test Script section to include the browser visibility setting
    if can_generate_script and st.button("🧠 Generate Test Script"):
        with st.spinner("Generating test script with AI..."):

            # Handle AI-generated test cases differently
            if test_case_input_method == "Let AI Generate Test Cases":
                # Convert AI test cases to JSON and send as file
                test_cases_json = json.dumps(
                    st.session_state["ai_generated_test_cases"], indent=2
                )
                files = {
                    "test_case_file": (
                        "ai_generated_test_cases.json",
                        test_cases_json.encode("utf-8"),
                        "application/json",
                    )
                }
                data = {
                    "url": url,
                    "show_browser": str(show_browser),
                    "browser_size": browser_size
                }  # Add show_browser
            else:
                # Handle uploaded file or manual input
                if test_case_input_method == "Upload Test Case File":
                    files = {
                        "test_case_file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type,
                        )
                    }
                else:  # Manual Test Case Input
                    files = {
                        "test_case_file": (
                            "manual.txt",
                            manual_test_cases.encode("utf-8"),
                            "text/plain",
                        )
                    }
                data = {
                    "url": url,
                    "show_browser": str(show_browser),
                    "browser_size": browser_size
                }  # Add show_browser

            res = requests.post(
                f"{BACKEND_URL}/generate_test_script", data=data, files=files
            )
            if res.status_code == 200:
                test_script = res.json()["test_script"]
                st.session_state["test_script"] = test_script
                st.session_state["original_test_script"] = (
                    test_script  # Store original right away
                )
                st.success("✅ Test script generated successfully!")
                st.subheader("🐍 Generated Test Script:")
                st.code(test_script, language="python")
                st.download_button(
                    "⬇️ Download Test Script",
                    test_script,
                    "test_script.py",
                    "text/plain",
                )
            else:
                # Better error handling for generate test script
                try:
                    error_data = res.json()
                    st.error(f"Error: {error_data.get('error', 'Unknown error')}")
                    if "traceback" in error_data:
                        with st.expander("Error Details"):
                            st.code(error_data["traceback"], language="text")
                except requests.exceptions.JSONDecodeError:
                    st.error(f"Backend Error (Status {res.status_code})")
                    st.error(
                        "The backend returned a non-JSON response. This usually means there's a server error."
                    )
                    with st.expander("Raw Response"):
                        st.code(res.text, language="text")
                except Exception as e:
                    st.error(f"Failed to parse error response: {str(e)}")
                    with st.expander("Raw Response"):
                        st.code(res.text, language="text")

    # Add this after the test script generation section, before the Run Test section:
    if "test_script" in st.session_state:
        st.subheader("🐍 Generated Test Script:")

        # Add edit functionality with a container for better organization
        with st.container():
            # Show the current script in a text area
            edited_script = st.text_area(
                "Edit Test Script",
                value=st.session_state["test_script"],
                height=500,
                key="script_editor",
                help="Edit your test script here. Click 'Save Changes' to update.",
            )

            # Create two columns for actions
            col1, col2 = st.columns(2)

            with col1:
                # Save and Validate combined
                if st.button("💾 Save & Validate Changes", type="primary"):
                    # Update the script in session state
                    st.session_state["test_script"] = edited_script

                    # Validate the updated script
                    try:
                        validation_response = requests.post(
                            f"{BACKEND_URL}/validate_script",
                            json={"test_script": edited_script},
                        )

                        if validation_response.status_code == 200:
                            validation_result = validation_response.json()
                            if validation_result["valid"]:
                                st.success(
                                    "✅ Changes saved and script validated successfully!"
                                )
                                if validation_result.get("warnings"):
                                    with st.expander("⚠️ Validation Warnings"):
                                        for warning in validation_result["warnings"]:
                                            st.warning(warning)
                                    if st.button("🤖 Get AI Help with Warnings"):
                                        with st.spinner("Getting AI suggestions..."):
                                            ai_response = requests.post(
                                                f"{BACKEND_URL}/ai_script_help",
                                                json={
                                                    "script": edited_script,
                                                    "warnings": validation_result[
                                                        "warnings"
                                                    ],
                                                    "help_type": "warning",
                                                },
                                            )

                                            if ai_response.ok:
                                                response_data = ai_response.json()[
                                                    "response"
                                                ]
                                                st.info("🤖 AI Analysis:")

                                                for analysis in response_data.get(
                                                    "warning_analysis", []
                                                ):
                                                    st.markdown(
                                                        f"**Analysis:** {analysis}"
                                                    )

                                                with st.expander(
                                                    "💡 Improvement Suggestions"
                                                ):
                                                    for suggestion in response_data.get(
                                                        "suggestions", []
                                                    ):
                                                        st.markdown(f"• {suggestion}")

                                                if response_data.get("code_snippets"):
                                                    with st.expander(
                                                        "📝 Code Improvements"
                                                    ):
                                                        for snippet in response_data[
                                                            "code_snippets"
                                                        ]:
                                                            st.code(
                                                                snippet,
                                                                language="python",
                                                            )
                            else:
                                st.error("❌ Script validation failed:")
                                with st.expander("Show Validation Error"):
                                    st.code(
                                        validation_result["error"], language="python"
                                    )

                                # Add AI assistance for validation errors
                                if st.button("🔄 Let AI Fix Script"):
                                    with st.spinner(
                                        "AI is analyzing and fixing the script..."
                                    ):
                                        ai_response = requests.post(
                                            f"{BACKEND_URL}/ai_script_help",
                                            json={
                                                "script": edited_script,
                                                "error": validation_result["error"],
                                                "help_type": "error",
                                            },
                                        )

                                        if ai_response.status_code == 200:
                                            try:
                                                response_data = ai_response.json()
                                                if response_data.get("success"):
                                                    response_content = response_data[
                                                        "response"
                                                    ]

                                                    # Show explanation
                                                    if (
                                                        "explanation"
                                                        in response_content
                                                    ):
                                                        st.markdown(
                                                            "### 🔍 Error Analysis"
                                                        )
                                                        st.markdown(
                                                            response_content[
                                                                "explanation"
                                                            ]
                                                        )

                                                    # Show and apply fixed script if available
                                                    if (
                                                        "fixed_script"
                                                        in response_content
                                                    ):
                                                        st.markdown(
                                                            "### ✅ Fixed Script"
                                                        )
                                                        st.code(
                                                            response_content[
                                                                "fixed_script"
                                                            ],
                                                            language="python",
                                                        )
                                                        if st.button("Apply AI Fixes"):
                                                            st.session_state[
                                                                "script_editor"
                                                            ] = response_content[
                                                                "fixed_script"
                                                            ]
                                                            st.success(
                                                                "✅ AI fixes applied! Please validate again."
                                                            )
                                                            st.rerun()

                                                    # Show best practices
                                                    if response_content.get(
                                                        "best_practices"
                                                    ):
                                                        with st.expander(
                                                            "📚 Best Practices"
                                                        ):
                                                            for (
                                                                practice
                                                            ) in response_content[
                                                                "best_practices"
                                                            ]:
                                                                st.markdown(
                                                                    f"• {practice}"
                                                                )
                                                else:
                                                    st.error(
                                                        f"AI Error: {response_data.get('error', 'Unknown error')}"
                                                    )
                                                    if response_data.get("details"):
                                                        with st.expander(
                                                            "Error Details"
                                                        ):
                                                            st.code(
                                                                response_data["details"]
                                                            )
                                            except Exception as e:
                                                st.error(
                                                    f"Error processing AI response: {str(e)}"
                                                )
                                                with st.expander("Raw Response"):
                                                    st.code(ai_response.text)
                                        else:
                                            st.error(
                                                f"Failed to get AI help (Status {ai_response.status_code}). Please try again."
                                            )
                                            with st.expander("Response Details"):
                                                st.code(ai_response.text)
                        else:
                            st.error("Failed to validate script")
                    except Exception as e:
                        st.error(f"Validation error: {str(e)}")

            with col2:
                # Enhanced download options
                download_col1, download_col2 = st.columns(2)
                with download_col1:
                    st.download_button(
                        "⬇️ Download Script (Python)",
                        edited_script,
                        "test_script.py",
                        "text/plain",
                        help="Download the current script as a Python file",
                    )
                with download_col2:
                    st.download_button(
                        "⬇️ Download Script (Text)",
                        edited_script,
                        "test_script.txt",
                        "text/plain",
                        help="Download the current script as a text file",
                    )

            # Add AI Assistant for script questions
            with st.expander("🤖 AI Script Assistant"):
                # Add tabs for different types of assistance
                assist_tab1, assist_tab2 = st.tabs(["Ask Question", "Analyze Error"])

                with assist_tab1:
                    script_question = st.text_area(
                        "Ask a question about the script or request improvements:",
                        placeholder="Example: How can I modify this script to add more detailed logging?",
                        key="script_question",
                    )
                    if script_question and st.button(
                        "Get AI Help", key="question_help"
                    ):
                        with st.spinner("AI is analyzing your question..."):
                            ai_response = requests.post(
                                f"{BACKEND_URL}/ai_script_help",
                                json={
                                    "script": edited_script,
                                    "question": script_question,
                                    "help_type": "general",
                                },
                            )

                            if ai_response.status_code == 200:
                                response_data = ai_response.json()
                                if response_data.get("success"):
                                    response_content = response_data["response"]

                                    # Show response in tabs
                                    result_tab1, result_tab2, result_tab3 = st.tabs(
                                        ["Answer", "Suggestions", "Best Practices"]
                                    )

                                    with result_tab1:
                                        if "answer" in response_content:
                                            st.markdown("### 💡 Answer")
                                            st.markdown(response_content["answer"])
                                        elif "explanation" in response_content:
                                            st.markdown("### 💡 Explanation")
                                            st.markdown(response_content["explanation"])

                                    with result_tab2:
                                        if response_content.get("suggestions"):
                                            st.markdown("### 📝 Suggestions")
                                            for suggestion in response_content[
                                                "suggestions"
                                            ]:
                                                st.markdown(f"• {suggestion}")

                                    with result_tab3:
                                        if response_content.get("best_practices"):
                                            st.markdown("### 📚 Best Practices")
                                            for practice in response_content[
                                                "best_practices"
                                            ]:
                                                st.markdown(f"• {practice}")
                                else:
                                    st.error(
                                        f"AI Error: {response_data.get('error', 'Unknown error')}"
                                    )
                            else:
                                st.error("Failed to get AI help. Please try again.")

                with assist_tab2:
                    st.info("💡 Use this tab to analyze and fix script errors")
                    if st.button("🔍 Analyze Current Script", key="analyze_script"):
                        with st.spinner("AI is analyzing the script..."):
                            # First validate the script
                            validation_response = requests.post(
                                f"{BACKEND_URL}/validate_script",
                                json={"test_script": edited_script},
                            )

                            if validation_response.status_code == 200:
                                validation_result = validation_response.json()
                                if not validation_result["valid"]:
                                    # If validation fails, send for AI analysis
                                    ai_response = requests.post(
                                        f"{BACKEND_URL}/ai_script_help",
                                        json={
                                            "script": edited_script,
                                            "error": validation_result.get(
                                                "error", "Unknown error"
                                            ),
                                            "help_type": "error",
                                        },
                                    )

                                    if ai_response.status_code == 200:
                                        response_data = ai_response.json()
                                        if response_data.get("success"):
                                            response_content = response_data["response"]

                                            # Show error analysis
                                            st.error("🔍 Script has errors:")
                                            if "explanation" in response_content:
                                                st.markdown("### Error Analysis")
                                                st.markdown(
                                                    response_content["explanation"]
                                                )

                                            # Show fixed script if available
                                            if "fixed_script" in response_content:
                                                st.markdown("### ✅ Suggested Fix")
                                                st.code(
                                                    response_content["fixed_script"],
                                                    language="python",
                                                )
                                                if st.button("Apply Fix"):
                                                    st.session_state[
                                                        "script_editor"
                                                    ] = response_content["fixed_script"]
                                                    st.success(
                                                        "✅ Fix applied! Please validate the script again."
                                                    )
                                                    st.rerun()
                                        else:
                                            st.error(
                                                f"AI Error: {response_data.get('error', 'Unknown error')}"
                                            )
                                else:
                                    st.success("✅ Script looks good! No errors found.")
                                    if validation_result.get("warnings"):
                                        st.warning(
                                            "⚠️ However, there are some warnings to consider:"
                                        )
                                        for warning in validation_result["warnings"]:
                                            st.markdown(f"• {warning}")
                            else:
                                st.error("Failed to validate script. Please try again.")

            # Script Information
            with st.expander("ℹ️ Script Information"):
                st.info(
                    """
                    **Current Script Details:**
                    - Length: {} lines
                    - Size: {} bytes
                    - Contains browser visibility setting: {}
                    """.format(
                        len(edited_script.split("\n")),
                        len(edited_script.encode("utf-8")),
                        "show_browser" in edited_script,
                    )
                )

    # Step 4: Run Test
    if "test_script" in st.session_state and st.button("🚀 Run Test"):
        with st.spinner("Running test script..."):
            res = requests.post(
                f"{BACKEND_URL}/run_test",
                json={"test_script": st.session_state["test_script"]},
            )
            if res.status_code == 200:
                result = res.json()
                st.success(result["result"])
                st.info("🔍 Insight:")
                st.markdown(f"```\n{result['insight']}\n```")

                if "log_entries" in result:
                    st.subheader("📝 Test Execution Log (Structured by Test Cases)")

                    # Convert to DataFrame
                    log_df = pd.DataFrame(result["log_entries"])

                    # Apply styling to make test case headers stand out
                    def style_log_row(row):
                        if row.get("type") == "test_case_header":
                            # Dark blue background with white text for test case headers
                            return [
                                "background-color: #1e3a8a; color: white; font-weight: bold"
                            ] * len(row)
                        elif row.get("type") == "action":
                            # Light gray background for action rows
                            return ["background-color: #f3f4f6; color: #374151"] * len(
                                row
                            )
                        else:
                            # Default style for other rows
                            return [""] * len(row)

                    # Display columns in specific order
                    columns_to_display = ["timestamp", "action", "result"]
                    styled_df = log_df[columns_to_display].style.apply(
                        style_log_row, axis=1
                    )
                    st.dataframe(styled_df, use_container_width=True)

                    # Group logs by test case for summary
                    test_summary = {}
                    current_test = None
                    for _, row in log_df.iterrows():
                        if row["type"] == "test_case_header":
                            current_test = row["test_case"]
                            test_summary[current_test] = {
                                "description": row["action"],
                                "result": row["result"],
                                "actions": [],
                            }
                        elif current_test and row["type"] == "action":
                            test_summary[current_test]["actions"].append(
                                {"action": row["action"], "result": row["result"]}
                            )

                    # Show test summary
                    st.subheader("📊 Test Summary")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Tests", len(test_summary))
                    with col2:
                        passed = sum(
                            1 for t in test_summary.values() if "PASSED" in t["result"]
                        )
                        st.metric("Passed", passed)
                    with col3:
                        failed = sum(
                            1 for t in test_summary.values() if "FAILED" in t["result"]
                        )
                        st.metric("Failed", failed)

                    # Download options
                    csv = log_df.to_csv(index=False)
                    st.download_button(
                        "📥 Download Detailed Log (CSV)",
                        csv,
                        "test_execution_log.csv",
                        "text/csv",
                    )

                    # JSON download with full details
                    json_log = json.dumps(result, indent=2)
                    st.download_button(
                        "📥 Download Full Results (JSON)",
                        json_log,
                        "test_results.json",
                        "application/json",
                    )

                # Display screenshots if available
                if "screenshots" in result and result["screenshots"]:
                    st.subheader(
                        f"📸 Test Case Screenshots ({len(result['screenshots'])} images)"
                    )

                    # Group screenshots by test case
                    screenshots_by_test = {}
                    for screenshot in result["screenshots"]:
                        test_case = screenshot["test_case"]
                        if test_case not in screenshots_by_test:
                            screenshots_by_test[test_case] = []
                        screenshots_by_test[test_case].append(screenshot)

                    # Display screenshots for each test case
                    for test_case, screenshots in screenshots_by_test.items():
                        with st.expander(
                            f"📸 {test_case} Screenshots ({len(screenshots)} images)"
                        ):
                            cols = st.columns(2)
                            for i, screenshot in enumerate(screenshots):
                                with cols[i % 2]:
                                    st.image(
                                        screenshot["data"],
                                        caption=f"{screenshot['description']}\n{screenshot['timestamp']}",
                                        use_column_width=True,
                                    )

            else:
                st.error("Failed to run test. Please check your backend server.")

    # Show current progress
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔄 Progress")

    progress_items = []
    if url:
        progress_items.append("✅ URL provided")

    if test_case_input_method == "Let AI Generate Test Cases":
        if "ai_generated_test_cases" in st.session_state:
            progress_items.append("✅ Test cases generated")
        elif ai_prompt:
            progress_items.append("⏳ Ready to generate test cases")
    elif test_case_input_method == "Upload Test Case File":
        if uploaded_file:
            progress_items.append("✅ File uploaded")
    elif test_case_input_method == "Manual Test Case Input":
        if manual_test_cases.strip():
            progress_items.append("✅ Manual test cases provided")

    if "test_script" in st.session_state:
        progress_items.append("✅ Test script generated")

    for item in progress_items:
        st.sidebar.markdown(item)

# Footer
st.markdown("---")
st.markdown(
    "🚀 **Enhanced AI-Powered Testing Tool** - Now with better test case parsing and execution!"
)