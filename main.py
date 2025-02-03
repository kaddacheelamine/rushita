from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import sqlite3
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins; you should restrict this in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Pydantic Models (same as before)
class Medicine(BaseModel):
    name: str
    dosage: str
    frequency: str
    note: str = ""


class PrescriptionData(BaseModel):
    patientName: str
    patientAge: str
    patientDescription: str
    currentDate: str
    medicines: List[Medicine]
    sendToValue: str = ""


# Database setup
DATABASE_NAME = "prescriptions.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access to rows
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patientName TEXT NOT NULL,
            patientAge TEXT NOT NULL,
            patientDescription TEXT NOT NULL,
            currentDate TEXT NOT NULL,
            sendToValue TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prescription_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            dosage TEXT NOT NULL,
            frequency TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (prescription_id) REFERENCES prescriptions(id)
        )
    """)
    conn.commit()
    conn.close()


create_tables()  # Create tables when the app starts


@app.get("/prescriptions/{prescription_id}")
async def get_prescription(prescription_id: int):  # changed to int
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prescriptions WHERE id = ?", (prescription_id,))
    prescription_row = cursor.fetchone()

    if not prescription_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Prescription not found")

    cursor.execute("SELECT * FROM medicines WHERE prescription_id = ?", (prescription_id,))
    medicines_rows = cursor.fetchall()

    medicines = [
        Medicine(
            name=row['name'],
            dosage=row['dosage'],
            frequency=row['frequency'],
            note=row['note']
        )
        for row in medicines_rows
    ]

    prescription = PrescriptionData(
        patientName=prescription_row['patientName'],
        patientAge=prescription_row['patientAge'],
        patientDescription=prescription_row['patientDescription'],
        currentDate=prescription_row['currentDate'],
        sendToValue=prescription_row['sendToValue'],
        medicines=medicines
    )
    conn.close()
    return prescription


@app.post("/prescriptions/{prescription_id}")
async def update_prescription(prescription_id: int, updated_prescription: PrescriptionData): # changed to int
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM prescriptions WHERE id = ?", (prescription_id,))
    existing_prescription = cursor.fetchone()
    if not existing_prescription:
         conn.close()
         raise HTTPException(status_code=404, detail="Prescription not found")


    cursor.execute("""
        UPDATE prescriptions SET patientName = ?, patientAge = ?, patientDescription = ?, 
        currentDate = ?, sendToValue = ? WHERE id = ?
    """, (
        updated_prescription.patientName,
        updated_prescription.patientAge,
        updated_prescription.patientDescription,
        updated_prescription.currentDate,
        updated_prescription.sendToValue,
        prescription_id
    ))


    cursor.execute("DELETE FROM medicines WHERE prescription_id = ?", (prescription_id,))

    for medicine in updated_prescription.medicines:
        cursor.execute("""
            INSERT INTO medicines (prescription_id, name, dosage, frequency, note) VALUES (?, ?, ?, ?, ?)
        """, (
            prescription_id,
            medicine.name,
            medicine.dosage,
            medicine.frequency,
            medicine.note
        ))

    conn.commit()
    conn.close()
    return {"message": "Prescription updated"}


@app.post("/store")
async def create_prescription(prescription: PrescriptionData):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO prescriptions (patientName, patientAge, patientDescription, currentDate, sendToValue) 
        VALUES (?, ?, ?, ?, ?)
    """, (
        prescription.patientName,
        prescription.patientAge,
        prescription.patientDescription,
        prescription.currentDate,
        prescription.sendToValue
    ))
    prescription_id = cursor.lastrowid


    for medicine in prescription.medicines:
        cursor.execute("""
            INSERT INTO medicines (prescription_id, name, dosage, frequency, note) VALUES (?, ?, ?, ?, ?)
        """, (
            prescription_id,
            medicine.name,
            medicine.dosage,
            medicine.frequency,
            medicine.note
        ))

    conn.commit()
    conn.close()
    return {"message": "Prescription created with ID: "+str(prescription_id)}
