from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "campus" / "campus.sqlite"


COLLEGES = [
    (1, "计算机学院"),
    (2, "航空学院"),
    (3, "经管学院"),
    (4, "自动化学院"),
    (5, "材料学院"),
]

MAJORS = [
    (1, 1, "计算机科学与技术", "工科"),
    (2, 1, "人工智能", "工科"),
    (3, 2, "飞行器设计", "工科"),
    (4, 2, "无人机系统工程", "工科"),
    (5, 3, "信息管理", "管理"),
    (6, 3, "工商管理", "管理"),
    (7, 4, "自动化", "工科"),
    (8, 4, "机器人工程", "工科"),
    (9, 5, "材料科学与工程", "工科"),
    (10, 5, "新能源材料", "工科"),
]

MAJOR_STUDENT_COUNTS = {
    1: 38,
    2: 34,
    3: 22,
    4: 16,
    5: 24,
    6: 19,
    7: 31,
    8: 24,
    9: 18,
    10: 14,
}

TEACHERS = [
    (1, 1, "陈明远", "教授"),
    (2, 1, "孙若琳", "教授"),
    (3, 1, "周启航", "副教授"),
    (4, 1, "吴嘉宁", "副教授"),
    (5, 1, "赵景行", "讲师"),
    (6, 1, "林可", "讲师"),
    (7, 2, "刘远峰", "教授"),
    (8, 2, "唐诗雨", "副教授"),
    (9, 2, "韩承志", "教授"),
    (10, 2, "罗文博", "讲师"),
    (11, 3, "何知远", "教授"),
    (12, 3, "郭念", "副教授"),
    (13, 3, "邱晨", "副教授"),
    (14, 3, "宋佳", "讲师"),
    (15, 4, "马天行", "教授"),
    (16, 4, "梁书衡", "教授"),
    (17, 4, "谢安琪", "副教授"),
    (18, 4, "许凌", "讲师"),
    (19, 5, "朱怀瑾", "教授"),
    (20, 5, "沈砚", "副教授"),
    (21, 5, "叶清", "讲师"),
]

COURSES = [
    (1, 1, "数据库系统", "核心专业课", 3.0),
    (2, 1, "数据结构", "核心专业课", 4.0),
    (3, 2, "机器学习", "核心专业课", 3.0),
    (4, 2, "深度学习导论", "核心专业课", 3.0),
    (5, 3, "空气动力学", "核心专业课", 3.0),
    (6, 4, "无人机控制", "核心专业课", 3.0),
    (7, 5, "管理信息系统", "专业课", 2.0),
    (8, 6, "运营管理", "专业课", 2.0),
    (9, 7, "控制原理", "核心专业课", 3.0),
    (10, 8, "机器人导航", "核心专业课", 3.0),
    (11, 9, "材料力学", "核心专业课", 3.0),
    (12, 10, "新能源材料基础", "核心专业课", 3.0),
    (13, 1, "科技写作", "通识选修", 2.0),
    (14, 2, "创新创业基础", "通识选修", 2.0),
    (15, 5, "数据可视化", "通识选修", 2.0),
]

OFFERINGS = [
    (1, 1, 1, "2026春", "学院路校区"),
    (2, 2, 3, "2025秋", "学院路校区"),
    (3, 3, 2, "2026春", "学院路校区"),
    (4, 4, 4, "2025秋", "学院路校区"),
    (5, 5, 7, "2026春", "沙河校区"),
    (6, 6, 8, "2026春", "沙河校区"),
    (7, 7, 11, "2026春", "学院路校区"),
    (8, 8, 12, "2025秋", "学院路校区"),
    (9, 9, 15, "2026春", "沙河校区"),
    (10, 10, 16, "2026春", "沙河校区"),
    (11, 11, 19, "2026春", "良乡校区"),
    (12, 12, 20, "2025秋", "良乡校区"),
    (13, 13, 5, "2026春", "学院路校区"),
    (14, 14, 6, "2026春", "学院路校区"),
    (15, 15, 13, "2026春", "学院路校区"),
]

DORMITORIES = [
    (1, "学院路校区", "知行一号楼", "101", 6),
    (2, "学院路校区", "知行二号楼", "208", 6),
    (3, "沙河校区", "启航三号楼", "305", 4),
    (4, "沙河校区", "启航四号楼", "412", 4),
    (5, "良乡校区", "明德一号楼", "120", 4),
    (6, "良乡校区", "明德二号楼", "218", 4),
]


def grade_point(score: float) -> float:
    if score >= 90:
        return 4.0
    if score >= 85:
        return 3.7
    if score >= 80:
        return 3.3
    if score >= 75:
        return 3.0
    if score >= 70:
        return 2.5
    if score >= 65:
        return 2.0
    if score >= 60:
        return 1.5
    return 0.0


def ensure_columns(conn: sqlite3.Connection) -> None:
    project_columns = {row[1] for row in conn.execute("PRAGMA table_info(projects)")}
    if "approved_date" not in project_columns:
        conn.execute("ALTER TABLE projects ADD COLUMN approved_date TEXT")


