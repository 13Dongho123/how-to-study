from app.extensions import db
from app.models import SyllabusKeyword, SyllabusTopic, Topic

DEFAULT_TOPICS = [
    ("파일시스템", 3, "파일/디렉터리 구조, 권한, 링크"),
    ("사용자/권한", 3, "계정, 그룹, sudo, ACL"),
    ("프로세스/서비스", 2, "ps, top, systemctl, journalctl"),
    ("네트워크", 2, "ip, ss, netstat, DNS, 방화벽"),
    ("셸/스크립트", 2, "bash 기본 문법, 변수, 파이프"),
]

SYLLABUS = {
    "파일 관리": ["ls", "cp", "mv", "rm", "find", "tar", "chmod", "chown"],
    "프로세스 관리": ["ps", "top", "kill", "nice", "systemctl", "journalctl"],
    "네트워크": ["ip", "ping", "ss", "netstat", "curl", "wget", "dns"],
    "셸 활용": ["grep", "awk", "sed", "xargs", "pipe", "redirect"],
}


def seed_defaults():
    for name, weight, desc in DEFAULT_TOPICS:
        if not Topic.query.filter_by(name=name).first():
            db.session.add(Topic(name=name, weight=weight, description=desc))

    for topic_name, keywords in SYLLABUS.items():
        st = SyllabusTopic.query.filter_by(name=topic_name).first()
        if not st:
            st = SyllabusTopic(name=topic_name)
            db.session.add(st)
            db.session.flush()
        for kw in keywords:
            exists = SyllabusKeyword.query.filter_by(topic_id=st.id, keyword=kw).first()
            if not exists:
                db.session.add(SyllabusKeyword(topic_id=st.id, keyword=kw))

    db.session.commit()
