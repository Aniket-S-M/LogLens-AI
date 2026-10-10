
import requests
import streamlit as st
import json
from pathlib import Path

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="LogLens AI",
    page_icon="🔎",
    layout="wide",
)

st.title("🔎 LogLens AI")
st.caption("AI-powered log analysis and failure triage")

# Sidebar: backend and model status
with st.sidebar:
    st.header("System status")
    st.write("**Inference:** Local Ollama")
    st.write("**Model:** `phi3:mini`")
    st.write("**Backend:** FastAPI")

    if st.button("Check API health", use_container_width=True):
        try:
            response = requests.get(
                f"{API_URL}/health",
                timeout=5,
            )
            response.raise_for_status()
            health = response.json()
            st.success(f"API online: {health.get('status', 'ok')}")
        except requests.RequestException as exc:
            st.error("API unavailable. Start the FastAPI server.")
            st.caption(str(exc))

st.divider()

# Log input
st.subheader("Submit application logs")

uploaded_file = st.file_uploader(
    "Upload a log file",
    type=["log", "txt"],
)

uploaded_logs = ""
if uploaded_file is not None:
    uploaded_logs = uploaded_file.getvalue().decode(
        "utf-8",
        errors="replace",
    )

logs = st.text_area(
    "Paste logs here",
    value=uploaded_logs,
    height=260,
    placeholder=(
        "2026-10-09 10:00:03 ERROR Database connection failed\n"
        "2026-10-09 10:00:04 ERROR Connection refused"
    ),
)

analyze_clicked = st.button(
    "Analyze logs",
    type="primary",
    use_container_width=True,
)

regression_clicked = st.button(
    "🔁 Group Regression Failures",
    use_container_width=True,
)

if regression_clicked:
    if not logs.strip():
        st.warning("Upload a log file or paste logs first.")
    elif len(logs) > 100_000:
        st.error("Logs exceed the 100,000-character API limit.")
    else:
        try:
            with st.spinner("Grouping repeated failures..."):
                response = requests.post(
                    f"{API_URL}/regression",
                    json={"logs": logs},
                    timeout=15,
                )

            if response.status_code == 200:
                result = response.json()
                groups = result.get("groups", [])

                st.subheader("🔁 Regression Triage")
                col1, col2, col3 = st.columns(3)
                col1.metric("Failure occurrences", result["failure_count"])
                col2.metric("Unique failure groups", result["unique_failure_groups"])
                col3.metric("Parsed log events", result["total_events"])

                if not groups:
                    st.success("No error-level failures detected in the logs.")
                else:
                    st.warning(
                        f"Found {len(groups)} distinct failure group(s). "
                        "Groups are ordered by occurrence count."
                    )

                    for index, group in enumerate(groups, start=1):
                        title = group["signature"]
                        with st.expander(
                            f'{index}. {title} — {group["count"]} occurrence(s)',
                            expanded=(index == 1),
                        ):
                            st.write(f'**Severity:** {group["severity"]}')
                            st.write(f'**First line:** {group["first_line"]}')
                            st.write(
                                "**Affected lines:** "
                                + ", ".join(map(str, group["line_numbers"]))
                            )

                            st.markdown("**Example messages**")
                            for example in group["examples"]:
                                st.code(example, language="text")

            elif response.status_code == 422:
                st.error("Invalid logs submitted.")
                st.code(response.text)
            else:
                st.error(
                    f"Regression triage failed: HTTP {response.status_code}"
                )
                st.code(response.text)

        except requests.Timeout:
            st.error("Regression triage timed out.")
        except requests.RequestException as exc:
            st.error("Could not connect to FastAPI. Is the backend running?")
            st.caption(str(exc))
        except (KeyError, TypeError, ValueError) as exc:
            st.error("The API returned an unexpected response.")
            st.caption(str(exc))


if analyze_clicked:
    if not logs.strip():
        st.warning("Upload a log file or paste logs first.")
    elif len(logs) > 100_000:
        st.error("Logs exceed the 100,000-character API limit.")
    else:
        try:
            with st.spinner(
                "Analyzing logs with local Phi-3... "
                "This may take several seconds."
            ):
                response = requests.post(
                    f"{API_URL}/analyze",
                    json={"logs": logs},
                    timeout=180,
                )

            if response.status_code == 200:
                result = response.json()
                report = result["report"]
                metrics = result["metrics"]
                diagnoses = report["diagnoses"]

                st.success("Analysis completed")

                col1, col2, col3 = st.columns(3)
                col1.metric("Analysis status", report["status"])
                col2.metric("Diagnoses", len(diagnoses))
                col3.metric(
                    "Inference latency",
                    f'{metrics["latency_ms"] / 1000:.2f} s',
                )

                if not diagnoses:
                    st.info(
                        "No diagnosis was returned. "
                        "The logs may not contain sufficient evidence."
                    )

                for index, diagnosis in enumerate(diagnoses, start=1):
                    st.divider()
                    st.subheader(f'{index}. {diagnosis["title"]}')

                    severity = diagnosis["severity"].upper()
                    if severity in {"CRITICAL", "HIGH"}:
                        st.error(f"Severity: {severity}")
                    elif severity == "MEDIUM":
                        st.warning(f"Severity: {severity}")
                    else:
                        st.info(f"Severity: {severity}")

                    st.markdown("**Summary**")
                    st.write(diagnosis["summary"])

                    with st.expander(
                        "Likely cause and uncertainty",
                        expanded=True,
                    ):
                        st.markdown("**Likely cause**")
                        st.write(diagnosis["likely_cause"])

                        st.markdown("**Uncertainty**")
                        st.write(diagnosis["uncertainty"])

                    st.markdown("**Recommended actions**")
                    for action in diagnosis["recommended_actions"]:
                        st.markdown(f"- {action}")

                    st.markdown("**Evidence from logs**")
                    for item in diagnosis["evidence"]:
                        st.code(
                            f'Line {item["line_number"]}: '
                            f'{item["excerpt"]}',
                            language="text",
                        )

                with st.expander("Inference details"):
                    st.json(metrics)

            elif response.status_code == 422:
                st.error("Invalid request. Check the submitted logs.")
                st.code(response.text)

            else:
                st.error(
                    f"Analysis failed with HTTP {response.status_code}"
                )
                st.code(response.text)

        except requests.Timeout:
            st.error(
                "Analysis timed out. Check whether Ollama is running "
                "and try again."
            )
        except requests.RequestException as exc:
            st.error(
                "Could not connect to FastAPI. "
                "Make sure the backend is running."
            )
            st.caption(str(exc))
        except (KeyError, ValueError) as exc:
            st.error("The API returned an unexpected response.")
            st.caption(str(exc))

