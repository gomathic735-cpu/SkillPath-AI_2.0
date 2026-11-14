import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import re
from datetime import datetime
from pypdf import PdfReader
from docx import Document
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# =====================================================
# PAGE CONFIG
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
    return sqlite3.connect(DB_NAME, check_same_thread=False)


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
        ("Python", 80, 60, 35),
        ("Java", 50, 30, 0),
        ("SQL", 60, 40, 0),
        ("Communication", 85, 70, 0)
    ]

    for skill in default_skills:

        cur.execute("""
            INSERT OR IGNORE INTO skill_scores
            (skill, claimed, practiced, proven)
            VALUES (?, ?, ?, ?)
        """, skill)

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

    cur.execute(
        "SELECT proven FROM skill_scores WHERE skill=?",
        (skill,)
    )

    result = cur.fetchone()

    if result:

        old_score = result[0] or 0

        updated_score = max(
            old_score,
            new_score
        )

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
# RESUME SKILL DATABASE
# =====================================================

SKILL_KEYWORDS = {

    "Python": [
        "python", "pandas", "numpy", "django", "flask",
        "streamlit", "automation"
    ],

    "Java": [
        "java", "spring", "spring boot", "jdbc",
        "hibernate", "oop"
    ],

    "SQL": [
        "sql", "mysql", "postgresql", "sqlite",
        "database", "joins"
    ],

    "Web Development": [
        "html", "css", "javascript", "react",
        "node.js", "bootstrap"
    ],

    "Data Analysis": [
        "excel", "power bi", "tableau", "data analysis",
        "data visualization", "statistics"
    ],

    "Machine Learning": [
        "machine learning", "deep learning", "tensorflow",
        "pytorch", "scikit-learn", "artificial intelligence"
    ],

    "Cloud": [
        "aws", "azure", "google cloud", "cloud computing"
    ],

    "Communication": [
        "communication", "presentation", "teamwork",
        "leadership", "collaboration"
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
# JOB ROLE DATABASE
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

    file_name = uploaded_file.name.lower()

    try:

        if file_name.endswith(".pdf"):

            reader = PdfReader(uploaded_file)

            text_content = ""

            for page in reader.pages:

                text_content += page.extract_text() or ""

            return text_content

        elif file_name.endswith(".docx"):

            document = Document(uploaded_file)

            text_content = "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
            )

            return text_content

        elif file_name.endswith(".txt"):

            return uploaded_file.getvalue().decode(
                "utf-8",
                errors="ignore"
            )

        else:

            return None

    except Exception as error:

        st.error(f"Unable to read resume: {error}")

        return None


# =====================================================
# SKILL DETECTION
# =====================================================

def detect_skills(resume_text):

    detected = []

    resume_text = resume_text.lower()

    for category, keywords in SKILL_KEYWORDS.items():

        for keyword in keywords:

            pattern = r"(?<!\w)" + re.escape(keyword.lower()) + r"(?!\w)"

            if re.search(pattern, resume_text):

                detected.append(category)

                break

    return detected


# =====================================================
# RESUME ANALYSIS
# =====================================================

def analyze_resume(resume_text):

    detected_skills = detect_skills(resume_text)

    all_skills = list(SKILL_KEYWORDS.keys())

    missing_skills = [
        skill for skill in all_skills
        if skill not in detected_skills
    ]

    resume_score = round(
        len(detected_skills) / len(all_skills) * 100
    )

    return {
        "detected": detected_skills,
        "missing": missing_skills,
        "score": resume_score
    }


# =====================================================
# JOB MATCHING
# =====================================================

def calculate_job_matches(detected_skills):

    results = []

    for role, required_skills in JOB_ROLES.items():

        matched = [
            skill for skill in required_skills
            if skill in detected_skills
        ]

        missing = [
            skill for skill in required_skills
            if skill not in detected_skills
        ]

        percentage = round(
            len(matched) / len(required_skills) * 100
        )

        results.append({
            "Job Role": role,
            "Match": percentage,
            "Matched Skills": matched,
            "Missing Skills": missing
        })

    results.sort(
        key=lambda x: x["Match"],
        reverse=True
    )

    return results


# =====================================================
# PERSONALIZED RECOMMENDATIONS
# =====================================================

def get_recommendations():

    conn = get_connection()

    df = pd.read_sql_query("""
        SELECT skill, level, score
        FROM assessment_sessions
        ORDER BY attempted_at DESC
    """, conn)

    answers = pd.read_sql_query("""
        SELECT skill, topic, is_correct
        FROM assessment_answers
    """, conn)

    conn.close()

    recommendations = []

    if df.empty:

        recommendations.append(
            "Take your first assessment to receive personalized recommendations."
        )

    else:

        for skill in ["Python", "Java", "SQL"]:

            skill_data = df[df["skill"] == skill]

            if skill_data.empty:

                recommendations.append(
                    f"Start your {skill} Beginner assessment."
                )

                continue

            latest = skill_data.iloc[0]
            score = int(latest["score"])

            if score < 40:

                recommendations.append(
                    f"{skill}: Revise basic concepts and practice more questions."
                )

            elif score < 70:

                recommendations.append(
                    f"{skill}: Practice intermediate topics."
                )

            else:

                recommendations.append(
                    f"{skill}: Good performance! Try the next level."
                )

    if not answers.empty:

        incorrect = answers[
            answers["is_correct"] == 0
        ]

        if not incorrect.empty:

            weak_topics = (
                incorrect.groupby(["skill", "topic"])
                .size()
                .reset_index(name="mistakes")
                .sort_values("mistakes", ascending=False)
            )

            for _, row in weak_topics.head(3).iterrows():

                recommendations.append(
                    f"Revise {row['topic']} in {row['skill']}."
                )

    return recommendations


# =====================================================
# PDF REPORT GENERATOR
# =====================================================

def create_pdf_report():
    """Create a downloadable PDF summary of SkillPath AI progress."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        textColor=colors.HexColor("#B8860B"),
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=8
    )
    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#8A6508"),
        spaceBefore=14,
        spaceAfter=7
    )
    body_style = styles["BodyText"]

    story = [
        Paragraph("SkillPath AI - Progress Report", title_style),
        Paragraph(
            f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
            ParagraphStyle("Date", parent=body_style, alignment=TA_CENTER)
        ),
        Spacer(1, 18)
    ]

    conn = get_connection()
    history = pd.read_sql_query(
        """SELECT skill, level, score, correct_answers,
                  total_questions, attempted_at
           FROM assessment_sessions ORDER BY id DESC""",
        conn
    )
    conn.close()

    story.append(Paragraph("1. Assessment Summary", heading_style))
    if history.empty:
        story.append(Paragraph("No assessments completed yet.", body_style))
    else:
        average = round(float(history["score"].mean()), 1)
        story.append(Paragraph(
            f"Total assessments: {len(history)} | Average score: {average}%",
            body_style
        ))
        table_data = [["Skill", "Level", "Score", "Correct", "Date"]]
        for _, row in history.head(25).iterrows():
            table_data.append([
                str(row["skill"]),
                str(row["level"]),
                f"{int(row['score'])}%",
                f"{int(row['correct_answers'])}/{int(row['total_questions'])}",
                str(row["attempted_at"])
            ])
        table = Table(table_data, repeatRows=1, colWidths=[85, 75, 55, 65, 125])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#253047")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F1F3F6")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 5)
        ]))
        story.extend([Spacer(1, 8), table])

    story.append(Paragraph("2. Resume Analysis", heading_style))
    resume_skills = st.session_state.get("resume_skills")
    if resume_skills is not None:
        resume_score = st.session_state.get("resume_score", 0)
        story.append(Paragraph(
            f"Resume skill coverage: {resume_score}% "
            f"({len(resume_skills)} skill categories detected)",
            body_style
        ))
        story.append(Paragraph(
            "Detected categories: " + (
                ", ".join(resume_skills) if resume_skills else "None detected"
            ),
            body_style
        ))
        missing = [skill for skill in SKILL_KEYWORDS if skill not in resume_skills]
        story.append(Paragraph(
            "Skills to develop: " + (", ".join(missing) if missing else "None"),
            body_style
        ))
    else:
        story.append(Paragraph(
            "No resume has been analyzed in this session. "
            "Use the Resume Analyzer page first to include resume results.",
            body_style
        ))

    story.append(Paragraph("3. Job Role Matching", heading_style))
    if resume_skills is not None:
        matches = calculate_job_matches(resume_skills)
        match_data = [["Job Role", "Match", "Matched Categories", "To Develop"]]
        for item in matches:
            match_data.append([
                item["Job Role"],
                f'{item["Match"]}%',
                ", ".join(item["Matched Skills"]) or "-",
                ", ".join(item["Missing Skills"]) or "-"
            ])
        match_table = Table(
            match_data,
            repeatRows=1,
            colWidths=[105, 45, 130, 130]
        )
        match_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#253047")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F1F3F6")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 4)
        ]))
        story.append(match_table)
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            "Note: Job match percentages are based on detected skill categories "
            "only. They do not guarantee job eligibility or selection.",
            body_style
        ))
    else:
        story.append(Paragraph(
            "Analyze a resume to include job role matching results.",
            body_style
        ))

    story.append(Paragraph("4. Learning Recommendations", heading_style))
    for recommendation in get_recommendations():
        story.append(Paragraph("• " + recommendation, body_style))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "This report is generated from the information available in SkillPath AI. "
        "Resume analysis is keyword-based and should be used as a learning guide, "
        "not as an official ATS score or hiring prediction.",
        ParagraphStyle("Note", parent=body_style, fontSize=8, textColor=colors.grey)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# =====================================================
# NAVIGATION
# =====================================================

st.sidebar.title("🎯 SkillPath AI 2.3")

st.sidebar.caption("Smart Skill Development Platform")

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
        "PDF Report Download"
    ]
)


# =====================================================
# DASHBOARD
# =====================================================

if page == "Dashboard":

    st.title("🎯 SkillPath AI Dashboard")

    st.write(
        "Track your skills, prove your knowledge and improve your career readiness."
    )

    skills_df = get_skills()

    conn = get_connection()

    sessions = pd.read_sql_query(
        "SELECT * FROM assessment_sessions",
        conn
    )

    conn.close()

    total_assessments = len(sessions)

    average_score = (
        round(sessions["score"].mean(), 1)
        if not sessions.empty else 0
    )

    if not sessions.empty:

        strongest = sessions.groupby("skill")["score"].mean().idxmax()
        weakest = sessions.groupby("skill")["score"].mean().idxmin()

    else:

        strongest = "Not available"
        weakest = "Not available"

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Assessments", total_assessments)
    col2.metric("Average Accuracy", f"{average_score}%")
    col3.metric("Strongest Skill", strongest)
    col4.metric("Needs Improvement", weakest)

    st.divider()

    st.subheader("📊 Your Skill Progress")

    chart_df = skills_df.melt(
        id_vars=["skill"],
        value_vars=["claimed", "practiced", "proven"],
        var_name="Category",
        value_name="Score"
    )

    fig = px.bar(
        chart_df,
        x="skill",
        y="Score",
        color="Category",
        barmode="group"
    )

    fig.update_layout(template="plotly_dark")

    st.plotly_chart(fig, width="stretch")

    st.info(
        "Use Resume Analyzer to analyze your resume and discover your job opportunities."
    )


# =====================================================
# SKILL DNA
# =====================================================

elif page == "Skill DNA":

    st.title("🧬 Skill DNA Analysis")

    skills_df = get_skills()

    for _, row in skills_df.iterrows():

        st.subheader(row["skill"])

        col1, col2, col3 = st.columns(3)

        col1.metric("Claimed", f"{row['claimed']}%")
        col2.metric("Practiced", f"{row['practiced']}%")
        col3.metric("Proven", f"{row['proven']}%")

        gap = row["claimed"] - row["proven"]

        if gap > 30:

            st.warning(
                f"Your {row['skill']} skill has a {gap}% proof gap."
            )

        else:

            st.success("Your demonstrated skill is closer to your claimed skill.")

        st.progress(int(row["proven"]) / 100)


# =====================================================
# SKILL PROOF LAB
# =====================================================

elif page == "Skill Proof Lab":

    st.title("🧪 Skill Proof Lab")

    language = st.selectbox(
        "Select Skill",
        ["Python", "Java", "SQL"]
    )

    level = st.selectbox(
        "Select Level",
        ["Beginner", "Intermediate", "Advanced"]
    )

    questions = QUESTION_BANK[language][level]

    st.info("Each assessment contains 5 questions.")

    with st.form("assessment_form"):

        answers = []

        for i, item in enumerate(questions):

            topic, question, options, correct, explanation = item

            st.markdown(f"### Question {i + 1}")

            st.write(question)

            selected = st.radio(
                f"Your answer - Question {i + 1}",
                options,
                key=f"{language}_{level}_{i}"
            )

            answers.append(selected)

        submitted = st.form_submit_button("Submit Assessment")

    if submitted:

        correct_count = sum(
            answers[i] == questions[i][3]
            for i in range(len(questions))
        )

        score = int(
            correct_count / len(questions) * 100
        )

        attempted_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO assessment_sessions
            (skill, level, score, correct_answers,
             total_questions, attempted_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            language,
            level,
            score,
            correct_count,
            len(questions),
            attempted_at
        ))

        session_id = cur.lastrowid

        for i, item in enumerate(questions):

            topic, question, options, correct, explanation = item

            cur.execute("""
                INSERT INTO assessment_answers
                (session_id, skill, level, topic, question,
                 selected_answer, correct_answer, is_correct,
                 attempted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                language,
                level,
                topic,
                question,
                answers[i],
                correct,
                int(answers[i] == correct),
                attempted_at
            ))

        conn.commit()
        conn.close()

        update_proven_score(language, score)

        st.session_state["last_assessment"] = {
            "skill": language,
            "level": level,
            "score": score,
            "correct": correct_count
        }

        st.session_state["last_answers"] = answers

        st.rerun()

    if "last_assessment" in st.session_state:

        result = st.session_state["last_assessment"]

        st.divider()

        st.subheader("📊 Assessment Result")

        col1, col2 = st.columns(2)

        col1.metric("Score", f"{result['score']}%")

        col2.metric(
            "Correct Answers",
            f"{result['correct']}/5"
        )

        if result["score"] >= 80:
            st.success("Excellent performance!")

        elif result["score"] >= 60:
            st.info("Good progress. Practice more.")

        else:
            st.warning("Revise the topics and try again.")

        st.subheader("📝 Answer Review")

        for i, item in enumerate(
            QUESTION_BANK[result["skill"]][result["level"]]
        ):

            topic, question, options, correct, explanation = item

            st.write(f"**Question {i + 1}: {question}**")

            st.write(
                f"Your answer: {st.session_state['last_answers'][i]}"
            )

            st.write(f"Correct answer: {correct}")

            st.caption(explanation)


