"""
company_prep.py
===============

HireSense AI - Company-Specific Interview Preparation Module

Provides tailored interview preparation for major tech companies:
- FAANG (Facebook/Meta, Amazon, Apple, Netflix, Google)
- Microsoft, Uber, Airbnb, LinkedIn, Twitter/X, etc.
- Company-specific interview styles and focus areas
- Leadership principles and cultural fit questions
- Common interview patterns and expectations
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# ============================================================================
# Company Profiles
# ============================================================================

COMPANY_PROFILES = {
    "google": {
        "name": "Google",
        "logo": "🔍",
        "color": "#4285F4",
        "interview_style": "Structured and analytical",
        "rounds": ["Phone Screen", "Technical Phone", "Onsite (4-5 rounds)", "Team Match"],
        "focus_areas": [
            "Data structures and algorithms",
            "System design (for senior roles)",
            "Googleyness and Leadership",
            "Coding in preferred language",
            "Problem-solving approach"
        ],
        "leadership_principles": [
            "Focus on the user",
            "Think 10x",
            "Launch and iterate",
            "Fail well",
            "Be a good communicator"
        ],
        "common_questions": [
            "Design a URL shortener like bit.ly",
            "How would you improve Google Maps?",
            "Tell me about a time you had to deal with ambiguity",
            "Design YouTube's video recommendation system",
            "How do you prioritize competing projects?"
        ],
        "tips": [
            "Practice coding on a whiteboard or Google Docs",
            "Think out loud and explain your reasoning",
            "Ask clarifying questions before diving in",
            "Consider edge cases and scalability",
            "Show enthusiasm for Google's products"
        ],
        "interview_format": """
Google interviews focus heavily on problem-solving ability and 'Googleyness'.
- Technical rounds: 45 minutes each, expect 1-2 coding problems
- System design: Focus on scalability and trade-offs
- Behavioral: Use the STAR method, focus on impact and collaboration
- Hiring committee reviews all feedback independently
"""
    },
    "amazon": {
        "name": "Amazon",
        "logo": "📦",
        "color": "#FF9900",
        "interview_style": "Leadership Principles focused",
        "rounds": ["Online Assessment", "Phone Screen", "Onsite Loop (5-6 rounds)", "Bar Raiser"],
        "focus_areas": [
            "Leadership Principles (16 principles)",
            "System design and scalability",
            "Coding and problem-solving",
            "Behavioral questions (STAR method)",
            "Customer obsession examples"
        ],
        "leadership_principles": [
            "Customer Obsession",
            "Ownership",
            "Invent and Simplify",
            "Are Right, A Lot",
            "Learn and Be Curious",
            "Hire and Develop the Best",
            "Insist on the Highest Standards",
            "Think Big",
            "Bias for Action",
            "Frugality",
            "Earn Trust",
            "Dive Deep",
            "Have Backbone; Disagree and Commit",
            "Deliver Results",
            "Strive to be Earth's Best Employer",
            "Success and Scale Bring Broad Responsibility"
        ],
        "common_questions": [
            "Tell me about a time you went above and beyond for a customer",
            "Describe a situation where you had to make a decision without all the data",
            "Tell me about a time you failed and what you learned",
            "How do you handle disagreements with your manager?",
            "Design Amazon's product recommendation system"
        ],
        "tips": [
            "Prepare 2-3 stories for each Leadership Principle",
            "Use the STAR method consistently",
            "Quantify your impact with metrics",
            "Show ownership and customer focus",
            "Be prepared for the Bar Raiser round"
        ],
        "interview_format": """
