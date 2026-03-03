import json
from typing import Any, Dict, List

from openai import OpenAI

SYSTEM_PROMPT = (
    "You are a strict quiz generator. Return ONLY valid JSON array. "
    "No markdown, no commentary."
)

USER_PROMPT_TEMPLATE = """
Generate exactly {num_questions} questions in JSON array format.
Each item schema:
{{
  "type": "mcq" or "short",
  "question": "string",
  "choices": ["A","B","C","D"],  // required when type=mcq
  "answer": "string",
  "explanation": "string",
  "tags": ["keyword1", "keyword2"]
}}

Rules:
- Scope mode: {scope_mode}
- Focus keywords: {focus_keywords}
- If scope mode is SYLLABUS or CUSTOM, questions MUST be only about focus keywords.
- Mix conceptual and practical Linux command questions.
- Korean language.

Source context:
{source_text}
"""


class AIService:
    def __init__(self, api_key: str | None):
        self.api_key = api_key or ""
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def generate_quiz(
        self,
        source_text: str,
        num_questions: int = 10,
        scope_mode: str = "ALL",
        focus_keywords: List[str] | None = None,
    ) -> List[Dict[str, Any]]:
        focus_keywords = focus_keywords or []
        if not self.client:
            return self._dummy_questions(num_questions, focus_keywords)

        prompt = USER_PROMPT_TEMPLATE.format(
            num_questions=num_questions,
            scope_mode=scope_mode,
            focus_keywords=", ".join(focus_keywords) if focus_keywords else "N/A",
            source_text=source_text[:20000],
        )

        last_error = None
        for _ in range(3):
            try:
                resp = self.client.chat.completions.create(
                    model="gpt-4.1-mini",
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": (
                                "Return with root key 'questions' as an array.\n" + prompt
                            ),
                        },
                    ],
                    temperature=0.3,
                )
                content = resp.choices[0].message.content or "{}"
                data = json.loads(content)
                questions = data.get("questions") if isinstance(data, dict) else data
                validated = self._validate_questions(questions)
                if validated:
                    return validated[:num_questions]
            except Exception as exc:  # noqa: BLE001
                last_error = exc

        if last_error:
            raise ValueError(f"AI 퀴즈 생성 실패: {last_error}")
        raise ValueError("AI 퀴즈 생성 실패: JSON 파싱/검증 오류")

    def _validate_questions(self, questions: Any) -> List[Dict[str, Any]]:
        if not isinstance(questions, list):
            return []

        out = []
        for q in questions:
            if not isinstance(q, dict):
                continue
            q_type = q.get("type", "short")
            question = str(q.get("question", "")).strip()
            answer = str(q.get("answer", "")).strip()
            explanation = str(q.get("explanation", "")).strip()
            if not question or not answer:
                continue

            item = {
                "type": "mcq" if q_type == "mcq" else "short",
                "question": question,
                "answer": answer,
                "explanation": explanation,
                "choices": q.get("choices") if q_type == "mcq" else None,
                "tags": q.get("tags") if isinstance(q.get("tags"), list) else [],
            }
            if item["type"] == "mcq":
                if not isinstance(item["choices"], list) or len(item["choices"]) < 2:
                    continue
            out.append(item)
        return out

    def _dummy_questions(self, num_questions: int, focus_keywords: List[str]) -> List[Dict[str, Any]]:
        keyword = focus_keywords[0] if focus_keywords else "Linux 기본"
        sample = [
            {
                "type": "mcq",
                "question": f"{keyword}와 관련해 파일 권한을 확인하는 명령어는?",
                "choices": ["ls -l", "pwd", "whoami", "uname -r"],
                "answer": "ls -l",
                "explanation": "ls -l은 파일의 퍼미션, 소유자, 크기 정보를 함께 보여줍니다.",
                "tags": [keyword, "permissions"],
            },
            {
                "type": "short",
                "question": f"{keyword} 학습에서 grep 명령어의 기본 목적을 한 줄로 설명하세요.",
                "answer": "텍스트에서 패턴을 검색하기 위해 사용한다.",
                "explanation": "grep은 로그 분석이나 설정 파일 검색에 자주 사용됩니다.",
                "tags": [keyword, "grep"],
            },
        ]
        result = []
        idx = 0
        while len(result) < num_questions:
            result.append(sample[idx % len(sample)])
            idx += 1
        return result
