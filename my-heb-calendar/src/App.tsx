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
  create_sunset_event: boolean; // <--- חדש
}

const HEBREW_MONTHS = [
  { value: 7, name: 'תשרי' },
  { value: 8, name: 'חשוון' },
  { value: 9, name: 'כסלו' },
  { value: 10, name: 'טבת' },
  { value: 11, name: 'שבט' },
  { value: 12, name: 'אדר (או אדר א\')' },
  { value: 13, name: 'אדר ב\'' },
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
  const [hebMonth, setHebMonth] = useState<string>('6');
  const [location, setLocation] = useState<string>('Israel');
  const [title, setTitle] = useState<string>('');

  // <--- חדש: State עבור תיבת הסימון
  const [createSunsetEvent, setCreateSunsetEvent] = useState<boolean>(true);

  const [loading, setLoading] = useState<boolean>(false);

  const handleDownload = async () => {
    setLoading(true);
    const API_URL = "http://localhost:8000/api/generate-ics";

    const payload: EventPayload = {
      is_hebrew: isHebrew,
      greg_year: null, greg_month: null, greg_day: null,
      heb_month: null, heb_day: null,
      after_sunset: afterSunset,
      location, title,
      create_sunset_event: createSunsetEvent // <--- חדש: שולחים לשרת
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

      {/* אלמנט 1: בחר תאריך מקור (נשאר ללא שינוי) */}
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

      {/* אלמנט 2: מיקום גיאוגרפי (נשאר ללא שינוי) */}
      <div className="form-group">
        <h3>2. מיקום לחישוב זמני שקיעה</h3>
        <select value={location} onChange={(e) => setLocation(e.target.value)}>
          <option value="Israel">ישראל (ירושלים / תל אביב)</option>
          <option value="New York">ניו יורק, ארה"ב</option>
          <option value="London">לונדון, אנגליה</option>
        </select>
      </div>

      {/* אלמנט 3: כותרת האירוע (נשאר ללא שינוי) */}
      <div className="form-group">
        <h3>3. כותרת האירוע ביומן</h3>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="לדוגמה: יום הולדת עברי לירדן"
        />
      </div>

      {/* --- חדש: אלמנט 4 - הגדרות נוספות --- */}
      <div className="form-group">
        <h3>4. אפשרויות תצוגה</h3>
        <label className="checkbox-label" style={{ fontWeight: 'bold' }}>
          <input
            type="checkbox"
            checked={createSunsetEvent}
            onChange={e => setCreateSunsetEvent(e.target.checked)}
          />
          ליצור אירוע (של רבע שעה) בזמן השקיעה בערב (שעת השקיעה תחושב אוטומטית)?
        </label>
        <p style={{fontSize: '12px', color: '#7f8c8d', marginTop: '5px'}}>
          * אירוע יומי (ללא שעות) ייווצר תמיד ביום למחרת כדי לא לחסום לך את היומן.
        </p>
      </div>

      {/* כפתור הורדה */}
      <button
        className="submit-btn"
        onClick={handleDownload}
        disabled={loading || !title}
      >
        {loading ? 'מייצר קובץ ל-100 שנים...' : '⬇️ הורד קובץ יומן'}
      </button>
    </div>
  );
}

export default App;