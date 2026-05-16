import os
import json
from typing import List
from collections import deque
class Intern1:
    ### this block ensures that data entry is consistent even after closing and opening of program
    filename="interns.json"
    with open(filename,"r") as f:
        interns=json.load(f)
    intern_number=len(interns)
    interns=None
    ### Intern class starts from here ##############################
    def __init__(self,name: str="",role: str=""):
        self.name=name.strip().title()
        self.role=role.strip().title()
        self.intern_id=self.generate_id()
        self.status="Active"
        self.logged_hours:List[int]=[]
        self.logged_tasks:List[str]=[]
    @classmethod
    def generate_id(cls):
        cls.intern_number+=1
        return f"INT{cls.intern_number:03d}"
    def to_dict(self):
        return {"name":self.name,
                "role":self.role,
                "status":self.status,
                "hours":self.logged_hours,
                "task":self.logged_tasks}
    
    @classmethod
    def add_intern(cls):
        name=input("Enter intern name: ").strip()
        role=input("Enter inter role: ").strip()
        intern=cls(name,role) ## here all the things like intern_id,status,logged_hours,logged_tasks is all added
        # fist we load or json file to make changes
        # main problem with what we are doing write now is we are loading entire json file making changes it in 
    # and replacing entire original data(overwritten) in intern1.json file which is very unecessary because we just want to
        # add one new record so for large data this approach will be infeasible. Same is true for making any
        # changes in json file
        interns=cls.load_json()
        interns[intern.intern_id]=intern.to_dict()
        cls.save_json(interns)
    @classmethod
    def update_status(cls):
        intern_id=input("Enter intern id for status updates: ").strip().upper()
        interns=cls.load_json()
        if intern_id not in interns:
            raise ValueError("Intern id not present")
        intern=interns[intern_id]
        status=input("Enter intern status(Active/Inactive/Completed): ").strip().title()
        if status=="Active":
            intern["status"]="Active"
        elif status=="Inactive":
            intern["status"]="Inactive"
        elif status=="Completed":
            intern["status"]="Completed"
        else:
            raise ValueError("Invalid status entered")
        cls.save_json(interns)
    @classmethod
    def update_daily_log(cls):
        intern_id=input("Enter intern id for daily_log updates: ").strip().upper()
        interns=cls.load_json()
        if intern_id not in interns:
            raise ValueError("Intern id not present")
        intern=interns[intern_id]
        if intern["status"]!="Active":
            raise ValueError("Intern is not Active")
        hrs=int(input("Enter intern hrs: "))
        task=input("Enter intern task: ")
        intern["hours"].append(hrs)
        intern["task"].append(task)
        cls.save_json(interns)

    @classmethod
    def intern_summary(cls):
        intern_id=input("Enter intern id for Intern summary: ").strip().upper()
        interns=cls.load_json()
        if intern_id not in interns:
            raise ValueError("Intern id not present")
        intern=interns[intern_id]
        print(f"INTERN SUMMARY\n"f"Intern name: {intern["name"]}\n" f"Intern role {intern["role"]} \n" 
        f"Intern Total hrs: {sum(intern["hours"])} \n" f"Intern Average hrs: {sum(intern["hours"])/len(intern["hours"])}\n"
        f"Intern task history {intern["task"][:-1]}\n" f"Intern recent activity {intern["task"][-1]}")

    @classmethod
    def intern_stats(cls):
        interns=cls.load_json()
        print(f"Total number of interns: {len(interns)}\n")
        i=0
        for intern in interns.values():
            if intern["status"]=="Active":
                i+=1
        print(f"Total number of active interns: {i}\n")
        for intern_id,intern in interns.items():
            if intern["hours"]:
                print(f"Average working hrs for {intern_id}: {sum(intern["hours"])/len(intern["hours"])}")
            else:
                print(f"Intern {intern_id} has not yet logged in")
        total_hrs=0
        i=None
        for intern in interns.values():
            if total_hrs<sum(intern["hours"]):
                total_hrs=sum(intern["hours"])
                i=intern
        intern=i
        print(f"Top performer(w.r.t total_hrs) is\n")
        print(f"INTERN SUMMARY\n"f"Intern name: {intern["name"]}\n" f"Intern role {intern["role"]} \n")
    
    @classmethod
    def load_json(cls):
        if not os.path.exists(cls.filename):
            return {}
        else:
            with open(cls.filename,"r") as f:
                return json.load(f)
    @classmethod
    def save_json(cls,data):
        with open(cls.filename,"w") as f:
            json.dump(data,f,indent=4)
def main():
    while True:
        print("##### WELCOME TO INERN MANAGEMENT SYSTEM #####")
        print("1. To add Intern")
        print("2. To update Intern's Status")
        print("3. To update Intern's daily logs")
        print("4. To get Intern's summary")
        print("5. To get Intern's statistics")
        print("6. To Exit the menue")
        intern=Intern1()
        try:
            x=int(input("Enter your choice: "))
        except:
            raise ValueError("Please enter an Integer")
        if x==1:
            intern.add_intern()
        elif x==2:
            intern.update_status()
        elif x==3:
            intern.update_daily_log()
        elif x==4:
            intern.intern_summary()
        elif x==5:
            intern.intern_stats()
        elif x==6:
            break
        else:
            raise ValueError("Invalid choice. Please try again")
if __name__ == "__main__":
    main()