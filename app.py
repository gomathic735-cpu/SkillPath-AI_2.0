import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import re
import io

from datetime import datetime
from pypdf import PdfReader
from docx import Document
from agentic_planner import run_agentic_workflow

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="SkillPath AI 2.3",
    page_icon="🎯",
    layout="wide"
)

DB_NAME = "skillpath.db"


# =====================================================
# DATABASE
# =====================================================

def get_connection():
    return sqlite3.connect(
        DB_NAME,
        check_same_thread=False
    )


def initialize_database():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS skill_scores (
            skill TEXT PRIMARY KEY,
            claimed INTEGER,
            practiced INTEGER,
            proven INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS assessment_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill TEXT,
            level TEXT,
            score INTEGER,
            correct_answers INTEGER,
            total_questions INTEGER,
            attempted_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS assessment_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            skill TEXT,
            level TEXT,
            topic TEXT,
            question TEXT,
            selected_answer TEXT,
            correct_answer TEXT,
            is_correct INTEGER,
            attempted_at TEXT
        )
    """)

    default_skills = [
        ("Python", 0, 0, None),
        ("Java", 0, 0, None),
        ("SQL", 0, 0, None),
        ("Communication", 0, 0, None)
    ]

    for skill in default_skills:

        cur.execute("""
            INSERT OR IGNORE INTO skill_scores
            (skill, claimed, practiced, proven)
            VALUES (?, ?, ?, ?)
        """, skill)

        cur.execute("""
            SELECT MAX(score)
            FROM assessment_sessions
            WHERE skill=?
        """, (skill[0],))

        actual_score = cur.fetchone()[0]

        if actual_score is None:

            cur.execute("""
                UPDATE skill_scores
                SET claimed=0,
                    practiced=0,
                    proven=NULL
                WHERE skill=?
            """, (skill[0],))

        else:

            cur.execute("""
                UPDATE skill_scores
                SET proven=?
                WHERE skill=?
            """, (actual_score, skill[0]))

    conn.commit()
    conn.close()


initialize_database()


def get_skills():

    conn = get_connection()

    df = pd.read_sql_query(
        "SELECT * FROM skill_scores",
        conn
    )

    conn.close()

    return df


def update_proven_score(skill, new_score):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT proven
        FROM skill_scores
        WHERE skill=?
    """, (skill,))

    result = cur.fetchone()

    if result:

        old_score = result[0]

        if old_score is None:
            updated_score = new_score
        else:
            updated_score = max(old_score, new_score)

        cur.execute("""
            UPDATE skill_scores
            SET proven=?
            WHERE skill=?
        """, (updated_score, skill))

    conn.commit()
    conn.close()


# =====================================================
# QUESTION BANK
# =====================================================

