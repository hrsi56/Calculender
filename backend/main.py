from fastapi import FastAPI, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from pyluach import dates
from astral import LocationInfo, Observer
from astral.sun import sun
import datetime
import hashlib  # <--- הוספנו עבור המזהה הייחודי
from ics import Calendar, Event
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_methods=["*"],
	allow_headers=["*"],
)

# מאגר ערים מורחב עם גובה טופוגרפי
CITIES = {
	"Jerusalem": {"info": LocationInfo("Jerusalem", "Israel", "Asia/Jerusalem", 31.7683, 35.2137), "elevation": 800},
	"Tel Aviv": {"info": LocationInfo("Tel Aviv", "Israel", "Asia/Jerusalem", 32.0853, 34.7818), "elevation": 5},
	"Haifa": {"info": LocationInfo("Haifa", "Israel", "Asia/Jerusalem", 32.7940, 34.9896), "elevation": 290},
	"Rishon LeZion": {"info": LocationInfo("Rishon LeZion", "Israel", "Asia/Jerusalem", 31.9730, 34.7925),
	                  "elevation": 40},
	"Petah Tikva": {"info": LocationInfo("Petah Tikva", "Israel", "Asia/Jerusalem", 32.0836, 34.8797), "elevation": 15},
	"Ashdod": {"info": LocationInfo("Ashdod", "Israel", "Asia/Jerusalem", 31.8014, 34.6435), "elevation": 15},
	"Netanya": {"info": LocationInfo("Netanya", "Israel", "Asia/Jerusalem", 32.3215, 34.8532), "elevation": 30},
	"Beersheba": {"info": LocationInfo("Beersheba", "Israel", "Asia/Jerusalem", 31.2518, 34.7913), "elevation": 260},
	"Bnei Brak": {"info": LocationInfo("Bnei Brak", "Israel", "Asia/Jerusalem", 32.0809, 34.8315), "elevation": 20},
	"Holon": {"info": LocationInfo("Holon", "Israel", "Asia/Jerusalem", 32.0163, 34.7742), "elevation": 20},
	"Ramat Gan": {"info": LocationInfo("Ramat Gan", "Israel", "Asia/Jerusalem", 32.0684, 34.8248), "elevation": 80},
	"Rehovot": {"info": LocationInfo("Rehovot", "Israel", "Asia/Jerusalem", 31.8945, 34.8089), "elevation": 25},
	"Ashkelon": {"info": LocationInfo("Ashkelon", "Israel", "Asia/Jerusalem", 31.6668, 34.5743), "elevation": 10},
	"Modiin": {"info": LocationInfo("Modiin", "Israel", "Asia/Jerusalem", 31.8903, 35.0104), "elevation": 250},
	"Beit Shemesh": {"info": LocationInfo("Beit Shemesh", "Israel", "Asia/Jerusalem", 31.7455, 34.9867),
	                 "elevation": 220},
	"Tiberias": {"info": LocationInfo("Tiberias", "Israel", "Asia/Jerusalem", 32.7945, 35.5310), "elevation": -200},
	"Safed": {"info": LocationInfo("Safed", "Israel", "Asia/Jerusalem", 32.9646, 35.4960), "elevation": 900},
	"Eilat": {"info": LocationInfo("Eilat", "Israel", "Asia/Jerusalem", 29.5577, 34.9519), "elevation": 10},
	"New York": {"info": LocationInfo("New York", "USA", "America/New_York", 40.7128, -74.0060), "elevation": 10},
	"London": {"info": LocationInfo("London", "UK", "Europe/London", 51.5074, -0.1278), "elevation": 15},
	"Johannesburg": {"info": LocationInfo("Johannesburg", "South Africa", "Africa/Johannesburg", -26.2041, 28.0473),
	                 "elevation": 1750},
}


class EventRequest(BaseModel):
	is_hebrew: bool
	greg_year: Optional[int] = None
	greg_month: Optional[int] = None
	greg_day: Optional[int] = None
	after_sunset: bool = False
	heb_month: Optional[int] = None
	heb_day: Optional[int] = None
	location: str
	title: str
	create_sunset_event: bool = True


def is_leap_year(year: int) -> bool:
	try:
		dates.HebrewDate(year, 13, 1)
		return True
	except ValueError:
		return False