Amazon interviews are heavily focused on Leadership Principles.
- Every interviewer assesses specific LPs
- Expect behavioral questions in EVERY round
- Bar Raiser is an objective third-party interviewer
- System design focuses on AWS services and scalability
- Prepare specific examples with metrics and outcomes
"""
    },
    "meta": {
        "name": "Meta (Facebook)",
        "logo": "👤",
        "color": "#1877F2",
        "interview_style": "Move fast and be bold",
        "rounds": ["Recruiter Screen", "Technical Phone", "Onsite (4-5 rounds)", "Hiring Committee"],
        "focus_areas": [
            "Coding (primarily algorithms)",
            "System design",
            "Behavioral (Meta values)",
            "Product sense (for PM roles)",
            "Collaboration and impact"
        ],
        "leadership_principles": [
            "Move Fast",
            "Be Bold",
            "Focus on Long-Term Impact",
            "Build Awesome Things",
            "Live in the Future",
            "Be Direct and Respect Your Colleagues"
        ],
        "common_questions": [
            "Design Facebook's News Feed",
            "How would you improve Instagram Stories?",
            "Tell me about a time you had to move fast on a project",
            "Design a real-time chat system like Messenger",
            "How do you handle conflicting priorities?"
        ],
        "tips": [
            "Practice coding on CoderPad (their interview tool)",
            "Focus on clean, bug-free code",
            "System design should consider billions of users",
            "Show passion for connecting people",
            "Demonstrate impact and ownership"
        ],
        "interview_format": """
Meta interviews emphasize coding excellence and product thinking.
- Coding rounds: 45 minutes, usually 2 medium/hard problems
- System design: Focus on scale (billions of users)
- Behavioral: Focus on impact, collaboration, and Meta values
- Product sense questions for relevant roles
- Ninja (coding) and Jedi (design) interview tracks
"""
    },
    "apple": {
        "name": "Apple",
        "logo": "🍎",
        "color": "#555555",
        "interview_style": "Secretive and detail-oriented",
        "rounds": ["Recruiter Screen", "Technical Phone", "Onsite (6-8 rounds)", "Executive Review"],
        "focus_areas": [
            "Technical depth in your domain",
            "Attention to detail",
            "Design thinking and user experience",
            "Problem-solving creativity",
            "Collaboration and communication"
        ],
        "leadership_principles": [
            "Accessibility",
            "Education",
            "Environment",
            "Inclusion and Diversity",
            "Privacy",
            "Supplier Responsibility"
        ],
        "common_questions": [
            "Why do you want to work at Apple?",
            "Tell me about a product you designed from scratch",
            "How would you improve the iPhone experience?",
            "Describe a technically challenging project",
            "How do you handle feedback on your work?"
        ],
        "tips": [
            "Research Apple's products deeply",
            "Show passion for design and user experience",
            "Be prepared for long interview days",
            "Demonstrate attention to detail",
            "Expect some secrecy about the role"
        ],
        "interview_format": """
Apple interviews are thorough and detail-oriented.
- Longer onsite process (full day or multiple days)
- Heavy focus on domain expertise
- Design and UX questions are common
- May not reveal full project details until hired
- Executive review for senior roles
"""
    },
    "netflix": {
        "name": "Netflix",
        "logo": "🎬",
        "color": "#E50914",
        "interview_style": "Culture and freedom with responsibility",
        "rounds": ["Recruiter Screen", "Hiring Manager", "Technical/Cross-functional", "Executive"],
        "focus_areas": [
            "Netflix Culture (Freedom & Responsibility)",
            "Technical excellence",
            "Judgment and decision-making",
            "Communication and candor",
            "Innovation and curiosity"
        ],
        "leadership_principles": [
            "Judgment",
            "Communication",
            "Curiosity",
            "Courage",
            "Passion",
            "Selflessness",
            "Innovation",
            "Inclusion",
            "Integrity",
            "Impact"
        ],
        "common_questions": [
            "Tell me about a time you made a controversial decision",
            "How do you handle giving difficult feedback?",
            "Describe a situation where you took a risk",
            "How do you stay current in your field?",
            "Design Netflix's recommendation algorithm"
        ],
        "tips": [
            "Read and internalize the Netflix Culture Deck",
            "Prepare examples of candid feedback",
            "Show independent judgment",
            "Demonstrate high performance mindset",
            "Be ready to discuss compensation openly"
        ],
        "interview_format": """
