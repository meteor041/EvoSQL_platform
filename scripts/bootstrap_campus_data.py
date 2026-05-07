from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data' / 'campus'
DB_PATH = DATA_DIR / 'campus.sqlite'


def build_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript('''
    PRAGMA foreign_keys = ON;
    CREATE TABLE colleges (college_id INTEGER PRIMARY KEY, college_name TEXT NOT NULL);
    CREATE TABLE majors (major_id INTEGER PRIMARY KEY, college_id INTEGER NOT NULL, major_name TEXT NOT NULL, category TEXT NOT NULL, FOREIGN KEY (college_id) REFERENCES colleges(college_id));
    CREATE TABLE classes (class_id INTEGER PRIMARY KEY, major_id INTEGER NOT NULL, grade_year INTEGER NOT NULL, class_name TEXT NOT NULL, counselor_name TEXT NOT NULL, FOREIGN KEY (major_id) REFERENCES majors(major_id));
    CREATE TABLE students (student_id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL, college_id INTEGER NOT NULL, major_id INTEGER NOT NULL, student_name TEXT NOT NULL, gender TEXT NOT NULL, enrollment_year INTEGER NOT NULL, status TEXT NOT NULL, dorm_id INTEGER, FOREIGN KEY (class_id) REFERENCES classes(class_id), FOREIGN KEY (college_id) REFERENCES colleges(college_id), FOREIGN KEY (major_id) REFERENCES majors(major_id));
    CREATE TABLE dormitories (dorm_id INTEGER PRIMARY KEY, campus_name TEXT NOT NULL, building_name TEXT NOT NULL, room_no TEXT NOT NULL, capacity INTEGER NOT NULL);
    CREATE TABLE repair_orders (repair_id INTEGER PRIMARY KEY, dorm_id INTEGER NOT NULL, student_id INTEGER, category TEXT NOT NULL, status TEXT NOT NULL, report_date TEXT NOT NULL, resolved_date TEXT, FOREIGN KEY (dorm_id) REFERENCES dormitories(dorm_id), FOREIGN KEY (student_id) REFERENCES students(student_id));
    CREATE TABLE teachers (teacher_id INTEGER PRIMARY KEY, college_id INTEGER NOT NULL, teacher_name TEXT NOT NULL, title TEXT NOT NULL, FOREIGN KEY (college_id) REFERENCES colleges(college_id));
    CREATE TABLE courses (course_id INTEGER PRIMARY KEY, major_id INTEGER NOT NULL, course_name TEXT NOT NULL, course_type TEXT NOT NULL, credit REAL NOT NULL, FOREIGN KEY (major_id) REFERENCES majors(major_id));
    CREATE TABLE course_offerings (offering_id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL, teacher_id INTEGER NOT NULL, term TEXT NOT NULL, campus_name TEXT NOT NULL, FOREIGN KEY (course_id) REFERENCES courses(course_id), FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id));
    CREATE TABLE enrollments (enrollment_id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, offering_id INTEGER NOT NULL, score REAL, passed INTEGER NOT NULL, grade_point REAL, FOREIGN KEY (student_id) REFERENCES students(student_id), FOREIGN KEY (offering_id) REFERENCES course_offerings(offering_id));
    CREATE TABLE awards_penalties (record_id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, record_type TEXT NOT NULL, level TEXT NOT NULL, record_date TEXT NOT NULL, reason TEXT NOT NULL, FOREIGN KEY (student_id) REFERENCES students(student_id));
    CREATE TABLE projects (project_id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL, college_id INTEGER NOT NULL, project_name TEXT NOT NULL, project_level TEXT NOT NULL, approved_year INTEGER NOT NULL, funding REAL NOT NULL, status TEXT NOT NULL, FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id), FOREIGN KEY (college_id) REFERENCES colleges(college_id));
    CREATE TABLE papers (paper_id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL, college_id INTEGER NOT NULL, title TEXT NOT NULL, zone TEXT NOT NULL, publish_year INTEGER NOT NULL, journal TEXT NOT NULL, FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id), FOREIGN KEY (college_id) REFERENCES colleges(college_id));
    ''')

    colleges = [(1, '计算机学院'), (2, '航空学院'), (3, '经管学院'), (4, '自动化学院')]
    majors = [(1, 1, '计算机科学与技术', '工科'), (2, 1, '人工智能', '工科'), (3, 2, '飞行器设计', '工科'), (4, 3, '信息管理', '管理'), (5, 4, '自动化', '工科')]
    classes = [(1, 1, 2022, '计科2201', '张老师'), (2, 2, 2022, '人工智能2201', '李老师'), (3, 3, 2021, '飞设2101', '王老师'), (4, 4, 2022, '信管2201', '赵老师'), (5, 5, 2021, '自动化2101', '周老师')]
    dorms = [(1, '学院路校区', '1号楼', '101', 4), (2, '学院路校区', '1号楼', '102', 4), (3, '沙河校区', '3号楼', '301', 4), (4, '沙河校区', '3号楼', '302', 4), (5, '学院路校区', '2号楼', '201', 4)]
    teachers = [(1, 1, '陈教授', '教授'), (2, 1, '孙副教授', '副教授'), (3, 2, '刘教授', '教授'), (4, 3, '何副教授', '副教授'), (5, 4, '马教授', '教授')]
    courses = [(1, 1, '数据库系统', '核心专业课', 3.0), (2, 1, '数据结构', '核心专业课', 4.0), (3, 2, '机器学习', '核心专业课', 3.0), (4, 3, '空气动力学', '核心专业课', 3.0), (5, 4, '管理信息系统', '专业课', 2.0), (6, 5, '控制原理', '核心专业课', 3.0), (7, 1, '科技写作', '通识选修', 2.0), (8, 2, '创新创业基础', '通识选修', 2.0)]
    offerings = [(1, 1, 1, '2024秋', '学院路校区'), (2, 2, 2, '2024秋', '学院路校区'), (3, 3, 2, '2024秋', '学院路校区'), (4, 4, 3, '2024春', '沙河校区'), (5, 5, 4, '2024秋', '学院路校区'), (6, 6, 5, '2024春', '沙河校区'), (7, 7, 1, '2024秋', '学院路校区'), (8, 8, 5, '2024秋', '沙河校区')]
    projects = [(1, 1, 1, '面向教育问数的数据库智能体', '国家级', 2022, 120.0, '在研'), (2, 2, 1, '多模态校园治理分析', '省部级', 2023, 80.0, '在研'), (3, 3, 2, '飞行器气动优化平台', '国家级', 2024, 150.0, '在研'), (4, 4, 3, '数字化运营决策支持', '校级', 2023, 30.0, '结题'), (5, 5, 4, '智能控制系统验证', '国家级', 2022, 110.0, '在研'), (6, 5, 4, '机器人自主导航', '省部级', 2024, 70.0, '在研')]
    papers = [(1, 1, 1, '大模型驱动问数平台', '一区', 2022, 'Journal A'), (2, 1, 1, '智能数据治理方法', '二区', 2023, 'Journal B'), (3, 2, 1, '教育数据语义解析', '一区', 2024, 'Journal C'), (4, 3, 2, '飞行器设计优化', '一区', 2023, 'Journal D'), (5, 4, 3, '运营分析模型', '二区', 2024, 'Journal E'), (6, 5, 4, '自主控制框架', '一区', 2022, 'Journal F'), (7, 5, 4, '机器人协同规划', '一区', 2024, 'Journal G')]

    cur.executemany('INSERT INTO colleges VALUES (?, ?)', colleges)
    cur.executemany('INSERT INTO majors VALUES (?, ?, ?, ?)', majors)
    cur.executemany('INSERT INTO classes VALUES (?, ?, ?, ?, ?)', classes)
    cur.executemany('INSERT INTO dormitories VALUES (?, ?, ?, ?, ?)', dorms)
    cur.executemany('INSERT INTO teachers VALUES (?, ?, ?, ?)', teachers)
    cur.executemany('INSERT INTO courses VALUES (?, ?, ?, ?, ?)', courses)
    cur.executemany('INSERT INTO course_offerings VALUES (?, ?, ?, ?, ?)', offerings)
    cur.executemany('INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?)', projects)
    cur.executemany('INSERT INTO papers VALUES (?, ?, ?, ?, ?, ?, ?)', papers)

    students = []
    student_id = 1
    for class_id, major_id, grade_year, _, _ in classes:
        college_id = next(item[1] for item in majors if item[0] == major_id)
        for i in range(1, 9):
            dorm_id = ((student_id - 1) % len(dorms)) + 1
            gender = '男' if i % 2 else '女'
            status = '在读' if i != 8 else '毕业'
            students.append((student_id, class_id, college_id, major_id, f'学生{student_id:03d}', gender, grade_year, status, dorm_id))
            student_id += 1
    cur.executemany('INSERT INTO students VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', students)

    enrollments = []
    enrollment_id = 1
    for student in students:
        sid, _, _, major_id, *_ = student
        available = [off for off in offerings if next(c for c in courses if c[0] == off[1])[1] == major_id or off[1] in (7, 8)]
        for off in available[:3]:
            score = 55 + ((sid + off[0] * 7) % 41)
            passed = 1 if score >= 60 else 0
            grade_point = round(max(score - 50, 0) / 10, 1)
            enrollments.append((enrollment_id, sid, off[0], score, passed, grade_point))
            enrollment_id += 1
    cur.executemany('INSERT INTO enrollments VALUES (?, ?, ?, ?, ?, ?)', enrollments)

    repairs = [(1, 1, 1, '空调', '已完成', '2024-09-02', '2024-09-03'), (2, 1, 2, '网络', '已完成', '2024-09-07', '2024-09-08'), (3, 2, 3, '门锁', '处理中', '2024-10-02', None), (4, 3, 9, '空调', '已完成', '2024-10-12', '2024-10-13'), (5, 4, 10, '热水', '已完成', '2024-11-04', '2024-11-05'), (6, 5, 17, '网络', '已完成', '2024-11-09', '2024-11-10'), (7, 3, 18, '空调', '处理中', '2024-12-01', None), (8, 4, 20, '照明', '已完成', '2024-12-05', '2024-12-06')]
    records = [(1, 1, '奖励', '校级', '2024-05-03', '优秀学生干部'), (2, 2, '惩罚', '院级', '2024-06-11', '晚归'), (3, 9, '奖励', '国家级', '2024-09-21', '学科竞赛一等奖'), (4, 13, '奖励', '校级', '2024-10-01', '志愿服务先进个人'), (5, 17, '惩罚', '校级', '2024-10-15', '考试违纪'), (6, 22, '奖励', '院级', '2024-11-20', '科研创新奖')]
    cur.executemany('INSERT INTO repair_orders VALUES (?, ?, ?, ?, ?, ?, ?)', repairs)
    cur.executemany('INSERT INTO awards_penalties VALUES (?, ?, ?, ?, ?, ?)', records)
    conn.commit()
    conn.close()