QUESTION_BANK = {

    "Python": {

        "Beginner": [

            ("Variables", "Which symbol is used for assignment?",
             ["==", "=", "!=", "+"], "=", "The = operator assigns a value."),

            ("Data Types", "Which data type stores True or False?",
             ["int", "str", "bool", "float"], "bool",
             "Boolean values are True and False."),

            ("Output", "What is the output of print(2 + 3)?",
             ["23", "5", "2+3", "Error"], "5",
             "The + operator adds two numbers."),

            ("Strings", "Which function gives the length of a string?",
             ["count()", "length()", "len()", "size()"], "len()",
             "len() returns the number of characters."),

            ("Conditions", "Which keyword is used for a condition?",
             ["for", "if", "def", "class"], "if",
             "The if statement checks a condition.")
        ],

        "Intermediate": [

            ("Loops", "Which loop runs while a condition is True?",
             ["for", "while", "if", "switch"], "while",
             "A while loop continues while its condition is True."),

            ("Functions", "Which keyword defines a function?",
             ["function", "define", "def", "fun"], "def",
             "Python uses def to define functions."),

            ("Lists", "Which method adds an item to a list?",
             ["add()", "append()", "insertEnd()", "push()"], "append()",
             "append() adds an item at the end."),

            ("Dictionary", "Which brackets are used for dictionaries?",
             ["[]", "()", "{}", "<>"], "{}",
             "Dictionaries use curly brackets."),

            ("Exception Handling", "Which block handles exceptions?",
             ["try-except", "if-else", "for-while", "def-return"],
             "try-except", "try-except handles runtime exceptions.")
        ],

        "Advanced": [

            ("OOP", "Which concept allows a class to use another class?",
             ["Inheritance", "Iteration", "Compilation", "Casting"],
             "Inheritance", "Inheritance allows a class to reuse another class."),

            ("Decorators", "Which symbol is used before a decorator?",
             ["$", "#", "@", "&"], "@",
             "Python decorators use the @ symbol."),

            ("Generators", "Which keyword produces a generator value?",
             ["return", "yield", "break", "pass"], "yield",
             "yield produces values from a generator."),

            ("Lambda", "Lambda functions are generally:",
             ["Anonymous functions", "Classes", "Modules", "Loops"],
             "Anonymous functions", "Lambda creates a small anonymous function."),

            ("Memory", "Which keyword is used to create a class?",
             ["object", "class", "new", "struct"], "class",
             "The class keyword defines a class.")
        ]
    },

    "Java": {

        "Beginner": [

            ("Output", "Which method is the starting point of Java?",
             ["start()", "main()", "run()", "execute()"], "main()",
             "Java programs commonly start from main()."),

            ("Data Types", "Which type stores whole numbers?",
             ["double", "String", "int", "boolean"], "int",
             "int stores integer values."),

            ("Output", "Which statement prints output?",
             ["System.out.println()", "print()", "echo()", "display()"],
             "System.out.println()", "This statement prints output in Java."),

            ("Class", "Which keyword defines a class?",
             ["define", "class", "struct", "object"], "class",
             "Java uses class to define a class."),

            ("Conditions", "Which keyword checks a condition?",
             ["if", "loop", "class", "void"], "if",
             "if checks a condition.")
        ],

        "Intermediate": [

            ("OOP", "Which concept supports method overloading?",
             ["Polymorphism", "Encapsulation", "Abstraction", "Inheritance"],
             "Polymorphism", "Method overloading is compile-time polymorphism."),

            ("Inheritance", "Which keyword inherits a class?",
             ["implements", "extends", "inherits", "super"], "extends",
             "extends is used for class inheritance."),

            ("Arrays", "Array indexing starts from:",
             ["1", "0", "-1", "2"], "0",
             "Java arrays use zero-based indexing."),

            ("Exceptions", "Which block handles exceptions?",
             ["catch", "final", "static", "public"], "catch",
             "catch handles exceptions."),

            ("Strings", "Which method compares string values?",
             ["==", "equals()", "compare", "same()"], "equals()",
             "equals() compares string contents.")
        ],

        "Advanced": [

            ("Collections", "Which collection does not allow duplicates?",
             ["ArrayList", "HashSet", "LinkedList", "Vector"],
             "HashSet", "HashSet stores unique elements."),

            ("Threads", "Which method starts a new thread?",
             ["run()", "start()", "execute()", "begin()"], "start()",
             "start() begins a new thread."),

            ("Interfaces", "Which keyword is used to implement an interface?",
             ["extends", "implements", "interface", "abstract"],
             "implements", "A class uses implements for an interface."),

            ("Streams", "Which method converts a stream into a list?",
             ["collect()", "filter()", "map()", "sort()"], "collect()",
             "collect() gathers stream results."),

            ("Access Modifiers", "Which modifier allows access from anywhere?",
             ["private", "protected", "public", "default"], "public",
             "public provides broad accessibility.")
        ]
    },

    "SQL": {

        "Beginner": [

            ("SELECT", "Which command retrieves data?",
             ["INSERT", "SELECT", "DELETE", "UPDATE"], "SELECT",
             "SELECT retrieves records from a table."),

            ("WHERE", "Which clause filters records?",
             ["ORDER BY", "WHERE", "GROUP BY", "JOIN"], "WHERE",
             "WHERE filters records based on conditions."),

            ("INSERT", "Which command adds a new record?",
             ["ADD", "INSERT", "CREATE", "ALTER"], "INSERT",
             "INSERT adds records."),

            ("DELETE", "Which command removes records?",
             ["REMOVE", "DROP", "DELETE", "CLEAR"], "DELETE",
             "DELETE removes records from a table."),

            ("Sorting", "Which clause sorts query results?",
             ["SORT", "ORDER BY", "GROUP BY", "FILTER"], "ORDER BY",
             "ORDER BY sorts results.")
        ],

        "Intermediate": [

            ("Aggregate Functions", "Which function counts rows?",
             ["SUM()", "COUNT()", "AVG()", "MAX()"], "COUNT()",
             "COUNT() returns the number of rows."),

            ("GROUP BY", "Which clause groups similar values?",
             ["ORDER BY", "GROUP BY", "WHERE", "LIMIT"], "GROUP BY",
             "GROUP BY groups rows with matching values."),

            ("JOIN", "Which JOIN returns matching rows from both tables?",
             ["INNER JOIN", "LEFT JOIN", "CROSS JOIN", "FULL JOIN"],
             "INNER JOIN", "INNER JOIN returns matching rows."),

            ("Constraints", "Which constraint prevents duplicate values?",
             ["NOT NULL", "UNIQUE", "DEFAULT", "CHECK"], "UNIQUE",
             "UNIQUE prevents duplicate values."),

            ("Filtering", "Which operator checks a range?",
             ["LIKE", "BETWEEN", "IN", "IS"], "BETWEEN",
             "BETWEEN checks values within a range.")
        ],

        "Advanced": [

            ("Subqueries", "A query inside another query is called:",
             ["Nested loop", "Subquery", "Join", "Trigger"], "Subquery",
             "A subquery is a query inside another query."),

            ("Indexes", "What is the main purpose of an index?",
             ["Delete data", "Improve retrieval speed",
              "Change table name", "Create duplicates"],
             "Improve retrieval speed", "Indexes can speed up data retrieval."),

            ("Views", "A view is generally a:",
             ["Virtual table", "Physical database", "Trigger", "Index"],
             "Virtual table", "A view is a virtual table based on a query."),

            ("Transactions", "Which command saves a transaction?",
             ["ROLLBACK", "COMMIT", "DELETE", "DROP"], "COMMIT",
             "COMMIT saves transaction changes."),

            ("Window Functions", "Which clause defines a window?",
             ["OVER()", "GROUP()", "WINDOW BY", "PARTITION()"],
             "OVER()", "OVER() defines the window for a window function.")
        ]
    }
}
# =====================================================
# SKILL KEYWORDS
# =====================================================

