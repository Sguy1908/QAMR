"""Research dashboard: background execution, cooperative cancellation, saved artifacts."""

import io
import sys
import threading
import zipfile
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qamr_sim.config import Config
from qamr_sim.experiments.runner import run_one
from qamr_sim.io.export import load_run

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="QAMR research reconstruction", layout="wide")
st.title("QAMR · research reconstruction")
st.caption("Discrete-event observations • explicit model assumptions • no exact-reproduction claim")
st.warning(
    "Formal r-robustness is unverified. Disjoint paths and vertex connectivity are reported separately."
)

with st.sidebar:
    st.header("Configure and run")
    preset = st.selectbox(
        "Configuration",
        sorted(
            str(p.relative_to(ROOT))
            for p in (ROOT / "configs").glob("*.yaml")
            if "validation" not in p.name
        ),
    )
    text = st.text_area("YAML (SI units)", (ROOT / preset).read_text(), height=330, key=preset)
    try:
        config = Config.model_validate(yaml.safe_load(text))
        st.info(f"{config.profile} | {config.policy} | {config.event_fidelity_model}")
        st.caption(
            f"Service rate {config.mu:.3f}/s · traffic convention: {config.traffic_convention}"
        )
    except Exception as exc:
        config = None
        st.error(str(exc))
    job = st.session_state.get("job")
    running = job is not None and job["thread"].is_alive()
    if st.button("Run simulation", disabled=config is None or running):
        job = {"progress": 0.0, "stop": threading.Event(), "path": None, "error": None}

        def worker(cfg, state):
            try:
                state["path"] = str(
                    run_one(
                        cfg,
                        ROOT / "results/dashboard",
                        resume=False,
                        progress=lambda fraction: state.update(progress=fraction),
                        cancelled=state["stop"].is_set,
                    )
                )
            except Exception as exc:
                state["error"] = str(exc)

        job["thread"] = threading.Thread(target=worker, args=(config, job), daemon=True)
        st.session_state["job"] = job
        job["thread"].start()
        st.rerun()
    if st.button("Cancel active run", disabled=not running):
        job["stop"].set()
    if job:
        st.progress(job["progress"])
        if job["error"]:
            st.error(job["error"])
        if job["path"]:
            st.success("Saved " + job["path"])
    st.button("Refresh progress and saved runs")


@st.fragment(run_every="2s")
def progress_panel():
    state = st.session_state.get("job")
    if state and state["thread"].is_alive():
        st.progress(
            state["progress"],
            text="Simulation running; cancellation checked at simulation-time checkpoints",
        )


progress_panel()

tabs = st.tabs(["Assumptions", "Saved results", "Comparisons and sensitivity"])
with tabs[0]:
    st.markdown((ROOT / "docs/assumptions.md").read_text())
    if config:
        st.download_button(
            "Download resolved configuration",
            yaml.safe_dump(config.model_dump(mode="json")),
            file_name="resolved_config.yaml",
        )
