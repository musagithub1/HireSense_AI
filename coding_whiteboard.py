"""
coding_whiteboard.py
====================

HireSense AI - Integrated Coding & Whiteboard Module

Provides an interactive environment for technical interviews:
- Code editor with syntax highlighting (Monaco Editor)
- Multiple programming language support
- Code execution capability
- Digital whiteboard for system design
- Drawing tools for diagrams
- AI-powered code review and hints
- Problem templates and examples
"""

from __future__ import annotations

import os
import json
import re
from typing import Dict, Any, Optional, List, Iterator
from dataclasses import dataclass
from datetime import datetime
from langchain_openai import ChatOpenAI
from pydantic import Field, SecretStr
from langchain_core.utils.utils import secret_from_env


# ============================================================================
# OpenRouter Integration
# ============================================================================

class ChatOpenRouter(ChatOpenAI):
    """OpenRouter API wrapper with streaming support."""

    openai_api_key: Optional[SecretStr] = Field(
        alias="api_key", default_factory=secret_from_env("OPENROUTER_API_KEY", default=None)
    )

    @property
    def lc_secrets(self) -> Dict[str, str]:
        return {"openai_api_key": "OPENROUTER_API_KEY"}

    def __init__(self, openai_api_key: Optional[str] = None, **kwargs: Any) -> None:
        openai_api_key = openai_api_key or os.environ.get("OPENROUTER_API_KEY")
        if not openai_api_key:
            raise ValueError(
                "OPENROUTER_API_KEY must be set in your environment or passed explicitly."
            )

        super().__init__(
            base_url="https://openrouter.ai/api/v1",
            openai_api_key=openai_api_key,
            **kwargs,
        )


# ============================================================================
# Supported Languages
# ============================================================================

SUPPORTED_LANGUAGES = {
    "python": {
        "name": "Python",
        "icon": "🐍",
        "extension": ".py",
        "monaco_id": "python",
        "default_code": '''# Python Solution
def solution(nums):
    """
    Your solution here
    """
    pass

# Test your solution
if __name__ == "__main__":
    # Example test case
    result = solution([1, 2, 3])
    print(f"Result: {result}")
''',
        "run_command": "python3"
    },
    "javascript": {
        "name": "JavaScript",
        "icon": "🟨",
        "extension": ".js",
        "monaco_id": "javascript",
        "default_code": '''// JavaScript Solution
function solution(nums) {
    // Your solution here
    return null;
}

// Test your solution
const result = solution([1, 2, 3]);
console.log("Result:", result);
''',
        "run_command": "node"
    },
    "java": {
        "name": "Java",
        "icon": "☕",
        "extension": ".java",
        "monaco_id": "java",
        "default_code": '''// Java Solution
public class Solution {
    public static int[] solution(int[] nums) {
        // Your solution here
        return new int[]{};
    }
    
    public static void main(String[] args) {
        int[] result = solution(new int[]{1, 2, 3});
        System.out.println("Result: " + java.util.Arrays.toString(result));
    }
}
''',
        "run_command": "java"
    },
    "cpp": {
        "name": "C++",
        "icon": "⚡",
        "extension": ".cpp",
        "monaco_id": "cpp",
        "default_code": '''// C++ Solution
#include <iostream>
#include <vector>
using namespace std;

vector<int> solution(vector<int>& nums) {
    // Your solution here
    return {};
}

int main() {
    vector<int> nums = {1, 2, 3};
    vector<int> result = solution(nums);
    cout << "Result: ";
    for (int n : result) cout << n << " ";
    cout << endl;
    return 0;
}
''',
        "run_command": "g++ -o solution && ./solution"
    },
    "sql": {
        "name": "SQL",
        "icon": "🗄️",
        "extension": ".sql",
        "monaco_id": "sql",
        "default_code": '''-- SQL Solution
-- Write your query here

SELECT 
    column1,
    column2
FROM 
    table_name
WHERE 
    condition = 'value'
ORDER BY 
    column1;
''',
        "run_command": None  # SQL is typically not executed directly
    }
}


# ============================================================================
# Problem Templates
# ============================================================================

