"""
analytics_dashboard.py
======================

Analytics Dashboard for Mock Interview Arena.
Provides visualization and metrics for interview performance.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import io


def calculate_performance_metrics(
    stress_timeline: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]],
    total_questions: int
) -> Dict[str, Any]:
    """
    Calculate comprehensive performance metrics from interview data.
    
    Returns a dictionary with various performance indicators.
    """
    metrics = {
        "composure": {},
        "engagement": {},
        "performance": {},
        "timeline": {}
    }
    
    # Composure Metrics
    if stress_timeline:
        stress_values = [entry.get("stress_level", 0.5) for entry in stress_timeline]
        
        metrics["composure"] = {
            "average_stress": sum(stress_values) / len(stress_values),
            "peak_stress": max(stress_values),
            "lowest_stress": min(stress_values),
            "stress_variance": sum((x - sum(stress_values)/len(stress_values))**2 for x in stress_values) / len(stress_values),
            "composure_score": (1 - sum(stress_values) / len(stress_values)) * 100,
            "stability_score": max(0, 100 - (max(stress_values) - min(stress_values)) * 100),
            "readings_count": len(stress_values)
        }
        
        # Calculate recovery rate
        recovery_events = []
        for i in range(1, len(stress_values)):
            if stress_values[i] < stress_values[i-1]:
                recovery_events.append(stress_values[i-1] - stress_values[i])
        
        metrics["composure"]["recovery_rate"] = (
            sum(recovery_events) / len(recovery_events) if recovery_events else 0
        )
        
        # Stress zones
        high_stress_count = sum(1 for s in stress_values if s > 0.7)
        medium_stress_count = sum(1 for s in stress_values if 0.4 <= s <= 0.7)
        low_stress_count = sum(1 for s in stress_values if s < 0.4)
        
        metrics["composure"]["stress_zones"] = {
            "high": high_stress_count / len(stress_values) * 100,
            "medium": medium_stress_count / len(stress_values) * 100,
            "low": low_stress_count / len(stress_values) * 100
        }
    else:
        metrics["composure"] = {
            "average_stress": 0.5,
            "peak_stress": 0.5,
            "lowest_stress": 0.5,
            "composure_score": 50,
            "stability_score": 50,
            "recovery_rate": 0,
            "readings_count": 0,
            "stress_zones": {"high": 0, "medium": 100, "low": 0}
        }
    
    # Engagement Metrics
    user_responses = [h for h in conversation_history if h["role"] == "user"]
    answered_questions = [r for r in user_responses if r["content"] != "[Skipped]"]
    skipped_questions = [r for r in user_responses if r["content"] == "[Skipped]"]
    
    total_words = sum(len(r["content"].split()) for r in answered_questions)
    avg_response_length = total_words / len(answered_questions) if answered_questions else 0
    
    metrics["engagement"] = {
        "questions_answered": len(answered_questions),
        "questions_skipped": len(skipped_questions),
        "completion_rate": len(answered_questions) / total_questions * 100 if total_questions > 0 else 0,
        "total_words": total_words,
        "avg_response_length": avg_response_length,
        "response_quality_indicator": min(100, avg_response_length / 50 * 100)  # Target ~50 words
    }
    
    # Performance Score (composite)
    composure_weight = 0.3
    engagement_weight = 0.4
    response_weight = 0.3
    
    composure_component = metrics["composure"]["composure_score"] * composure_weight
    engagement_component = metrics["engagement"]["completion_rate"] * engagement_weight
    response_component = metrics["engagement"]["response_quality_indicator"] * response_weight
    
    metrics["performance"] = {
        "overall_score": composure_component + engagement_component + response_component,
        "composure_component": composure_component,
        "engagement_component": engagement_component,
        "response_component": response_component,
        "grade": get_grade(composure_component + engagement_component + response_component)
    }
    
    # Timeline data for charts
    if stress_timeline:
        metrics["timeline"] = {
            "timestamps": [entry.get("timestamp", i*5) for i, entry in enumerate(stress_timeline)],
            "stress_levels": [entry.get("stress_level", 0.5) for entry in stress_timeline],
            "confidence_levels": [1 - entry.get("stress_level", 0.5) for entry in stress_timeline]
        }
    
    return metrics


def get_grade(score: float) -> str:
    """Convert numerical score to letter grade."""
    if score >= 90:
        return "A+"
    elif score >= 85:
        return "A"
    elif score >= 80:
        return "A-"
    elif score >= 75:
        return "B+"
    elif score >= 70:
        return "B"
    elif score >= 65:
        return "B-"
    elif score >= 60:
        return "C+"
    elif score >= 55:
        return "C"
    elif score >= 50:
        return "C-"
    elif score >= 45:
        return "D"
    else:
        return "F"


def render_metrics_cards(metrics: Dict[str, Any]):
    """Render the main metrics as cards."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        score = metrics["performance"]["overall_score"]
        grade = metrics["performance"]["grade"]
        st.metric(
            "Overall Score",
            f"{score:.1f}/100",
            delta=f"Grade: {grade}"
        )
    
    with col2:
        composure = metrics["composure"]["composure_score"]
        delta_text = "Excellent" if composure > 70 else "Good" if composure > 50 else "Needs Work"
        st.metric(
            "Composure Score",
            f"{composure:.1f}/100",
            delta=delta_text
        )
    
    with col3:
        completion = metrics["engagement"]["completion_rate"]
        answered = metrics["engagement"]["questions_answered"]
        st.metric(
            "Completion Rate",
            f"{completion:.0f}%",
            delta=f"{answered} answered"
        )
    
    with col4:
        avg_stress = metrics["composure"]["average_stress"]
        peak = metrics["composure"]["peak_stress"]
        st.metric(
            "Avg Stress Level",
            f"{avg_stress:.0%}",
            delta=f"Peak: {peak:.0%}",
            delta_color="inverse"
        )