def build_metadata_and_qa() -> None:
    metadata = {
        'domains': {
            'teaching': ['colleges', 'majors', 'classes', 'students', 'courses', 'course_offerings', 'enrollments'],
            'student_affairs': ['students', 'dormitories', 'repair_orders', 'awards_penalties'],
            'research': ['teachers', 'projects', 'papers', 'colleges'],
        },
        'business_terms': {
            '挂科率': "挂科率 = 未通过人数 / 选课人数，未通过定义为 passed = 0",
            '一区论文': "一区论文对应 papers.zone = '一区'",
            '通识选修': "通识选修对应 courses.course_type = '通识选修'",
            '国家级项目': "国家级项目对应 projects.project_level = '国家级'",
            '在读学生': "在读学生对应 students.status = '在读'",
        },
        'synonyms': {'学院': ['college', '院系'], '专业': ['major'], '宿舍报修': ['维修', '报修工单'], '科研经费': ['项目经费', 'funding']},
    }
    (DATA_DIR / 'campus_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')

    queries = []
    def add(question: str, sql: str, aliases: list[str] | None = None) -> None:
        queries.append({'question': question, 'aliases': aliases or [], 'sql': sql})
    add('统计各学院当前学生人数', "SELECT c.college_name, COUNT(*) AS student_count FROM students s JOIN colleges c ON s.college_id = c.college_id WHERE s.status = '在读' GROUP BY c.college_name ORDER BY student_count DESC", ['各学院在读学生人数', '按学院统计当前学生数'])
    add('统计各专业当前学生人数', "SELECT m.major_name, COUNT(*) AS student_count FROM students s JOIN majors m ON s.major_id = m.major_id WHERE s.status = '在读' GROUP BY m.major_name ORDER BY student_count DESC", ['按专业统计在读学生人数'])
    add('统计各班级在读学生人数', "SELECT cl.class_name, COUNT(*) AS student_count FROM students s JOIN classes cl ON s.class_id = cl.class_id WHERE s.status = '在读' GROUP BY cl.class_name ORDER BY student_count DESC", ['各班在读人数'])
    add('统计各学院女生人数', "SELECT c.college_name, COUNT(*) AS female_count FROM students s JOIN colleges c ON s.college_id = c.college_id WHERE s.status = '在读' AND s.gender = '女' GROUP BY c.college_name ORDER BY female_count DESC", ['按学院统计女生数'])
    add('统计各学院男生人数', "SELECT c.college_name, COUNT(*) AS male_count FROM students s JOIN colleges c ON s.college_id = c.college_id WHERE s.status = '在读' AND s.gender = '男' GROUP BY c.college_name ORDER BY male_count DESC", ['按学院统计男生数'])
    add('查询各学院核心专业课平均分', "SELECT c.college_name, ROUND(AVG(e.score), 2) AS avg_score FROM enrollments e JOIN students s ON e.student_id = s.student_id JOIN course_offerings o ON e.offering_id = o.offering_id JOIN courses co ON o.course_id = co.course_id JOIN colleges c ON s.college_id = c.college_id WHERE co.course_type = '核心专业课' GROUP BY c.college_name ORDER BY avg_score DESC", ['各学院核心课平均成绩'])
    add('查询数据库系统课程的通过率', "SELECT ROUND(AVG(CASE WHEN e.passed = 1 THEN 1.0 ELSE 0 END), 3) AS pass_rate FROM enrollments e JOIN course_offerings o ON e.offering_id = o.offering_id JOIN courses c ON o.course_id = c.course_id WHERE c.course_name = '数据库系统'", ['数据库系统通过率'])
    add('查询机器学习课程的通过率', "SELECT ROUND(AVG(CASE WHEN e.passed = 1 THEN 1.0 ELSE 0 END), 3) AS pass_rate FROM enrollments e JOIN course_offerings o ON e.offering_id = o.offering_id JOIN courses c ON o.course_id = c.course_id WHERE c.course_name = '机器学习'", ['机器学习通过率'])
    add('查询挂科学生人数', 'SELECT COUNT(DISTINCT student_id) AS failed_student_count FROM enrollments WHERE passed = 0', ['有挂科记录的学生数'])
    add('统计各学院挂科率', "SELECT c.college_name, ROUND(AVG(CASE WHEN e.passed = 0 THEN 1.0 ELSE 0 END), 3) AS fail_rate FROM enrollments e JOIN students s ON e.student_id = s.student_id JOIN colleges c ON s.college_id = c.college_id GROUP BY c.college_name ORDER BY fail_rate DESC", ['按学院统计挂科率'])
    add('统计通识选修课平均分', "SELECT ROUND(AVG(e.score), 2) AS avg_score FROM enrollments e JOIN course_offerings o ON e.offering_id = o.offering_id JOIN courses c ON o.course_id = c.course_id WHERE c.course_type = '通识选修'", ['通识选修平均成绩'])
    add('统计各课程选课人数', 'SELECT c.course_name, COUNT(*) AS enrollment_count FROM enrollments e JOIN course_offerings o ON e.offering_id = o.offering_id JOIN courses c ON o.course_id = c.course_id GROUP BY c.course_name ORDER BY enrollment_count DESC', ['各门课选课人数'])
    add('查询学分最高的课程', 'SELECT course_name, credit FROM courses ORDER BY credit DESC LIMIT 1', ['最高学分课程'])
    add('查询当前在读学生最多的学院', "SELECT c.college_name, COUNT(*) AS student_count FROM students s JOIN colleges c ON s.college_id = c.college_id WHERE s.status = '在读' GROUP BY c.college_name ORDER BY student_count DESC LIMIT 1", ['学生数最多的学院'])
    add('统计各宿舍楼报修工单数量', 'SELECT d.building_name, COUNT(*) AS repair_count FROM repair_orders r JOIN dormitories d ON r.dorm_id = d.dorm_id GROUP BY d.building_name ORDER BY repair_count DESC', ['按宿舍楼统计报修数'])
    add('查询报修最多的类别', 'SELECT category, COUNT(*) AS repair_count FROM repair_orders GROUP BY category ORDER BY repair_count DESC LIMIT 1', ['最常见报修类别'])
    add('查询还未完成的宿舍报修单数量', "SELECT COUNT(*) AS pending_repairs FROM repair_orders WHERE status <> '已完成'", ['未完成报修数'])
    add('统计各校区宿舍报修数量', 'SELECT d.campus_name, COUNT(*) AS repair_count FROM repair_orders r JOIN dormitories d ON r.dorm_id = d.dorm_id GROUP BY d.campus_name ORDER BY repair_count DESC', ['按校区统计报修数'])
    add('统计各月份宿舍报修趋势', 'SELECT substr(report_date, 1, 7) AS month, COUNT(*) AS repair_count FROM repair_orders GROUP BY substr(report_date, 1, 7) ORDER BY month', ['宿舍报修月度趋势'])
    add('查询获得奖励的学生人数', "SELECT COUNT(DISTINCT student_id) AS rewarded_students FROM awards_penalties WHERE record_type = '奖励'", ['奖励学生数量'])
    add('查询受到惩罚的学生人数', "SELECT COUNT(DISTINCT student_id) AS penalized_students FROM awards_penalties WHERE record_type = '惩罚'", ['惩罚学生数量'])
    add('统计各学院奖励记录数量', "SELECT c.college_name, COUNT(*) AS reward_count FROM awards_penalties ap JOIN students s ON ap.student_id = s.student_id JOIN colleges c ON s.college_id = c.college_id WHERE ap.record_type = '奖励' GROUP BY c.college_name ORDER BY reward_count DESC", ['按学院统计奖励记录'])
    add('统计各学院惩罚记录数量', "SELECT c.college_name, COUNT(*) AS penalty_count FROM awards_penalties ap JOIN students s ON ap.student_id = s.student_id JOIN colleges c ON s.college_id = c.college_id WHERE ap.record_type = '惩罚' GROUP BY c.college_name ORDER BY penalty_count DESC", ['按学院统计惩罚记录'])
    add('查询国家级项目数量', "SELECT COUNT(*) AS national_projects FROM projects WHERE project_level = '国家级'", ['国家级项目个数'])
    add('统计各学院国家级项目数量', "SELECT c.college_name, COUNT(*) AS national_project_count FROM projects p JOIN colleges c ON p.college_id = c.college_id WHERE p.project_level = '国家级' GROUP BY c.college_name ORDER BY national_project_count DESC", ['各学院国家级项目数'])
    add('统计各学院科研经费总额', 'SELECT c.college_name, ROUND(SUM(p.funding), 2) AS total_funding FROM projects p JOIN colleges c ON p.college_id = c.college_id GROUP BY c.college_name ORDER BY total_funding DESC', ['各学院项目经费总额'])
    add('查询经费最高的项目', 'SELECT project_name, funding FROM projects ORDER BY funding DESC LIMIT 1', ['最高经费项目'])
    add('统计近三年项目立项趋势', 'SELECT approved_year, COUNT(*) AS project_count FROM projects WHERE approved_year >= 2022 GROUP BY approved_year ORDER BY approved_year', ['项目年度趋势'])
    add('统计近三年国家级项目趋势', "SELECT approved_year, COUNT(*) AS project_count FROM projects WHERE project_level = '国家级' AND approved_year >= 2022 GROUP BY approved_year ORDER BY approved_year", ['国家级项目年度趋势'])
    add('统计各学院一区论文数量', "SELECT c.college_name, COUNT(*) AS zone1_papers FROM papers p JOIN colleges c ON p.college_id = c.college_id WHERE p.zone = '一区' GROUP BY c.college_name ORDER BY zone1_papers DESC", ['各学院一区论文数'])
    add('统计近三年一区论文趋势', "SELECT publish_year, COUNT(*) AS paper_count FROM papers WHERE zone = '一区' AND publish_year >= 2022 GROUP BY publish_year ORDER BY publish_year", ['一区论文年度趋势'])
    add('查询一区论文数量最多的学院', "SELECT c.college_name, COUNT(*) AS zone1_papers FROM papers p JOIN colleges c ON p.college_id = c.college_id WHERE p.zone = '一区' GROUP BY c.college_name ORDER BY zone1_papers DESC LIMIT 1", ['一区论文最多的学院'])
    add('查询每位教师的项目数量', 'SELECT t.teacher_name, COUNT(p.project_id) AS project_count FROM teachers t LEFT JOIN projects p ON t.teacher_id = p.teacher_id GROUP BY t.teacher_name ORDER BY project_count DESC', ['教师项目数统计'])
    add('查询每位教师的一区论文数量', "SELECT t.teacher_name, COUNT(p.paper_id) AS zone1_paper_count FROM teachers t LEFT JOIN papers p ON t.teacher_id = p.teacher_id AND p.zone = '一区' GROUP BY t.teacher_name ORDER BY zone1_paper_count DESC", ['教师一区论文数'])
    add('查询既有国家级项目又有一区论文的教师', "SELECT DISTINCT t.teacher_name FROM teachers t JOIN projects pr ON t.teacher_id = pr.teacher_id JOIN papers pa ON t.teacher_id = pa.teacher_id WHERE pr.project_level = '国家级' AND pa.zone = '一区' ORDER BY t.teacher_name", ['同时有国家级项目和一区论文的教师'])
    add('查询未发表一区论文的教师', "SELECT t.teacher_name FROM teachers t WHERE t.teacher_id NOT IN (SELECT teacher_id FROM papers WHERE zone = '一区') ORDER BY t.teacher_name", ['没有一区论文的教师'])
    add('查询没有国家级项目的学院', "SELECT college_name FROM colleges WHERE college_id NOT IN (SELECT college_id FROM projects WHERE project_level = '国家级') ORDER BY college_name", ['未获国家级项目的学院'])
    add('查询没有奖励记录的学院', "SELECT c.college_name FROM colleges c WHERE c.college_id NOT IN (SELECT DISTINCT s.college_id FROM awards_penalties ap JOIN students s ON ap.student_id = s.student_id WHERE ap.record_type = '奖励') ORDER BY c.college_name", ['无奖励记录学院'])
    add('查询各学院平均绩点', 'SELECT c.college_name, ROUND(AVG(e.grade_point), 2) AS avg_gpa FROM enrollments e JOIN students s ON e.student_id = s.student_id JOIN colleges c ON s.college_id = c.college_id GROUP BY c.college_name ORDER BY avg_gpa DESC', ['各学院 GPA'])
    add('查询平均绩点最高的学院', 'SELECT c.college_name, ROUND(AVG(e.grade_point), 2) AS avg_gpa FROM enrollments e JOIN students s ON e.student_id = s.student_id JOIN colleges c ON s.college_id = c.college_id GROUP BY c.college_name ORDER BY avg_gpa DESC LIMIT 1', ['GPA最高的学院'])
    add('查询在读学生的平均绩点', "SELECT ROUND(AVG(e.grade_point), 2) AS avg_gpa FROM enrollments e JOIN students s ON e.student_id = s.student_id WHERE s.status = '在读'", ['当前学生平均绩点'])
    add('统计各校区开课数量', 'SELECT campus_name, COUNT(*) AS offering_count FROM course_offerings GROUP BY campus_name ORDER BY offering_count DESC', ['按校区统计课程开设数'])
    add('查询学院路校区开课数量', "SELECT COUNT(*) AS offering_count FROM course_offerings WHERE campus_name = '学院路校区'", ['学院路校区课程数'])
    add('查询沙河校区开课数量', "SELECT COUNT(*) AS offering_count FROM course_offerings WHERE campus_name = '沙河校区'", ['沙河校区课程数'])
    add('查询各课程平均分排名前五', 'SELECT c.course_name, ROUND(AVG(e.score), 2) AS avg_score FROM enrollments e JOIN course_offerings o ON e.offering_id = o.offering_id JOIN courses c ON o.course_id = c.course_id GROUP BY c.course_name ORDER BY avg_score DESC LIMIT 5', ['平均分前五课程'])
    add('查询各课程挂科人数排名前五', 'SELECT c.course_name, SUM(CASE WHEN e.passed = 0 THEN 1 ELSE 0 END) AS fail_count FROM enrollments e JOIN course_offerings o ON e.offering_id = o.offering_id JOIN courses c ON o.course_id = c.course_id GROUP BY c.course_name ORDER BY fail_count DESC LIMIT 5', ['挂科人数前五课程'])
    add('查询每个学院的教师数量', 'SELECT c.college_name, COUNT(*) AS teacher_count FROM teachers t JOIN colleges c ON t.college_id = c.college_id GROUP BY c.college_name ORDER BY teacher_count DESC', ['各学院教师数'])
    add('查询教授数量最多的学院', "SELECT c.college_name, COUNT(*) AS professor_count FROM teachers t JOIN colleges c ON t.college_id = c.college_id WHERE t.title = '教授' GROUP BY c.college_name ORDER BY professor_count DESC LIMIT 1", ['教授最多的学院'])
    add('查询各学院教授数量', "SELECT c.college_name, COUNT(*) AS professor_count FROM teachers t JOIN colleges c ON t.college_id = c.college_id WHERE t.title = '教授' GROUP BY c.college_name ORDER BY professor_count DESC", ['按学院统计教授数'])
    add('查询各学院副教授数量', "SELECT c.college_name, COUNT(*) AS associate_professor_count FROM teachers t JOIN colleges c ON t.college_id = c.college_id WHERE t.title = '副教授' GROUP BY c.college_name ORDER BY associate_professor_count DESC", ['按学院统计副教授数'])
    add('查询经费总额最高的学院', 'SELECT c.college_name, ROUND(SUM(p.funding), 2) AS total_funding FROM projects p JOIN colleges c ON p.college_id = c.college_id GROUP BY c.college_name ORDER BY total_funding DESC LIMIT 1', ['科研经费最高学院'])
    add('查询每年新增一区论文数量', "SELECT publish_year, COUNT(*) AS paper_count FROM papers WHERE zone = '一区' GROUP BY publish_year ORDER BY publish_year", ['年度新增一区论文'])
    add('查询每年新增项目数量', 'SELECT approved_year, COUNT(*) AS project_count FROM projects GROUP BY approved_year ORDER BY approved_year', ['年度新增项目'])
    add('查询在读学生最多的专业', "SELECT m.major_name, COUNT(*) AS student_count FROM students s JOIN majors m ON s.major_id = m.major_id WHERE s.status = '在读' GROUP BY m.major_name ORDER BY student_count DESC LIMIT 1", ['学生最多的专业'])
    add('查询没有挂科记录的学生人数', 'SELECT COUNT(*) AS no_fail_students FROM students s WHERE s.student_id NOT IN (SELECT DISTINCT student_id FROM enrollments WHERE passed = 0)', ['无挂科学生数量'])
    add('查询有奖励且没有惩罚的学生人数', "SELECT COUNT(*) AS clean_reward_students FROM students s WHERE s.student_id IN (SELECT student_id FROM awards_penalties WHERE record_type = '奖励') AND s.student_id NOT IN (SELECT student_id FROM awards_penalties WHERE record_type = '惩罚')", ['只奖励无惩罚学生数'])
    add('查询国家级项目经费总额', "SELECT ROUND(SUM(funding), 2) AS total_funding FROM projects WHERE project_level = '国家级'", ['国家级项目总经费'])
    add('查询在研项目数量', "SELECT COUNT(*) AS active_projects FROM projects WHERE status = '在研'", ['当前在研项目数'])
    add('查询结题项目数量', "SELECT COUNT(*) AS closed_projects FROM projects WHERE status = '结题'", ['已结题项目数'])
    add('查询各学院在研项目数量', "SELECT c.college_name, COUNT(*) AS active_projects FROM projects p JOIN colleges c ON p.college_id = c.college_id WHERE p.status = '在研' GROUP BY c.college_name ORDER BY active_projects DESC", ['各学院在研项目数'])
    add('统计近三年省部级项目趋势', "SELECT approved_year, COUNT(*) AS project_count FROM projects WHERE project_level = '省部级' AND approved_year >= 2022 GROUP BY approved_year ORDER BY approved_year", ['省部级项目年度趋势'])
    add('统计近三年全部论文趋势', 'SELECT publish_year, COUNT(*) AS paper_count FROM papers WHERE publish_year >= 2022 GROUP BY publish_year ORDER BY publish_year', ['全部论文年度趋势'])

    clarifications = [
        {'question': '查看近三年项目趋势', 'aliases': ['近三年项目走势'], 'type': 'clarification', 'clarification_question': '你要看哪一类项目趋势？', 'options': ['全部项目', '国家级项目', '省部级项目'], 'followups': {'全部项目': '统计近三年项目立项趋势', '国家级项目': '统计近三年国家级项目趋势', '省部级项目': '统计近三年省部级项目趋势'}},
        {'question': '查看论文趋势', 'aliases': ['论文年度趋势'], 'type': 'clarification', 'clarification_question': '你要看全部论文还是一区论文趋势？', 'options': ['全部论文', '一区论文'], 'followups': {'全部论文': '统计近三年全部论文趋势', '一区论文': '统计近三年一区论文趋势'}},
        {'question': '查看学生规模', 'aliases': ['学生规模统计'], 'type': 'clarification', 'clarification_question': '你要按学院、专业还是班级查看学生规模？', 'options': ['学院', '专业', '班级'], 'followups': {'学院': '统计各学院当前学生人数', '专业': '统计各专业当前学生人数', '班级': '统计各班级在读学生人数'}},
    ]
    (DATA_DIR / 'campus_qa.json').write_text(json.dumps(queries + clarifications, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    build_db()
    build_metadata_and_qa()
    print('campus data ready')