Netflix interviews focus heavily on culture fit and judgment.
- Culture deck is essential reading
- Expect candid conversations about performance
- Technical bar is very high
- Compensation discussions are direct
- Freedom and Responsibility is core to everything
"""
    },
    "microsoft": {
        "name": "Microsoft",
        "logo": "🪟",
        "color": "#00A4EF",
        "interview_style": "Growth mindset and collaboration",
        "rounds": ["Recruiter Screen", "Technical Phone", "Onsite (4-5 rounds)", "As Appropriate"],
        "focus_areas": [
            "Growth mindset",
            "Technical problem-solving",
            "System design",
            "Collaboration and teamwork",
            "Customer empathy"
        ],
        "leadership_principles": [
            "Growth Mindset",
            "Customer Obsessed",
            "Diverse and Inclusive",
            "One Microsoft",
            "Making a Difference"
        ],
        "common_questions": [
            "Tell me about a time you learned from failure",
            "How do you approach learning new technologies?",
            "Design a cloud storage system like OneDrive",
            "Describe a time you helped a teammate grow",
            "How would you improve Microsoft Teams?"
        ],
        "tips": [
            "Emphasize growth mindset and learning",
            "Show collaborative approach",
            "Understand Azure and Microsoft products",
            "Prepare for 'As Appropriate' (final decision maker)",
            "Demonstrate customer empathy"
        ],
        "interview_format": """
Microsoft interviews emphasize growth mindset and collaboration.
- Technical rounds focus on problem-solving approach
- 'As Appropriate' is the final interviewer with veto power
- Behavioral questions focus on learning and growth
- System design often involves Azure services
- Team fit is very important
"""
    },
    "uber": {
        "name": "Uber",
        "logo": "🚗",
        "color": "#000000",
        "interview_style": "Fast-paced and data-driven",
        "rounds": ["Recruiter Screen", "Technical Phone", "Onsite (4-5 rounds)", "Hiring Committee"],
        "focus_areas": [
            "Algorithms and data structures",
            "System design at scale",
            "Real-time systems",
            "Data-driven decision making",
            "Uber cultural norms"
        ],
        "leadership_principles": [
            "We build globally, we live locally",
            "We are customer obsessed",
            "We celebrate differences",
            "We act like owners",
            "We persevere",
            "We value ideas over hierarchy",
            "We make big bold bets",
            "We do the right thing"
        ],
        "common_questions": [
            "Design Uber's ride matching system",
            "How would you detect fraudulent rides?",
            "Design a surge pricing algorithm",
            "Tell me about a time you made a data-driven decision",
            "How do you handle competing priorities?"
        ],
        "tips": [
            "Understand real-time systems and geolocation",
            "Prepare for scale (millions of rides per day)",
            "Show data-driven thinking",
            "Demonstrate ownership mentality",
            "Know Uber's business model well"
        ],
        "interview_format": """
Uber interviews focus on scale and real-time systems.
- Heavy emphasis on system design
- Geolocation and mapping questions common
- Data structures for real-time matching
- Behavioral focuses on ownership and impact
- Fast-paced interview process
"""
    },
    "airbnb": {
        "name": "Airbnb",
        "logo": "🏠",
        "color": "#FF5A5F",
        "interview_style": "Mission-driven and values-focused",
        "rounds": ["Recruiter Screen", "Technical Phone", "Onsite (5-6 rounds)", "Cross-functional"],
        "focus_areas": [
            "Core values alignment",
            "Technical excellence",
            "Design and user experience",
            "Hospitality mindset",
            "Belonging and inclusion"
        ],
        "leadership_principles": [
            "Champion the Mission",
            "Be a Host",
            "Embrace the Adventure",
            "Be a Cereal Entrepreneur",
            "Simplify",
            "Every Frame Matters"
        ],
        "common_questions": [
            "Why Airbnb? What does belonging mean to you?",
            "Design Airbnb's search and ranking system",
            "Tell me about a time you went above and beyond as a host",
            "How would you improve the guest experience?",
            "Describe a product you built with attention to detail"
        ],
        "tips": [
            "Understand Airbnb's mission deeply",
            "Show hospitality mindset",
            "Prepare for cross-functional interviews",
            "Demonstrate attention to design details",
            "Share stories about belonging and community"
        ],
        "interview_format": """