def render_stress_timeline_chart(metrics: Dict[str, Any]):
    """Render the stress timeline chart."""
    st.markdown("### 📈 Stress Level Timeline")
    
    if metrics.get("timeline") and metrics["timeline"].get("timestamps"):
        timeline = metrics["timeline"]
        
        # Create DataFrame for chart
        df = pd.DataFrame({
            "Time (seconds)": timeline["timestamps"],
            "Stress %": [s * 100 for s in timeline["stress_levels"]],
            "Confidence %": [c * 100 for c in timeline["confidence_levels"]]
        })
        
        # Line chart
        st.line_chart(
            df.set_index("Time (seconds)"),
            width="stretch"
        )
        
        # Add annotations
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"📊 **{len(timeline['timestamps'])}** readings recorded")
        with col2:
            peak_idx = timeline["stress_levels"].index(max(timeline["stress_levels"]))
            st.warning(f"⚠️ Peak stress at **{timeline['timestamps'][peak_idx]}s**")
        with col3:
            calm_idx = timeline["stress_levels"].index(min(timeline["stress_levels"]))
            st.success(f"😊 Calmest at **{timeline['timestamps'][calm_idx]}s**")
    else:
        st.info("No stress data recorded during this session.")


def render_stress_distribution(metrics: Dict[str, Any]):
    """Render stress zone distribution."""
    st.markdown("### 🎯 Stress Zone Distribution")
    
    zones = metrics["composure"].get("stress_zones", {"high": 0, "medium": 100, "low": 0})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🟢 Low Stress Zone")
        st.markdown(f"### {zones['low']:.1f}%")
        st.progress(zones['low'] / 100)
        st.caption("Confident & Relaxed")
    
    with col2:
        st.markdown("#### 🟡 Medium Stress Zone")
        st.markdown(f"### {zones['medium']:.1f}%")
        st.progress(zones['medium'] / 100)
        st.caption("Alert & Focused")
    
    with col3:
        st.markdown("#### 🔴 High Stress Zone")
        st.markdown(f"### {zones['high']:.1f}%")
        st.progress(zones['high'] / 100)
        st.caption("Anxious & Tense")