SKILL_KEYWORDS = {

    "Python": [
        "python", "pandas", "numpy", "django",
        "flask", "streamlit", "automation"
    ],

    "Java": [
        "java", "spring", "spring boot",
        "jdbc", "hibernate", "oop"
    ],

    "SQL": [
        "sql", "mysql", "postgresql",
        "sqlite", "database", "joins"
    ],

    "Web Development": [
        "html", "css", "javascript", "react",
        "node.js", "bootstrap"
    ],

    "Data Analysis": [
        "excel", "power bi", "tableau",
        "data analysis", "data visualization", "statistics"
    ],

    "Machine Learning": [
        "machine learning", "deep learning",
        "tensorflow", "pytorch", "scikit-learn",
        "artificial intelligence"
    ],

    "Cloud": [
        "aws", "azure", "google cloud",
        "cloud computing"
    ],

    "Communication": [
        "communication", "presentation",
        "teamwork", "leadership", "collaboration"
    ],

    "Version Control": [
        "git", "github", "gitlab", "version control"
    ],

    "C Programming": [
        "c programming", "c language", "embedded c"
    ],

    "C++": [
        "c++", "cpp", "stl"
    ]
}


# =====================================================
# JOB ROLE REQUIREMENTS
# =====================================================

JOB_ROLES = {

    "Python Developer": [
        "Python",
        "SQL",
        "Version Control",
        "Web Development"
    ],

    "Java Developer": [
        "Java",
        "SQL",
        "Version Control",
        "Web Development"
    ],

    "Data Analyst": [
        "SQL",
        "Data Analysis",
        "Python",
        "Communication"
    ],

    "Frontend Developer": [
        "Web Development",
        "Version Control",
        "Communication"
    ],

    "Machine Learning Engineer": [
        "Python",
        "Machine Learning",
        "SQL",
        "Data Analysis"
    ],

    "Full Stack Developer": [
        "Python",
        "Java",
        "SQL",
        "Web Development",
        "Version Control"
    ],

    "Software Engineer": [
        "Python",
        "Java",
        "SQL",
        "Version Control",
        "Communication"
    ],

    "Cloud Engineer": [
        "Cloud",
        "Python",
        "Version Control",
        "Communication"
    ]
}


# =====================================================
# RESUME TEXT EXTRACTION
# =====================================================

def extract_resume_text(uploaded_file):

    if uploaded_file is None:
        return ""

    file_name = uploaded_file.name.lower()

    try:

        if file_name.endswith(".pdf"):

            reader = PdfReader(uploaded_file)

            text_content = ""

            for page in reader.pages:
                page_text = page.extract_text()

                if page_text:
                    text_content += page_text + "\n"

            return text_content

        elif file_name.endswith(".docx"):

            document = Document(uploaded_file)

            text_content = ""

            for paragraph in document.paragraphs:
                text_content += paragraph.text + "\n"

            return text_content

        elif file_name.endswith(".txt"):

            return uploaded_file.read().decode(
                "utf-8",
                errors="ignore"
            )

        else:

            return ""

    except Exception as error:

        st.error(f"Resume reading error: {error}")

        return ""


# =====================================================
# SKILL DETECTION
# =====================================================

def detect_skills(resume_text):

    detected_skills = []

    text = resume_text.lower()

    for skill, keywords in SKILL_KEYWORDS.items():

        found = False

        for keyword in keywords:

            pattern = r"\b" + re.escape(keyword.lower()) + r"\b"

            if re.search(pattern, text):

                found = True
                break

        if found:
            detected_skills.append(skill)

    return detected_skills


# =====================================================
# RESUME ANALYSIS
# =====================================================

def analyze_resume(resume_text):

    detected_skills = detect_skills(resume_text)

    word_count = len(resume_text.split())

    sections = {

        "Education": [
            "education",
            "academic",
            "degree",
            "college"
        ],

        "Experience": [
            "experience",
            "internship",
            "work experience"
        ],

        "Projects": [
            "projects",
            "project"
        ],

        "Certifications": [
            "certification",
            "certifications",
            "certificate"
        ],

        "Skills": [
            "skills",
            "technical skills"
        ]
    }

    section_results = {}

    lower_text = resume_text.lower()

    for section, keywords in sections.items():

        section_results[section] = any(
            keyword in lower_text
            for keyword in keywords
        )

    suggestions = []

    for section, found in section_results.items():

        if not found:

            suggestions.append(
                f"Consider adding a clear {section} section."
            )

    if len(detected_skills) < 3:

        suggestions.append(
            "Add more relevant technical skills to your resume."
        )

    if word_count < 100:

        suggestions.append(
            "Your resume content is short. Add more details about your education and projects."
        )

    if not suggestions:

        suggestions.append(
            "Your resume contains the main sections. Continue improving project descriptions and measurable achievements."
        )

    return {

        "detected_skills": detected_skills,

        "word_count": word_count,

        "sections": section_results,

        "suggestions": suggestions,

        "skill_count": len(detected_skills)
    }