# =====================================================
# ASSESSMENT HISTORY
# =====================================================

elif page == "Assessment History":

    st.title("📚 Assessment History")

    conn = get_connection()

    history = pd.read_sql_query("""
        SELECT skill, level, score, correct_answers,
               total_questions, attempted_at
        FROM assessment_sessions
        ORDER BY id DESC
    """, conn)

    conn.close()

    if history.empty:

        st.info("No assessment history available.")

    else:

        st.dataframe(
            history,
            width="stretch",
            hide_index=True
        )

        csv = history.to_csv(index=False).encode("utf-8")

        st.download_button(
            "⬇️ Download History",
            data=csv,
            file_name="skillpath_history.csv",
            mime="text/csv"
        )


# =====================================================
# AI RECOMMENDATIONS
# =====================================================

elif page == "AI Recommendations":

    st.title("🤖 AI Recommendations")

    recommendations = get_recommendations()

    for i, recommendation in enumerate(recommendations, 1):

        st.markdown(
            f"""
            <div>
            <b>Recommendation {i}</b><br><br>
            {recommendation}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write("")

    st.caption(
        "These recommendations use rule-based performance analysis."
    )


# =====================================================
# PERFORMANCE ANALYTICS
# =====================================================

elif page == "Performance Analytics":

    st.title("📈 Performance Analytics")

    conn = get_connection()

    history = pd.read_sql_query("""
        SELECT * FROM assessment_sessions
        ORDER BY id ASC
    """, conn)

    answers = pd.read_sql_query("""
        SELECT * FROM assessment_answers
    """, conn)

    conn.close()

    if history.empty:

        st.info("Complete assessments to view analytics.")

    else:

        language_avg = (
            history.groupby("skill")["score"]
            .mean()
            .reset_index()
        )

        fig = px.bar(
            language_avg,
            x="skill",
            y="score",
            color="skill",
            title="Language-wise Performance"
        )

        fig.update_layout(template="plotly_dark")

        st.plotly_chart(fig, width="stretch")

        level_avg = (
            history.groupby(["skill", "level"])["score"]
            .mean()
            .reset_index()
        )

        fig2 = px.bar(
            level_avg,
            x="level",
            y="score",
            color="skill",
            barmode="group",
            title="Level-wise Performance"
        )

        fig2.update_layout(template="plotly_dark")

        st.plotly_chart(fig2, width="stretch")

        fig3 = px.line(
            history,
            x="attempted_at",
            y="score",
            color="skill",
            markers=True,
            title="Assessment Progress"
        )

        fig3.update_layout(template="plotly_dark")

        st.plotly_chart(fig3, width="stretch")

        if not answers.empty:

            mistakes = answers[
                answers["is_correct"] == 0
            ]

            if not mistakes.empty:

                weak_topics = (
                    mistakes.groupby(["skill", "topic"])
                    .size()
                    .reset_index(name="Mistakes")
                    .sort_values("Mistakes", ascending=False)
                )

                st.subheader("Topics to Improve")

                st.dataframe(
                    weak_topics,
                    width="stretch",
                    hide_index=True
                )


# =====================================================
# CAREER INTELLIGENCE
# =====================================================

elif page == "Career Intelligence":

    st.title("💼 Career Intelligence")

    skills_df = get_skills()

    technical = skills_df[
        skills_df["skill"].isin(["Python", "Java", "SQL"])
    ]

    readiness = int(technical["proven"].mean())

    st.metric(
        "Technical Skill Readiness",
        f"{readiness}%"
    )

    st.progress(readiness / 100)

    st.subheader("Suggested Career Paths")

    for role in JOB_ROLES:

        st.write(f"**{role}**")


# =====================================================
# ADAPTIVE LEARNING
# =====================================================

elif page == "Adaptive Learning":

    st.title("🧠 Adaptive Learning Path")

    conn = get_connection()

    history = pd.read_sql_query("""
        SELECT skill, level, score
        FROM assessment_sessions
        ORDER BY id DESC
    """, conn)

    conn.close()

    for skill in ["Python", "Java", "SQL"]:

        st.subheader(skill)

        skill_history = history[
            history["skill"] == skill
        ]

        if skill_history.empty:

            st.info(
                f"Start {skill} Beginner assessment."
            )

        else:

            latest = skill_history.iloc[0]

            score = int(latest["score"])
            level = latest["level"]

            if score >= 80:

                if level == "Beginner":
                    next_level = "Intermediate"

                elif level == "Intermediate":
                    next_level = "Advanced"

                else:
                    next_level = "Advanced practice"

                st.success(
                    f"Recommended next step: {next_level}"
                )

            else:

                st.warning(
                    f"Revise {level} topics and retake assessment."
                )


# =====================================================
# WHAT-IF SIMULATOR
# =====================================================

elif page == "What-If Simulator":

    st.title("🔮 What-If Simulator")

    skills_df = get_skills()

    current_scores = {}

    for skill in ["Python", "Java", "SQL"]:

        current_scores[skill] = int(
            skills_df[
                skills_df["skill"] == skill
            ]["proven"].iloc[0]
        )

    current = round(
        sum(current_scores.values()) / 3
    )

    st.metric(
        "Current Technical Readiness",
        f"{current}%"
    )

    targets = {}

    for skill in ["Python", "Java", "SQL"]:

        targets[skill] = st.slider(
            f"{skill} Target",
            0,
            100,
            current_scores[skill]
        )

    predicted = round(
        sum(targets.values()) / 3
    )

    st.metric(
        "Predicted Technical Readiness",
        f"{predicted}%"
    )

    difference = predicted - current

    if difference > 0:

        st.success(
            f"Readiness improves by {difference}% in this simulation."
        )

    elif difference < 0:

        st.warning(
            f"Readiness decreases by {abs(difference)}% in this simulation."
        )

    else:

        st.info("Readiness remains the same.")


# =====================================================
# RESUME ANALYZER
# =====================================================

elif page == "Resume Analyzer":

    st.title("📄 Resume Intelligence Analyzer")

    st.write(
        "Upload your resume to identify skills and understand your resume coverage."
    )

    uploaded_file = st.file_uploader(
        "Upload your Resume",
        type=["pdf", "docx", "txt"]
    )

    if uploaded_file is not None:

        if st.button("Analyze My Resume"):

            resume_text = extract_resume_text(
                uploaded_file
            )

            if resume_text:

                if len(resume_text.strip()) < 30:

                    st.warning(
                        "Very little text was extracted. "
                        "If this is a scanned PDF, OCR may be required."
                    )

                else:

                    result = analyze_resume(
                        resume_text
                    )

                    st.session_state["resume_text"] = resume_text

                    st.session_state["resume_skills"] = result["detected"]

                    st.session_state["resume_score"] = result["score"]

                    st.rerun()

    if "resume_skills" in st.session_state:

        st.divider()

        st.subheader("📊 Resume Analysis Result")

        col1, col2 = st.columns(2)

        col1.metric(
            "Resume Skill Coverage",
            f"{st.session_state['resume_score']}%"
        )

        col2.metric(
            "Detected Skill Categories",
            len(st.session_state["resume_skills"])
        )

        st.progress(
            st.session_state["resume_score"] / 100
        )

        st.subheader("✅ Detected Skills")

        if st.session_state["resume_skills"]:

            for skill in st.session_state["resume_skills"]:

                st.success(skill)

        else:

            st.warning(
                "No supported skills were detected. "
                "Check whether your resume contains a readable skills section."
            )

        st.subheader("💡 Skills You Can Add or Develop")

        missing = [
            skill
            for skill in SKILL_KEYWORDS
            if skill not in st.session_state["resume_skills"]
        ]

        for skill in missing:

            st.write(f"• {skill}")

        st.info(
            "Only include skills you genuinely know. "
            "Do not add a skill to your resume just to increase the score."
        )

        st.subheader("📝 Resume Improvement Suggestions")

        resume_text = st.session_state["resume_text"].lower()

        if "project" not in resume_text:

            st.write(
                "• Add a Projects section with your project descriptions."
            )

        if "education" not in resume_text:

            st.write(
                "• Add an Education section."
            )

        if "experience" not in resume_text:

            st.write(
                "• Add internship, work experience or practical project experience if available."
            )

        if "github" not in resume_text:

            st.write(
                "• Add your GitHub profile if you have relevant code repositories."
            )

        if "certification" not in resume_text:

            st.write(
                "• Include relevant certifications if you have completed any."
            )

        st.caption(
            "This is a keyword-based resume analysis, not an ATS certification or hiring prediction."
        )


# =====================================================
# JOB ROLE MATCHING
# =====================================================

elif page == "Job Role Matching":

    st.title("💼 Job Role Matching")

    st.write(
        "Find job roles that match the skills detected in your resume."
    )

    if "resume_skills" not in st.session_state:

        st.warning(
            "Please analyze your resume first in the Resume Analyzer page."
        )

    else:

        detected_skills = st.session_state["resume_skills"]

        st.subheader("Your Detected Skills")

        st.write(", ".join(detected_skills))

        matches = calculate_job_matches(
            detected_skills
        )

        st.divider()

        st.subheader("🎯 Recommended Job Roles")

        for result in matches:

            with st.expander(
                f"{result['Job Role']} — {result['Match']}% Match"
            ):

                st.progress(
                    result["Match"] / 100
                )

                st.write("**Matching Skills**")

                if result["Matched Skills"]:

                    for skill in result["Matched Skills"]:

                        st.success(skill)

                else:

                    st.write("No matching skills detected yet.")

                st.write("**Skills to Develop**")

                if result["Missing Skills"]:

                    for skill in result["Missing Skills"]:

                        st.warning(skill)

                else:

                    st.success(
                        "All listed required skills were detected!"
                    )

                st.info(
                    "Match percentage is based only on the listed skill categories. "
                    "It does not guarantee job eligibility or selection."
                )

        st.divider()

        st.subheader("📚 Your Next Learning Steps")

        best_match = matches[0]

        if best_match["Missing Skills"]:

            st.write(
                f"To improve your {best_match['Job Role']} skill match, "
                "focus on:"
            )

            for skill in best_match["Missing Skills"]:

                st.write(f"• {skill}")

        else:

            st.success(
                "Your detected skills cover all the listed skills for this role."
            )


# =====================================================
# PDF REPORT DOWNLOAD
# =====================================================

elif page == "PDF Report Download":

    st.title("📥 Download Your SkillPath AI Report")

    st.write(
        "Download a PDF summary containing your assessment history, "
        "resume skill analysis, job role matches and learning recommendations."
    )

    st.info(
        "For resume and job matching details, analyze your resume first "
        "in the Resume Analyzer page. Assessment history is included automatically."
    )

    if st.button("🔄 Generate PDF Report"):
        try:
            pdf_data = create_pdf_report()
            st.session_state["skillpath_pdf_report"] = pdf_data
            st.success("Your PDF report is ready!")
        except Exception as error:
            st.error(f"Unable to generate PDF report: {error}")

    if "skillpath_pdf_report" in st.session_state:
        st.download_button(
            label="⬇️ Download SkillPath AI Report (PDF)",
            data=st.session_state["skillpath_pdf_report"],
            file_name="SkillPath_AI_Progress_Report.pdf",
            mime="application/pdf"
        )


# =====================================================
# FOOTER
# =====================================================

st.sidebar.divider()

st.sidebar.caption("SkillPath AI 2.3")

st.sidebar.caption(
    "Smart Learning • Resume Intelligence • Career Matching"
)