# Evaluation dashboard
st.divider()
st.header("📊 Model Evaluation")

project_root = Path(__file__).resolve().parent
results_path = project_root / "evaluation" / "results.json"

if not results_path.exists():
    st.info(
        "No evaluation results found. "
        "Run: python evaluation/run_evaluation.py"
    )
else:
    try:
        evaluation = json.loads(
            results_path.read_text(encoding="utf-8")
        )

        total = evaluation.get("total_cases", 0)
        completed = evaluation.get("completed_cases", 0)
        failed = evaluation.get("failed_cases", 0)
        status_rate = evaluation.get("status_match_rate", 0.0)
        keyword_rate = evaluation.get("average_keyword_coverage")
        evidence_rate = evaluation.get("average_evidence_coverage")
        latency = evaluation.get("average_latency_ms")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total cases", total)
        col2.metric("Completed", completed)
        col3.metric("Status agreement", f"{status_rate:.0%}")
        col4.metric(
            "Average latency",
            f"{latency / 1000:.2f} s" if latency is not None else "N/A",
        )

        col5, col6 = st.columns(2)
        col5.metric(
            "Keyword coverage",
            f"{keyword_rate:.0%}" if keyword_rate is not None else "N/A",
        )
        col6.metric(
            "Evidence coverage",
            f"{evidence_rate:.0%}" if evidence_rate is not None else "N/A",
        )

        st.caption(
            f"{failed} evaluation execution error(s). "
            "Coverage metrics use simple text matching."
        )

        rows = []
        for item in evaluation.get("results", []):
            rows.append({
                "Case": item["id"],
                "Category": item["category"],
                "Expected": item["expected_status"],
                "Actual": item["actual_status"],
                "Status match": item["status_match"],
                "Keyword coverage": (
                    f'{item["keyword_coverage"]:.0%}'
                    if item.get("keyword_coverage") is not None
                    else "N/A"
                ),
                "Evidence coverage": (
                    f'{item["evidence_coverage"]:.0%}'
                    if item.get("evidence_coverage") is not None
                    else "N/A"
                ),
                "Latency (s)": round(item["latency_ms"] / 1000, 2),
            })

        st.subheader("Case-by-case results")
        st.dataframe(rows, use_container_width=True, hide_index=True)

        with st.expander("View detailed evaluation JSON"):
            st.json(evaluation)

    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        st.error("Could not load the evaluation results.")
        st.caption(str(exc))

# Historical incident retrieval
st.divider()
st.header("📚 Historical Incident Search")
st.caption(
    "Search documented incidents for similar symptoms, root causes, "
    "and previously recorded resolutions."
)

incident_query = st.text_input(
    "Describe the error or failure",
    placeholder="e.g. Database connection refused",
    key="incident_query",
)

incident_top_k = st.slider(
    "Maximum incidents to retrieve",
    min_value=1,
    max_value=5,
    value=3,
)

if st.button("Search Historical Incidents", type="primary"):
    if not incident_query.strip():
        st.warning("Enter an error message or failure description.")
    else:
        try:
            with st.spinner("Searching historical incidents..."):
                response = requests.post(
                    f"{API_URL}/incidents/search",
                    json={
                        "query": incident_query,
                        "top_k": incident_top_k,
                    },
                    timeout=60,
                )

            if response.status_code == 200:
                result = response.json()
                matches = result.get("matches", [])

                st.metric("Incidents retrieved", result["match_count"])

                if not matches:
                    st.info("No historical incidents were found.")
                else:
                    for index, incident in enumerate(matches, start=1):
                        distance = incident["distance"]

                        with st.expander(
                            f'{index}. {incident["title"]} '
                            f'({incident["id"]})',
                            expanded=(index == 1),
                        ):
                            st.write(f'**Category:** {incident["category"]}')
                            st.write(f'**Symptoms:** {incident["symptoms"]}')
                            st.write(f'**Possible root cause:** {incident["root_cause"]}')
                            st.write(f'**Documented resolution:** {incident["resolution"]}')
                            st.caption(f'Source: {incident["source"]}')
                            st.caption(
                                f"Cosine distance: {distance:.4f} "
                                "(lower indicates a closer match)"
                            )

            else:
                st.error(
                    f"Incident search failed: HTTP {response.status_code}"
                )
                st.code(response.text)

        except requests.Timeout:
            st.error(
                "Incident search timed out. Check the API and embedding model."
            )
        except requests.RequestException as exc:
            st.error("Could not connect to FastAPI.")
            st.caption(str(exc))
        except (KeyError, TypeError, ValueError) as exc:
            st.error("The API returned an unexpected response.")
            st.caption(str(exc))