# =====================================================
# JOB ROLE MATCHING
# =====================================================

def calculate_job_matches(user_skills):

    results = []

    for role, required_skills in JOB_ROLES.items():

        matched = []

        missing = []

        for skill in required_skills:

            if skill in user_skills:
                matched.append(skill)

            else:
                missing.append(skill)

        if len(required_skills) > 0:

            percentage = round(
                len(matched) / len(required_skills) * 100
            )

        else:

            percentage = 0

        results.append({

            "Role": role,

            "Match": percentage,

            "Matched Skills": ", ".join(matched),

            "Missing Skills": ", ".join(missing),

            "Required Skills": len(required_skills)
        })

    results.sort(
        key=lambda item: item["Match"],
        reverse=True
    )

    return results


# =====================================================
# AI RECOMMENDATIONS
# =====================================================

def get_recommendations():

    conn = get_connection()

    skills_df = pd.read_sql_query(
        "SELECT * FROM skill_scores",
        conn
    )

    history_df = pd.read_sql_query(
        """
        SELECT skill, level, score, attempted_at
        FROM assessment_sessions
        ORDER BY id DESC
        """,
        conn
    )

    answers_df = pd.read_sql_query(
        """
        SELECT skill, topic, is_correct
        FROM assessment_answers
        ORDER BY id DESC
        """,
        conn
    )

    conn.close()

    recommendations = []

    if skills_df.empty:

        return [
            "Start by selecting a skill and completing an assessment."
        ]

    for _, row in skills_df.iterrows():

        skill = row["skill"]

        proven = row["proven"]

        if pd.isna(proven):

            recommendations.append(
                f"{skill}: Complete an assessment to understand your current skill level."
            )

        elif proven < 40:

            recommendations.append(
                f"{skill}: Your current proven score is {proven}%. Revise basic concepts and practise beginner questions."
            )

        elif proven < 70:

            recommendations.append(
                f"{skill}: Your current proven score is {proven}%. Practise more questions and strengthen intermediate concepts."
            )

        else:

            recommendations.append(
                f"{skill}: Good progress with {proven}%. Try advanced topics and build a practical project."
            )

    if not history_df.empty:

        latest = history_df.iloc[0]

        recommendations.append(
            f"Your latest assessment was in {latest['skill']} with a score of {latest['score']}%."
        )

    if not answers_df.empty:

        incorrect = answers_df[
            answers_df["is_correct"] == 0
        ]

        if not incorrect.empty:

            weak_topics = (
                incorrect.groupby("topic")
                .size()
                .sort_values(ascending=False)
            )

            for topic, count in weak_topics.head(3).items():

                recommendations.append(
                    f"Revision priority: Practise {topic}. You answered {count} question(s) incorrectly in this topic."
                )

    return recommendations


# =====================================================
# PDF REPORT GENERATOR
# =====================================================

def create_pdf_report():

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=20
    )

    story = []

    story.append(
        Paragraph(
            "SkillPath AI - Learning Progress Report",
            title_style
        )
    )

    story.append(
        Paragraph(
            f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
            styles["Normal"]
        )
    )

    story.append(Spacer(1, 20))

    # Assessment history

    conn = get_connection()

    history_df = pd.read_sql_query(
        """
        SELECT skill, level, score,
               correct_answers, total_questions, attempted_at
        FROM assessment_sessions
        ORDER BY id DESC
        """,
        conn
    )

    skills_df = pd.read_sql_query(
        "SELECT * FROM skill_scores",
        conn
    )

    conn.close()

    story.append(
        Paragraph("Assessment History", styles["Heading2"])
    )

    if not history_df.empty:

        table_data = [[
            "Skill",
            "Level",
            "Score",
            "Correct",
            "Total"
        ]]

        for _, row in history_df.iterrows():

            table_data.append([

                str(row["skill"]),

                str(row["level"]),

                str(row["score"]) + "%",

                str(row["correct_answers"]),

                str(row["total_questions"])
            ])

        table = Table(
            table_data,
            repeatRows=1
        )

        table.setStyle(
            TableStyle([

                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),

                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),

                ("ALIGN", (0, 0), (-1, -1), "CENTER"),

                ("PADDING", (0, 0), (-1, -1), 7)
            ])
        )

        story.append(table)

    else:

        story.append(
            Paragraph(
                "No assessments completed yet.",
                styles["Normal"]
            )
        )

    story.append(Spacer(1, 20))

    # Skill profile

    story.append(
        Paragraph("Skill Profile", styles["Heading2"])
    )

    if not skills_df.empty:

        skill_data = [[
            "Skill",
            "Claimed",
            "Practiced",
            "Proven"
        ]]

        for _, row in skills_df.iterrows():

            proven = (
                "Not Assessed"
                if pd.isna(row["proven"])
                else str(row["proven"]) + "%"
            )

            skill_data.append([

                str(row["skill"]),

                str(row["claimed"]),

                str(row["practiced"]),

                proven
            ])

        skill_table = Table(
            skill_data,
            repeatRows=1
        )

        skill_table.setStyle(
            TableStyle([

                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),

                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),

                ("ALIGN", (0, 0), (-1, -1), "CENTER"),

                ("PADDING", (0, 0), (-1, -1), 7)
            ])
        )

        story.append(skill_table)

    story.append(Spacer(1, 20))

    # Recommendations

    story.append(
        Paragraph("Learning Recommendations", styles["Heading2"])
    )

    recommendations = get_recommendations()

    for recommendation in recommendations:

        safe_text = (
            recommendation
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        story.append(
            Paragraph(
                "• " + safe_text,
                styles["Normal"]
            )
        )

        story.append(Spacer(1, 6))

    document.build(story)

    buffer.seek(0)

    return buffer
    # =====================================================
# NAVIGATION
# =====================================================

st.sidebar.title("🎯 SkillPath AI")
st.sidebar.caption("Your Personal Career Development Platform")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Skill DNA",
        "Skill Proof Lab",
        "Assessment History",
        "AI Recommendations",
        "Performance Analytics",
        "Career Intelligence",
        "Adaptive Learning",
        "What-If Simulator",
        "Resume Analyzer",
        "Job Role Matching",
        "Agentic Career Planner",
        "PDF Report Download"
    ]
)

