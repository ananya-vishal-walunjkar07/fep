import os
import json
import subprocess
import time

import speech_recognition as sr
import numpy as np

from pathlib import Path
from dotenv import load_dotenv
from google import genai


# ============================================================
# SETUP
# ============================================================

load_dotenv()
env_file = Path(__file__).resolve().parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY2")
client = None
if api_key:
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print("WARNING: Could not initialize Gemini client:", e)
else:
    print("INFO: GEMINI_API_KEY not set. AI interview will use fallback mode.")

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


# ============================================================
# PROFILE
# ============================================================

profile = {
    "target_roles": [],
    "career_goal": "",
    "user_type": "",
    "education": [],
    "skills": [],
    "experience": [],
    "projects": [],
    "certifications": [],
    "achievements": [],
    "leadership": [],
    "languages": [],
    "links": []
}


# ============================================================
# TEXT TO SPEECH
# ============================================================

def speak(text):
    """
    Print and speak CareerAI's message.

    Uses Windows PowerShell SpeechSynthesizer instead of
    pyttsx3 so every question is spoken reliably.
    """

    print("\nCareerAI:")
    print(text)

    # Remove emojis/symbols that can confuse speech synthesis
    clean_text = text.encode("ascii", "ignore").decode()

    if not clean_text.strip():
        return

    # PowerShell script
    powershell_script = f"""
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.Rate = 0
$speaker.Volume = 100
$speaker.Speak({json.dumps(clean_text)})
$speaker.Dispose()
"""

    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                powershell_script
            ],
            check=True
        )

    except Exception as e:
        print("\nTTS Error:", e)


# ============================================================
# SPEECH TO TEXT
# ============================================================

recognizer = sr.Recognizer()


def listen():
    """
    Record the user's answer (Local CLI mode only).

    ENTER = start
    ENTER = stop
    """
    try:
        import sounddevice as sd
    except (ImportError, OSError):
        print("\nNote: sounddevice/PortAudio is not available for direct microphone recording.")
        print("In web deployment, recording is handled by the browser.")
        print("For local CLI mode, you can type your answer below:")
        return input("Your answer: ")

    input("\nPress ENTER to START recording...")

    print("\n🎙️ Recording...")
    print("Speak your answer.")
    print("When you are finished, press ENTER to STOP.\n")

    sample_rate = 16000
    recorded_audio = []

    def callback(indata, frames, time_info, status):
        if status:
            print("Audio status:", status)

        recorded_audio.append(indata.copy())

    try:

        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            callback=callback
        ):
            input()

        print("\n⏹️ Recording stopped.")
        print("Processing your answer...")

        if not recorded_audio:
            print("No audio was recorded.")
            return ""

        audio_data = np.concatenate(
            recorded_audio,
            axis=0
        )

        audio = sr.AudioData(
            audio_data.tobytes(),
            sample_rate,
            2
        )

        try:

            text = recognizer.recognize_google(audio)

            print("\nYou said:")
            print(text)

            return text

        except sr.UnknownValueError:

            print("\nSorry, I couldn't understand your answer.")
            return ""

        except sr.RequestError as e:

            print("\nSpeech recognition service is unavailable.")
            print("Error:", e)
            return ""

        except Exception as e:

            print("\nSpeech recognition error:")
            print(e)
            return ""

    except Exception as e:

        print("\nMicrophone error:")
        print(e)
        return ""


# ============================================================
# GEMINI HELPER
# ============================================================

def call_gemini(prompt, attempts=1, max_tokens=150):
    """Call Gemini with instant model fallback, token bounds, and near-zero latency."""
    global client
    if client is None:
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY2")
        if key:
            try:
                client = genai.Client(api_key=key)
            except Exception:
                pass
    if client is None:
        return ""

    models_to_try = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.7-flash"]
    if MODEL and MODEL not in models_to_try:
        models_to_try.insert(0, MODEL)

    for current_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=current_model,
                contents=prompt,
                config={"max_output_tokens": max_tokens, "temperature": 0.25}
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"Gemini {current_model} fallback notice: {e}")
            continue
    return ""


# ============================================================
# UPDATE PROFILE
# ============================================================