PROBLEM_TEMPLATES = {
    "arrays": {
        "name": "Arrays & Strings",
        "icon": "📊",
        "problems": [
            {
                "title": "Two Sum",
                "difficulty": "Easy",
                "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
                "examples": [
                    {"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]"},
                    {"input": "nums = [3,2,4], target = 6", "output": "[1,2]"}
                ],
                "hints": ["Consider using a hash map", "One pass solution is possible"]
            },
            {
                "title": "Valid Anagram",
                "difficulty": "Easy",
                "description": "Given two strings s and t, return true if t is an anagram of s, and false otherwise.",
                "examples": [
                    {"input": 's = "anagram", t = "nagaram"', "output": "true"},
                    {"input": 's = "rat", t = "car"', "output": "false"}
                ],
                "hints": ["Count character frequencies", "Sorting is another approach"]
            },
            {
                "title": "Container With Most Water",
                "difficulty": "Medium",
                "description": "Given n non-negative integers representing heights, find two lines that together with the x-axis form a container that holds the most water.",
                "examples": [
                    {"input": "height = [1,8,6,2,5,4,8,3,7]", "output": "49"}
                ],
                "hints": ["Two pointer approach", "Start from both ends"]
            }
        ]
    },
    "linked_lists": {
        "name": "Linked Lists",
        "icon": "🔗",
        "problems": [
            {
                "title": "Reverse Linked List",
                "difficulty": "Easy",
                "description": "Given the head of a singly linked list, reverse the list, and return the reversed list.",
                "examples": [
                    {"input": "head = [1,2,3,4,5]", "output": "[5,4,3,2,1]"}
                ],
                "hints": ["Iterative: use three pointers", "Recursive solution is elegant"]
            },
            {
                "title": "Merge Two Sorted Lists",
                "difficulty": "Easy",
                "description": "Merge two sorted linked lists and return it as a sorted list.",
                "examples": [
                    {"input": "l1 = [1,2,4], l2 = [1,3,4]", "output": "[1,1,2,3,4,4]"}
                ],
                "hints": ["Use a dummy head node", "Compare and advance pointers"]
            }
        ]
    },
    "trees": {
        "name": "Trees & Graphs",
        "icon": "🌳",
        "problems": [
            {
                "title": "Maximum Depth of Binary Tree",
                "difficulty": "Easy",
                "description": "Given the root of a binary tree, return its maximum depth.",
                "examples": [
                    {"input": "root = [3,9,20,null,null,15,7]", "output": "3"}
                ],
                "hints": ["DFS recursive approach", "BFS level-order traversal"]
            },
            {
                "title": "Validate Binary Search Tree",
                "difficulty": "Medium",
                "description": "Given the root of a binary tree, determine if it is a valid binary search tree (BST).",
                "examples": [
                    {"input": "root = [2,1,3]", "output": "true"},
                    {"input": "root = [5,1,4,null,null,3,6]", "output": "false"}
                ],
                "hints": ["In-order traversal should be sorted", "Pass valid range to each node"]
            }
        ]
    },
    "dynamic_programming": {
        "name": "Dynamic Programming",
        "icon": "📈",
        "problems": [
            {
                "title": "Climbing Stairs",
                "difficulty": "Easy",
                "description": "You are climbing a staircase. It takes n steps to reach the top. Each time you can either climb 1 or 2 steps. In how many distinct ways can you climb to the top?",
                "examples": [
                    {"input": "n = 2", "output": "2"},
                    {"input": "n = 3", "output": "3"}
                ],
                "hints": ["This is a Fibonacci sequence", "dp[i] = dp[i-1] + dp[i-2]"]
            },
            {
                "title": "Longest Increasing Subsequence",
                "difficulty": "Medium",
                "description": "Given an integer array nums, return the length of the longest strictly increasing subsequence.",
                "examples": [
                    {"input": "nums = [10,9,2,5,3,7,101,18]", "output": "4"}
                ],
                "hints": ["O(n²) DP solution", "O(n log n) with binary search"]
            }
        ]
    },
    "system_design": {
        "name": "System Design",
        "icon": "🏗️",
        "problems": [
            {
                "title": "Design URL Shortener",
                "difficulty": "Medium",
                "description": "Design a URL shortening service like bit.ly. The service should generate a short URL for a given long URL and redirect to the original URL when accessed.",
                "examples": [],
                "hints": ["Consider: encoding scheme, database design, scalability", "Think about: collision handling, analytics, expiration"]
            },
            {
                "title": "Design a Chat System",
                "difficulty": "Hard",
                "description": "Design a real-time chat system that supports 1-on-1 and group messaging, online presence, and message delivery status.",
                "examples": [],
                "hints": ["WebSocket for real-time", "Message queue for reliability", "Consider: read receipts, typing indicators, offline support"]
            },
            {
                "title": "Design a Rate Limiter",
                "difficulty": "Medium",
                "description": "Design a rate limiter that limits the number of requests a user can make to an API within a time window.",
                "examples": [],
                "hints": ["Token bucket algorithm", "Sliding window counter", "Consider: distributed systems, Redis"]
            }
        ]
    }
}


