from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from pyluach import dates
from astral import LocationInfo, Observer  # הוספנו את Observer
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

# מאגר הערים המורחב כולל גובה טופוגרפי (במטרים) וקואורדינטות מדויקות
CITIES = {
	# ======= ישראל =======
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
	# מתחת לפני הים
	"Safed": {"info": LocationInfo("Safed", "Israel", "Asia/Jerusalem", 32.9646, 35.4960), "elevation": 900},
	"Eilat": {"info": LocationInfo("Eilat", "Israel", "Asia/Jerusalem", 29.5577, 34.9519), "elevation": 10},
	"Kfar Saba": {"info": LocationInfo("Kfar Saba", "Israel", "Asia/Jerusalem", 32.1714, 34.9069), "elevation": 30},
	"Ra'anana": {"info": LocationInfo("Ra'anana", "Israel", "Asia/Jerusalem", 32.1836, 34.8739), "elevation": 40},

	# ======= עולם (קהילות יהודיות בולטות) =======
	"New York": {"info": LocationInfo("New York", "USA", "America/New_York", 40.7128, -74.0060), "elevation": 10},
	"Los Angeles": {"info": LocationInfo("Los Angeles", "USA", "America/Los_Angeles", 34.0522, -118.2437),
	                "elevation": 90},
	"Miami": {"info": LocationInfo("Miami", "USA", "America/New_York", 25.7617, -80.1918), "elevation": 2},
	"Chicago": {"info": LocationInfo("Chicago", "USA", "America/Chicago", 41.8781, -87.6298), "elevation": 180},
	"London": {"info": LocationInfo("London", "UK", "Europe/London", 51.5074, -0.1278), "elevation": 15},
	"Paris": {"info": LocationInfo("Paris", "France", "Europe/Paris", 48.8566, 2.3522), "elevation": 35},
	"Antwerp": {"info": LocationInfo("Antwerp", "Belgium", "Europe/Brussels", 51.2194, 4.4025), "elevation": 10},
	"Buenos Aires": {
		"info": LocationInfo("Buenos Aires", "Argentina", "America/Argentina/Buenos_Aires", -34.6037, -58.3816),
		"elevation": 25},
	"Toronto": {"info": LocationInfo("Toronto", "Canada", "America/Toronto", 43.6510, -79.3470), "elevation": 76},
	"Montreal": {"info": LocationInfo("Montreal", "Canada", "America/Montreal", 45.5017, -73.5673), "elevation": 30},
	"Moscow": {"info": LocationInfo("Moscow", "Russia", "Europe/Moscow", 55.7558, 37.6173), "elevation": 150},
	"Melbourne": {"info": LocationInfo("Melbourne", "Australia", "Australia/Melbourne", -37.8136, 144.9631),
	              "elevation": 31},
	"Sydney": {"info": LocationInfo("Sydney", "Australia", "Australia/Sydney", -33.8688, 151.2093), "elevation": 30},
	"Johannesburg": {"info": LocationInfo("Johannesburg", "South Africa", "Africa/Johannesburg", -26.2041, 28.0473),
	                 "elevation": 1750},
	"Sao Paulo": {"info": LocationInfo("Sao Paulo", "Brazil", "America/Sao_Paulo", -23.5505, -46.6333),
	              "elevation": 760},
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
	create_sunset_event: bool = True


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

	# שליפת המידע על העיר + יצירת Observer שכולל את הגובה
	city_data = CITIES.get(req.location, CITIES["Jerusalem"])
	city_info = city_data["info"]
	city_elevation = city_data["elevation"]
	custom_observer = Observer(latitude=city_info.latitude, longitude=city_info.longitude, elevation=city_elevation)

	start_heb_year = dates.GregorianDate(start_greg_year, 1, 1).to_heb().year

	for i in range(100):
		current_heb_year = start_heb_year + i

		try:
			heb_event_date = dates.HebrewDate(current_heb_year, target_heb_month, target_heb_day)
		except ValueError:
			continue

		greg_end = heb_event_date.to_greg()
		end_date_py = datetime.date(greg_end.year, greg_end.month, greg_end.day)
		start_date_py = end_date_py - datetime.timedelta(days=1)

		try:
			e_allday = Event()
			e_allday.name = req.title
			e_allday.begin = end_date_py
			e_allday.make_all_day()
			cal.events.add(e_allday)

			if req.create_sunset_event:
				# עכשיו אנחנו שולחים את ה-custom_observer שכולל את הגובה!
				start_sunset = sun(custom_observer, date=start_date_py, tzinfo=city_info.timezone)['sunset']

				e_sunset = Event()
				e_sunset.name = f"תחילת {req.title}"
				e_sunset.begin = start_sunset
				e_sunset.end = start_sunset + datetime.timedelta(minutes=15)
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

# הגדרת הנתיב לתיקיית הריאקט המוכנה (שתיווצר על ידי דוקר)
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))

# בדיקה אם התיקייה קיימת כדי לא לקרוס בפיתוח מקומי
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")