Airbnb interviews are heavily values and mission-focused.
- Core values interview is critical
- Cross-functional rounds assess collaboration
- Design thinking is valued across roles
- Hospitality mindset is essential
- 'Be a Host' mentality in all interactions
"""
    },
    "linkedin": {
        "name": "LinkedIn",
        "logo": "💼",
        "color": "#0A66C2",
        "interview_style": "Professional and relationship-focused",
        "rounds": ["Recruiter Screen", "Hiring Manager", "Technical Loop", "Culture Add"],
        "focus_areas": [
            "LinkedIn culture and values",
            "Technical problem-solving",
            "Data and machine learning",
            "Professional networking domain",
            "Collaboration and communication"
        ],
        "leadership_principles": [
            "Members First",
            "Relationships Matter",
            "Be Open, Honest and Constructive",
            "Demand Excellence",
            "Take Intelligent Risks",
            "Act Like an Owner"
        ],
        "common_questions": [
            "Design LinkedIn's connection recommendation system",
            "How would you improve LinkedIn's feed algorithm?",
            "Tell me about a time you built strong relationships at work",
            "Design a professional skills endorsement system",
            "How do you handle constructive feedback?"
        ],
        "tips": [
            "Understand LinkedIn's professional mission",
            "Prepare for graph-based problems",
            "Show relationship-building skills",
            "Demonstrate data-driven thinking",
            "Know LinkedIn's products well"
        ],
        "interview_format": """
LinkedIn interviews balance technical skills with culture fit.
- Strong emphasis on 'Members First' mentality
- Graph algorithms and recommendations common
- Culture Add interview assesses values alignment
- Professional communication is highly valued
- Part of Microsoft family (growth mindset)
"""
    },
    "stripe": {
        "name": "Stripe",
        "logo": "💳",
        "color": "#635BFF",
        "interview_style": "Technical depth and user empathy",
        "rounds": ["Recruiter Screen", "Technical Phone", "Onsite (4-5 rounds)", "Founder Chat"],
        "focus_areas": [
            "Technical excellence",
            "API design and developer experience",
            "Financial systems and payments",
            "User empathy",
            "Writing and communication"
        ],
        "leadership_principles": [
            "Users First",
            "Move with Urgency",
            "Think Rigorously",
            "Trust and Amplify",
            "Global Optimization",
            "The Stripe Service",
            "Optimism"
        ],
        "common_questions": [
            "Design a payment processing system",
            "How would you improve Stripe's API documentation?",
            "Tell me about a time you simplified a complex system",
            "Design a fraud detection system",
            "How do you approach writing technical documentation?"
        ],
        "tips": [
            "Strong writing skills are essential",
            "Understand payments and financial systems",
            "Focus on developer experience",
            "Prepare for rigorous technical discussions",
            "Show user empathy in all answers"
        ],
        "interview_format": """
Stripe interviews emphasize technical depth and communication.
- Written communication is heavily valued
- API design questions are common
- Financial domain knowledge helpful
- Founder chat for culture fit
- Focus on simplicity and user experience
"""
    },
    "general": {
        "name": "General Tech Interview",
        "logo": "💻",
        "color": "#6366F1",
        "interview_style": "Standard tech interview format",
        "rounds": ["Phone Screen", "Technical Interview", "Onsite", "Hiring Decision"],
        "focus_areas": [
            "Data structures and algorithms",
            "System design",
            "Behavioral questions",
            "Technical communication",
            "Problem-solving approach"
        ],
        "leadership_principles": [
            "Technical Excellence",
            "Collaboration",
            "Communication",
            "Problem-Solving",
            "Continuous Learning"
        ],
        "common_questions": [
            "Tell me about yourself",
            "Why are you interested in this role?",
            "Describe a challenging technical project",
            "How do you handle disagreements?",
            "Where do you see yourself in 5 years?"
        ],
        "tips": [
            "Practice coding problems regularly",
            "Prepare STAR format stories",
            "Research the company thoroughly",
            "Ask thoughtful questions",
            "Follow up after the interview"
        ],
        "interview_format": """
Standard tech interview format varies by company.
- Usually 1-2 phone screens
- Onsite typically 4-6 rounds
- Mix of coding, system design, and behavioral
- Prepare for whiteboard or online coding
- Research company-specific processes
"""
    }
}


# ============================================================================
# Company-Specific Interview Prompts
# ============================================================================

def get_company_interview_prompt(company_key: str) -> str:
    """Generate company-specific interview prompt for the AI."""
    company = COMPANY_PROFILES.get(company_key, COMPANY_PROFILES["general"])
    
    principles_text = "\n".join([f"- {p}" for p in company["leadership_principles"]])
    focus_text = "\n".join([f"- {f}" for f in company["focus_areas"]])
    
    return f"""
=== COMPANY-SPECIFIC INTERVIEW: {company['name']} ===

You are conducting a mock interview specifically for {company['name']}.