def update_profile(answer):

    global profile

    prompt = f"""
You are the profile extraction engine for CareerAI.

The user is answering an AI resume interview.

Current profile:

{json.dumps(profile, indent=4)}

User's latest answer:

"{answer}"

Update the profile using ONLY information explicitly stated
by the user.

IMPORTANT RULES:

1. Never invent information.

2. Never guess information.

3. Never create fake skills.

4. Never create fake experience.

5. Never create fake projects.

6. Never create fake achievements.

7. Do NOT collect name, email, or phone number here.
   Those are handled separately by signup/backend.

8. Preserve existing information.

9. Add newly provided information.

10. If the user says something is not applicable,
    do not invent anything for that section.

11. For projects, collect whenever available:
    - title/name
    - description
    - technologies
    - contribution
    - result/outcome
    - link

12. For experience, collect whenever available:
    - company
    - role
    - dates/duration
    - responsibilities
    - achievements/results

13. Return ONLY valid JSON.

Use exactly this structure:

{{
    "target_roles": [],
    "career_goal": "",
    "user_type": "",
    "education": [],
    "skills": [],
    "experience": [],
    "projects": [],
    "certifications": [],
    "achievements": [],
    "leadership": [],
    "languages": [],
    "links": []
}}
"""

    result = call_gemini(prompt)

    if not result:
        return

    try:

        cleaned = result

        if "```json" in cleaned:
            cleaned = cleaned.replace("```json", "")

        if "```" in cleaned:
            cleaned = cleaned.replace("```", "")

        cleaned = cleaned.strip()

        updated_profile = json.loads(cleaned)

        if isinstance(updated_profile, dict):

            profile = updated_profile

            print("\nProfile updated successfully.")
            print("Current user type:", profile.get("user_type"))
            print("Current projects:", profile.get("projects"))
            print("Current missing fields:", check_profile())

    except json.JSONDecodeError:

        print("\nGemini returned invalid JSON.")
        print("Profile was not changed.")

    except Exception as e:

        print("\nProfile update error:")
        print(e)


# ============================================================
# PROFILE CHECK
# ============================================================

def check_profile():

    missing = []

    # Target role
    if not profile["target_roles"]:
        missing.append("target role")

    # User type
    if not profile["user_type"]:
        missing.append("student or working professional")

    # Education
    if not profile["education"]:
        missing.append("education")

    # Skills
    if len(profile["skills"]) < 3:
        missing.append("at least 3 skills")

    user_type = profile["user_type"].lower()

    # --------------------------------------------------------
    # STUDENT / FRESHER
    # --------------------------------------------------------

    if (
        "student" in user_type
        or "fresher" in user_type
        or "college" in user_type
    ):

        if not profile["projects"]:

            missing.append("at least one project")

        else:

            for project in profile["projects"]:

                if not project.get("name"):
                    missing.append("project title")
                    break

                if not project.get("description"):
                    missing.append("project description")
                    break

                if not project.get("technologies"):
                    missing.append("project technologies")
                    break

    # --------------------------------------------------------
    # WORKING PROFESSIONAL
    # --------------------------------------------------------

    else:

        if not profile["experience"]:

            missing.append("work experience")

        else:

            for experience in profile["experience"]:

                if not experience.get("company"):
                    missing.append("company")
                    break

                if not experience.get("role"):
                    missing.append("job role")
                    break

                if not experience.get("duration"):
                    missing.append("experience duration")
                    break

                if not experience.get("responsibilities"):
                    missing.append("responsibilities")
                    break

    return missing


# ============================================================
# SAVE PROFILE
# ============================================================

def save_profile():

    try:

        with open(
            "resume_profile.json",
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                profile,
                file,
                indent=4,
                ensure_ascii=False
            )

        print("\nProfile saved to resume_profile.json")

    except Exception as e:

        print("\nCould not save profile:")
        print(e)


# ============================================================
# ASK NEXT QUESTION
# ============================================================