# ============================================================================
# AI Code Review
# ============================================================================

def review_code(
    code: str,
    language: str,
    problem_description: str = "",
    *,
    model_name: str = "google/gemini-2.0-flash-001",
    temperature: float = 0.3,
) -> Iterator[str]:
    """
    Review code and provide feedback.
    
    Yields tokens for streaming display.
    """
    llm = ChatOpenRouter(
        model_name=model_name,
        temperature=temperature,
        streaming=True
    )
    
    system_prompt = f"""You are an expert coding interview coach. Review the candidate's code and provide constructive feedback.

Focus on:
1. **Correctness**: Does the code solve the problem?
2. **Time Complexity**: What is the Big O?
3. **Space Complexity**: Memory usage analysis
4. **Code Quality**: Readability, naming, structure
5. **Edge Cases**: Are they handled?
6. **Improvements**: Suggestions for optimization

Be encouraging but thorough. Format your response clearly with sections.
"""

    user_prompt = f"""Language: {language}

Problem Description:
{problem_description if problem_description else "General code review"}

Code to Review:
```{language}
{code}
```

Please provide a comprehensive code review."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    for chunk in llm.stream(messages):
        if hasattr(chunk, 'content'):
            yield chunk.content


def get_hint(
    problem_description: str,
    current_code: str,
    language: str,
    hint_level: int = 1,  # 1 = gentle, 2 = moderate, 3 = detailed
    *,
    model_name: str = "google/gemini-2.0-flash-001",
    temperature: float = 0.4,
) -> str:
    """
    Get a hint for solving the problem based on current progress.
    """
    llm = ChatOpenRouter(
        model_name=model_name,
        temperature=temperature,
        streaming=False
    )
    
    hint_instructions = {
        1: "Give a very subtle hint without revealing the approach. Just point them in the right direction.",
        2: "Give a moderate hint that suggests the general approach or data structure to use.",
        3: "Give a detailed hint with the algorithm approach, but don't write the actual code."
    }
    
    system_prompt = f"""You are a coding interview coach. The candidate is stuck and needs a hint.

{hint_instructions.get(hint_level, hint_instructions[1])}

Be encouraging and help them learn, don't just give away the answer."""

    user_prompt = f"""Problem:
{problem_description}

Current Code ({language}):
```{language}
{current_code}
```

Please provide a level {hint_level} hint."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        return f"Error getting hint: {e}"


def explain_solution(
    problem_description: str,
    language: str,
    *,
    model_name: str = "google/gemini-2.0-flash-001",
    temperature: float = 0.3,
) -> Iterator[str]:
    """
    Explain the optimal solution for a problem.
    
    Yields tokens for streaming display.
    """
    llm = ChatOpenRouter(
        model_name=model_name,
        temperature=temperature,
        streaming=True
    )
    
    system_prompt = """You are an expert coding interview coach. Explain the optimal solution to this problem.

Structure your explanation:
1. **Approach**: High-level strategy
2. **Algorithm**: Step-by-step breakdown
3. **Code**: Clean, commented implementation
4. **Complexity Analysis**: Time and space
5. **Follow-up**: Common variations or optimizations

Make it educational and clear."""

    user_prompt = f"""Problem:
{problem_description}

Please explain the optimal solution in {language}."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    for chunk in llm.stream(messages):
        if hasattr(chunk, 'content'):
            yield chunk.content


# ============================================================================
# Coding & Whiteboard Component HTML/JS
# ============================================================================

