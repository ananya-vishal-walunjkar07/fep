import io
import sys
from pathlib import Path

import speech_recognition as sr
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

# Locate the project root and load its .env file before importing the AI module.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import resume_interview as interview_ai


# Routes for /interview/start and /interview/answer
router = APIRouter()

# Separate router for /speech/transcribe
speech_router = APIRouter()

interview_started = False


class AnswerRequest(BaseModel):
    answer: str


@router.post("/start")
def start_interview():
    global interview_started

    interview_ai.profile = {
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
        "links": [],
    }

    interview_started = True

    try:
        question = interview_ai.ask_next_question()
        return {"success": True, "question": question}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not generate interview question: {exc}",
        )


@router.post("/answer")
def submit_answer(data: AnswerRequest):
    global interview_started
    if not interview_started:
        interview_started = True
        if not hasattr(interview_ai, "profile") or not interview_ai.profile:
            interview_ai.profile = {
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
                "links": [],
            }

    try:
        interview_ai.update_profile(data.answer)

        missing = interview_ai.check_profile()

        if not missing:
            interview_ai.save_profile()
            return {
                "success": True,
                "completed": True,
                "feedback": "Outstanding! You have completed the interview. Your background and career aspirations have been captured.",
                "next_question": "",
            }

        fb, question = interview_ai.generate_feedback_and_next_question(data.answer)

        return {
            "success": True,
            "completed": False,
            "feedback": fb,
            "next_question": question,
        }

    except Exception as exc:
        print("Submit answer notice:", exc)
        try:
            fb, question = interview_ai.generate_feedback_and_next_question(data.answer)
            return {
                "success": True,
                "completed": False,
                "feedback": fb,
                "next_question": question,
            }
        except Exception:
            return {
                "success": True,
                "completed": False,
                "feedback": "Thank you for sharing that!",
                "next_question": interview_ai.ask_next_question(),
            }


@speech_router.post("/speech/transcribe")
async def transcribe_speech(request: Request):
    audio_bytes = await request.body()

    if not audio_bytes:
        raise HTTPException(
            status_code=400,
            detail="No audio data received.",
        )

    try:
        recognizer = sr.Recognizer()

        with sr.AudioFile(io.BytesIO(audio_bytes)) as audio_file:
            audio = recognizer.record(audio_file)

        text = recognizer.recognize_google(audio)

        return {"success": True, "text": text}

    except sr.UnknownValueError:
        return {"success": True, "text": ""}

    except sr.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Speech recognition service unavailable: {exc}",
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not process audio: {exc}",
        )