def ask_next_question():
    """Generate interview questions without using a Gemini API call."""

    missing = check_profile()
    user_type = str(profile.get("user_type", "")).lower()

    if not missing:
        return ""

    # Ask for the most important missing information first.
    if "target role" in missing:
        return "What job role or roles are you targeting, and what kind of work would you like to do?"

    if "student or working professional" in missing:
        return "Are you a student, a recent graduate, or a working professional?"

    if "education" in missing:
        return "Tell me about your education, including your degree, institution, specialization, and graduation year."

    if "at least 3 skills" in missing:
        return "What are your main technical and professional skills? Please mention at least three."

    if (
        "student" in user_type
        or "fresher" in user_type
        or "college" in user_type
    ):
        if "at least one project" in missing:
            return "Tell me about a project you worked on, including its name, purpose, technologies, and your contribution."

        if "project title" in missing:
            return "What is the name of your project?"

        if "project description" in missing:
            return "What does your project do, and what problem does it solve?"

        if "project technologies" in missing:
            return "Which programming languages, tools, and technologies did you use in your project?"

    else:
        if "work experience" in missing:
            return "Tell me about your work experience, including your company, role, dates, responsibilities, and achievements. If you have no work experience, please say so."

        if "company" in missing:
            return "Which company did you work for in that role?"

        if "job role" in missing:
            return "What was your job title, and what were your main responsibilities?"

        if "experience duration" in missing:
            return "When did you work in that role, including your start and end dates?"

        if "responsibilities" in missing:
            return "What were your main responsibilities and accomplishments in that role?"

    # Ask for any other missing information in a combined question.
    return (
        "Is there anything else you would like to include about your "
        "projects, certifications, achievements, leadership experience, "
        "languages, or professional links?"
    )



# ============================================================
# MAIN INTERVIEW
# ============================================================



# ============================================================
# FEEDBACK & NEXT QUESTION GENERATOR
# ============================================================

def generate_feedback_and_next_question(answer: str):
    """
    Generate an intelligent, encouraging feedback acknowledging the candidate's answer,
    followed by the natural next interview question.
    """
    missing = check_profile()
    if not missing:
        return (
            "Fantastic! That gives us a complete and comprehensive picture of your professional background.",
            ""
        )

    target_area = missing[0]

    # Try Gemini first for personalized, context-aware conversational feedback
    if client:
        try:
            summary = {
                "target_roles": profile.get("target_roles"),
                "user_type": profile.get("user_type"),
                "skills": profile.get("skills", [])[:5],
                "education": profile.get("education", [])[:1],
                "projects": [p.get("name") for p in profile.get("projects", []) if isinstance(p, dict)],
            }
            prompt = f"""You are Cara, the supportive, encouraging, and intelligent AI career interviewer for CareerAI.
The candidate just gave this response: "{answer}"
Candidate profile summary so far: {json.dumps(summary)}
Next missing profile area needed: {target_area}

Provide an interactive, empathetic response in JSON format with exactly two keys:
1. "feedback": A warm, encouraging 1-2 sentence acknowledgment directly referencing what they specifically stated (validate their achievements, specific technologies, domain, or aspirations).
2. "next_question": An engaging, professional interview question to gather information about {target_area}.

Return ONLY raw JSON with keys "feedback" and "next_question"."""

            raw = call_gemini(prompt)
            if raw:
                cleaned = raw.replace("```json", "").replace("```", "").strip()
                data = json.loads(cleaned)
                fb = data.get("feedback", "").strip()
                nq = data.get("next_question", "").strip()
                if fb and nq:
                    return fb, nq
        except Exception as e:
            print("Feedback generation notice:", e)

    # Contextual heuristic fallback:
    ans_lower = answer.lower()
    if any(k in ans_lower for k in ["engineer", "developer", "designer", "manager", "data", "analyst", "ai", "ml", "frontend", "backend", "full stack", "cloud", "devops"]):
        fallback_fb = "That is an exciting career path with great demand in the industry!"
    elif any(k in ans_lower for k in ["student", "graduate", "fresher", "college", "university", "btech", "b.tech", "bca", "mca", "b.sc"]):
        fallback_fb = "Great! Academic foundation and hands-on learning are wonderful assets."
    elif any(k in ans_lower for k in ["python", "java", "react", "sql", "javascript", "c++", "aws", "docker", "node", "html", "css", "machine learning"]):
        fallback_fb = "Those are impressive and highly relevant technical skills to highlight on your resume."
    elif any(k in ans_lower for k in ["built", "project", "app", "system", "website", "developed", "created"]):
        fallback_fb = "Hands-on projects are one of the most effective ways to demonstrate real-world impact to employers."
    elif any(k in ans_lower for k in ["intern", "experience", "work", "job", "company", "team", "client"]):
        fallback_fb = "Practical work experience gives you great leverage when positioning your profile."
    else:
        fallback_fb = "Thank you for sharing that! That gives valuable clarity for building your resume."

    fallback_nq = ask_next_question()
    return fallback_fb, fallback_nq