def reset_tables(conn: sqlite3.Connection) -> None:
    for table in [
        "awards_penalties",
        "repair_orders",
        "papers",
        "projects",
        "enrollments",
        "course_offerings",
        "courses",
        "teachers",
        "students",
        "dormitories",
        "classes",
        "majors",
        "colleges",
    ]:
        conn.execute(f"DELETE FROM {table}")


def seed_foundation(conn: sqlite3.Connection) -> None:
    conn.executemany("INSERT INTO colleges VALUES (?, ?)", COLLEGES)
    conn.executemany("INSERT INTO majors VALUES (?, ?, ?, ?)", MAJORS)
    classes = []
    for major_id, _college_id, major_name, _category in MAJORS:
        classes.append((major_id, major_id, 2023 + major_id % 3, f"{major_name}{2023 + major_id % 3}级1班", f"辅导员{major_id:02d}"))
    conn.executemany("INSERT INTO classes VALUES (?, ?, ?, ?, ?)", classes)
    conn.executemany("INSERT INTO dormitories VALUES (?, ?, ?, ?, ?)", DORMITORIES)
    conn.executemany("INSERT INTO teachers VALUES (?, ?, ?, ?)", TEACHERS)
    conn.executemany("INSERT INTO courses VALUES (?, ?, ?, ?, ?)", COURSES)
    conn.executemany("INSERT INTO course_offerings VALUES (?, ?, ?, ?, ?)", OFFERINGS)


def seed_students(conn: sqlite3.Connection) -> None:
    students = []
    student_id = 1
    for major_id, college_id, major_name, _category in MAJORS:
        for index in range(1, MAJOR_STUDENT_COUNTS[major_id] + 1):
            gender = "女" if (index + major_id) % 3 == 0 else "男"
            status = "休学" if index == MAJOR_STUDENT_COUNTS[major_id] and major_id in {4, 10} else "在读"
            enrollment_year = 2022 + (index % 4)
            dorm_id = ((student_id - 1) % len(DORMITORIES)) + 1
            students.append(
                (
                    student_id,
                    major_id,
                    college_id,
                    major_id,
                    f"{major_name}学生{index:02d}",
                    gender,
                    enrollment_year,
                    status,
                    dorm_id,
                )
            )
            student_id += 1
    conn.executemany("INSERT INTO students VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", students)


def seed_enrollments(conn: sqlite3.Connection) -> None:
    major_to_offerings = {
        1: [1, 2, 13],
        2: [3, 4, 14],
        3: [5, 13],
        4: [6, 14],
        5: [7, 8, 15],
        6: [8, 15],
        7: [9, 13],
        8: [10, 14],
        9: [11, 15],
        10: [12, 13],
    }
    base_scores = {1: 84, 2: 89, 3: 76, 4: 73, 5: 80, 6: 78, 7: 83, 8: 81, 9: 72, 10: 75}
    hard_offerings = {5, 6, 11, 12}
    enrollments = []
    enrollment_id = 1
    rows = conn.execute("SELECT student_id, major_id, status FROM students ORDER BY student_id").fetchall()
    for student_id, major_id, status in rows:
        if status != "在读":
            continue
        for offering_id in major_to_offerings[major_id]:
            score = base_scores[major_id] + ((student_id + offering_id) % 11) - 5
            if offering_id in hard_offerings and student_id % 7 == 0:
                score = 54 + student_id % 5
            if offering_id in {11, 12} and student_id % 5 == 0:
                score = 58
            score = float(max(45, min(98, score)))
            passed = 1 if score >= 60 else 0
            enrollments.append((enrollment_id, student_id, offering_id, score, passed, grade_point(score)))
            enrollment_id += 1
    conn.executemany("INSERT INTO enrollments VALUES (?, ?, ?, ?, ?, ?)", enrollments)


