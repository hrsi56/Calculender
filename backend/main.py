from fastapi import FastAPI, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from pyluach import dates
from astral import LocationInfo, Observer
from astral.sun import sun
import datetime
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

CITIES = {
	"Jerusalem": {"info": LocationInfo("Jerusalem", "Israel", "Asia/Jerusalem", 31.7683, 35.2137), "elevation": 800},
	"Tel Aviv": {"info": LocationInfo("Tel Aviv", "Israel", "Asia/Jerusalem", 32.0853, 34.7818), "elevation": 5},
	"Haifa": {"info": LocationInfo("Haifa", "Israel", "Asia/Jerusalem", 32.7940, 34.9896), "elevation": 290},
	"New York": {"info": LocationInfo("New York", "USA", "America/New_York", 40.7128, -74.0060), "elevation": 10},
	"London": {"info": LocationInfo("London", "UK", "Europe/London", 51.5074, -0.1278), "elevation": 15},
	# השאר את שאר הערים שלך כאן...
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


# לוגיקת הליבה - מופרדת כדי שתשמש גם את ה-POST וגם את ה-GET
def create_calendar_internal(req: EventRequest):
	if not req.is_hebrew:
		g_date = dates.GregorianDate(req.greg_year, req.greg_month, req.greg_day)
		h_date = g_date.to_heb()
		if req.after_sunset:
			h_date = h_date + 1
		start_greg_year = req.greg_year
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
		start_greg_year = datetime.datetime.now().year
		start_heb_year = dates.GregorianDate(start_greg_year, 1, 1).to_heb().year
		target_heb_day = req.heb_day
		if req.heb_month == 12:
			adar_type = "ADAR_I"
		elif req.heb_month == 13:
			adar_type = "ADAR_MAIN"
		else:
			adar_type = "OTHER"
			target_heb_month = req.heb_month

	cal = Calendar()
	city_data = CITIES.get(req.location, CITIES["Jerusalem"])
	city_info = city_data["info"]
	custom_observer = Observer(latitude=city_info.latitude, longitude=city_info.longitude,
	                           elevation=city_data["elevation"])

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

		e_allday = Event()
		e_allday.name = req.title
		e_allday.begin = end_date_py
		e_allday.make_all_day()
		cal.events.add(e_allday)

		if req.create_sunset_event:
			try:
				start_sunset = \
				sun(custom_observer, date=end_date_py - datetime.timedelta(days=1), tzinfo=city_info.timezone)['sunset']
				e_sunset = Event()
				e_sunset.name = f"תחילת {req.title}"
				e_sunset.begin = start_sunset
				e_sunset.end = start_sunset + datetime.timedelta(minutes=15)
				cal.events.add(e_sunset)
			except:
				pass

	return cal.serialize()


@app.post("/api/generate-ics")
def generate_ics_post(req: EventRequest):
	content = create_calendar_internal(req)
	return Response(content=content, media_type="text/calendar",
	                headers={"Content-Disposition": "attachment; filename=events.ics"})


# ה-Endpoint החדש עבור סנכרון (Subscription)
@app.get("/api/subscribe.ics")
def subscribe_ics_get(
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
	content = create_calendar_internal(req)
	# כאן לא מחזירים Attachment, כדי שהדפדפן/אפליקציה יקראו את זה כזרם נתונים (Stream)
	return Response(content=content, media_type="text/calendar")


static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
if os.path.isdir(static_dir):
	app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")