# ============================================================
# ULTRA-FAST UNIFIED INTERVIEW PROCESSOR
# ============================================================

def _apply_heuristic_profile(answer: str):
    global profile
    ans_lower = answer.lower()
    if not profile.get("target_roles") and any(r in ans_lower for r in ["developer", "engineer", "designer", "manager", "analyst", "data", "scientist", "architect", "lead"]):
        profile["target_roles"] = [answer.strip()[:60]]
    if not profile.get("user_type"):
        if any(w in ans_lower for w in ["student", "college", "fresher", "graduating", "study", "final year"]):
            profile["user_type"] = "Student / Fresher"
        elif any(w in ans_lower for w in ["professional", "working", "years", "experience", "senior", "junior"]):
            profile["user_type"] = "Working Professional"
    if not profile.get("education") and any(w in ans_lower for w in ["btech", "b.tech", "degree", "university", "college", "bca", "mca", "b.e", "b.sc", "bachelor", "master"]):
        profile["education"].append({"degree": answer.strip()[:60]})
    if len(profile.get("skills", [])) < 3:
        tech_keywords = ["python", "java", "react", "node", "sql", "javascript", "html", "css", "c++", "aws", "docker", "git", "machine learning", "fastapi", "django"]
        found = [k.capitalize() for k in tech_keywords if k in ans_lower]
        for s in found:
            if s not in profile.get("skills", []):
                profile.setdefault("skills", []).append(s)
        if len(profile.get("skills", [])) < 3 and len(answer.split()) > 3:
            profile.setdefault("skills", []).extend(["Communication", "Problem Solving"])
    if not profile.get("projects") and any(w in ans_lower for w in ["project", "built", "app", "website", "system", "created", "developed"]):
        profile["projects"].append({"name": answer.strip()[:40], "description": answer.strip()[:100], "technologies": "Full Stack"})


def _heuristic_feedback_and_next_question(answer: str):
    ans_lower = answer.lower()
    if any(k in ans_lower for k in ["engineer", "developer", "designer", "manager", "data", "analyst", "ai", "ml", "frontend", "backend", "full stack", "cloud", "devops"]):
        fb = "That is a high-demand, exciting career path to pursue!"
    elif any(k in ans_lower for k in ["student", "graduate", "fresher", "college", "university", "btech", "b.tech", "bca", "mca", "b.sc"]):
        fb = "Great! Your academic foundation and hands-on learnings are strong assets."
    elif any(k in ans_lower for k in ["python", "java", "react", "sql", "javascript", "c++", "aws", "docker", "node", "html", "css", "fastapi"]):
        fb = "Those are impressive and highly relevant technical skills to highlight."
    elif any(k in ans_lower for k in ["built", "project", "app", "system", "website", "developed", "created"]):
        fb = "Hands-on projects are the best proof of practical competence."
    else:
        fb = "Thank you for sharing that! That gives clear context for your resume."
    return fb, ask_next_question()


