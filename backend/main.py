from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from pyluach import dates
from astral import LocationInfo
from astral.sun import sun
import datetime
from ics import Calendar, Event

app = FastAPI()

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_methods=["*"],
	allow_headers=["*"],
)

CITIES = {
	"Israel": LocationInfo("Jerusalem", "Israel", "Asia/Jerusalem", 31.7683, 35.2137),
	"New York": LocationInfo("New York", "USA", "America/New_York", 40.7128, -74.0060),
	"London": LocationInfo("London", "UK", "Europe/London", 51.5074, -0.1278)
}


class EventRequest(BaseModel):
	is_hebrew: bool
	greg_year: Optional[int] = None
	greg_month: Optional[int] = None
	greg_day: Optional[int] = None
	after_sunset: bool
	heb_month: Optional[int] = None
	heb_day: Optional[int] = None
	location: str
	title: str
	create_sunset_event: bool = True  # <--- הוספנו את השדה החדש


@app.post("/api/generate-ics")
def generate_ics(req: EventRequest):
	if not req.is_hebrew:
		g_date = dates.GregorianDate(req.greg_year, req.greg_month, req.greg_day)
		h_date = g_date.to_heb()
		if req.after_sunset:
			h_date = h_date + 1
		target_heb_month = h_date.month
		target_heb_day = h_date.day
		start_greg_year = req.greg_year
	else:
		target_heb_month = req.heb_month
		target_heb_day = req.heb_day
		start_greg_year = datetime.datetime.now().year

	cal = Calendar()
	city = CITIES.get(req.location, CITIES["Israel"])
	start_heb_year = dates.GregorianDate(start_greg_year, 1, 1).to_heb().year

	for i in range(100):
		current_heb_year = start_heb_year + i

		try:
			heb_event_date = dates.HebrewDate(current_heb_year, target_heb_month, target_heb_day)
		except ValueError:
			continue

		greg_end = heb_event_date.to_greg()
		end_date_py = datetime.date(greg_end.year, greg_end.month, greg_end.day)  # היום הלועזי העיקרי
		start_date_py = end_date_py - datetime.timedelta(days=1)  # אתמול (לחישוב השקיעה)

		try:
			# --- 1. יצירת האירוע היומי (All-Day Event) ---
			# העברת אובייקט מסוג date (ללא שעה) תגרום ליומן להתייחס לזה כאירוע של יום שלם שמופיע למעלה
			e_allday = Event()
			e_allday.name = req.title
			e_allday.begin = end_date_py
			e_allday.make_all_day()  # פונקציה מובנית בספרייה לאירוע יומי
			cal.events.add(e_allday)

			# --- 2. יצירת אירוע השקיעה (אם המשתמש אישר) ---
			if req.create_sunset_event:
				start_sunset = sun(city.observer, date=start_date_py, tzinfo=city.timezone)['sunset']

				e_sunset = Event()
				e_sunset.name = f"תחילת {req.title}"
				e_sunset.begin = start_sunset
				e_sunset.end = start_sunset + datetime.timedelta(minutes=15)  # אירוע של רבע שעה
				cal.events.add(e_sunset)

		except Exception as e:
			print(f"Error processing {end_date_py}: {e}")
			continue

	ics_content = cal.serialize()
	return Response(
		content=ics_content,
		media_type="text/calendar",
		headers={"Content-Disposition": "attachment; filename=events.ics"}
	)