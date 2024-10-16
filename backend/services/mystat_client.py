from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum, auto
from typing import Optional, List, Union, Dict, Any, Callable
from pathlib import Path
import requests

class HomeworkType(Enum):
    HOMEWORK = 0
    LAB = 1

class HomeworkStatus(Enum):
    CHECKED = 1
    UPLOADED = 2
    ACTIVE = 3
    DELETED = 5
    OVERDUE = 6

class GamingPointTypes(Enum):
    GEMS = 1
    COINS = 2

class AchievementNames(Enum):
    LESSON_RATE = "EVALUATION_LESSON_MARK"
    PAIR_VISIT = "PAIR_VISIT"
    ASSESSMENT = "ASSESMENT"
    HOMEWORK_COMPLETED = "HOMETASK_INTIME"

class PointTypesNames(Enum):
    DIAMOND = "DIAMOND"
    COIN = "COIN"

@dataclass
class LoginData:
    username: str
    password: str

@dataclass
class AuthResponse:
    access_token: str
    refresh_token: str
    expires_in_access: int
    expires_in_refresh: int
    user_type: int
    city_data: dict

@dataclass
class AuthError:
    field: str
    message: str

@dataclass
class ClientConfig:
    login_data: LoginData
    language: str = "en"
    cache: Optional[str] = None
    access_token: Optional[str] = None
    token_expires_at: Optional[int] = None
    group_id: Optional[int] = None
    on_unauthorized: Optional[Callable[[str], None]] = None

@dataclass
class ClientData:
    login_data: LoginData
    language: str
    cache: Optional[str]
    access_token: str
    token_expires_at: int
    group_id: Optional[int] = None

@dataclass
class ScheduleEntry:
    date: str
    started_at: str
    finished_at: str
    room_name: str
    subject_name: str
    teacher_name: str
    lesson: int

@dataclass
class Review:
    date: str
    full_spec: str
    message: str
    spec: str
    teacher: str

@dataclass
class LessonVisit:
    spec_id: int
    lesson_number: int
    status_was: int
    class_work_mark: Optional[int]
    control_work_mark: Optional[int]
    home_work_mark: Optional[int]
    lab_work_mark: Optional[int]
    date_visit: str
    spec_name: str
    lesson_theme: str
    teacher_name: str

@dataclass
class AttendanceEntry:
    date: str
    has_rasp: bool
    points: Optional[int]
    previous_points: Optional[int]

@dataclass
class NewsEntry:
    id_bbs: int
    theme: str
    time: str

@dataclass
class NewsDetails:
    id_bbs: int
    is_viewed: bool
    text_bbs: str
    theme: str
    time: str

@dataclass
class Exam:
    exam_id: int
    id_file: int
    mark: int
    mark_type: int
    need_access: int
    date: str
    spec: str
    teacher: str
    comment_delete_file: Optional[str]
    comment_teach: Optional[str]
    ex_file_name: Optional[str]
    file_path: Optional[str]
    need_access_stud: Optional[bool]

@dataclass
class StudentInfo:
    id: int
    position: int
    amount: int
    full_name: str
    photo_path: str

@dataclass
class ActivityEntry:
    achievements_id: int
    achievements_type: int
    action: int
    badge: int
    current_point: int
    point_types_id: int
    subject_mark: Optional[int]
    date: str
    achievements_name: str
    point_types_name: str
    subject_name: Optional[str]
    old_competition: bool