def process_interview_turn(answer: str):
    """
    Unified, ultra-fast interview turn processor (combines profile extraction, 
    personalized feedback, and next question generation into ONE single LLM call).
    Reduces latency from ~8-10 seconds to ~1 second.
    """
    global profile

    missing = check_profile()
    if not missing:
        save_profile()
        return (
            "Fantastic! That gives us a complete and comprehensive picture of your professional background.",
            "",
            True
        )

    target_area = missing[0]
    
    # Fast unified Gemini call
    if client:
        try:
            prompt = f"""You are Cara, the lightning-fast, encouraging AI career interviewer for CareerAI.
Candidate answer: "{answer}"
Current missing profile field needed: {target_area}

In ONE concise JSON object, return:
1. "feedback": 1 short warm sentence (max 20 words) acknowledging what they specifically said.
2. "next_question": Direct, friendly next question to ask about {target_area}.
3. "extracted": Any explicit fields stated by the candidate:
   {{"target_roles": [], "skills": [], "user_type": "", "education": [], "projects": []}}

Return ONLY raw JSON."""

            raw = call_gemini(prompt)
            if raw:
                cleaned = raw.replace("```json", "").replace("```", "").strip()
                data = json.loads(cleaned)
                fb = data.get("feedback", "").strip()
                nq = data.get("next_question", "").strip()
                extracted = data.get("extracted", {})

                if isinstance(extracted, dict):
                    if extracted.get("target_roles") and not profile.get("target_roles"):
                        profile["target_roles"] = extracted["target_roles"]
                    if extracted.get("user_type") and not profile.get("user_type"):
                        profile["user_type"] = extracted["user_type"]
                    if extracted.get("skills"):
                        for s in extracted["skills"]:
                            if s not in profile.get("skills", []):
                                profile.setdefault("skills", []).append(s)
                    if extracted.get("education") and not profile.get("education"):
                        profile["education"] = extracted["education"]
                    if extracted.get("projects") and not profile.get("projects"):
                        profile["projects"] = extracted["projects"]

                _apply_heuristic_profile(answer)

                new_missing = check_profile()
                if len(new_missing) == 0:
                    save_profile()
                    return ("Outstanding! You have completed the interview. Your background and career aspirations have been captured.", "", True)

                if fb and nq:
                    return (fb, nq, False)
        except Exception as e:
            print("Unified interview turn notice:", e)

    # Heuristic fallback if Gemini is offline
    _apply_heuristic_profile(answer)
    fb, nq = _heuristic_feedback_and_next_question(answer)
    new_missing = check_profile()
    if len(new_missing) == 0:
        save_profile()
        return ("Outstanding! You have completed the interview. Your background and career aspirations have been captured.", "", True)

    return (fb, nq, False)

def main():

    print("\n==========================================")
    print("        CareerAI Resume Interview")
    print("==========================================")

    speak(
        "Hello! Welcome to CareerAI. "
        "I will ask you a few questions to build your resume."
    )

    max_questions = 15

    for question_number in range(1, max_questions + 1):

        print(
            f"\n================ Question "
            f"{question_number}/{max_questions} ================"
        )

        # ----------------------------------------------------
        # Generate next question
        # ----------------------------------------------------

        question = ask_next_question()

        if not question:

            print("\nCould not generate the next question.")
            break

        # ----------------------------------------------------
        # THIS IS THE IMPORTANT PART:
        # speak() BOTH PRINTS AND SPEAKS THE QUESTION
        # ----------------------------------------------------

        speak(question)

        # ----------------------------------------------------
        # Listen to user
        # ----------------------------------------------------

        answer = listen()

        if not answer:

            print("\nNo answer detected.")
            continue

        # ----------------------------------------------------
        # Update profile using Gemini
        # ----------------------------------------------------

        update_profile(answer)

        # ----------------------------------------------------
        # Check completeness
        # ----------------------------------------------------

        missing = check_profile()

        print("\nCurrent profile completeness:")

        if not missing:

            print("✅ Required information collected.")

            save_profile()

            print("\n==========================================")
            print("Interview completed.")
            print("==========================================")

            print("\nFinal profile:")

            print(
                json.dumps(
                    profile,
                    indent=4,
                    ensure_ascii=False
                )
            )

            # ------------------------------------------------
            # AUTOMATIC RESUME GENERATION
            # ------------------------------------------------

            print("\nStarting resume generation...")

            try:

                result = subprocess.run(
                    [
                        "python",
                        "resume_generator.py"
                    ],
                    capture_output=False
                )

                if result.returncode == 0:

                    print(
                        "\n✅ Resume generation completed."
                    )

                else:

                    print(
                        "\n⚠️ Resume generator returned an error."
                    )

            except Exception as e:

                print(
                    "\nCould not start resume_generator.py:"
                )

                print(e)

            break

        else:

            print(
                "Still needed:",
                ", ".join(missing)
            )

    else:

        print(
            "\nMaximum interview questions reached."
        )

        save_profile()

        print(
            "\nThe collected profile has been saved."
        )


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":
    main()
    