def render_performance_breakdown(metrics: Dict[str, Any]):
    """Render detailed performance breakdown."""
    st.markdown("### 📊 Performance Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Composure Analysis")
        
        composure_data = {
            "Metric": [
                "Average Stress",
                "Peak Stress",
                "Lowest Stress",
                "Stability Score",
                "Recovery Rate"
            ],
            "Value": [
                f"{metrics['composure']['average_stress']:.0%}",
                f"{metrics['composure']['peak_stress']:.0%}",
                f"{metrics['composure']['lowest_stress']:.0%}",
                f"{metrics['composure']['stability_score']:.1f}/100",
                f"{metrics['composure']['recovery_rate']:.2f}"
            ],
            "Status": [
                "🟢" if metrics['composure']['average_stress'] < 0.4 else "🟡" if metrics['composure']['average_stress'] < 0.6 else "🔴",
                "🟢" if metrics['composure']['peak_stress'] < 0.6 else "🟡" if metrics['composure']['peak_stress'] < 0.8 else "🔴",
                "🟢" if metrics['composure']['lowest_stress'] < 0.3 else "🟡",
                "🟢" if metrics['composure']['stability_score'] > 70 else "🟡" if metrics['composure']['stability_score'] > 50 else "🔴",
                "🟢" if metrics['composure']['recovery_rate'] > 0.1 else "🟡"
            ]
        }
        
        st.dataframe(
            pd.DataFrame(composure_data),
            hide_index=True,
            width="stretch"
        )
    
    with col2:
        st.markdown("#### Engagement Analysis")
        
        engagement_data = {
            "Metric": [
                "Questions Answered",
                "Questions Skipped",
                "Completion Rate",
                "Total Words",
                "Avg Response Length"
            ],
            "Value": [
                str(metrics['engagement']['questions_answered']),
                str(metrics['engagement']['questions_skipped']),
                f"{metrics['engagement']['completion_rate']:.0f}%",
                str(metrics['engagement']['total_words']),
                f"{metrics['engagement']['avg_response_length']:.0f} words"
            ],
            "Status": [
                "🟢",
                "🟢" if metrics['engagement']['questions_skipped'] == 0 else "🟡",
                "🟢" if metrics['engagement']['completion_rate'] == 100 else "🟡" if metrics['engagement']['completion_rate'] >= 80 else "🔴",
                "🟢" if metrics['engagement']['total_words'] > 200 else "🟡",
                "🟢" if metrics['engagement']['avg_response_length'] > 40 else "🟡" if metrics['engagement']['avg_response_length'] > 20 else "🔴"
            ]
        }
        
        st.dataframe(
            pd.DataFrame(engagement_data),
            hide_index=True,
            width="stretch"
        )


def render_recommendations(metrics: Dict[str, Any]):
    """Render personalized recommendations based on performance."""
    st.markdown("### 💡 Personalized Recommendations")
    
    recommendations = []
    
    # Composure recommendations
    if metrics["composure"]["average_stress"] > 0.6:
        recommendations.append({
            "area": "Stress Management",
            "icon": "😰",
            "tip": "Practice deep breathing exercises before interviews. Try the 4-7-8 technique: inhale for 4 seconds, hold for 7, exhale for 8.",
            "priority": "High"
        })
    
    if metrics["composure"]["peak_stress"] > 0.8:
        recommendations.append({
            "area": "Peak Stress Control",
            "icon": "📈",
            "tip": "Your stress peaked significantly during the interview. Practice mock interviews more frequently to build comfort with the format.",
            "priority": "High"
        })
    
    if metrics["composure"]["stability_score"] < 60:
        recommendations.append({
            "area": "Emotional Stability",
            "icon": "🎢",
            "tip": "Your stress levels fluctuated considerably. Try to maintain a steady pace and take brief pauses before answering difficult questions.",
            "priority": "Medium"
        })
    
    # Engagement recommendations
    if metrics["engagement"]["avg_response_length"] < 30:
        recommendations.append({
            "area": "Response Depth",
            "icon": "📝",
            "tip": "Your answers were relatively brief. Use the STAR method (Situation, Task, Action, Result) to structure more comprehensive responses.",
            "priority": "Medium"
        })
    
    if metrics["engagement"]["questions_skipped"] > 0:
        recommendations.append({
            "area": "Question Coverage",
            "icon": "⏭️",
            "tip": f"You skipped {metrics['engagement']['questions_skipped']} question(s). Even partial answers are better than skipping - they show your thought process.",
            "priority": "Medium"
        })
    
    if metrics["engagement"]["completion_rate"] < 100:
        recommendations.append({
            "area": "Interview Completion",
            "icon": "🏁",
            "tip": "Try to complete all questions in future interviews. Time management and concise answers can help.",
            "priority": "Low"
        })
    
    # Positive feedback
    if metrics["composure"]["composure_score"] > 70:
        recommendations.append({
            "area": "Composure",
            "icon": "🌟",
            "tip": "Excellent composure! You maintained calm throughout most of the interview. Keep up the great work!",
            "priority": "Positive"
        })
    
    if metrics["engagement"]["avg_response_length"] > 50:
        recommendations.append({
            "area": "Response Quality",
            "icon": "✨",
            "tip": "Great job providing detailed responses! Your answers showed depth and thoughtfulness.",
            "priority": "Positive"
        })
    
    # Display recommendations
    if not recommendations:
        st.success("🎉 Great performance! No specific areas for improvement identified.")
    else:
        for rec in recommendations:
            if rec["priority"] == "Positive":
                st.success(f"{rec['icon']} **{rec['area']}**: {rec['tip']}")
            elif rec["priority"] == "High":
                st.error(f"{rec['icon']} **{rec['area']}** (Priority: {rec['priority']}): {rec['tip']}")
            elif rec["priority"] == "Medium":
                st.warning(f"{rec['icon']} **{rec['area']}** (Priority: {rec['priority']}): {rec['tip']}")
            else:
                st.info(f"{rec['icon']} **{rec['area']}**: {rec['tip']}")


