# --- שלב 1: בניית אפליקציית הריאקט ---
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY my-heb-calendar/package*.json ./
RUN npm install
COPY my-heb-calendar/ ./
RUN npm run build

# --- שלב 2: הרמת שרת הפייתון והגשת הקבצים ---
FROM python:3.11-slim
WORKDIR /app

# התקנת הספריות של פייתון
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# העתקת קוד השרת
COPY backend/ ./backend/

# לקיחת קבצי הריאקט המוכנים משלב 1, ושמירתם בתיקיית static
COPY --from=frontend-builder /app/frontend/dist ./static

# חשיפת הפורט
EXPOSE 10000

# הפעלת השרת
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "10000"]