class APIClient:
    BASE_URL = "https://msapi.itstep.org/api/v2"
    APP_KEY = "6a56a5df2667e65aab73ce76d1dd737f7d1faef9c52e8b8c55ac75f565d8e8a6"

    def __init__(self, config: ClientConfig):
        self.config = config
        self.client_data: Optional[ClientData] = None

    async def initialize(self):
        if self.config.access_token and self.config.token_expires_at:
            self.client_data = ClientData(
                login_data=self.config.login_data,
                language=self.config.language,
                cache=self.config.cache,
                access_token=self.config.access_token,
                token_expires_at=self.config.token_expires_at,
                group_id=self.config.group_id
            )
        else:
            user = await self.auth_user(self.config.login_data)
            if isinstance(user, list):
                raise Exception(user)
            
            self.client_data = ClientData(
                login_data=self.config.login_data,
                language=self.config.language or "en",
                cache=self.config.cache,
                access_token=user.access_token,
                token_expires_at=user.expires_in_access * 1000,
                group_id=self.config.group_id
            )

    @staticmethod
    def format_date(date_obj: date) -> str:
        return date_obj.strftime("%Y-%m-%d")

    def is_token_expired(self) -> bool:
        if not self.client_data:
            return True
        return datetime.now().timestamp() * 1000 >= self.client_data.token_expires_at

    async def auth_user(self, login_data: LoginData) -> Union[AuthResponse, List[AuthError]]:
        body = {
            "application_key": self.APP_KEY,
            "id_city": None,
            "username": login_data.username,
            "password": login_data.password
        }

        response = requests.post(
            f"{self.BASE_URL}/auth/login",
            json=body,
            headers={
                "accept": "application/json",
                "Content-Type": "application/json"
            }
        )
        
        data = response.json()
        if isinstance(data, list):
            return [AuthError(**error) for error in data]
        return AuthResponse(**data)

    async def update_token(self):
        user = await self.auth_user(self.config.login_data)
        if isinstance(user, list):
            raise Exception(user)
        
        if self.client_data:
            self.client_data.access_token = user.access_token
            self.client_data.token_expires_at = user.expires_in_access * 1000

    async def get(self, path: str, retry: bool = True) -> Optional[Dict[str, Any]]:
        if not self.client_data:
            raise Exception("Client not initialized")

        if self.is_token_expired():
            await self.update_token()

        response = requests.get(
            f"{self.BASE_URL}/{path}",
            headers={
                "x-language": self.client_data.language,
                "authorization": f"Bearer {self.client_data.access_token}",
                "accept": "application/json"
            }
        )

        if response.status_code == 401:
            if self.config.on_unauthorized:
                self.config.on_unauthorized(path)
                return None

            if retry:
                await self.update_token()
                return await self.get(path, False)

            raise Exception("Access token is expired or invalid")

        return response.json()

    # User Information Methods
    async def get_user_info(self) -> Dict[str, Any]:
        return await self.get("settings/user-info")

    async def get_user_settings(self) -> Dict[str, Any]:
        return await self.get("profile/operations/settings")

    # Schedule Methods
    async def get_month_schedule(self, date_obj: Optional[date] = None) -> List[ScheduleEntry]:
        if not date_obj:
            date_obj = date.today()
        response = await self.get(f"schedule/operations/get-month?date_filter={self.format_date(date_obj)}")
        return [ScheduleEntry(**entry) for entry in response]

    async def get_schedule_by_date(self, date_obj: Optional[date] = None) -> List[ScheduleEntry]:
        if not date_obj:
            date_obj = date.today()
        response = await self.get(f"schedule/operations/get-by-date?date_filter={self.format_date(date_obj)}")
        return [ScheduleEntry(**entry) for entry in response]

    # Review and Progress Methods
    async def get_reviews(self) -> List[Review]:
        response = await self.get("reviews/index/list")
        return [Review(**review) for review in response]

    async def get_visits(self) -> List[LessonVisit]:
        response = await self.get("progress/operations/student-visits")
        return [LessonVisit(**visit) for visit in response]

    async def get_attendance(self) -> List[AttendanceEntry]:
        response = await self.get("dashboard/chart/attendance")
        return [AttendanceEntry(**entry) for entry in response]

    # Homework Methods
    async def get_homework_by_type(self, page: int = 1, 
                                 homework_type: HomeworkType = HomeworkType.HOMEWORK) -> Dict[str, Any]:
        if not self.client_data or not self.client_data.group_id:
            user_info = await self.get_user_info()
            if not user_info:
                raise Exception("Unable to get user group id")
            self.client_data.group_id = user_info["current_group_id"]

        return await self.get(
            f"homework/operations/list?page={page}&type={homework_type.value}"
            f"&group_id={self.client_data.group_id}"
        )

    async def get_homework_list(self, page: int = 1,
                              status: HomeworkStatus = HomeworkStatus.ACTIVE,
                              homework_type: HomeworkType = HomeworkType.HOMEWORK) -> Dict[str, Any]:
        if not self.client_data or not self.client_data.group_id:
            user_info = await self.get_user_info()
            if not user_info:
                raise Exception("Unable to get user group id")
            self.client_data.group_id = user_info["current_group_id"]

        return await self.get(
            f"homework/operations/list?page={page}&status={status.value}"
            f"&type={homework_type.value}&group_id={self.client_data.group_id}"
        )

    # News Methods
    async def get_latest_news(self) -> List[NewsEntry]:
        response = await self.get("news/operations/latest-news")
        return [NewsEntry(**entry) for entry in response]

    async def get_news_details(self, news_id: int) -> NewsDetails:
        response = await self.get(f"news/operations/detail-news?news_id={news_id}")
        return NewsDetails(**response)

    # Exam Methods
    async def get_all_exams(self) -> List[Exam]:
        response = await self.get("progress/operations/student-exams")
        return [Exam(**exam) for exam in response]

    async def get_future_exams(self) -> List[Exam]:
        response = await self.get("dashboard/info/future-exams")
        return [Exam(**exam) for exam in response]

    # Student and Group Methods
    async def get_stream_leaders(self) -> List[StudentInfo]:
        response = await self.get("dashboard/progress/leader-stream")
        return [StudentInfo(**student) for student in response]

    async def get_group_leaders(self) -> List[StudentInfo]:
        response = await self.get("dashboard/progress/leader-group")
        return [StudentInfo(**student) for student in response]

    async def get_activity(self) -> List[ActivityEntry]:
        response = await self.get("dashboard/progress/activity")
        return [ActivityEntry(**entry) for entry in response]

    async def get_activity_log(self) -> List[Dict[str, Any]]:
        return await self.get("dashboard/progress/activity-web")

    async def get_group_info(self) -> List[Dict[str, Any]]:
        return await self.get("homework/settings/group-history")

    async def get_homework_count(self) -> List[Dict[str, Any]]:
        return await self.get("count/homework")

    # Homework Upload and Delete Methods
    async def upload_homework(self, homework_id: int, answer_text: Optional[str] = None,
                            file: Optional[Path] = None, spent_time_hour: int = 99,
                            spent_time_min: int = 99) -> Dict[str, Any]:
        if not self.client_data:
            raise Exception("Client not initialized")

        if self.is_token_expired():
            await self.update_token()

        form_data = {
            "id": str(homework_id),
            "spentTimeHour": str(spent_time_hour),
            "spentTimeMin": str(spent_time_min)
        }

        if answer_text:
            form_data["answerText"] = answer_text

        files = {}
        if file:
            files["file"] = (file.name, file.open("rb"))

        response = requests.post(
            f"{self.BASE_URL}/homework/operations/create",
            data=form_data,
            files=files,
            headers={
                "x-language": self.client_data.language,
                "authorization": f"Bearer {self.client_data.access_token}",
                "accept": "application/json"
            }
        )

        if not response.ok:
            raise Exception(response.json())

        return response.json()

    async def delete_homework(self, homework_id: Union[int, str]) -> bool:
        if not self.client_data:
            raise Exception("Client not initialized")

        if self.is_token_expired():
            await self.update_token()

        response = requests.post(
            f"{self.BASE_URL}/homework/operations/delete",
            json={"id": homework_id},
            headers={
                "Content-Type": "application/json",
                "x-language": self.client_data.language,
                "authorization": f"Bearer {self.client_data.access_token}",
                "accept": "application/json"
            }
        )

        if not response.ok:
            raise Exception(response.text)

        return response.text != "null"

async def create_client(config: ClientConfig) -> APIClient:
    client = APIClient(config)
    await client.initialize()
    return client