# --- לוגיקת הליבה: יצירת הלוח ל-100 שנה ---
def _create_calendar_internal(req: EventRequest) -> str:
	if not req.is_hebrew:
		g_date = dates.GregorianDate(req.greg_year, req.greg_month, req.greg_day)
		h_date = g_date.to_heb()
		if req.after_sunset:
			h_date = h_date + 1

		start_heb_year = h_date.year
		target_heb_day = h_date.day

		if h_date.month == 12:
			adar_type = "ADAR_I" if is_leap_year(h_date.year) else "ADAR_MAIN"
		elif h_date.month == 13:
			adar_type = "ADAR_MAIN"
		else:
			adar_type = "OTHER"
			target_heb_month = h_date.month
	else:
		now = datetime.datetime.now()
		start_heb_year = dates.GregorianDate(now.year, now.month, now.day).to_heb().year
		target_heb_day = req.heb_day
		if req.heb_month == 12:
			adar_type = "ADAR_I"
		elif req.heb_month == 13:
			adar_type = "ADAR_MAIN"
		else:
			adar_type = "OTHER"
			target_heb_month = req.heb_month

	cal = Calendar()
	cal.creator = "Calculender App"  # עוזר לגוגל לזהות את המקור

	city_data = CITIES.get(req.location, CITIES["Jerusalem"])
	city_info = city_data["info"]
	obs = Observer(latitude=city_info.latitude, longitude=city_info.longitude, elevation=city_data["elevation"])

	# יצירת מזהה קבוע לשם האירוע כדי שיישאר זהה גם ברענונים עתידיים
	title_hash = hashlib.md5(req.title.encode('utf-8')).hexdigest()[:8]

	for i in range(100):
		current_heb_year = start_heb_year + i
		current_is_leap = is_leap_year(current_heb_year)

		if adar_type == "ADAR_I":
			calc_month = 12
		elif adar_type == "ADAR_MAIN":
			calc_month = 13 if current_is_leap else 12
		else:
			calc_month = target_heb_month

		try:
			heb_event_date = dates.HebrewDate(current_heb_year, calc_month, target_heb_day)
		except ValueError:
			if target_heb_day == 30:
				next_month = calc_month + 1
				if (next_month == 13 and not current_is_leap) or next_month == 14:
					next_month = 1
				try:
					heb_event_date = dates.HebrewDate(current_heb_year, next_month, 1)
				except:
					continue
			else:
				continue

		greg_end = heb_event_date.to_greg()
		end_date_py = datetime.date(greg_end.year, greg_end.month, greg_end.day)

		e_all = Event()
		e_all.name = req.title
		e_all.begin = end_date_py
		e_all.make_all_day()
		# הגדרת UID קבוע (חובה כדי שגוגל לא ישכפל אירועים!)
		e_all.uid = f"allday-{current_heb_year}-{calc_month}-{target_heb_day}-{title_hash}@calculender.app"
		cal.events.add(e_all)

		if req.create_sunset_event:
			try:
				start_sunset = sun(obs, date=end_date_py - datetime.timedelta(days=1), tzinfo=city_info.timezone)[
					'sunset']
				e_sun = Event()
				e_sun.name = f"תחילת {req.title}"
				e_sun.begin = start_sunset
				e_sun.end = start_sunset + datetime.timedelta(minutes=15)
				# הגדרת UID קבוע גם לאירוע השקיעה
				e_sun.uid = f"sunset-{current_heb_year}-{calc_month}-{target_heb_day}-{title_hash}@calculender.app"
				cal.events.add(e_sun)
			except:
				pass

	return cal.serialize()


# --- Endpoints ---

@app.post("/api/generate-ics")
def generate_ics_download(req: EventRequest):
	ics_content = _create_calendar_internal(req)
	return Response(
		content=ics_content,
		media_type="text/calendar",
		headers={"Content-Disposition": "attachment; filename=events.ics"}
	)


@app.get("/api/subscribe.ics")
def generate_ics_subscribe(
		is_hebrew: bool,
		title: str,
		location: str,
		heb_month: Optional[int] = None,
		heb_day: Optional[int] = None,
		greg_year: Optional[int] = None,
		greg_month: Optional[int] = None,
		greg_day: Optional[int] = None,
		after_sunset: bool = False,
		create_sunset_event: bool = True
):
	req = EventRequest(
		is_hebrew=is_hebrew, title=title, location=location,
		heb_month=heb_month, heb_day=heb_day,
		greg_year=greg_year, greg_month=greg_month, greg_day=greg_day,
		after_sunset=after_sunset, create_sunset_event=create_sunset_event
	)
	ics_content = _create_calendar_internal(req)

	# הוספת כותרות שמונעות מהדפדפן לשמור עותק ישן (Caching)
	headers = {
		"Cache-Control": "no-cache, no-store, must-revalidate",
		"Pragma": "no-cache",
		"Expires": "0"
	}
	return Response(content=ics_content, media_type="text/calendar", headers=headers)


# --- Endpoint חדש למניעת הירדמות של השרת ---
@app.get("/api/ping")
def ping_server():
	return {"status": "alive", "message": "Calculender server is awake!"}


# הגשת React
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
if os.path.isdir(static_dir):
	app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")