with tabs[1]:
    paths = (
        sorted(p.parent for p in (ROOT / "results").rglob("summary.json"))
        if (ROOT / "results").exists()
        else []
    )
    if not paths:
        st.info("Run a simulation to display measured outputs.")
    else:
        chosen = st.selectbox("Saved run", paths, format_func=lambda p: str(p.relative_to(ROOT)))
        run = load_run(chosen)
        summary = run["summary"]
        st.subheader(f"{run['config']['profile']} / {run['config']['policy']}")
        columns = st.columns(4)
        for col, key, label in zip(
            columns,
            ["throughput", "mean_fidelity", "mean_queue_wait", "offered"],
            ["Pairs/s", "Delivered fidelity", "Queue wait (s)", "Offered requests"],
        ):
            value = summary[key]
            col.metric(label, "Undefined" if value is None else f"{value:.4g}")
        st.caption(
            f"{summary['measurement_seconds']} measurement seconds; {summary['delivered_measurement']} delivered samples. Completed-arrival cohort CDFs are censored."
        )
        sections = st.tabs(
            [
                "Topology",
                "Queues and memory",
                "CDFs",
                "Request trace",
                "Analytical comparison",
                "Report and downloads",
            ]
        )
        with sections[0]:
            graph = nx.node_link_graph(run["topology"])
            positions = nx.get_node_attributes(graph, "pos") or nx.spring_layout(graph, seed=0)
            figure = go.Figure()
            xs, ys = [], []
            for u, v in graph.edges:
                xs += [positions[u][0], positions[v][0], None]
                ys += [positions[u][1], positions[v][1], None]
            figure.add_trace(
                go.Scatter(
                    x=xs, y=ys, mode="lines", line=dict(color="#a0a8b4", width=1), hoverinfo="skip"
                )
            )
            figure.add_trace(
                go.Scatter(
                    x=[positions[n][0] for n in graph],
                    y=[positions[n][1] for n in graph],
                    text=[str(n) for n in graph],
                    mode="markers+text",
                    textposition="top center",
                    marker=dict(size=9),
                )
            )
            st.plotly_chart(figure, width="stretch")
            st.json(run["topology"].get("graph", {}))
            st.json(run["topology"].get("pair_properties", []))
            st.dataframe(run["path_metrics"].head(1000))
        with sections[1]:
            nodes = run["node_metrics"]
            st.plotly_chart(
                px.bar(nodes, x="node", y=["mean_queue", "mean_qubits"], barmode="group"),
                width="stretch",
            )
            st.dataframe(nodes)
        with sections[2]:
            requests = run["requests"]
            cohort = requests[
                (requests.status == "completed")
                & (requests.arrival >= run["config"]["warmup_seconds"])
            ]
            figure = go.Figure()
            for metric in ("queue_wait", "sojourn", "service_time"):
                values = np.sort(cohort[metric])
                if len(values):
                    figure.add_trace(
                        go.Scatter(
                            x=values,
                            y=np.arange(1, len(values) + 1) / len(values),
                            name=metric,
                            mode="lines",
                            line_shape="hv",
                        )
                    )
            figure.update_layout(xaxis_title="Seconds", yaxis_title="Empirical CDF")
            st.plotly_chart(figure, width="stretch")
        with sections[3]:
            requests = run["requests"]
            st.dataframe(requests)
            if len(requests):
                rid = st.selectbox("Request ID", requests.request_id)
                st.dataframe(run["attempts"][run["attempts"].parent_id == rid])
                st.dataframe(run["events"][run["events"].request_id == rid])
            st.json(summary["terminal_counts"])
        with sections[4]:
            paths = run["path_metrics"]
            if len(paths):
                if (~paths.node_ok).any():
                    st.warning(
                        "Some analytical node loads were unstable; infinite estimates are not measured delays."
                    )
                st.dataframe(
                    paths[
                        [
                            "paper_fidelity",
                            "fidelity",
                            "delay",
                            "mu_path",
                            "rho_path",
                            "aggregate_ok",
                            "node_ok",
                            "memory_mean_ok",
                            "eligible",
                        ]
                    ]
                    .describe(include="all")
                    .astype(str)
                )
            st.caption(
                "Eq. (5) paper proxy and endpoint-aging estimates are distinct. See the report for Eq. (26) assumptions."
            )
        with sections[5]:
            st.markdown((chosen / "report.md").read_text())
            st.json(run["manifest"])
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
                for file in chosen.rglob("*"):
                    if file.is_file():
                        z.write(file, file.relative_to(chosen))
            st.download_button(
                "Download run, data, figures and report",
                archive.getvalue(),
                file_name=chosen.name + ".zip",
            )
with tabs[2]:
    files = (
        sorted((ROOT / "results").rglob("replications.parquet"))
        if (ROOT / "results").exists()
        else []
    )
    if files:
        file = st.selectbox("Saved sweep", files)
        frame = pd.read_parquet(file)
        metric = st.selectbox(
            "Metric", ["throughput", "mean_fidelity", "mean_queue_wait", "mean_latency"]
        )
        st.plotly_chart(
            px.scatter(
                frame,
                x="arrival_rate",
                y=metric,
                color="policy",
                symbol="replication",
                hover_data=["scenario", "topology_seed"],
            ),
            width="stretch",
        )
        ci = file.parent / "confidence_intervals.csv"
        if ci.exists():
            st.dataframe(pd.read_csv(ci))
        st.dataframe(frame)
        st.caption(
            "Individual replication points; interval tables group scenario and policy. No pooling of sensitivity axes."
        )
    else:
        st.info("Use qamr-sim sweep to generate independent-replication comparisons.")
