import React, { useState } from 'react';
import './App.css';

interface EventPayload {
  is_hebrew: boolean;
  greg_year: number | null;
  greg_month: number | null;
  greg_day: number | null;
  after_sunset: boolean;
  heb_month: number | null;
  heb_day: number | null;
  location: string;
  title: string;
  create_sunset_event: boolean;
}

const HEBREW_MONTHS = [
  { value: 7, name: 'תשרי' },
  { value: 8, name: 'חשוון' },
  { value: 9, name: 'כסלו' },
  { value: 10, name: 'טבת' },
  { value: 11, name: 'שבט' },
  { value: 12, name: "אדר א' בשנה מעוברת" },
  { value: 13, name: "אדר (שנה רגילה) / אדר ב'" }, // <-- אדר העיקרי
  { value: 1, name: 'ניסן' },
  { value: 2, name: 'אייר' },
  { value: 3, name: 'סיוון' },
  { value: 4, name: 'תמוז' },
  { value: 5, name: 'אב' },
  { value: 6, name: 'אלול' },
];

const App: React.FC = () => {
  const [isHebrew, setIsHebrew] = useState<boolean>(false);
  const [gregDate, setGregDate] = useState<string>('');
  const [afterSunset, setAfterSunset] = useState<boolean>(false);

  const [hebDay, setHebDay] = useState<string>('');

  // הגדרנו את חודש 13 (אדר העיקרי) כברירת המחדל
  const [hebMonth, setHebMonth] = useState<string>('13');

  // הגדרנו את ירושלים כברירת המחדל למיקום
  const [location, setLocation] = useState<string>('Jerusalem');

  const [title, setTitle] = useState<string>('');
  const [createSunsetEvent, setCreateSunsetEvent] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);

  const handleDownload = async () => {
    setLoading(true);
    const API_URL = "/api/generate-ics";

    const payload: EventPayload = {
      is_hebrew: isHebrew,
      greg_year: null, greg_month: null, greg_day: null,
      heb_month: null, heb_day: null,
      after_sunset: afterSunset,
      location, title,
      create_sunset_event: createSunsetEvent
    };

    if (!isHebrew) {
      if (!gregDate) {
        alert('אנא בחר תאריך לועזי');
        setLoading(false);
        return;
      }
      const [year, month, day] = gregDate.split('-');
      payload.greg_year = parseInt(year);
      payload.greg_month = parseInt(month);
      payload.greg_day = parseInt(day);
    } else {
      if (!hebDay) {
        alert('אנא הזן יום עברי');
        setLoading(false);
        return;
      }
      payload.heb_month = parseInt(hebMonth);
      payload.heb_day = parseInt(hebDay);
    }

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error("שגיאה בתקשורת עם השרת");

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `${title || 'calendar-events'}.ics`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (error) {
      alert("הייתה בעיה ביצירת הקובץ. ודא ששרת הפייתון פועל.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <h1>מחולל אירועים ליומן 📅</h1>

      <div className="form-group">
        <h3>1. בחר תאריך מקור</h3>
        <select value={String(isHebrew)} onChange={(e) => setIsHebrew(e.target.value === 'true')}>
          <option value={'false'}>לפי תאריך לועזי</option>
          <option value={'true'}>לפי תאריך עברי</option>
        </select>

        {!isHebrew ? (
          <div>
            <input
              type="date"
              value={gregDate}
              onChange={e => setGregDate(e.target.value)}
            />
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={afterSunset}
                onChange={e => setAfterSunset(e.target.checked)}
              />
              האירוע התרחש לאחר השקיעה
            </label>
          </div>
        ) : (
          <div className="flex-row">
            <input
              type="number"
              min="1"
              max="30"
              value={hebDay}
              onChange={e => setHebDay(e.target.value)}
              placeholder="יום (1-30)"
            />
            <select value={hebMonth} onChange={e => setHebMonth(e.target.value)}>
              {HEBREW_MONTHS.map(m => (
                <option key={m.value} value={m.value}>{m.name}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className="form-group">
        <h3>2. מיקום לחישוב זמני שקיעה</h3>
        <select value={location} onChange={(e) => setLocation(e.target.value)}>
          <optgroup label="ישראל">
            <option value="Jerusalem">ירושלים</option>
            <option value="Tel Aviv">תל אביב - יפו</option>
            <option value="Haifa">חיפה</option>
            <option value="Rishon LeZion">ראשון לציון</option>
            <option value="Petah Tikva">פתח תקווה</option>
            <option value="Ashdod">אשדוד</option>
            <option value="Netanya">נתניה</option>
            <option value="Beersheba">באר שבע</option>
            <option value="Bnei Brak">בני ברק</option>
            <option value="Holon">חולון</option>
            <option value="Ramat Gan">רמת גן</option>
            <option value="Rehovot">רחובות</option>
            <option value="Ashkelon">אשקלון</option>
            <option value="Modiin">מודיעין</option>
            <option value="Beit Shemesh">בית שמש</option>
            <option value="Tiberias">טבריה</option>
            <option value="Safed">צפת</option>
            <option value="Eilat">אילת</option>
            <option value="Kfar Saba">כפר סבא</option>
            <option value="Ra'anana">רעננה</option>
          </optgroup>
          <optgroup label="מסביב לעולם">
            <option value="New York">ניו יורק (USA)</option>
            <option value="Los Angeles">לוס אנג'לס (USA)</option>
            <option value="Miami">מיאמי (USA)</option>
            <option value="Chicago">שיקגו (USA)</option>
            <option value="London">לונדון (UK)</option>
            <option value="Paris">פריז (France)</option>
            <option value="Antwerp">אנטוורפן (Belgium)</option>
            <option value="Buenos Aires">בואנוס איירס (Argentina)</option>
            <option value="Toronto">טורונטו (Canada)</option>
            <option value="Montreal">מונטריאול (Canada)</option>
            <option value="Moscow">מוסקבה (Russia)</option>
            <option value="Melbourne">מלבורן (Australia)</option>
            <option value="Sydney">סידני (Australia)</option>
            <option value="Johannesburg">יוהנסבורג (South Africa)</option>
            <option value="Sao Paulo">סאו פאולו (Brazil)</option>
          </optgroup>
        </select>
      </div>

      <div className="form-group">
        <h3>3. כותרת האירוע ביומן</h3>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="לדוגמה: יום הולדת עברי לירדן"
        />
      </div>

      <div className="form-group">
        <h3>4. אפשרויות תצוגה</h3>
        <label className="checkbox-label" style={{ fontWeight: 'bold' }}>
          <input
            type="checkbox"
            checked={createSunsetEvent}
            onChange={e => setCreateSunsetEvent(e.target.checked)}
          />
          ליצור אירוע (של רבע שעה) בזמן השקיעה בערב?
        </label>
        <p style={{fontSize: '12px', color: '#7f8c8d', marginTop: '5px'}}>
          * אירוע יומי (ללא שעות) ייווצר תמיד ביום למחרת כדי לא לחסום לך את היומן.
        </p>
      </div>

      <button
        className="submit-btn"
        onClick={handleDownload}
        disabled={loading || !title}
      >
        {loading ? 'מייצר קובץ ל-100 שנים...' : '⬇️ הורד קובץ יומן'}
      </button>
      {/* --- התוספת החדשה: קישור ל-GitHub --- */}
      <div className="github-link">
        <a href="https://github.com/hrsi56/Calculender" target="_blank" rel="noopener noreferrer">
          <svg height="20" width="20" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path>
          </svg>
          קוד פתוח ב-GitHub
        </a>
      </div>
    </div>
  );
}

export default App;