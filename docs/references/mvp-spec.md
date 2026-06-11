# AI Mock Interview System MVP Spec

## Goal

Build a first usable version of an AI mock interview trainer for junior/senior university students and job seekers.

The MVP focuses on one complete practice loop:

1. The user enters resume highlights.
2. The user enters a target job description.
3. The system generates a mock interview plan.
4. The user answers interview questions.
5. The system produces a structured interview report.

## Target Users

- Junior and senior university students looking for internships or full-time jobs.
- Social job seekers who want to practice before real interviews.

## MVP Scope

### Included

- Resume application entry.
- Resume input.
- Job description input.
- Company or role expectation input.
- Interview mode selection.
- AI interviewer simulation with staged questions.
- Answer collection.
- Final report with scores, strengths, risks, and next practice suggestions.

### Not Included Yet

- Real model API calls.
- Real vector database.
- File upload parsing.
- Login and user accounts.
- Payment.
- Multi-user admin dashboard.

## Interview Flow

1. Preparation
   - User creates a lightweight resume application.
   - User fills in candidate name, target role, application type, resume highlights, target JD, company expectation, and interview mode.
2. Opening
   - Interviewer asks for a self-introduction.
3. Project Deep Dive
   - Interviewer asks about a project or experience from the resume.
4. Technical / Role Question
   - Interviewer asks a role-related question based on the JD.
5. Behavioral Question
   - Interviewer asks about collaboration, pressure, learning, or conflict.
6. Salary / Expectation
   - Interviewer asks about expectation, availability, or career plan.
7. Report
   - System summarizes answers and gives structured feedback.

## Future RAG Design

### RAG 1: Role Knowledge Base

Stores job-related and interview-related knowledge:

- Job descriptions.
- Company requirements.
- Interview question bank.
- Standard answer points.
- Technology knowledge.
- Common follow-up questions.

### RAG 2: Candidate Profile Base

Stores candidate-related context:

- Resume content.
- Project experience.
- Skills.
- Education background.
- Self-introduction.
- Historical interview answers.
- Weakness profile.

## Model Behavior Rules

Natural output is preferred for:

- Opening conversation.
- Self-introduction guidance.
- Follow-up transitions.
- Encouragement.

Stable output is preferred for:

- Technical scoring.
- Salary advice.
- Resume risk analysis.
- Job matching.
- Final reports.

## Acceptance Criteria

- The user can complete a mock interview without leaving the page.
- The app asks at least five staged questions.
- The next question uses the user's resume or JD content in some way.
- The app saves answers during the session.
- The final report includes scores, strengths, risks, and action suggestions.

## Phase 2: Real Model API

The next version should replace local rule-based question generation with a backend model proxy.

### API Key Rule

- The real API key MUST stay on the backend.
- The frontend MUST NOT store or send the API key directly.
- Local secrets should be stored in `.env`, which is ignored by Git.

### Backend Endpoints

#### POST /api/interview/questions

Input:

- resume
- jd
- company
- mode

Output:

- questions: array of five staged interview questions

#### POST /api/interview/next-question

Input:

- profile
- history
- nextStage

Output:

- stage
- stability
- prompt

Behavior:

- The model should read previous answers before asking the next question.
- The next question should follow the planned interview stages.
- If the previous answer is weak, the next question may include one focused follow-up.
- The system should still finish in five stages.

#### POST /api/interview/report

Input:

- profile
- answers

Output:

- score
- strengths
- risks
- actions

### Model Settings

Question generation should be more natural:

- temperature around 0.7

Report and scoring should be more stable:

- temperature around 0.2

### Fallback Rule

If the model API fails, the app should fall back to local MVP rules so the user can still complete the interview.

## Phase 3: Dynamic Interviewer

The interviewer should no longer behave like a fixed questionnaire.

After each user answer:

1. Save the current answer.
2. Send the profile, answer history, and next stage to the backend.
3. Generate the next question based on the previous answer.
4. Continue until the final report.

The fixed five-stage flow remains:

1. Self-introduction.
2. Project deep dive.
3. Technical / role question.
4. Behavioral question.
5. Salary and career plan.

The MVP uses five stages only as the fastest practice mode. Later versions should support configurable interview depth.

Recommended modes:

- Quick: 5 questions.
- Standard: 8 questions.
- Deep: 12 questions.

Deep modes should add more rounds for:

- Project deep dive.
- Technical follow-up.
- Scenario problem solving.
- Resume risk probing.

## Phase 4: Resume Application Entry

The product should feel like a job-seeking workflow, not just a chat page.

The first screen should include a lightweight resume application entry:

- Candidate name.
- Target role.
- Application type.
- Resume highlights.
- Target JD.
- Company expectation.
- Interview mode.

In the MVP, the resume is entered as text. Later versions may support PDF, Word, and image resume parsing.

## Phase 5: Resume Upload Parsing

The application entry should support real resume upload.

Supported MVP formats:

- PDF resume.
- Image resume: PNG, JPG, JPEG, WebP.

Behavior:

- Uploaded files are parsed by the backend.
- PDF resumes are converted to text.
- Image resumes are interpreted by a vision model.
- The parsed resume summary should fill the resume highlights field.
- The original file should not be stored by the MVP backend.

Future versions may support:

- Word resumes.
- Multi-page image resumes.
- Structured resume fields.
- Candidate profile RAG storage.

## Phase 6: Interview History and Review

The product should keep a lightweight practice history so users can review progress.

MVP storage:

- Browser localStorage.

Saved fields:

- Interview time.
- Candidate name.
- Target role.
- Application type.
- Interview mode.
- Questions.
- Answers.
- Final report.

Review view:

- Shows each question and user answer.
- Shows score, strengths, risks, and next actions.
- Helps users compare repeated practice sessions.

## Phase 7: Python FastAPI Backend

The project should provide a Python backend version for candidates who are more familiar with Python.

The FastAPI backend should mirror the current Node backend:

- POST /api/interview/next-question
- POST /api/interview/report
- POST /api/resume/parse

Reasons:

- Easier for Python learners to explain in interviews.
- Clearer API schema with Pydantic.
- Better path for later RAG, data processing, and model orchestration.

The Node backend remains as a working reference during migration.

Backend module layout:

- config.py: environment variables and project paths.
- schemas.py: request and response models.
- llm_client.py: DashScope / Qwen API calls.
- resume_parser.py: PDF and image resume parsing.
- routes/interview.py: interview question and report endpoints.
- routes/resume.py: resume upload endpoint.
- main.py: FastAPI app entry.
