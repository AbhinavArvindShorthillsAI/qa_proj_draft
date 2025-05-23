# import streamlit as st
# import requests

# st.set_page_config(page_title="AI-Powered QA Tool", layout="wide")
# st.title("🧪 AI-Powered Automated Testing Tool")

# # Input URL
# url = st.text_input("Enter Website URL:", "")

# # Upload test case file
# uploaded_file = st.file_uploader("Upload Test Case File (CSV/JSON/TXT)", type=["csv", "json", "txt"])

# if url and uploaded_file:
#     if st.button("🧠 Generate Test Script"):
#         with st.spinner("Generating test script with AI..."):

#             files = {
#                 'test_case_file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
#             }
#             data = {'url': url}

#             response = requests.post(
#                 "http://localhost:5000/generate_test",
#                 data=data,
#                 files=files
#             )

#             if response.status_code == 200:
#                 test_script = response.json()["test_script"]
#                 st.session_state["test_script"] = test_script
#                 st.code(test_script, language="python")
#             else:
#                 st.error(f"Error generating test script: {response.text}")

#     if "test_script" in st.session_state:
#         if st.button("🏃 Run Test"):
#             with st.spinner("Running test..."):
#                 response = requests.post(
#                     "http://localhost:5000/run_test",
#                     json={"test_script": st.session_state["test_script"]}
#                 )

#                 result = response.json()
#                 st.success(result["result"])
#                 st.info("🔍 Insight:")
#                 st.markdown(f"```\n{result['insight']}\n```")
# else:
#     st.warning("Please enter a URL and upload a test case file.")


import streamlit as st
import requests
import pandas as pd
from io import StringIO

st.set_page_config(page_title="AI-Powered QA Tool", layout="wide")
st.title("🧪 AI-Powered Automated Testing Tool")

url = st.text_input("Enter Website URL:", "")
test_case_input_method = st.radio("Choose how to provide test cases:", ("Upload Test Case File", "Manual Test Case Input"))

manual_test_cases = ""
uploaded_file = None

if test_case_input_method == "Upload Test Case File":
    uploaded_file = st.file_uploader("Upload Test Case File (CSV/JSON/TXT)", type=["csv", "json", "txt"])
else:
    manual_test_cases = st.text_area("Enter your test cases (one per line):")

if url and (uploaded_file or manual_test_cases):
    if st.button("🧠 Generate Test Script"):
        with st.spinner("Generating test script with AI..."):
            files = None
            data = {"url": url}

            if uploaded_file:
                files = {
                    'test_case_file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                }
            else:
                files = {
                    'test_case_file': ('manual.txt', manual_test_cases.encode('utf-8'), 'text/plain')
                }

            response = requests.post("http://localhost:5000/generate_test", data=data, files=files)

            if response.status_code == 200:
                test_script = response.json()["test_script"].strip()
                if test_script.startswith("```"):
                    test_script = test_script.strip("`").replace("python", "").strip()

                st.session_state["test_script"] = test_script
                st.code(test_script, language="python")
            else:
                st.error(f"Error generating test script: {response.text}")

    if "test_script" in st.session_state:
        if st.button("🏃 Run Test"):
            with st.spinner("Running test..."):
                response = requests.post("http://localhost:5000/run_test", json={"test_script": st.session_state["test_script"]})

                result = response.json()
                st.success(result["result"])
                st.info("🔍 Insight:")
                st.markdown(f"```\n{result['insight']}\n```")

                if "log_csv" in result:
                    log_csv = result["log_csv"]
                    if log_csv.strip():
                        df = pd.read_csv(StringIO(log_csv))
                        st.subheader("📝 Test Execution Log")
                        st.dataframe(df)
                        st.download_button("⬇️ Download Log", log_csv, "test_log.csv", "text/csv")
                    else:
                        st.info("ℹ️ No log entries were recorded during this test.")
else:
    st.warning("Please enter a URL and provide test cases.")


