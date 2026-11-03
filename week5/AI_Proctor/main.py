
import os
import ast
from itertools import combinations
from difflib import SequenceMatcher

from dotenv import load_dotenv
from groq import Groq

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ==========================================
# 1. CONFIGURATION
# ==========================================

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

if not API_KEY:
    raise ValueError("GROQ_API_KEY missing in .env")

client = Groq(api_key=API_KEY)

SUBMISSION_FOLDER = "submissions"


# ==========================================
# 2. LOAD STUDENT SUBMISSIONS
# ==========================================

def load_submissions():

    submissions = {}

    if not os.path.exists(SUBMISSION_FOLDER):
        print("Submissions folder not found!")
        return submissions

    for filename in os.listdir(SUBMISSION_FOLDER):

        if filename.endswith(".py"):

            path = os.path.join(
                SUBMISSION_FOLDER,
                filename
            )

            with open(path, "r", encoding="utf-8") as file:
                submissions[filename] = file.read()

    return submissions


# ==========================================
# 3. NORMALIZE CODE USING AST
# ==========================================

class CodeNormalizer(ast.NodeTransformer):

    def visit_Name(self, node):
        node.id = "VARIABLE"
        return node

    def visit_arg(self, node):
        node.arg = "ARGUMENT"
        return node

    def visit_FunctionDef(self, node):
        node.name = "FUNCTION"
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        node.name = "FUNCTION"
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        node.name = "CLASS"
        self.generic_visit(node)
        return node


def normalize_code(code):

    try:

        tree = ast.parse(code)

        tree = CodeNormalizer().visit(tree)

        ast.fix_missing_locations(tree)

        return ast.dump(
            tree,
            include_attributes=False
        )

    except SyntaxError:
        return None


# ==========================================
# 4. AST SIMILARITY
# ==========================================

def calculate_ast_similarity(code1, code2):

    normalized1 = normalize_code(code1)
    normalized2 = normalize_code(code2)

    if normalized1 is None or normalized2 is None:
        return None

    score = SequenceMatcher(
        None,
        normalized1,
        normalized2,
        autojunk=False
    ).ratio()

    return round(score * 100, 2)


# ==========================================
# 5. TEXT SIMILARITY
# ==========================================

def calculate_text_similarity(code1, code2):

    if not code1.strip() or not code2.strip():
        return 0.0

    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 5)
    )

    try:

        vectors = vectorizer.fit_transform(
            [code1, code2]
        )

        score = cosine_similarity(
            vectors[0:1],
            vectors[1:2]
        )[0][0]

        return round(score * 100, 2)

    except ValueError:
        return 0.0


# ==========================================
# 6. COMPLETE CODE COMPARISON
# ==========================================

def compare_codes(code1, code2):

    normalized1 = normalize_code(code1)
    normalized2 = normalize_code(code2)

    if normalized1 is None or normalized2 is None:
        text_score = calculate_text_similarity(
            code1, code2
        )
        ast_score = None
    else:
        text_score = calculate_text_similarity(
            normalized1, normalized2
        )
        ast_score = calculate_ast_similarity(
            code1, code2
        )

    if ast_score is None:
        final_score = text_score
    else:
        final_score = (
            0.5 * text_score +
            0.5 * ast_score
        )

    return {
        "text_similarity": text_score,
        "ast_similarity": ast_score,
        "final_similarity": round(final_score, 2)
    }


# ==========================================
# 7. GROQ AI ANALYSIS
# ==========================================

def groq_analysis(code1, code2, result):

    prompt = f"""
    You are an academic code similarity reviewer.

    Compare these two Python student submissions.

    Similarity results:
    {result}

    STUDENT 1 CODE:
    {code1[:4000]}

    STUDENT 2 CODE:
    {code2[:4000]}

    Analyze:

    1. Similarity in programming logic.
    2. Similarity in code structure.
    3. Differences in implementation.
    4. Whether similarities could be expected
       from solving the same problem.
    5. What evidence a human reviewer should inspect.

    Do not accuse either student of cheating.
    Do not infer who copied from whom.

    Give a concise, objective report.
    """

    response = client.chat.completions.create(

        model=MODEL,

        messages=[
            {
                "role": "system",
                "content": (
                    "You are an objective academic "
                    "code similarity analysis assistant."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.2
    )

    return response.choices[0].message.content


# ==========================================
# 8. PLAGIARISM DETECTION
# ==========================================

def plagiarism_checker():

    submissions = load_submissions()

    if len(submissions) < 2:
        print("At least two student files are required.")
        return

    print("\nTotal submissions:", len(submissions))

    for (name1, code1), (name2, code2) in combinations(
        submissions.items(), 2
    ):

        result = compare_codes(code1, code2)

        score = result["final_similarity"]

        print("\n" + "=" * 60)

        print("Student 1:", name1)
        print("Student 2:", name2)

        print(
            "Text Similarity:",
            result["text_similarity"], "%"
        )

        print(
            "AST Similarity:",
            result["ast_similarity"], "%"
        )

        print(
            "Overall Similarity:",
            score, "%"
        )

        if score >= 75:
            print("Review Priority: HIGH")

        elif score >= 50:
            print("Review Priority: MEDIUM")

        else:
            print("Review Priority: LOW")

        # Groq AI analysis
        print("\nGenerating Groq AI analysis...")

        try:

            report = groq_analysis(
                code1,
                code2,
                result
            )

            print("\nGROQ AI REPORT:")
            print(report)

        except Exception as error:

            print("Groq API Error:", error)


# ==========================================
# 9. MAIN FUNCTION
# ==========================================

def main():

    print("=" * 60)
    print("       AI CODE PROCTORING SYSTEM")
    print("=" * 60)

    plagiarism_checker()

    print("\nAnalysis completed!")


if __name__ == "__main__":
    main()