def export_analytics_report(
    metrics: Dict[str, Any],
    conversation_history: List[Dict[str, str]],
    report_text: Optional[str] = None
) -> str:
    """Generate a comprehensive analytics report in Markdown format."""
    
    report = f"""# Interview Analytics Report
Generated: {datetime.now().strftime("%B %d, %Y at %H:%M")}

## Executive Summary

| Metric | Value | Grade |
|--------|-------|-------|
| Overall Score | {metrics['performance']['overall_score']:.1f}/100 | {metrics['performance']['grade']} |
| Composure Score | {metrics['composure']['composure_score']:.1f}/100 | - |
| Completion Rate | {metrics['engagement']['completion_rate']:.0f}% | - |
| Average Stress | {metrics['composure']['average_stress']:.0%} | - |

## Composure Analysis

### Stress Metrics
- **Average Stress Level**: {metrics['composure']['average_stress']:.0%}
- **Peak Stress**: {metrics['composure']['peak_stress']:.0%}
- **Lowest Stress**: {metrics['composure']['lowest_stress']:.0%}
- **Stability Score**: {metrics['composure']['stability_score']:.1f}/100
- **Recovery Rate**: {metrics['composure']['recovery_rate']:.3f}

### Stress Zone Distribution
- 🟢 Low Stress (Confident): {metrics['composure']['stress_zones']['low']:.1f}%
- 🟡 Medium Stress (Alert): {metrics['composure']['stress_zones']['medium']:.1f}%
- 🔴 High Stress (Anxious): {metrics['composure']['stress_zones']['high']:.1f}%

## Engagement Analysis

- **Questions Answered**: {metrics['engagement']['questions_answered']}
- **Questions Skipped**: {metrics['engagement']['questions_skipped']}
- **Completion Rate**: {metrics['engagement']['completion_rate']:.0f}%
- **Total Words**: {metrics['engagement']['total_words']}
- **Average Response Length**: {metrics['engagement']['avg_response_length']:.0f} words

## Performance Score Breakdown

| Component | Weight | Score | Contribution |
|-----------|--------|-------|--------------|
| Composure | 30% | {metrics['composure']['composure_score']:.1f} | {metrics['performance']['composure_component']:.1f} |
| Engagement | 40% | {metrics['engagement']['completion_rate']:.1f} | {metrics['performance']['engagement_component']:.1f} |
| Response Quality | 30% | {metrics['engagement']['response_quality_indicator']:.1f} | {metrics['performance']['response_component']:.1f} |
| **Total** | **100%** | - | **{metrics['performance']['overall_score']:.1f}** |

"""
    
    if report_text:
        report += f"""
## AI-Generated Analysis

{report_text}

"""
    
    report += """
---
*Report generated by Ultimate AI Academic Assistant V5.0 - Mock Interview Arena*
"""
    
    return report


def render_full_dashboard(
    stress_timeline: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]],
    total_questions: int,
    report_text: Optional[str] = None
):
    """Render the complete analytics dashboard."""
    
    # Calculate metrics
    metrics = calculate_performance_metrics(
        stress_timeline,
        conversation_history,
        total_questions
    )
    
    # Main metrics cards
    render_metrics_cards(metrics)
    
    st.markdown("---")
    
    # Stress timeline
    render_stress_timeline_chart(metrics)
    
    st.markdown("---")
    
    # Stress distribution
    render_stress_distribution(metrics)
    
    st.markdown("---")
    
    # Performance breakdown
    render_performance_breakdown(metrics)
    
    st.markdown("---")
    
    # Recommendations
    render_recommendations(metrics)
    
    st.markdown("---")
    
    # Export options
    st.markdown("### 📥 Export Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        report_md = export_analytics_report(metrics, conversation_history, report_text)
        st.download_button(
            "📄 Download Full Report (Markdown)",
            report_md,
            file_name=f"interview_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            width="stretch"
        )
    
    with col2:
        # Export raw data as JSON
        export_data = {
            "metrics": metrics,
            "stress_timeline": stress_timeline,
            "generated_at": datetime.now().isoformat()
        }
        st.download_button(
            "📊 Download Raw Data (JSON)",
            json.dumps(export_data, indent=2),
            file_name=f"interview_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            width="stretch"
        )
    
    return metrics
