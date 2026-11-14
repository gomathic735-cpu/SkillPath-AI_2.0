# ==========================================================
# SKILLPATH AI - COLLABORATIVE AGENTIC CAREER PLANNER
# ==========================================================

from datetime import datetime


# ----------------------------------------------------------
# AGENT 1: PROFILE AGENT
# ----------------------------------------------------------

def profile_agent(current_skills, assessment_history, target_role):

    scores = {}

    for item in assessment_history:

        skill = item.get("skill", "")
        score = int(item.get("score", 0))

        if skill not in scores:
            scores[skill] = []

        scores[skill].append(score)

    average_scores = {}

    for skill, values in scores.items():
        average_scores[skill] = round(
            sum(values) / len(values), 1
        )

    profile = {
        "current_skills": current_skills,
        "assessment_scores": average_scores,
        "target_role": target_role,
        "profile_created": datetime.now().strftime(
            "%d-%m-%Y %I:%M %p"
        )
    }

    return profile


# ----------------------------------------------------------
# AGENT 2: SKILL GAP AGENT
# ----------------------------------------------------------

def skill_gap_agent(profile, role_requirements):

    target_role = profile["target_role"]

    required_skills = role_requirements.get(
        target_role, []
    )

    current_skills = profile["current_skills"]

    matched_skills = [
        skill for skill in required_skills
        if skill in current_skills
    ]

    missing_skills = [
        skill for skill in required_skills
        if skill not in current_skills
    ]

    if required_skills:

        match_percentage = round(
            len(matched_skills) / len(required_skills) * 100
        )

    else:
        match_percentage = 0

    return {
        "required_skills": required_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "match_percentage": match_percentage
    }


# ----------------------------------------------------------
# AGENT 3: LEARNING AGENT
# ----------------------------------------------------------

def learning_agent(skill_gaps):

    learning_resources = {

        "Python": [
            "Revise variables and data types",
            "Practice conditions and loops",
            "Build a Python mini project"
        ],

        "Java": [
            "Understand Java syntax and data types",
            "Practice OOP concepts",
            "Build a Java application"
        ],

        "SQL": [
            "Practice SELECT and WHERE queries",
            "Learn JOIN and GROUP BY",
            "Create and query a sample database"
        ],

        "Web Development": [
            "Learn HTML page structure",
            "Practice CSS styling",
            "Build an interactive JavaScript webpage"
        ],

        "Data Analysis": [
            "Practice Excel data handling",
            "Learn data visualization",
            "Analyze a real-world dataset"
        ],

        "Machine Learning": [
            "Learn basic statistics",
            "Practice Python data preprocessing",
            "Build a simple prediction model"
        ],

        "Cloud": [
            "Understand cloud computing basics",
            "Explore cloud storage and deployment",
            "Deploy a small application"
        ],

        "Communication": [
            "Practice explaining technical concepts",
            "Improve presentation skills",
            "Participate in group discussions"
        ],

        "Version Control": [
            "Learn Git basics",
            "Practice commits and branches",
            "Upload a project to GitHub"
        ],

        "C Programming": [
            "Practice variables and operators",
            "Learn functions and arrays",
            "Build a small C program"
        ],

        "C++": [
            "Understand C++ syntax",
            "Practice classes and objects",
            "Solve programming problems"
        ]
    }

    roadmap = []

    for skill in skill_gaps["missing_skills"]:

        tasks = learning_resources.get(
            skill,
            [
                f"Learn the fundamentals of {skill}",
                f"Practice important {skill} concepts",
                f"Build a small {skill} project"
            ]
        )

        roadmap.append({
            "skill": skill,
            "tasks": tasks,
            "status": "Not Started"
        })

    return roadmap


# ----------------------------------------------------------
# AGENT 4: MENTOR AGENT
# ----------------------------------------------------------

def mentor_agent(profile, skill_gaps):

    scores = profile["assessment_scores"]

    guidance = []
    priority_skills = []

    for skill, score in scores.items():

        if score < 40:

            guidance.append(
                f"{skill}: Your score is {score}%. "
                "Revise beginner concepts and retake the assessment."
            )

            priority_skills.append(skill)

        elif score < 70:

            guidance.append(
                f"{skill}: Your score is {score}%. "
                "Practice more questions before moving to the next level."
            )

        else:

            guidance.append(
                f"{skill}: Your score is {score}%. "
                "Good progress! Try intermediate or advanced topics."
            )

    if not scores:

        guidance.append(
            "Complete your first skill assessment "
            "to receive performance-based mentoring."
        )

    if skill_gaps["missing_skills"]:

        guidance.append(
            "Focus on the missing skills identified "
            "for your selected career goal."
        )

    else:

        guidance.append(
            "Your selected skills cover all listed "
            "requirements for this role. Continue building projects."
        )

    return {
        "guidance": guidance,
        "priority_skills": priority_skills
    }


# ----------------------------------------------------------
# AGENT ORCHESTRATOR
# ----------------------------------------------------------

def run_agentic_workflow(
    current_skills,
    assessment_history,
    target_role,
    role_requirements
):

    # Shared context passed between agents

    profile = profile_agent(
        current_skills,
        assessment_history,
        target_role
    )

    skill_gaps = skill_gap_agent(
        profile,
        role_requirements
    )

    roadmap = learning_agent(
        skill_gaps
    )

    mentor = mentor_agent(
        profile,
        skill_gaps
    )

    result = {

        "profile": profile,

        "skill_analysis": skill_gaps,

        "learning_roadmap": roadmap,

        "mentor": mentor,

        "agent_trace": [
            {
                "agent": "Profile Agent",
                "action": "Analyzed learner profile and assessment history",
                "status": "Completed"
            },
            {
                "agent": "Skill Gap Agent",
                "action": "Compared learner skills with career requirements",
                "status": "Completed"
            },
            {
                "agent": "Learning Agent",
                "action": "Generated a personalized learning roadmap",
                "status": "Completed"
            },
            {
                "agent": "Mentor Agent",
                "action": "Generated performance-based guidance",
                "status": "Completed"
            }
        ]
    }

    return result