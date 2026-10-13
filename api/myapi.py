import csv
import os

from fastapi import FastAPI, Path, Query
from typing import List, Optional
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# End points
# GET = GET AN INFORMATION
# POST = CREATE SOMETHING NEW 
# PUT = UPDATE 
# DELETE = DELETE SOMETHING

CSV_PATH = os.path.join(os.path.dirname(__file__), "q-fastapi.csv")

with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
    students = [
        {"studentId": int(row["studentId"]), "class": row["class"]}
        for row in csv.DictReader(f)
    ]
    
students1 = [{'studentId': 1,'name':'tom','age':6, 'class': '6X'},
            {'studentId': 2,'name':'tim','age':6, 'class': '10D'},
            {'studentId': 3,'name':'rose','age':7, 'class': '8A'},
            {'studentId': 4,'name':'ram','age':8, 'class': '8C'}
            ]

students2 = { 
            1:{'name':'tom','age':6, 'class': '6X'},
            2:{'name':'tim','age':6, 'class': '10D'},
            3:{'studentId': 3,'name':'rose','age':7, 'class': '8A'},
            4:{'studentId': 4,'name':'ram','age':8, 'class': '8C'}
            }

# for student in students1:
#     print(student)

# for student_id, student in students2.items():
#     if students2[student_id]["name"]=="tom":
#         print(student_id, student["name"]) 
        
# for student_id, student in students2.items():
#     if student["name"]=="tom":
#         print(student_id,student)


# @app.get("/")
# def index():
#     return {"name": "first data"}

# @app.get("/get_student/{student_id}")
# def get_student(student_id: int = Path(..., description="The id of the student you want to view", gt=0, lt=3)):
#     return students[student_id]

@app.get("/api")
def get_students_by_class(class_: Optional[List[str]] = Query(None, alias="class")):
    if not class_:
        return {"students": students}
    return {"students": [s for s in students if s["class"] in class_]}

# @app.get("/get_by_name")
# def get_student(*, name: Optional[str] = None, age: int = None):
#     for student_id in students:
#         if students[student_id]["name"]==name and students[student_id]["age"]==age:
#             return students[student_id]
#     return {"Data not found"}


# @app.get("/get_by_name")
# def get_student_by_name(*, name: Optional[str] = None, age: Optional[int] = None):
#     matches = []
#     for student in students1:
#         if student["name"] == name and student["age"] == age:
#             matches.append(student)
#             return student
#     return {"message": "Data not found"}


# #combine query parameter alongside path parameter


# @app.get("/get_by_name/{student_id}")
# def name_search(*, student_id: int, name: Optional[str] = None, age: Optional[int] = None):
#     matches = []
#     for student in students1:
#         if student["studentId"] == student_id or student["name"] == name or student["age"] == age:
#             matches.append(student)      # just collect, don't return yet
#     if matches:                          # after the loop has checked everyone
#         return matches
#     return {"message": "Data Not found"}

