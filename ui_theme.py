"""Shared visual system and presentation helpers for HireSense AI."""

from __future__ import annotations

import html
from collections.abc import Sequence
from pathlib import Path

import streamlit as st

BRAND_LOGO_PATH = (
    Path(__file__).resolve().parent / "static" / "brand" / "hiresense-ai-logo.png"
)

THEME_CSS = """
<style>
:root {
    --hs-bg: #07101f;
    --hs-bg-soft: #0a1426;
    --hs-sidebar: #08111f;
    --hs-surface: rgba(15, 27, 48, 0.92);
    --hs-surface-strong: #111f36;
    --hs-surface-hover: #172743;
    --hs-border: rgba(148, 163, 184, 0.16);
    --hs-border-strong: rgba(148, 163, 184, 0.28);
    --hs-primary: #7c5cff;
    --hs-primary-hover: #6c4cf5;
    --hs-primary-soft: rgba(124, 92, 255, 0.14);
    --hs-accent: #22d3ee;
    --hs-success: #34d399;
    --hs-warning: #fbbf24;
    --hs-danger: #fb7185;
    --hs-text: #f8fafc;
    --hs-text-soft: #d8e1ee;
    --hs-muted: #94a3b8;
    --hs-muted-2: #64748b;
    --hs-shadow: 0 22px 60px rgba(0, 0, 0, 0.24);
    --hs-radius-sm: 10px;
    --hs-radius: 16px;
    --hs-radius-lg: 24px;
}

html,
body,
[class*="css"] {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
}

body {
    color: var(--hs-text);
}

.stApp {
    background:
        radial-gradient(circle at 14% -8%, rgba(124, 92, 255, 0.18), transparent 28rem),
        radial-gradient(circle at 94% 4%, rgba(34, 211, 238, 0.08), transparent 24rem),
        linear-gradient(180deg, var(--hs-bg) 0%, #050b15 100%);
}

[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stToolbar"] {
    right: 1rem;
}

[data-testid="stAppViewContainer"] > .main {
    background: transparent;
}

.block-container {
    width: min(100%, 1240px);
    padding: 2.35rem 2.75rem 4rem;
}

h1,
h2,
h3,
h4,
h5,
h6 {
    color: var(--hs-text);
    letter-spacing: -0.025em;
}

p,
li,
label,
[data-testid="stMarkdownContainer"] {
    color: var(--hs-text-soft);
}

a {
    color: #a5b4fc;
}

hr {
    margin: 1.65rem 0;
    border-color: var(--hs-border) !important;
}

.hs-brand {
    display: flex;
    max-width: 17rem;
    align-items: flex-start;
    flex-direction: column;
    gap: 0.5rem;
    margin: 0.15rem 0 1.65rem;
}

.hs-brand-logo-frame,
.hs-live-brand {
    position: relative;
    width: 100%;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.13);
    border-radius: 0.9rem;
    background: #ffffff;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.2);
}

.hs-brand-logo-frame {
    aspect-ratio: 5.65 / 1;
}

.hs-brand-logo,
.hs-live-brand img {
    display: block;
    width: 100%;
    height: auto;
    transform: translateY(-27%);
}

.hs-brand-product {
    padding-left: 0.2rem;
    color: var(--hs-muted);
    font-size: 0.69rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.hs-live-brand {
    width: 10.5rem;
    aspect-ratio: 5.65 / 1;
    margin-bottom: 0.75rem;
    border-radius: 0.6rem;
    box-shadow: none;
}

.hs-hero {
    position: relative;
    margin: 0 0 1.65rem;
    overflow: hidden;
    padding: 2rem 2.15rem;
    border: 1px solid var(--hs-border);
    border-radius: var(--hs-radius-lg);
    background:
        linear-gradient(120deg, rgba(124, 92, 255, 0.16), rgba(34, 211, 238, 0.035) 58%),
        rgba(11, 22, 40, 0.84);
    box-shadow: var(--hs-shadow);
}

.hs-hero::after {
    position: absolute;
    top: -6rem;
    right: -3rem;
    width: 16rem;
    height: 16rem;
    border-radius: 50%;
    background: rgba(34, 211, 238, 0.08);
    content: "";
    filter: blur(2px);
}

.hs-hero > * {
    position: relative;
    z-index: 1;
}

.hs-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    margin-bottom: 0.7rem;
    color: #a5b4fc;
    font-size: 0.73rem;
    font-weight: 780;
    letter-spacing: 0.13em;
    text-transform: uppercase;
}

.hs-eyebrow::before {
    width: 0.48rem;
    height: 0.48rem;
    border-radius: 50%;
    background: var(--hs-accent);
    box-shadow: 0 0 0 5px rgba(34, 211, 238, 0.08);
    content: "";
}

.hs-page-title {
    max-width: 760px;
    margin: 0;
    color: var(--hs-text);
    font-size: clamp(2rem, 4.3vw, 3.45rem);
    font-weight: 790;
    letter-spacing: -0.052em;
    line-height: 1.04;
}

.hs-page-description {
    max-width: 720px;
    margin: 0.9rem 0 0;
    color: var(--hs-muted);
    font-size: 1rem;
    line-height: 1.65;
}

.hs-section-heading {
    margin: 0.15rem 0 1rem;
}

.hs-section-number {
    display: inline-grid;
    width: 1.75rem;
    height: 1.75rem;
    margin-right: 0.55rem;
    place-items: center;
    border: 1px solid rgba(124, 92, 255, 0.38);
    border-radius: 0.58rem;
    background: var(--hs-primary-soft);
    color: #c4b5fd;
    font-size: 0.75rem;
    font-weight: 800;
}

.hs-section-title {
    color: var(--hs-text);
    font-size: 1.02rem;
    font-weight: 760;
}

.hs-section-description {
    margin: 0.38rem 0 0 2.42rem;
    color: var(--hs-muted);
    font-size: 0.84rem;
    line-height: 1.5;
}

.hs-stepper {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.65rem;
    margin: 0 0 1.55rem;
}

.hs-step {
    min-height: 4.8rem;
    padding: 0.85rem 0.9rem;
    border: 1px solid var(--hs-border);
    border-radius: var(--hs-radius);
    background: rgba(15, 27, 48, 0.68);
}

.hs-step-index {
    display: grid;
    width: 1.45rem;
    height: 1.45rem;
    margin-bottom: 0.45rem;
    place-items: center;
    border: 1px solid var(--hs-border-strong);
    border-radius: 50%;
    color: var(--hs-muted);
    font-size: 0.67rem;
    font-weight: 800;
}

.hs-step-label {
    color: var(--hs-muted);
    font-size: 0.78rem;
    font-weight: 700;
}

.hs-step.active {
    border-color: rgba(124, 92, 255, 0.58);
    background: linear-gradient(145deg, rgba(124, 92, 255, 0.18), rgba(15, 27, 48, 0.82));
}

.hs-step.active .hs-step-index {
    border-color: var(--hs-primary);
    background: var(--hs-primary);
    color: white;
}

.hs-step.active .hs-step-label,
.hs-step.done .hs-step-label {
    color: var(--hs-text-soft);
}

.hs-step.done .hs-step-index {
    border-color: rgba(52, 211, 153, 0.38);
    background: rgba(52, 211, 153, 0.13);
    color: var(--hs-success);
}

.hs-live-topbar,
.hs-result-hero {
    margin-bottom: 1.35rem;
    padding: 1.35rem 1.45rem;
    border: 1px solid var(--hs-border);
    border-radius: var(--hs-radius-lg);
    background: rgba(10, 20, 38, 0.84);
    box-shadow: var(--hs-shadow);
}

.hs-live-row,
.hs-result-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
}

.hs-live-title,
.hs-result-title {
    margin: 0;
    color: var(--hs-text);
    font-size: clamp(1.35rem, 2.8vw, 1.9rem);
    font-weight: 760;
    letter-spacing: -0.035em;
}

.hs-meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.8rem;
}

.hs-chip {
    display: inline-flex;
    min-height: 1.75rem;
    align-items: center;
    padding: 0.3rem 0.65rem;
    border: 1px solid var(--hs-border);
    border-radius: 999px;
    background: rgba(148, 163, 184, 0.07);
    color: var(--hs-muted);
    font-size: 0.72rem;
    font-weight: 690;
}

.hs-chip.accent {
    border-color: rgba(34, 211, 238, 0.28);
    background: rgba(34, 211, 238, 0.08);
    color: #a5f3fc;
}

.hs-progress-copy {
    flex: 0 0 auto;
    color: var(--hs-muted);
    font-size: 0.76rem;
    font-weight: 700;
}

.hs-result-score {
    display: grid;
    min-width: 5.1rem;
    min-height: 5.1rem;
    place-items: center;
    border: 1px solid rgba(124, 92, 255, 0.42);
    border-radius: 1.2rem;
    background: linear-gradient(145deg, rgba(124, 92, 255, 0.22), rgba(34, 211, 238, 0.08));
}

.hs-result-score strong {
    display: block;
    color: var(--hs-text);
    font-size: 1.4rem;
    line-height: 1;
}

.hs-result-score span {
    display: block;
    margin-top: 0.3rem;
    color: var(--hs-muted);
    font-size: 0.65rem;
    font-weight: 750;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.hs-empty {
    padding: 3rem 1.5rem;
    border: 1px dashed var(--hs-border-strong);
    border-radius: var(--hs-radius-lg);
    background: rgba(15, 27, 48, 0.42);
    text-align: center;
}

.hs-empty-mark {
    display: grid;
    width: 3rem;
    height: 3rem;
    margin: 0 auto 1rem;
    place-items: center;
    border-radius: 1rem;
    background: var(--hs-primary-soft);
    color: #c4b5fd;
    font-weight: 850;
}

.hs-empty h3 {
    margin: 0;
    font-size: 1.1rem;
}

.hs-empty p {
    max-width: 460px;
    margin: 0.55rem auto 0;
    color: var(--hs-muted);
    font-size: 0.87rem;
}

.hs-footer {
    margin-top: 3rem;
    padding-top: 1.3rem;
    border-top: 1px solid var(--hs-border);
    color: var(--hs-muted-2);
    font-size: 0.76rem;
    text-align: center;
}

/* Sidebar */
[data-testid="stSidebar"] {
    border-right: 1px solid var(--hs-border);
    background:
        linear-gradient(180deg, rgba(124, 92, 255, 0.055), transparent 12rem),
        var(--hs-sidebar);
}

[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding: 1.35rem 1rem;
}

[data-testid="stSidebar"] hr {
    margin: 1.1rem 0;
}

[data-testid="stSidebar"] .stButton > button {
    min-height: 2.75rem;
    justify-content: flex-start;
    padding-inline: 0.9rem;
    border-color: transparent;
    background: transparent;
    color: var(--hs-muted);
    box-shadow: none;
    text-align: left;
}

[data-testid="stSidebar"] .stButton > button:hover {
    border-color: var(--hs-border);
    background: rgba(148, 163, 184, 0.07);
    color: var(--hs-text);
}

[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    border-color: rgba(124, 92, 255, 0.34);
    background: var(--hs-primary-soft);
    color: #ddd6fe;
}

.hs-profile {
    padding: 0.9rem;
    border: 1px solid var(--hs-border);
    border-radius: var(--hs-radius);
    background: rgba(15, 27, 48, 0.66);
}

.hs-profile-label {
    margin-bottom: 0.35rem;
    color: var(--hs-muted-2);
    font-size: 0.64rem;
    font-weight: 780;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.hs-profile-name {
    color: var(--hs-text);
    font-size: 0.86rem;
    font-weight: 720;
}

.hs-profile-email {
    margin-top: 0.18rem;
    overflow: hidden;
    color: var(--hs-muted);
    font-size: 0.72rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.hs-sidebar-label {
    margin: 0.95rem 0 0.42rem;
    padding-left: 0.28rem;
    color: var(--hs-muted-2);
    font-size: 0.63rem;
    font-weight: 780;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.hs-sidebar-status {
    display: flex;
    align-items: center;
    gap: 0.48rem;
    margin-top: 1rem;
    padding: 0.75rem 0.85rem;
    border: 1px solid rgba(52, 211, 153, 0.17);
    border-radius: var(--hs-radius-sm);
    background: rgba(52, 211, 153, 0.055);
    color: #a7f3d0;
    font-size: 0.7rem;
    font-weight: 690;
}

.hs-sidebar-status::before {
    width: 0.48rem;
    height: 0.48rem;
    border-radius: 50%;
    background: var(--hs-success);
    box-shadow: 0 0 0 4px rgba(52, 211, 153, 0.08);
    content: "";
}

/* Streamlit primitives */
.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] > button {
    min-height: 2.72rem;
    border: 1px solid var(--hs-border-strong);
    border-radius: var(--hs-radius-sm);
    background: rgba(20, 34, 57, 0.84);
    color: var(--hs-text-soft);
    font-weight: 710;
    box-shadow: none;
    transition: border-color 150ms ease, background 150ms ease, transform 150ms ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    border-color: rgba(165, 180, 252, 0.52);
    background: var(--hs-surface-hover);
    color: white;
    transform: translateY(-1px);
}

.stButton > button:focus-visible,
.stDownloadButton > button:focus-visible,
[data-testid="stFormSubmitButton"] > button:focus-visible {
    outline: 3px solid rgba(34, 211, 238, 0.24);
    outline-offset: 2px;
}

.stButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] > button[kind="primary"] {
    border-color: rgba(255, 255, 255, 0.12);
    background: linear-gradient(135deg, var(--hs-primary), #5948df);
    color: white;
    box-shadow: 0 12px 28px rgba(79, 70, 229, 0.25);
}

.stButton > button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #8b73ff, var(--hs-primary-hover));
}

.stButton > button:disabled {
    border-color: var(--hs-border);
    background: rgba(30, 41, 59, 0.52);
    color: var(--hs-muted-2);
    box-shadow: none;
    transform: none;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: var(--hs-border) !important;
    border-radius: var(--hs-radius-lg) !important;
    background: var(--hs-surface);
    box-shadow: 0 16px 42px rgba(0, 0, 0, 0.14);
}

[data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: 0.2rem;
}

[data-testid="stMetric"] {
    min-height: 7rem;
    padding: 1rem 1.05rem;
    border: 1px solid var(--hs-border);
    border-radius: var(--hs-radius);
    background: rgba(15, 27, 48, 0.78);
}

[data-testid="stMetricLabel"] {
    color: var(--hs-muted);
    font-size: 0.76rem;
}

[data-testid="stMetricValue"] {
    color: var(--hs-text);
    font-weight: 760;
    letter-spacing: -0.035em;
}

[data-testid="stMetricDelta"] {
    font-size: 0.72rem;
}

[data-testid="stAlert"] {
    border: 1px solid var(--hs-border);
    border-radius: var(--hs-radius);
    background: rgba(15, 27, 48, 0.82);
}

[data-testid="stExpander"] {
    overflow: hidden;
    border: 1px solid var(--hs-border) !important;
    border-radius: var(--hs-radius) !important;
    background: rgba(15, 27, 48, 0.66);
}

[data-testid="stExpander"] details summary {
    min-height: 3.15rem;
}

[data-testid="stFileUploader"] {
    padding: 0.7rem;
    border: 1px dashed var(--hs-border-strong);
    border-radius: var(--hs-radius);
    background: rgba(10, 20, 38, 0.46);
}

[data-testid="stFileUploaderDropzone"] {
    border: 0;
    background: transparent;
}

[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div,
[data-baseweb="select"] > div,
[data-baseweb="base-input"] {
    border-color: var(--hs-border-strong) !important;
    border-radius: var(--hs-radius-sm) !important;
    background: rgba(8, 17, 31, 0.7) !important;
}

input,
textarea {
    color: var(--hs-text) !important;
}

input::placeholder,
textarea::placeholder {
    color: var(--hs-muted-2) !important;
}

[data-testid="stRadio"] > div,
[data-testid="stCheckbox"] {
    gap: 0.55rem;
}

[data-testid="stProgress"] > div > div {
    background: rgba(148, 163, 184, 0.12);
}

[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, var(--hs-primary), var(--hs-accent));
}

[data-baseweb="tab-list"] {
    gap: 0.45rem;
    padding: 0.32rem;
    border: 1px solid var(--hs-border);
    border-radius: 0.85rem;
    background: rgba(8, 17, 31, 0.6);
}

[data-baseweb="tab"] {
    border-radius: 0.62rem;
}

[data-baseweb="tab"][aria-selected="true"] {
    background: var(--hs-primary-soft);
    color: #ddd6fe;
}

/* Keep embedded browser components visually connected to the page. */
iframe {
    border-radius: var(--hs-radius);
}

@media (max-width: 900px) {
    .block-container {
        padding: 1.6rem 1.2rem 3rem;
    }

    .hs-hero {
        padding: 1.55rem 1.35rem;
    }

    .hs-stepper {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 640px) {
    .block-container {
        padding-inline: 0.85rem;
    }

    .hs-page-title {
        font-size: 2.15rem;
    }

    .hs-stepper {
        grid-template-columns: 1fr;
    }

    .hs-live-row,
    .hs-result-row {
        align-items: flex-start;
        flex-direction: column;
    }

    .hs-result-score {
        min-width: 100%;
        min-height: 4.1rem;
    }
}

@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        scroll-behavior: auto !important;
        animation: none !important;
        transition: none !important;
    }
}
</style>
"""