def seed_projects(conn: sqlite3.Connection) -> None:
    projects = [
        (1, 1, 1, "面向教育问数的数据库智能体", "国家级", 2024, 180.0, "在研", "2024-03-12"),
        (2, 2, 1, "多模态校园治理分析", "省部级", 2025, 96.0, "在研", "2025-09-22"),
        (3, 3, 1, "可信 Text-to-SQL 评测平台", "国家级", 2026, 220.0, "在研", "2026-05-02"),
        (4, 4, 1, "智能数据库安全审计", "校级", 2026, 42.0, "在研", "2026-05-07"),
        (5, 7, 2, "飞行器气动优化平台", "国家级", 2023, 165.0, "结题", "2023-04-18"),
        (6, 8, 2, "低空无人机协同设计", "省部级", 2025, 88.0, "在研", "2025-11-03"),
        (7, 9, 2, "空天结构数字孪生", "国家级", 2026, 190.0, "在研", "2026-05-05"),
        (8, 10, 2, "风洞实验数据治理", "校级", 2026, 36.0, "在研", "2026-05-12"),
        (9, 11, 3, "数字化运营决策支持", "省部级", 2024, 92.0, "结题", "2024-06-01"),
        (10, 12, 3, "高校预算绩效分析", "校级", 2025, 34.0, "在研", "2025-10-13"),
        (11, 13, 3, "校园资源配置优化", "省部级", 2026, 101.0, "在研", "2026-05-18"),
        (12, 14, 3, "学生发展预测模型", "校级", 2026, 28.0, "在研", "2026-05-22"),
        (13, 15, 4, "智能控制系统验证", "国家级", 2024, 155.0, "在研", "2024-08-20"),
        (14, 16, 4, "机器人自主导航", "省部级", 2025, 90.0, "在研", "2025-12-10"),
        (15, 17, 4, "工业过程控制优化", "国家级", 2026, 176.0, "在研", "2026-05-09"),
        (16, 18, 4, "实验室设备预测维护", "校级", 2026, 31.0, "在研", "2026-05-25"),
        (17, 19, 5, "高性能复合材料制备", "国家级", 2023, 142.0, "结题", "2023-07-16"),
        (18, 20, 5, "新能源材料界面调控", "省部级", 2025, 83.0, "在研", "2025-09-28"),
        (19, 21, 5, "材料实验数据平台", "校级", 2026, 29.0, "在研", "2026-05-28"),
        (20, 19, 5, "轻量化材料服役评估", "国家级", 2026, 160.0, "在研", "2026-05-30"),
    ]
    conn.executemany("INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", projects)


def seed_papers(conn: sqlite3.Connection) -> None:
    papers = []
    paper_id = 1
    teacher_targets = {
        1: (8, 1),
        2: (6, 1),
        3: (5, 1),
        7: (7, 2),
        9: (5, 2),
        11: (6, 3),
        12: (4, 3),
        15: (7, 4),
        16: (5, 4),
        19: (6, 5),
        20: (3, 5),
    }
    for teacher_id, (count, college_id) in teacher_targets.items():
        for index in range(count):
            year = 2022 + (index % 5)
            zone = "一区" if index % 3 != 1 else "二区"
            papers.append(
                (
                    paper_id,
                    teacher_id,
                    college_id,
                    f"校园智慧分析研究{teacher_id:02d}-{index + 1:02d}",
                    zone,
                    year,
                    f"Journal {chr(65 + teacher_id % 20)}",
                )
            )
            paper_id += 1
    conn.executemany("INSERT INTO papers VALUES (?, ?, ?, ?, ?, ?, ?)", papers)


def seed_repairs_and_awards(conn: sqlite3.Connection) -> None:
    repairs = []
    categories = ["水电", "网络", "门窗", "空调"]
    statuses = ["已完成", "处理中", "待派单"]
    for idx in range(1, 37):
        dorm_id = ((idx - 1) % len(DORMITORIES)) + 1
        student_id = ((idx * 5) % 230) + 1
        month = ((idx - 1) % 12) + 1
        day = ((idx * 3) % 26) + 1
        status = statuses[idx % len(statuses)]
        report_date = f"2026-{month:02d}-{day:02d}"
        resolved_date = None if status != "已完成" else f"2026-{month:02d}-{min(day + 2, 28):02d}"
        repairs.append((idx, dorm_id, student_id, categories[idx % len(categories)], status, report_date, resolved_date))
    conn.executemany("INSERT INTO repair_orders VALUES (?, ?, ?, ?, ?, ?, ?)", repairs)

    award_students = {
        1: [3, 9, 18, 31, 44],
        2: [75, 82, 91],
        3: [112, 126, 139],
        4: [151, 166, 180],
        5: [198, 211, 224],
    }
    penalty_students = {
        1: [52],
        2: [101],
        3: [143],
        4: [187],
        5: [231],
    }
    awards = []
    record_id = 1
    for college_id, student_ids in award_students.items():
        for offset, student_id in enumerate(student_ids):
            awards.append((record_id, student_id, "奖励", "省级" if offset == 0 else "校级", f"2026-0{college_id}-15", "学科竞赛"))
            record_id += 1
    for college_id, student_ids in penalty_students.items():
        for student_id in student_ids:
            awards.append((record_id, student_id, "惩罚", "院级", f"2026-0{college_id + 1}-18", "考试违纪"))
            record_id += 1
    conn.executemany("INSERT INTO awards_penalties VALUES (?, ?, ?, ?, ?, ?)", awards)


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        ensure_columns(conn)
        reset_tables(conn)
        seed_foundation(conn)
        seed_students(conn)
        seed_enrollments(conn)
        seed_projects(conn)
        seed_papers(conn)
        seed_repairs_and_awards(conn)
        conn.commit()
        conn.execute("VACUUM")
    finally:
        conn.close()
    print(f"Seeded campus demo data: {DB_PATH}")


if __name__ == "__main__":
    main()