INTERVIEW STYLE: {company['interview_style']}

KEY FOCUS AREAS:
{focus_text}

{company['name'].upper()} LEADERSHIP PRINCIPLES/VALUES:
{principles_text}

INTERVIEW FORMAT:
{company['interview_format']}

IMPORTANT INSTRUCTIONS:
1. Tailor your questions to {company['name']}'s interview style
2. Reference their leadership principles in behavioral questions
3. Ask questions that assess fit with {company['name']}'s culture
4. For technical questions, consider {company['name']}'s scale and products
5. Provide feedback aligned with what {company['name']} interviewers look for
6. Mention specific {company['name']} products or services when relevant
"""


def get_company_specific_questions(company_key: str, interview_type: str = "Mixed") -> List[str]:
    """Get company-specific sample questions."""
    company = COMPANY_PROFILES.get(company_key, COMPANY_PROFILES["general"])
    return company.get("common_questions", [])


def get_company_tips(company_key: str) -> List[str]:
    """Get interview tips for a specific company."""
    company = COMPANY_PROFILES.get(company_key, COMPANY_PROFILES["general"])
    return company.get("tips", [])


def get_company_list() -> List[Dict]:
    """Get list of supported companies for display."""
    return [
        {
            "key": key,
            "name": profile["name"],
            "logo": profile["logo"],
            "color": profile["color"],
            "display": f"{profile['logo']} {profile['name']}"
        }
        for key, profile in COMPANY_PROFILES.items()
    ]


def get_company_info(company_key: str) -> Dict:
    """Get full information about a company."""
    return COMPANY_PROFILES.get(company_key, COMPANY_PROFILES["general"])


# ============================================================================
# Company-Specific Report Generation
# ============================================================================

def get_company_report_prompt(company_key: str) -> str:
    """Generate company-specific report evaluation prompt."""
    company = COMPANY_PROFILES.get(company_key, COMPANY_PROFILES["general"])
    
    principles_text = "\n".join([f"- {p}" for p in company["leadership_principles"]])
    
    return f"""
When generating the interview report, evaluate the candidate specifically against {company['name']}'s standards:

{company['name'].upper()} EVALUATION CRITERIA:
{principles_text}

Include in your report:
1. How well the candidate demonstrated {company['name']}'s values
2. Specific feedback on {company['name']}'s interview focus areas
3. Likelihood of success in {company['name']}'s interview process
4. Targeted recommendations for {company['name']} preparation
5. Comparison to typical {company['name']} candidate expectations
"""


# ============================================================================
# FAANG Quick Access
# ============================================================================

FAANG_COMPANIES = ["meta", "amazon", "apple", "netflix", "google"]
FAANG_PLUS = FAANG_COMPANIES + ["microsoft"]
TOP_TECH = FAANG_PLUS + ["uber", "airbnb", "linkedin", "stripe"]


def get_faang_companies() -> List[Dict]:
    """Get FAANG company profiles."""
    return [
        {
            "key": key,
            **COMPANY_PROFILES[key]
        }
        for key in FAANG_COMPANIES
    ]


def get_top_tech_companies() -> List[Dict]:
    """Get top tech company profiles."""
    return [
        {
            "key": key,
            **COMPANY_PROFILES[key]
        }
        for key in TOP_TECH
    ]


# ============================================================================
# Company Comparison
# ============================================================================

def compare_companies(company_keys: List[str]) -> Dict:
    """Compare interview styles across multiple companies."""
    comparison = {
        "companies": [],
        "common_focus": [],
        "unique_aspects": {}
    }
    
    all_focus_areas = []
    
    for key in company_keys:
        company = COMPANY_PROFILES.get(key)
        if company:
            comparison["companies"].append({
                "key": key,
                "name": company["name"],
                "style": company["interview_style"],
                "rounds": len(company["rounds"]),
                "principles_count": len(company["leadership_principles"])
            })
            all_focus_areas.extend(company["focus_areas"])
            comparison["unique_aspects"][key] = {
                "unique_principles": company["leadership_principles"][:3],
                "interview_format": company["interview_format"][:200]
            }
    
    # Find common focus areas
    from collections import Counter
    focus_counter = Counter(all_focus_areas)
    comparison["common_focus"] = [area for area, count in focus_counter.items() if count > 1]
    
    return comparison
