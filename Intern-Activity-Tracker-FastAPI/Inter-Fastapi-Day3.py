from fastapi import FastAPI,Path,HTTPException,Query
 #Path is useful to provide desciption about query parameters #HTTPException(for writing status code)Exception class # in fast api
import json 
from fastapi.responses import JSONResponse
from pydantic import BaseModel,Field
from typing import List,Annotated,Literal
import aiofiles
app=FastAPI()

class Intern3(BaseModel):
    name: Annotated[str, Field(..., description="Name of the intern")]
    role: Annotated[str, Field(..., description="Role of the intern")]
    hours: Annotated[
        List[Annotated[int,Field(ge=0)]],
        Field(default_factory=list, description="Daily log_hrs")
    ]
    tasks: Annotated[
        List[str],
        Field(default_factory=list, description="Daily log_task")
    ]
    status: Annotated[
        Literal["Active", "Inactive", "Completed"],
        Field("Active", description="Current status of the intern")
    ]

class ActivityUpdate(BaseModel):
    hrs: Annotated[int, Field(..., gt=0, description="Hours worked (must be positive)")]
    task: Annotated[str, Field(..., min_length=1, description="Task description")]
    

def generate_id(data):
        intern_number=len(data)+2
        return f"INT{intern_number:03d}"
async def load_data():
    async with aiofiles.open("interns.json",'r') as f:
        data=await f.read()
    return json.loads(data)
async def save_data(data):
    async with aiofiles.open("interns.json",'w') as f:
        await f.write(json.dumps(data,indent=4))


@app.get("/")
def hello():
    return {"message":"hello world"}


@app.get("/interns1")
async def view():
    data=await load_data()
    return data

# @app.post("/interns/{intern_id}/activity")
@app.post("/interns/{intern_id}/activity", status_code=201)
async def add_intern_activity(
    intern_id: str = Path(..., example="INT003"),
    activity: ActivityUpdate = ...
    ):
    interns = await load_data()
    intern_id = intern_id.strip().upper()
    if intern_id not in interns:
        raise HTTPException(status_code=404, detail="Intern not found")
    intern = interns[intern_id]
    if intern["status"] != "Active":
        raise HTTPException(status_code=403, detail="Intern not Active")
    intern["hours"].append(activity.hrs)
    intern["task"].append(activity.task)
    await save_data(interns)
    return {"message": "Activity added successfully"}


@app.get("/interns/{intern_id}")
async def get_intern(intern_id: str=Path(...,description="Inter ID as in json file",example="INT003")):
    intern_id=intern_id.strip().upper()
    interns=await load_data()
    if intern_id not in interns:
        raise HTTPException(status_code=404,detail="Intern not found")
    intern=interns[intern_id]
    total_hrs=sum(intern["hours"])
    if total_hrs>0:
        avg_hrs=total_hrs/len(intern["hours"])
    else:
        avg_hrs=0
    return {
        "Name of Intern":intern["name"],
        "Role of Intern":intern["role"],
        "Total Intern hours":total_hrs,
        "Average Intern hours":avg_hrs
    }

@app.get("/statistics")
async def get_summary():
    interns = await load_data()
    averages = []
    top_intern = None
    max_hours = -1
    for intern_id, intern in interns.items():
        total=sum(intern["hours"])
        avg=total/len(intern["hours"]) if intern["hours"] else 0
        averages.append({"intern_id": intern_id, "average_hours": avg})
        if total > max_hours:
            max_hours=total
            top_intern=intern
    return {
        "total_interns": len(interns),
        "averages": averages,
        "top_performer": {
            "name": top_intern["name"],
            "role": top_intern["role"],
            "total_hours": max_hours
        }
    }


@app.post("/interns")
async def add_intern(intern: Intern3 ,status_code=201):
    interns=await load_data()
    intern_id =generate_id(interns)
    interns[intern_id] = {
        "name": intern.name,
        "role": intern.role,
        "status": "Active",
        "hours": intern.hours,
        "tasks": intern.tasks
    }
    await save_data(interns)
    return JSONResponse(status_code=201,content={"message":f"Intern with intern id {intern_id} saved succesfully"})

    