def apply_theme() -> None:
    """Install the HireSense design system on the current Streamlit page."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def enable_focus_mode() -> None:
    """Hide workspace navigation while a candidate is in an interview."""
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }
        .block-container {
            width: min(100%, 1080px);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def brand_logo_source() -> str:
    """Return the Streamlit-served URL for the supplied HireSense logo."""
    if not BRAND_LOGO_PATH.is_file():
        return ""
    return "app/static/brand/hiresense-ai-logo.png"


def render_brand(*, compact: bool = False) -> None:
    """Render the HireSense product lockup."""
    product = "Interview intelligence" if not compact else "Interview studio"
    logo_source = brand_logo_source()
    if not logo_source:
        st.markdown(
            '<div class="hs-brand"><strong>HireSense AI</strong></div>',
            unsafe_allow_html=True,
        )
        return
    st.markdown(
        f"""
        <div class="hs-brand">
            <div class="hs-brand-logo-frame">
                <img class="hs-brand-logo" src="{logo_source}" alt="HireSense AI">
            </div>
            <div class="hs-brand-product">{product}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(kicker: str, title: str, description: str) -> None:
    """Render a product-specific page hero."""
    st.markdown(
        f"""
        <section class="hs-hero">
            <div class="hs-eyebrow">{html.escape(kicker)}</div>
            <h1 class="hs-page-title">{html.escape(title)}</h1>
            <p class="hs-page-description">{html.escape(description)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_section_heading(number: int, title: str, description: str = "") -> None:
    """Render a compact numbered section heading."""
    description_html = (
        f'<p class="hs-section-description">{html.escape(description)}</p>'
        if description
        else ""
    )
    st.markdown(
        f"""
        <div class="hs-section-heading">
            <span class="hs-section-number">{int(number):02d}</span>
            <span class="hs-section-title">{html.escape(title)}</span>
            {description_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stepper(active_step: int) -> None:
    """Render the four-part interview setup progress indicator."""
    labels = ("Interview focus", "Role context", "Experience", "Review")
    resolved = min(4, max(1, int(active_step)))
    steps = []
    for index, label in enumerate(labels, start=1):
        state = "done" if index < resolved else "active" if index == resolved else ""
        marker = "✓" if index < resolved else str(index)
        current = ' aria-current="step"' if index == resolved else ""
        steps.append(
            f'<div class="hs-step {state}" role="listitem"{current}>'
            f'<div class="hs-step-index">{marker}</div>'
            f'<div class="hs-step-label">{html.escape(label)}</div>'
            "</div>"
        )
    # st.markdown parses blank lines between sibling HTML blocks as fenced code.
    # Use Streamlit's direct HTML renderer so the progress grid cannot leak raw
    # markup into the interface.
    st.html(
        f'<div class="hs-stepper" role="list" '
        f'aria-label="Interview setup progress">{"".join(steps)}</div>'
    )


def setup_active_step(*, has_resume: bool, has_job_description: bool) -> int:
    """Return the setup step that should be visually emphasized."""
    if not has_resume or not has_job_description:
        return 2
    return 4


def render_live_header(
    *,
    interview_type: str,
    company: str,
    language: str,
    mode: str,
    question_number: int,
    total_questions: int,
) -> None:
    """Render the focused top bar used during an interview."""
    current = min(max(1, int(question_number)), max(1, int(total_questions)))
    total = max(1, int(total_questions))
    logo_source = brand_logo_source()
    logo_html = (
        f'<div class="hs-live-brand"><img src="{logo_source}" alt="HireSense AI"></div>'
        if logo_source
        else ""
    )
    st.markdown(
        f"""
        <section class="hs-live-topbar">
            <div class="hs-live-row">
                <div>
                    {logo_html}
                    <div class="hs-eyebrow">Live interview room</div>
                    <h1 class="hs-live-title">{html.escape(interview_type)} interview</h1>
                </div>
                <div class="hs-progress-copy">Question {current} of {total}</div>
            </div>
            <div class="hs-meta-row">
                <span class="hs-chip accent">{html.escape(mode)}</span>
                <span class="hs-chip">{html.escape(company)}</span>
                <span class="hs-chip">{html.escape(language)}</span>
                <span class="hs-chip">Adaptive follow-ups</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_results_header(
    *,
    interview_type: str,
    company: str,
    score: float | None,
    reliability: str,
) -> None:
    """Render the report summary without inventing a score."""
    if score is None:
        score_value = "N/A"
        score_label = "Not assessed"
    else:
        score_value = f"{score:.1f}/5"
        score_label = "Evidence score"
    st.markdown(
        f"""
        <section class="hs-result-hero">
            <div class="hs-result-row">
                <div>
                    <div class="hs-eyebrow">Interview report</div>
                    <h1 class="hs-result-title">Your evidence-backed assessment</h1>
                    <div class="hs-meta-row">
                        <span class="hs-chip accent">{html.escape(interview_type)}</span>
                        <span class="hs-chip">{html.escape(company)}</span>
                        <span class="hs-chip">Reliability: {html.escape(reliability)}</span>
                    </div>
                </div>
                <div class="hs-result-score">
                    <div>
                        <strong>{score_value}</strong>
                        <span>{score_label}</span>
                    </div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(mark: str, title: str, description: str) -> None:
    """Render a calm, branded empty state."""
    st.markdown(
        f"""
        <section class="hs-empty">
            <div class="hs-empty-mark">{html.escape(mark[:2])}</div>
            <h3>{html.escape(title)}</h3>
            <p>{html.escape(description)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_label(label: str) -> None:
    """Render a small sidebar section label."""
    st.markdown(
        f'<div class="hs-sidebar-label">{html.escape(label)}</div>',
        unsafe_allow_html=True,
    )


def render_sidebar_profile(display_name: str, email: str) -> None:
    """Render the compact account card in the sidebar."""
    st.markdown(
        f"""
        <div class="hs-profile">
            <div class="hs-profile-label">Active session</div>
            <div class="hs-profile-name">{html.escape(display_name)}</div>
            <div class="hs-profile-email">{html.escape(email)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_status(history_count: int) -> None:
    """Render a nontechnical readiness summary."""
    suffix = "interview" if int(history_count) == 1 else "interviews"
    st.markdown(
        f"""
        <div class="hs-sidebar-status">
            Platform ready · {int(history_count)} saved {suffix}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer(items: Sequence[str] | None = None) -> None:
    """Render a compact product footer."""
    labels = items or (
        "Adaptive interviews",
        "Accessible voice",
        "Transcript-verified scoring",
    )
    st.markdown(
        f'<footer class="hs-footer">HireSense AI · {" · ".join(html.escape(item) for item in labels)}</footer>',
        unsafe_allow_html=True,
    )