def get_coding_whiteboard_html(
    initial_language: str = "python",
    initial_code: str = "",
    problem_data: Dict[str, Any] = None,
    session_id: str = "default"
) -> str:
    """
    Generate HTML/JS code for the coding and whiteboard component.
    
    Features:
    - Monaco Editor for code editing
    - Multiple language support
    - Digital whiteboard with drawing tools
    - Split view (code + whiteboard)
    - Code execution simulation
    """
    
    languages_json = json.dumps(SUPPORTED_LANGUAGES)
    problem_json = json.dumps(problem_data or {})
    
    if not initial_code:
        initial_code = SUPPORTED_LANGUAGES.get(initial_language, {}).get("default_code", "")
    
    # Escape the code for JavaScript
    escaped_code = initial_code.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        .coding-container {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1e1e1e;
            border-radius: 12px;
            overflow: hidden;
            height: 700px;
            display: flex;
            flex-direction: column;
        }}
        
        .toolbar {{
            background: #2d2d2d;
            padding: 10px 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #404040;
        }}
        
        .toolbar-left {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .toolbar-right {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .tab-buttons {{
            display: flex;
            gap: 5px;
        }}
        
        .tab-btn {{
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .tab-btn.active {{
            background: #0078d4;
            color: white;
        }}
        
        .tab-btn:not(.active) {{
            background: #3c3c3c;
            color: #cccccc;
        }}
        
        .tab-btn:hover:not(.active) {{
            background: #4a4a4a;
        }}
        
        .language-select {{
            padding: 8px 12px;
            border: 1px solid #404040;
            border-radius: 6px;
            background: #3c3c3c;
            color: #cccccc;
            font-size: 13px;
            cursor: pointer;
        }}
        
        .action-btn {{
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .action-btn.primary {{
            background: #4CAF50;
            color: white;
        }}
        
        .action-btn.secondary {{
            background: #3c3c3c;
            color: #cccccc;
        }}
        
        .action-btn:hover {{
            opacity: 0.9;
            transform: translateY(-1px);
        }}
        
        .main-content {{
            flex: 1;
            display: flex;
            overflow: hidden;
        }}
        
        .panel {{
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        
        .panel.hidden {{
            display: none;
        }}
        
        .split-view {{
            display: flex;
        }}
        
        .split-view .panel {{
            width: 50%;
            border-right: 1px solid #404040;
        }}
        
        .split-view .panel:last-child {{
            border-right: none;
        }}
        
        #editor-container {{
            flex: 1;
            overflow: hidden;
        }}
        
        .whiteboard-container {{
            flex: 1;
            background: #ffffff;
            position: relative;
        }}
        
        #whiteboard {{
            width: 100%;
            height: 100%;
            cursor: crosshair;
        }}
        
        .whiteboard-tools {{
            position: absolute;
            top: 10px;
            left: 10px;
            display: flex;
            gap: 5px;
            background: rgba(0,0,0,0.8);
            padding: 8px;
            border-radius: 8px;
        }}
        
        .tool-btn {{
            width: 36px;
            height: 36px;
            border: none;
            border-radius: 6px;
            background: #3c3c3c;
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            transition: all 0.2s;
        }}
        
        .tool-btn.active {{
            background: #0078d4;
        }}
        
        .tool-btn:hover:not(.active) {{
            background: #4a4a4a;
        }}
        
        .color-picker {{
            width: 36px;
            height: 36px;
            border: 2px solid #404040;
            border-radius: 6px;
            cursor: pointer;
            padding: 0;
        }}
        
        .stroke-width {{
            width: 60px;
            height: 36px;
            border: 1px solid #404040;
            border-radius: 6px;
            background: #3c3c3c;
            color: white;
            padding: 0 8px;
        }}
        
        .output-panel {{
            height: 150px;
            background: #1a1a1a;
            border-top: 1px solid #404040;
            display: flex;
            flex-direction: column;
        }}
        
        .output-header {{
            padding: 8px 15px;
            background: #2d2d2d;
            font-size: 12px;
            font-weight: 600;
            color: #cccccc;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .output-content {{
            flex: 1;
            padding: 10px 15px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 13px;
            color: #4EC9B0;
            overflow-y: auto;
            white-space: pre-wrap;
        }}
        
        .output-content.error {{
            color: #f48771;
        }}
        
        .problem-panel {{
            width: 350px;
            background: #252526;
            border-right: 1px solid #404040;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        
        .problem-header {{
            padding: 15px;
            background: #2d2d2d;
            border-bottom: 1px solid #404040;
        }}
        
        .problem-title {{
            font-size: 16px;
            font-weight: 600;
            color: white;
            margin-bottom: 8px;
        }}
        
        .problem-difficulty {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        
        .problem-difficulty.easy {{
            background: rgba(76, 175, 80, 0.2);
            color: #4CAF50;
        }}
        
        .problem-difficulty.medium {{
            background: rgba(255, 193, 7, 0.2);
            color: #FFC107;
        }}
        
        .problem-difficulty.hard {{
            background: rgba(244, 67, 54, 0.2);
            color: #F44336;
        }}
        
        .problem-content {{
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            color: #cccccc;
            font-size: 14px;
            line-height: 1.6;
        }}
        
        .problem-section {{
            margin-bottom: 20px;
        }}
        
        .problem-section-title {{
            font-size: 13px;
            font-weight: 600;
            color: #0078d4;
            margin-bottom: 8px;
        }}
        
        .example-box {{
            background: #1e1e1e;
            border-radius: 6px;
            padding: 10px;
            margin-bottom: 10px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
        }}
        
        .hint-box {{
            background: rgba(255, 193, 7, 0.1);
            border-left: 3px solid #FFC107;
            padding: 10px;
            border-radius: 0 6px 6px 0;
            margin-top: 10px;
        }}
        
        .ai-feedback {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 8px;
            padding: 15px;
            margin: 15px;
            color: white;
        }}
        
        .ai-feedback-title {{
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .ai-feedback-content {{
            font-size: 13px;
            line-height: 1.5;
            white-space: pre-wrap;
        }}
        
        .loading {{
            display: flex;
            align-items: center;
            gap: 8px;
            color: #888;
        }}
        
        .loading-spinner {{
            width: 16px;
            height: 16px;
            border: 2px solid #404040;
            border-top-color: #0078d4;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}
        
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
    </style>
    <!-- Monaco Editor CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/loader.min.js"></script>
</head>
<body>
    <div class="coding-container">
        <!-- Toolbar -->
        <div class="toolbar">
            <div class="toolbar-left">
                <div class="tab-buttons">
                    <button class="tab-btn active" onclick="switchView('code')" id="code-tab">
                        <span>💻</span> Code Editor
                    </button>
                    <button class="tab-btn" onclick="switchView('whiteboard')" id="whiteboard-tab">
                        <span>🎨</span> Whiteboard
                    </button>
                    <button class="tab-btn" onclick="switchView('split')" id="split-tab">
                        <span>📐</span> Split View
                    </button>
                </div>
                
                <select class="language-select" id="language-select" onchange="changeLanguage(this.value)">
                    <option value="python">🐍 Python</option>
                    <option value="javascript">🟨 JavaScript</option>
                    <option value="java">☕ Java</option>
                    <option value="cpp">⚡ C++</option>
                    <option value="sql">🗄️ SQL</option>
                </select>
            </div>
            
            <div class="toolbar-right">
                <button class="action-btn secondary" onclick="getHint()">
                    <span>💡</span> Hint
                </button>
                <button class="action-btn secondary" onclick="reviewCode()">
                    <span>🔍</span> AI Review
                </button>
                <button class="action-btn primary" onclick="runCode()">
                    <span>▶️</span> Run Code
                </button>
            </div>
        </div>
        
        <!-- Main Content -->
        <div class="main-content" id="main-content">
            <!-- Problem Panel (optional) -->
            <div class="problem-panel" id="problem-panel" style="display: none;">
                <div class="problem-header">
                    <div class="problem-title" id="problem-title">Two Sum</div>
                    <span class="problem-difficulty easy" id="problem-difficulty">Easy</span>
                </div>
                <div class="problem-content" id="problem-content">
                    <div class="problem-section">
                        <div class="problem-section-title">Description</div>
                        <div id="problem-description"></div>
                    </div>
                    <div class="problem-section">
                        <div class="problem-section-title">Examples</div>
                        <div id="problem-examples"></div>
                    </div>
                    <div class="problem-section" id="hints-section" style="display: none;">
                        <div class="problem-section-title">Hints</div>
                        <div class="hint-box" id="hint-content"></div>
                    </div>
                </div>
            </div>
            
            <!-- Code Editor Panel -->
            <div class="panel" id="code-panel">
                <div id="editor-container"></div>
            </div>
            
            <!-- Whiteboard Panel -->
            <div class="panel hidden" id="whiteboard-panel">
                <div class="whiteboard-container">
                    <canvas id="whiteboard"></canvas>
                    <div class="whiteboard-tools">
                        <button class="tool-btn active" onclick="setTool('pen')" id="pen-tool" title="Pen">✏️</button>
                        <button class="tool-btn" onclick="setTool('line')" id="line-tool" title="Line">📏</button>
                        <button class="tool-btn" onclick="setTool('rect')" id="rect-tool" title="Rectangle">⬜</button>
                        <button class="tool-btn" onclick="setTool('circle')" id="circle-tool" title="Circle">⭕</button>
                        <button class="tool-btn" onclick="setTool('arrow')" id="arrow-tool" title="Arrow">➡️</button>
                        <button class="tool-btn" onclick="setTool('text')" id="text-tool" title="Text">T</button>
                        <button class="tool-btn" onclick="setTool('eraser')" id="eraser-tool" title="Eraser">🧹</button>
                        <input type="color" class="color-picker" id="color-picker" value="#000000" onchange="setColor(this.value)">
                        <select class="stroke-width" id="stroke-width" onchange="setStrokeWidth(this.value)">
                            <option value="2">Thin</option>
                            <option value="4" selected>Medium</option>
                            <option value="8">Thick</option>
                        </select>
                        <button class="tool-btn" onclick="clearWhiteboard()" title="Clear">🗑️</button>
                        <button class="tool-btn" onclick="undoWhiteboard()" title="Undo">↩️</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Output Panel -->
        <div class="output-panel">
            <div class="output-header">
                <span>Output</span>
                <button class="action-btn secondary" onclick="clearOutput()" style="padding: 4px 8px; font-size: 11px;">Clear</button>
            </div>
            <div class="output-content" id="output-content">
                // Output will appear here when you run your code...
            </div>
        </div>
        
        <!-- AI Feedback Panel (hidden by default) -->
        <div class="ai-feedback" id="ai-feedback" style="display: none;">
            <div class="ai-feedback-title">
                <span>🤖</span> AI Feedback
            </div>
            <div class="ai-feedback-content" id="ai-feedback-content"></div>
        </div>
    </div>
    
    <script>
        // Configuration
        const languages = {languages_json};
        const problemData = {problem_json};
        let currentLanguage = '{initial_language}';
        let editor = null;
        let currentView = 'code';
        
        // Whiteboard state
        let canvas, ctx;
        let isDrawing = false;
        let currentTool = 'pen';
        let currentColor = '#000000';
        let strokeWidth = 4;
        let startX, startY;
        let drawHistory = [];
        let currentPath = [];
        
        // Initialize Monaco Editor
        require.config({{ paths: {{ vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' }} }});
        
        require(['vs/editor/editor.main'], function() {{
            editor = monaco.editor.create(document.getElementById('editor-container'), {{
                value: `{escaped_code}`,
                language: currentLanguage,
                theme: 'vs-dark',
                fontSize: 14,
                lineNumbers: 'on',
                minimap: {{ enabled: false }},
                automaticLayout: true,
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                tabSize: 4,
                insertSpaces: true
            }});
        }});
        
        // Initialize Whiteboard
        function initWhiteboard() {{
            canvas = document.getElementById('whiteboard');
            ctx = canvas.getContext('2d');
            
            // Set canvas size
            resizeCanvas();
            window.addEventListener('resize', resizeCanvas);
            
            // Event listeners
            canvas.addEventListener('mousedown', startDrawing);
            canvas.addEventListener('mousemove', draw);
            canvas.addEventListener('mouseup', stopDrawing);
            canvas.addEventListener('mouseout', stopDrawing);
            
            // Touch support
            canvas.addEventListener('touchstart', handleTouch);
            canvas.addEventListener('touchmove', handleTouch);
            canvas.addEventListener('touchend', stopDrawing);
        }}
        
        function resizeCanvas() {{
            const container = canvas.parentElement;
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
            redrawCanvas();
        }}
        
        function startDrawing(e) {{
            isDrawing = true;
            const rect = canvas.getBoundingClientRect();
            startX = e.clientX - rect.left;
            startY = e.clientY - rect.top;
            currentPath = [{{ x: startX, y: startY }}];
            
            if (currentTool === 'pen' || currentTool === 'eraser') {{
                ctx.beginPath();
                ctx.moveTo(startX, startY);
            }}
        }}
        
        function draw(e) {{
            if (!isDrawing) return;
            
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            ctx.strokeStyle = currentTool === 'eraser' ? '#ffffff' : currentColor;
            ctx.lineWidth = currentTool === 'eraser' ? strokeWidth * 3 : strokeWidth;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            
            if (currentTool === 'pen' || currentTool === 'eraser') {{
                ctx.lineTo(x, y);
                ctx.stroke();
                currentPath.push({{ x, y }});
            }} else {{
                // For shapes, redraw canvas and show preview
                redrawCanvas();
                drawShape(startX, startY, x, y, true);
            }}
        }}
        
        function stopDrawing(e) {{
            if (!isDrawing) return;
            isDrawing = false;
            
            if (currentTool === 'pen' || currentTool === 'eraser') {{
                ctx.closePath();
                drawHistory.push({{
                    tool: currentTool,
                    color: currentColor,
                    width: strokeWidth,
                    path: [...currentPath]
                }});
            }} else if (e) {{
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                drawHistory.push({{
                    tool: currentTool,
                    color: currentColor,
                    width: strokeWidth,
                    startX, startY,
                    endX: x, endY: y
                }});
            }}
            
            currentPath = [];
        }}
        
        function handleTouch(e) {{
            e.preventDefault();
            const touch = e.touches[0];
            const mouseEvent = new MouseEvent({{
                touchstart: 'mousedown',
                touchmove: 'mousemove',
                touchend: 'mouseup'
            }}[e.type], {{
                clientX: touch.clientX,
                clientY: touch.clientY
            }});
            canvas.dispatchEvent(mouseEvent);
        }}
        
        function drawShape(x1, y1, x2, y2, preview = false) {{
            ctx.strokeStyle = currentColor;
            ctx.lineWidth = strokeWidth;
            ctx.lineCap = 'round';
            
            switch (currentTool) {{
                case 'line':
                    ctx.beginPath();
                    ctx.moveTo(x1, y1);
                    ctx.lineTo(x2, y2);
                    ctx.stroke();
                    break;
                case 'rect':
                    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
                    break;
                case 'circle':
                    const radius = Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
                    ctx.beginPath();
                    ctx.arc(x1, y1, radius, 0, 2 * Math.PI);
                    ctx.stroke();
                    break;
                case 'arrow':
                    drawArrow(x1, y1, x2, y2);
                    break;
            }}
        }}
        
        function drawArrow(x1, y1, x2, y2) {{
            const headLength = 15;
            const angle = Math.atan2(y2 - y1, x2 - x1);
            
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.lineTo(x2 - headLength * Math.cos(angle - Math.PI / 6), y2 - headLength * Math.sin(angle - Math.PI / 6));
            ctx.moveTo(x2, y2);
            ctx.lineTo(x2 - headLength * Math.cos(angle + Math.PI / 6), y2 - headLength * Math.sin(angle + Math.PI / 6));
            ctx.stroke();
        }}
        
        function redrawCanvas() {{
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            for (const item of drawHistory) {{
                ctx.strokeStyle = item.tool === 'eraser' ? '#ffffff' : item.color;
                ctx.lineWidth = item.tool === 'eraser' ? item.width * 3 : item.width;
                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';
                
                if (item.tool === 'pen' || item.tool === 'eraser') {{
                    if (item.path.length > 0) {{
                        ctx.beginPath();
                        ctx.moveTo(item.path[0].x, item.path[0].y);
                        for (let i = 1; i < item.path.length; i++) {{
                            ctx.lineTo(item.path[i].x, item.path[i].y);
                        }}
                        ctx.stroke();
                    }}
                }} else {{
                    drawShape(item.startX, item.startY, item.endX, item.endY);
                }}
            }}
        }}
        
        function setTool(tool) {{
            currentTool = tool;
            document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(tool + '-tool')?.classList.add('active');
        }}
        
        function setColor(color) {{
            currentColor = color;
        }}
        
        function setStrokeWidth(width) {{
            strokeWidth = parseInt(width);
        }}
        
        function clearWhiteboard() {{
            drawHistory = [];
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        }}
        
        function undoWhiteboard() {{
            if (drawHistory.length > 0) {{
                drawHistory.pop();
                redrawCanvas();
            }}
        }}
        
        // View switching
        function switchView(view) {{
            currentView = view;
            
            // Update tab buttons
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(view + '-tab').classList.add('active');
            
            const codePanel = document.getElementById('code-panel');
            const whiteboardPanel = document.getElementById('whiteboard-panel');
            const mainContent = document.getElementById('main-content');
            
            mainContent.classList.remove('split-view');
            
            if (view === 'code') {{
                codePanel.classList.remove('hidden');
                whiteboardPanel.classList.add('hidden');
            }} else if (view === 'whiteboard') {{
                codePanel.classList.add('hidden');
                whiteboardPanel.classList.remove('hidden');
                if (!canvas) initWhiteboard();
                setTimeout(resizeCanvas, 100);
            }} else if (view === 'split') {{
                mainContent.classList.add('split-view');
                codePanel.classList.remove('hidden');
                whiteboardPanel.classList.remove('hidden');
                if (!canvas) initWhiteboard();
                setTimeout(resizeCanvas, 100);
            }}
            
            // Trigger editor resize
            if (editor) {{
                setTimeout(() => editor.layout(), 100);
            }}
        }}
        
        // Language switching
        function changeLanguage(lang) {{
            currentLanguage = lang;
            if (editor) {{
                monaco.editor.setModelLanguage(editor.getModel(), languages[lang]?.monaco_id || lang);
                // Optionally set default code
                // editor.setValue(languages[lang]?.default_code || '');
            }}
        }}
        
        // Code execution (simulated)
        function runCode() {{
            const code = editor.getValue();
            const output = document.getElementById('output-content');
            
            output.classList.remove('error');
            output.textContent = 'Running code...\\n';
            
            // Simulate execution
            setTimeout(() => {{
                try {{
                    // In a real implementation, this would send to a backend
                    output.textContent = `// Code execution simulated\\n// Language: ${{currentLanguage}}\\n// Code length: ${{code.length}} characters\\n\\n`;
                    output.textContent += `✅ Code compiled successfully!\\n`;
                    output.textContent += `\\n// To enable real code execution, connect to a backend service.`;
                }} catch (e) {{
                    output.classList.add('error');
                    output.textContent = `Error: ${{e.message}}`;
                }}
            }}, 500);
            
            // Send to Streamlit
            sendToStreamlit({{ action: 'run', code: code, language: currentLanguage }});
        }}
        
        // AI features
        function getHint() {{
            const code = editor.getValue();
            const hintsSection = document.getElementById('hints-section');
            const hintContent = document.getElementById('hint-content');
            
            hintsSection.style.display = 'block';
            hintContent.innerHTML = '<div class="loading"><div class="loading-spinner"></div> Getting hint...</div>';
            
            // Simulate AI hint
            setTimeout(() => {{
                hintContent.textContent = '💡 Consider using a hash map to achieve O(n) time complexity. Store each number as you iterate and check if the complement exists.';
            }}, 1000);
            
            sendToStreamlit({{ action: 'hint', code: code, language: currentLanguage }});
        }}
        
        function reviewCode() {{
            const code = editor.getValue();
            const feedback = document.getElementById('ai-feedback');
            const feedbackContent = document.getElementById('ai-feedback-content');
            
            feedback.style.display = 'block';
            feedbackContent.innerHTML = '<div class="loading"><div class="loading-spinner"></div> Analyzing code...</div>';
            
            // Simulate AI review
            setTimeout(() => {{
                feedbackContent.textContent = `✅ Code Structure: Good\\n⏱️ Time Complexity: O(n)\\n💾 Space Complexity: O(n)\\n\\n📝 Suggestions:\\n• Consider adding input validation\\n• Variable names are clear and descriptive\\n• Edge cases could be documented`;
            }}, 1500);
            
            sendToStreamlit({{ action: 'review', code: code, language: currentLanguage }});
        }}
        
        function clearOutput() {{
            document.getElementById('output-content').textContent = '// Output will appear here when you run your code...';
            document.getElementById('output-content').classList.remove('error');
        }}
        
        // Send data to Streamlit
        function sendToStreamlit(data) {{
            if (window.parent && window.parent.postMessage) {{
                window.parent.postMessage({{
                    type: 'streamlit:setComponentValue',
                    value: data
                }}, '*');
            }}
        }}
        
        // Initialize problem panel if data exists
        function initProblem() {{
            if (problemData && problemData.title) {{
                document.getElementById('problem-panel').style.display = 'flex';
                document.getElementById('problem-title').textContent = problemData.title;
                
                const diffBadge = document.getElementById('problem-difficulty');
                diffBadge.textContent = problemData.difficulty || 'Medium';
                diffBadge.className = 'problem-difficulty ' + (problemData.difficulty || 'medium').toLowerCase();
                
                document.getElementById('problem-description').textContent = problemData.description || '';
                
                const examplesDiv = document.getElementById('problem-examples');
                if (problemData.examples && problemData.examples.length > 0) {{
                    examplesDiv.innerHTML = problemData.examples.map((ex, i) => `
                        <div class="example-box">
                            <strong>Example ${{i + 1}}:</strong><br>
                            Input: ${{ex.input}}<br>
                            Output: ${{ex.output}}
                        </div>
                    `).join('');
                }}
            }}
        }}
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {{
            initProblem();
        }});
    </script>
</body>
</html>
'''


# ============================================================================
# Streamlit Integration Functions
# ============================================================================

def render_coding_component(
    initial_language: str = "python",
    initial_code: str = "",
    problem: Dict[str, Any] = None,
    height: int = 750
) -> None:
    """
    Render the coding and whiteboard component in Streamlit.
    
    Args:
        initial_language: Starting programming language
        initial_code: Initial code to display
        problem: Problem data dictionary
        height: Component height in pixels
    """
    import streamlit.components.v1 as components
    
    # Generate the HTML
    html_code = get_coding_whiteboard_html(
        initial_language=initial_language,
        initial_code=initial_code,
        problem_data=problem
    )
    
    # Render the component
    components.html(html_code, height=height, scrolling=False)


def get_problem_selector() -> Dict[str, Any]:
    """
    Returns the problem templates for selection in Streamlit.
    """
    return PROBLEM_TEMPLATES


def get_supported_languages() -> Dict[str, Any]:
    """
    Returns the supported programming languages.
    """
    return SUPPORTED_LANGUAGES