st.sidebar.divider()
st.sidebar.info("Build Skills. Prove Skills. Grow Your Career.")


# =====================================================
# DASHBOARD
# =====================================================

if page == "Dashboard":

    st.title("🎯 SkillPath AI Dashboard")

    st.write(
        "Welcome to your personal skill development platform."
    )

    skills_df = get_skills()

    conn = get_connection()

    history_df = pd.read_sql_query(
        "SELECT * FROM assessment_sessions",
        conn
    )

    conn.close()

    total_skills = len(skills_df)

    total_assessments = len(history_df)

    if not history_df.empty:
        average_score = round(history_df["score"].mean(), 1)
    else:
        average_score = 0

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Skills", total_skills)
    col2.metric("Assessments", total_assessments)
    col3.metric("Average Score", f"{average_score}%")

    st.divider()

    st.subheader("📊 Your Skill Overview")

    if not skills_df.empty:

        chart_df = skills_df.copy()

        chart_df["proven"] = chart_df["proven"].fillna(0)

        fig = px.bar(
            chart_df,
            x="skill",
            y="proven",
            title="Proven Skill Scores",
            labels={
                "skill": "Skills",
                "proven": "Score (%)"
            }
        )

        fig.update_layout(
            yaxis_range=[0, 100]
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.divider()

    st.subheader("🚀 Quick Actions")

    col1, col2 = st.columns(2)

    with col1:

        st.info(
            "Complete skill assessments to measure your actual knowledge."
        )

    with col2:

        st.info(
            "Explore career matches and personalized learning recommendations."
        )


# =====================================================
# SKILL DNA
# =====================================================

elif page == "Skill DNA":

    st.title("🧬 Skill DNA")

    st.write(
        "Understand your current skills and identify your strengths."
    )

    skills_df = get_skills()

    st.subheader("Your Skill Profile")

    st.dataframe(
        skills_df,
        use_container_width=True
    )

    st.divider()

    st.subheader("Add a Skill")

    skill_name = st.selectbox(
        "Choose a skill",
        list(SKILL_KEYWORDS.keys())
    )

    if st.button("Add Skill"):

        conn = get_connection()

        cur = conn.cursor()

        cur.execute(
            """
            INSERT OR IGNORE INTO skill_scores
            (skill, claimed, practiced, proven)
            VALUES (?, 0, 0, NULL)
            """,
            (skill_name,)
        )

        conn.commit()
        conn.close()

        st.success("Skill added successfully!")
        st.rerun()

    st.divider()

    if not skills_df.empty:

        chart_df = skills_df.copy()

        chart_df["proven"] = chart_df["proven"].fillna(0)

        fig = px.bar(
            chart_df,
            x="skill",
            y="proven",
            title="Your Proven Skills"
        )

        fig.update_layout(yaxis_range=[0, 100])

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# =====================================================
# SKILL PROOF LAB
# =====================================================

elif page == "Skill Proof Lab":

    st.title("🧪 Skill Proof Lab")

    st.write(
        "Test your knowledge through skill-based assessments."
    )

    skill = st.selectbox(
        "Select Skill",
        list(QUESTION_BANK.keys())
    )

    level = st.selectbox(
        "Select Difficulty",
        ["Beginner", "Intermediate", "Advanced"]
    )

    questions = QUESTION_BANK[skill][level]

    st.divider()

    st.subheader(f"{skill} - {level} Assessment")

    answers = []

    for index, question in enumerate(questions):

        topic, question_text, options, correct, explanation = question

        st.markdown(
            f"**Q{index + 1}. {question_text}**"
        )

        selected = st.radio(
            "Choose your answer",
            options,
            key=f"quiz_{skill}_{level}_{index}",
            index=None
        )

        answers.append({
            "topic": topic,
            "question": question_text,
            "selected": selected,
            "correct": correct,
            "explanation": explanation
        })

    if st.button(
        "Submit Assessment",
        use_container_width=True
    ):

        if any(answer["selected"] is None for answer in answers):

            st.warning("Please answer all questions.")

        else:

            correct_count = sum(
                1 for answer in answers
                if answer["selected"] == answer["correct"]
            )

            total = len(questions)

            score = round(
                correct_count / total * 100
            )

            attempted_at = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            conn = get_connection()

            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO assessment_sessions
                (
                    skill,
                    level,
                    score,
                    correct_answers,
                    total_questions,
                    attempted_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    skill,
                    level,
                    score,
                    correct_count,
                    total,
                    attempted_at
                )
            )

            session_id = cur.lastrowid

            for answer in answers:

                is_correct = int(
                    answer["selected"] == answer["correct"]
                )

                cur.execute(
                    """
                    INSERT INTO assessment_answers
                    (
                        session_id,
                        skill,
                        level,
                        topic,
                        question,
                        selected_answer,
                        correct_answer,
                        is_correct,
                        attempted_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        skill,
                        level,
                        answer["topic"],
                        answer["question"],
                        answer["selected"],
                        answer["correct"],
                        is_correct,
                        attempted_at
                    )
                )

            conn.commit()
            conn.close()

            update_proven_score(skill, score)

            st.session_state["last_assessment"] = {
                "skill": skill,
                "score": score,
                "correct": correct_count,
                "total": total,
                "answers": answers
            }

            st.rerun()

    if "last_assessment" in st.session_state:

        result = st.session_state["last_assessment"]

        st.divider()

        st.subheader("📋 Assessment Result")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Score",
            f'{result["score"]}%'
        )

        col2.metric(
            "Correct Answers",
            result["correct"]
        )

        col3.metric(
            "Total Questions",
            result["total"]
        )

        if result["score"] >= 70:

            st.success("Good work! Keep improving your skills.")

        else:

            st.warning(
                "Keep practising. Review the explanations below."
            )

        st.subheader("Answer Review")

        for index, answer in enumerate(result["answers"]):

            with st.expander(
                f"Question {index + 1}: {answer['topic']}"
            ):

                st.write(answer["question"])

                st.write(
                    f"Your Answer: {answer['selected']}"
                )

                st.write(
                    f"Correct Answer: {answer['correct']}"
                )

                st.info(answer["explanation"])


# =====================================================
# ASSESSMENT HISTORY
# =====================================================

elif page == "Assessment History":

    st.title("📚 Assessment History")

    conn = get_connection()

    history_df = pd.read_sql_query(
        """
        SELECT skill, level, score,
               correct_answers, total_questions, attempted_at
        FROM assessment_sessions
        ORDER BY id DESC
        """,
        conn
    )

    conn.close()

    if history_df.empty:

        st.info("No assessment records available.")

    else:

        st.dataframe(
            history_df,
            use_container_width=True
        )

        st.subheader("Assessment Score Trend")

        fig = px.line(
            history_df.sort_values("attempted_at"),
            x="attempted_at",
            y="score",
            color="skill",
            markers=True,
            title="Your Assessment Progress"
        )

        fig.update_layout(
            yaxis_range=[0, 100]
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# =====================================================
# AI RECOMMENDATIONS
# =====================================================

elif page == "AI Recommendations":

    st.title("🤖 AI Learning Recommendations")

    st.write(
        "Recommendations based on your assessment performance."
    )

    recommendations = get_recommendations()

    for index, recommendation in enumerate(
        recommendations,
        1
    ):

        st.info(
            f"{index}. {recommendation}"
        )


# =====================================================
# PERFORMANCE ANALYTICS
# =====================================================

elif page == "Performance Analytics":

    st.title("📈 Performance Analytics")

    conn = get_connection()

    history_df = pd.read_sql_query(
        "SELECT * FROM assessment_sessions",
        conn
    )

    conn.close()

    if history_df.empty:

        st.info("Complete an assessment to view analytics.")

    else:

        average = round(
            history_df["score"].mean(),
            1
        )

        highest = history_df["score"].max()

        lowest = history_df["score"].min()

        col1, col2, col3 = st.columns(3)

        col1.metric("Average Score", f"{average}%")

        col2.metric("Highest Score", f"{highest}%")

        col3.metric("Lowest Score", f"{lowest}%")

        st.divider()

        skill_performance = (
            history_df.groupby("skill")["score"]
            .mean()
            .reset_index()
        )

        fig = px.bar(
            skill_performance,
            x="skill",
            y="score",
            title="Average Performance by Skill"
        )

        fig.update_layout(
            yaxis_range=[0, 100]
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.subheader("Performance by Difficulty")

        level_performance = (
            history_df.groupby("level")["score"]
            .mean()
            .reset_index()
        )

        fig2 = px.bar(
            level_performance,
            x="level",
            y="score",
            title="Average Score by Difficulty"
        )

        st.plotly_chart(
            fig2,
            use_container_width=True
        )


# =====================================================
# CAREER INTELLIGENCE
# =====================================================

elif page == "Career Intelligence":

    st.title("💼 Career Intelligence")

    st.write(
        "Explore career requirements and compare them with your skills."
    )

    selected_role = st.selectbox(
        "Choose a career",
        list(JOB_ROLES.keys())
    )

    required_skills = JOB_ROLES[selected_role]

    st.subheader(selected_role)

    st.write("Skills required for this career:")

    for skill in required_skills:

        st.success(skill)

    st.divider()

    st.subheader("Career Preparation Suggestions")

    st.write("• Build at least two practical projects.")

    st.write("• Maintain a GitHub profile.")

    st.write("• Practise technical interview questions.")

    st.write("• Improve communication and presentation skills.")

    st.write("• Complete assessments to prove your knowledge.")


# =====================================================
# ADAPTIVE LEARNING
# =====================================================

elif page == "Adaptive Learning":

    st.title("🧠 Adaptive Learning")

    st.write(
        "Learning suggestions based on your assessment scores."
    )

    conn = get_connection()

    history_df = pd.read_sql_query(
        """
        SELECT skill, level, score
        FROM assessment_sessions
        ORDER BY id DESC
        """,
        conn
    )

    conn.close()

    if history_df.empty:

        st.info(
            "Complete an assessment to receive adaptive learning suggestions."
        )

    else:

        latest_scores = (
            history_df.drop_duplicates("skill")
        )

        for _, row in latest_scores.iterrows():

            skill = row["skill"]

            score = row["score"]

            st.subheader(skill)

            if score < 40:

                st.warning(
                    "Focus on beginner concepts and practise basic questions."
                )

            elif score < 70:

                st.info(
                    "Practise intermediate topics and strengthen your understanding."
                )

            else:

                st.success(
                    "Good performance! Try advanced topics and practical projects."
                )


# =====================================================
# WHAT-IF SIMULATOR
# =====================================================

elif page == "What-If Simulator":

    st.title("🔮 What-If Simulator")

    st.write(
        "Explore how additional assessment scores could affect your average."
    )

    conn = get_connection()

    history_df = pd.read_sql_query(
        "SELECT score FROM assessment_sessions",
        conn
    )

    conn.close()

    if history_df.empty:

        st.info(
            "Complete at least one assessment to use the simulator."
        )

    else:

        current_average = history_df["score"].mean()

        simulated_score = st.slider(
            "Choose a hypothetical next assessment score",
            0,
            100,
            80
        )

        simulated_average = (
            current_average * len(history_df) + simulated_score
        ) / (len(history_df) + 1)

        improvement = (
            simulated_average - current_average
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Current Average",
            f"{current_average:.1f}%"
        )

        col2.metric(
            "Simulated Average",
            f"{simulated_average:.1f}%"
        )

        col3.metric(
            "Improvement",
            f"{improvement:+.1f}%"
        )

        st.progress(
            min(max(simulated_average / 100, 0), 1)
        )

        st.caption(
            "Simulation does not change actual assessment records."
        )


# =====================================================
# RESUME ANALYZER
# =====================================================

elif page == "Resume Analyzer":

    st.title("📄 Resume Analyzer")

    st.write(
        "Upload your resume to identify skills and improve your career profile."
    )

    uploaded_file = st.file_uploader(
        "Upload Resume",
        type=["pdf", "docx", "txt"]
    )

    if uploaded_file:

        resume_text = extract_resume_text(uploaded_file)

        if resume_text.strip():

            analysis = analyze_resume(resume_text)

            st.session_state["resume_analysis"] = analysis

            st.subheader("Resume Overview")

            col1, col2 = st.columns(2)

            col1.metric(
                "Detected Skills",
                analysis["skill_count"]
            )

            col2.metric(
                "Word Count",
                analysis["word_count"]
            )

            st.divider()

            st.subheader("Detected Skills")

            if analysis["detected_skills"]:

                for skill in analysis["detected_skills"]:

                    st.success(skill)

            else:

                st.warning(
                    "No supported skills detected. Add relevant skill names to your resume."
                )

            st.divider()

            st.subheader("Resume Section Analysis")

            for section, found in analysis["sections"].items():

                if found:

                    st.success(f"{section}: Found")

                else:

                    st.warning(f"{section}: Not Found")

            st.divider()

            st.subheader("Improvement Suggestions")

            for suggestion in analysis["suggestions"]:

                st.info(suggestion)

        else:

            st.error(
                "Could not extract text. Please upload a readable PDF, DOCX or TXT file."
            )


# =====================================================
# JOB ROLE MATCHING
# =====================================================

elif page == "Job Role Matching":

    st.title("🎯 Job Role Matching")

    st.write(
        "Find career roles that match your current skills."
    )

    selected_skills = st.multiselect(
        "Select your skills",
        options=list(SKILL_KEYWORDS.keys())
    )

    if st.button(
        "Find Matching Careers",
        use_container_width=True
    ):

        if not selected_skills:

            st.warning("Select at least one skill.")

        else:

            matches = calculate_job_matches(
                selected_skills
            )

            st.session_state["job_matches"] = matches

    if "job_matches" in st.session_state:

        matches = st.session_state["job_matches"]

        st.divider()

        st.subheader("Career Match Results")

        for item in matches:

            with st.expander(
                f'{item["Role"]} - {item["Match"]}% Match'
            ):

                st.progress(
                    item["Match"] / 100
                )

                st.write(
                    "**Matched Skills:**",
                    item["Matched Skills"] or "None"
                )

                st.write(
                    "**Skills to Develop:**",
                    item["Missing Skills"] or "None"
                )


# =====================================================
# AGENTIC CAREER PLANNER
# =====================================================

elif page == "Agentic Career Planner":

    st.title("🤖 Agentic Career Planner")

    st.write(
        "Four specialized agents collaborate to analyze your skills, "
        "identify skill gaps, create a learning roadmap and provide "
        "performance-based mentoring."
    )

    st.divider()

    st.subheader("👤 Learner Profile")

    current_skills = st.multiselect(
        "Select the skills you currently know",
        options=list(SKILL_KEYWORDS.keys()),
        default=["Python", "SQL"]
    )

    target_role = st.selectbox(
        "Choose your target career",
        list(JOB_ROLES.keys())
    )

    if st.button(
        "🚀 Run Agent Collaboration",
        use_container_width=True
    ):

        conn = get_connection()

        history_df = pd.read_sql_query(
            """
            SELECT skill, score, level, attempted_at
            FROM assessment_sessions
            ORDER BY id DESC
            """,
            conn
        )

        conn.close()

        history = history_df.to_dict("records")

        result = run_agentic_workflow(
            current_skills,
            history,
            target_role,
            JOB_ROLES
        )

        st.session_state["agentic_result"] = result

        st.session_state["agentic_role"] = target_role

    if "agentic_result" in st.session_state:

        result = st.session_state["agentic_result"]

        gaps = result["skill_analysis"]

        st.divider()

        st.subheader("📊 Career Readiness")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Career Skill Match",
            f'{gaps["match_percentage"]}%'
        )

        col2.metric(
            "Matched Skills",
            len(gaps["matched_skills"])
        )

        col3.metric(
            "Skills to Learn",
            len(gaps["missing_skills"])
        )

        st.progress(
            gaps["match_percentage"] / 100
        )

        st.divider()

        st.subheader("🤝 Agent Collaboration Log")

        for agent in result["agent_trace"]:

            with st.expander(
                f'{agent["agent"]} - {agent["status"]}'
            ):

                st.write(agent["action"])

        st.divider()

        st.subheader("✅ Existing Skills")

        if gaps["matched_skills"]:

            for skill in gaps["matched_skills"]:

                st.success(skill)

        else:

            st.info("No matching skills selected.")

        st.subheader("🎯 Skills to Develop")

        if gaps["missing_skills"]:

            for skill in gaps["missing_skills"]:

                st.warning(skill)

        else:

            st.success(
                "All listed skills for this career are selected!"
            )

        st.divider()

        st.subheader("🗺️ Personalized Learning Roadmap")

        total_tasks = 0

        completed_tasks = 0

        for index, item in enumerate(
            result["learning_roadmap"],
            1
        ):

            with st.expander(
                f'{index}. {item["skill"]}'
            ):

                for task_no, task in enumerate(
                    item["tasks"],
                    1
                ):

                    key = (
                        f'agent_task_{target_role}_'
                        f'{item["skill"]}_{task_no}'
                    )

                    completed = st.checkbox(
                        task,
                        key=key
                    )

                    total_tasks += 1

                    if completed:

                        completed_tasks += 1

        if total_tasks > 0:

            st.metric(
                "Completed Learning Tasks",
                f"{completed_tasks}/{total_tasks}"
            )

            st.progress(
                completed_tasks / total_tasks
            )

        else:

            st.success(
                "No skill gaps found. Start building practical projects!"
            )

        st.divider()

        st.subheader("🧑‍🏫 AI Mentor Guidance")

        for guidance in result["mentor"]["guidance"]:

            st.info(guidance)

        if result["mentor"]["priority_skills"]:

            st.warning(
                "Priority Revision: " +
                ", ".join(
                    result["mentor"]["priority_skills"]
                )
            )

        st.caption(
            "Prototype: Four coordinated rule-based agents. "
            "No external LLM API is connected."
        )


# =====================================================
# PDF REPORT DOWNLOAD
# =====================================================

elif page == "PDF Report Download":

    st.title("📥 PDF Report Download")

    st.write(
        "Generate a report containing your skill profile, "
        "assessment history and learning recommendations."
    )

    if st.button(
        "Generate PDF Report",
        use_container_width=True
    ):

        try:

            pdf_file = create_pdf_report()

            st.download_button(
                label="⬇️ Download Your Report",
                data=pdf_file,
                file_name="SkillPath_AI_Report.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            st.success(
                "Your PDF report is ready!"
            )

        except Exception as error:

            st.error(
                f"Unable to generate PDF: {error}"
            )


# =====================================================
# FOOTER
# =====================================================

st.sidebar.divider()

st.sidebar.caption(
    "SkillPath AI 2.3 | Personalized Learning & Career Intelligence"
)